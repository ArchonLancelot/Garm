"""Garm MCP server: dossier tools for any MCP-capable agent.

Thin adapter over the ``garm`` package — validation, indexing, recall
scoring, and the premise registry all live there. This module only
translates MCP tool calls into garm function calls and returns
JSON-serializable results.

Requires the ``mcp`` package (the one non-stdlib part of this repo):
    pip install mcp

Run from the repo root:
    python -m mcp_server --dir /path/to/dossiers

Bank directory resolution per call: explicit ``dir`` argument, else the
GARM_DIR environment variable, else ./dossiers.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from garm import autopsy as AU
from garm import dossier as D
from garm import premise as PR
from garm import retrieval as RU
from garm import semantic as SEM

server = MCPServer("garm")


def _ann(read_only: bool, destructive: bool = False,
         idempotent: bool = False, open_world: bool = False
         ) -> ToolAnnotations:
    """MCP tool annotations, set from actual behavior (v0.2.7).

    readOnlyHint: the tool changes nothing. destructiveHint: it deletes or
    destroys data (none of Garm's tools do — kills are reversible via
    reopen). idempotentHint: repeating the call is a safe no-op.
    openWorldHint: it touches the network (none do — local files only).
    """
    return ToolAnnotations(
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=open_world,
    )


def _bank(d: str | None) -> Path:
    return Path(d or os.environ.get("GARM_DIR", "dossiers"))


def _require_bank(d: str | None) -> Path:
    base = _bank(d)
    if not base.is_dir():
        raise ValueError(f"dossier directory not found: {base}")
    return base


def recall_impl(task: str, top: int = 3,
                failure_class: str | None = None,
                include_dead: bool = False,
                semantic: bool = False,
                dir: str | None = None) -> str:
    """Rank failure dossiers for a task description.

    Dead routes (dossiers resting on a killed premise) are excluded unless
    ``include_dead`` is true; then they are returned marked premise_dead.
    v0.2.7: BM25 term weighting — Unicode math symbols are canonicalized
    and query terms expand through a curated synonym map (still lexical,
    no embeddings). ``matched_terms`` shows alias matches as
    ``query~dossier-term``. v0.2.9: ``semantic=true`` opts into the Tier 2
    meaning lane — embedding cosine similarity leading the ranking
    (needs the fastembed package and one ``garm semantic warmup`` run;
    hard error otherwise, never silent fallback). Returns a JSON array
    (as text) of ranked dossier objects.
    """
    base = _require_bank(dir)
    if (failure_class is not None
            and failure_class not in D.VALID_FAILURE_CLASSES):
        raise ValueError(
            f"failure_class must be one of {D.VALID_FAILURE_CLASSES}"
        )
    query_keys = D.extract_keywords(task)
    try:
        registry = PR.load_registry(base)
    except ValueError as exc:
        raise ValueError(str(exc))
    scored: list[dict] = []
    live: list[dict] = []
    for md in sorted(base.rglob("*.md")):
        if D.validate_dossier(md):
            continue
        entry = D.build_index_entry(md, base, registry)
        if failure_class and entry.get("failure_class") != failure_class:
            continue
        if entry.get("premise_dead") and not include_dead:
            continue
        live.append(entry)
    # BM25 needs whole-corpus document frequencies: score in one pass.
    ranks: dict[str, tuple[int, int]] = {}
    if semantic:
        sem_backend = SEM.SemanticIndex(base)
        sem_backend.ensure_ready()  # hard error, never silent fallback
        scores, ranks = RU.score_corpus(
            query_keys, live, semantic=sem_backend,
            query_text=task, return_ranks=True)
    else:
        scores = RU.score_corpus(query_keys, live)
    for entry in live:
        total, sig_n, task_n, body_n, sem_n, _fix_b, _ins_b = scores[
            entry["id"]]
        rb, rs = ranks.get(entry["id"], (0, 0))
        scored.append({
            "id": entry["id"],
            "task": entry["task"],
            "score": total,
            "signature": entry["signature"],
            "matched_terms": RU.matched_terms(query_keys, entry),
            "signature_matches": sig_n,
            "task_matches": task_n,
            "body_matches": body_n,
            "semantic_score": sem_n,
            "semantic_lane_first": bool(semantic and rs < rb),
            "confirmed_fixes": entry["confirmed_fixes"],
            "confirmed_insights": entry["confirmed_insights"],
            "failure_class": entry["failure_class"],
            "origin": entry["origin"],
            "path": entry["path"],
            "premises": entry.get("premises", []),
            "premise_dead": bool(entry.get("premise_dead")),
        })
    scored.sort(key=lambda s: (-s["score"],
                               -(s["confirmed_fixes"]
                                 + s["confirmed_insights"]),
                               s["id"]))
    return json.dumps(scored[:max(1, top)], indent=2)


def init_impl(task: str, agent: str, failure_class: str,
              outcome: str = "failed",
              dir: str | None = None) -> dict:
    """Scaffold a new dossier file in the bank."""
    base = _bank(dir)
    try:
        path = D.init_dossier(task=task, agent=agent,
                              failure_class=failure_class,
                              outcome=outcome, out_dir=base)
    except ValueError as exc:
        raise ValueError(str(exc))
    return {
        "path": str(path),
        "id": path.stem,
        "note": ("Scaffold written. Fill every section honestly, then call "
                 "garm_validate — validation rejects untouched placeholder "
                 "text. Optional sections you don't need can be deleted."),
    }


def validate_impl(path: str) -> dict:
    """Validate a dossier file. Returns {"valid", "errors"}."""
    errors = D.validate_dossier(path)
    return {"path": path, "valid": not errors, "errors": errors}


def confirm_impl(id: str, insight: bool = False,
                 dir: str | None = None,
                 note: str | None = None) -> dict:
    """Confirm a dossier: bump confirmed_fixes (or insights) and re-index.

    note is optional: a one-line description of what the fix was (max 140
    chars), stored on the dossier so the track record is auditable.
    """
    base = _require_bank(dir)
    field = "confirmed_insights" if insight else "confirmed_fixes"
    try:
        path, new_count = D.confirm_dossier(base, id, field=field, note=note)
    except ValueError as exc:
        raise ValueError(str(exc))
    n, skipped = D.rebuild_index(base)
    return {"id": id, "field": field, "new_count": new_count,
            "indexed": n, "skipped_invalid": skipped, "path": str(path)}


def list_impl(dir: str | None = None) -> str:
    """List all valid dossiers in the bank.

    Returns a JSON array (as text) of dossier summary objects.
    """
    base = _require_bank(dir)
    rows: list[dict] = []
    for md in sorted(base.rglob("*.md")):
        if D.validate_dossier(md):
            continue
        fm = D.read_dossier(md)["frontmatter"]
        rows.append({
            "id": fm["id"],
            "task": fm["task"],
            "failure_class": fm.get("failure_class") or None,
            "confirmed_fixes": D._confirmed_fixes_of(fm),
            "confirmed_insights": D._confirmed_insights_of(fm),
            "origin": D._origin_of(fm),
            "outcome": fm["outcome"],
        })
    rows.sort(key=lambda r: r["id"])
    return json.dumps(rows, indent=2)


def premise_add_impl(statement: str, depends_on: list[str] | None = None,
                     dir: str | None = None) -> dict:
    """Register a load-bearing premise the bank's approaches rest on.

    depends_on names parent premise ids it assumes hold (the big routes
    it rests on). Returns the new premise id.
    """
    base = _bank(dir)
    base.mkdir(parents=True, exist_ok=True)
    try:
        pid = PR.add_premise(base, statement, depends_on=depends_on)
    except ValueError as exc:
        raise ValueError(str(exc))
    return {"id": pid, "statement": statement,
            "depends_on": depends_on or []}


def premise_kill_impl(id: str, by: str, dir: str | None = None,
                      evidence: str | None = None) -> dict:
    """Kill a premise: everything resting on it (transitively) dies.

    evidence is how strong the evidence was: "proof", "our-tests", or
    "outside-work" (optional). Rebuilds the index so dead routes are
    marked. Returns the premise ids closed and whether it was already
    killed.
    """
    base = _require_bank(dir)
    try:
        result = PR.kill_premise(base, id, by, evidence=evidence)
    except ValueError as exc:
        raise ValueError(str(exc))
    n, skipped = D.rebuild_index(base)
    return {"killed": result["killed"],
            "already_killed": result["already_killed"],
            "indexed": n, "skipped_invalid": skipped}


def premise_reopen_impl(id: str, by: str, dir: str | None = None) -> dict:
    """Reopen a killed premise: it and its inherited kills come back.

    Only premises that died solely because of this kill (marked
    "inherited from <id>") are revived; independently killed premises
    stay dead. Rebuilds the index so revived routes return to recall.
    Returns the premise ids reopened and whether it was already open.
    """
    base = _require_bank(dir)
    try:
        result = PR.reopen_premise(base, id, by)
    except ValueError as exc:
        raise ValueError(str(exc))
    n, skipped = D.rebuild_index(base)
    return {"reopened": result["reopened"],
            "already_open": result["already_open"],
            "indexed": n, "skipped_invalid": skipped}


def premise_list_impl(dir: str | None = None) -> str:
    """List registered premises as a JSON array: id, statement, deps,
    status, killer, and computed dead flag."""
    base = _require_bank(dir)
    return json.dumps(PR.list_premises(base), indent=2)


def autopsy_impl(task: str, agent: str, failure_class: str,
                 outcome: str = "failed",
                 answers: dict | None = None,
                 dir: str | None = None) -> dict:
    """Assisted autopsy drafting: turn answers into a dossier draft.

    ``answers`` maps answer keys to text (lists of strings allowed for
    what_was_tried and premises): root_cause, failure_signature,
    blocking_constraint, what_was_tried, challengeable_premises,
    what_retrieval_would_have_changed, open_questions, tokens, premises,
    confidence. Sections left out stay as guidance; a draft with empty
    required sections is still written but reported invalid with the
    sections named. Nothing is invented — answers go in verbatim.
    """
    base = _bank(dir)
    raw = {"task": task, "agent": agent, "failure_class": failure_class,
           "outcome": outcome, **(answers or {})}
    try:
        raw = AU.validate_raw_answers(raw)
    except ValueError as exc:
        raise ValueError(str(exc))
    frontmatter, sections = AU.normalize_answers(raw)
    premises_text = sections.get("premises", "")
    warnings = AU._check_premise_refs(premises_text, base)
    path, _text = AU.write_draft(
        task=frontmatter["task"], agent=frontmatter["agent"],
        outcome=frontmatter["outcome"],
        failure_class=frontmatter["failure_class"],
        sections=sections, out_dir=base,
    )
    errors = D.validate_dossier(path)
    indexed = 0
    skipped = 0
    if not errors:
        indexed, skipped = D.rebuild_index(base)
    return {
        "path": str(path),
        "id": path.stem,
        "valid": not errors,
        "errors": errors,
        "indexed": indexed,
        "skipped_invalid": skipped,
        "warnings": warnings,
    }


server.tool(
    name="garm_recall",
    description=(
        "Rank past failure dossiers for a task description. BM25 lexical "
        "scoring (signature-term matches count double, "
        "task-term matches single, confirmed dossiers gain "
        "up to +5 each). v0.2.7: terms weighted by rarity, math symbols are "
        "canonicalized to words and query terms expand through a curated "
        "synonym map, so paraphrases match. v0.2.9: set semantic=true for "
        "the opt-in Tier 2 meaning lane — embedding cosine similarity "
        "leading the ranking (needs the fastembed "
        "package and one `garm semantic warmup` run; hard error otherwise). "
        "Returns a JSON array of ranked dossiers with scores, signatures, "
        "matched terms (alias matches shown as query~dossier-term), and "
        "confirm counts."
    ),
    annotations=_ann(read_only=True, idempotent=True),
)(recall_impl)

server.tool(
    name="garm_init",
    description=(
        "Scaffold a new failure dossier in the bank and return its path. "
        "Then fill every section with the real autopsy — the scaffold is "
        "NOT a dossier — and call garm_validate before garm_confirm. "
        "failure_class must be one of: knowledge-gap, reasoning-error, "
        "execution-slip, tool-misuse, misread-task."
    ),
    annotations=_ann(read_only=False, idempotent=False),
)(init_impl)

server.tool(
    name="garm_validate",
    description=(
        "Validate a dossier file. Returns valid=true/false plus a list of "
        "errors. Rejects dossiers that are missing required sections or "
        "still contain untouched template placeholder text."
    ),
    annotations=_ann(read_only=True, idempotent=True),
)(validate_impl)

server.tool(
    name="garm_confirm",
    description=(
        "Confirm a dossier by id: bump its confirmed_fixes counter and "
        "rebuild the index. Use insight=true instead when the dossier's "
        "analysis generated a genuinely new idea in open-ended work with "
        "no verifiable fix. note is optional: a one-line description of "
        "what the fix was (max 140 chars), stored on the dossier so the "
        "track record is auditable."
    ),
    annotations=_ann(read_only=False, idempotent=False),
)(confirm_impl)

server.tool(
    name="garm_list",
    description=(
        "List all valid dossiers in the bank as a JSON array: id, task, "
        "failure class, confirm counts, origin, and outcome."
    ),
    annotations=_ann(read_only=True, idempotent=True),
)(list_impl)

server.tool(
    name="garm_premise_add",
    description=(
        "Register a load-bearing premise: a claim a whole family of "
        "approaches assumes (e.g. 'C7[K4] is biplanar'). depends_on names "
        "the big routes it rests on. Dossiers declare "
        "their premises in an optional ## Premises section. Returns the "
        "new premise id."
    ),
    annotations=_ann(read_only=False, idempotent=False),
)(premise_add_impl)

server.tool(
    name="garm_premise_kill",
    description=(
        "Close the big route: mark a premise false. The premise and every premise "
        "under it dies transitively; the index is rebuilt and recall "
        "stops suggesting the dead routes. by names the dossier (or note) "
        "that killed it; a by shaped like a dossier id must match a dossier "
        "in the bank. evidence is optional: proof, our-tests, or "
        "outside-work. One closed big route closes a whole family of "
        "approaches."
    ),
    annotations=_ann(read_only=False, idempotent=True),
)(premise_kill_impl)

server.tool(
    name="garm_premise_reopen",
    description=(
        "Reopen a killed premise: it goes back to open, along with every "
        "premise that died only because of its kill. Premises killed "
        "independently stay dead. The index is rebuilt and recall suggests "
        "the revived routes again. by names who is reopening it."
    ),
    annotations=_ann(read_only=False, idempotent=True),
)(premise_reopen_impl)

server.tool(
    name="garm_premise_list",
    description=(
        "List registered premises as a JSON array: id, statement, "
        "depends_on, status, killed_by, reopened_by, and the computed dead flag "
        "(true when killed directly or via a killed ancestor)."
    ),
    annotations=_ann(read_only=True, idempotent=True),
)(premise_list_impl)

server.tool(
    name="garm_autopsy",
    description=(
        "Assisted autopsy drafting: turn interview answers into a "
        "pre-filled dossier draft, closing-ceremony style. answers maps "
        "answer keys to text: root_cause, failure_signature, "
        "blocking_constraint, what_was_tried (string or list), "
        "challengeable_premises, what_retrieval_would_have_changed, "
        "open_questions, tokens, premises (string or list of premise "
        "ids), confidence. Unanswered sections stay as guidance; a draft "
        "with empty required sections is written but reported invalid "
        "with the missing sections named. Nothing is invented — answers "
        "go in verbatim."
    ),
    annotations=_ann(read_only=False, idempotent=False),
)(autopsy_impl)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="garm-mcp",
        description="Garm MCP server: dossier tools over stdio.",
    )
    ap.add_argument("--dir", default=None,
                    help="default dossier bank directory "
                         "(overrides GARM_DIR; a per-call dir argument "
                         "overrides this)")
    args = ap.parse_args(argv)
    if args.dir:
        os.environ["GARM_DIR"] = args.dir
    server.run()


if __name__ == "__main__":
    main()
