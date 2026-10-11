"""Garm MCP server: dossier tools for any MCP-capable agent.

Thin adapter over the ``garm`` package — validation, indexing, and recall
scoring all live there. This module only translates MCP tool calls into
garm function calls and returns JSON-serializable results.

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

from garm import dossier as D
from garm.cli import recall_score

server = MCPServer("garm")


def _bank(d: str | None) -> Path:
    return Path(d or os.environ.get("GARM_DIR", "dossiers"))


def _require_bank(d: str | None) -> Path:
    base = _bank(d)
    if not base.is_dir():
        raise ValueError(f"dossier directory not found: {base}")
    return base


def recall_impl(task: str, top: int = 3,
                failure_class: str | None = None,
                dir: str | None = None) -> str:
    """Rank failure dossiers for a task description.

    Returns a JSON array (as text) of ranked dossier objects.
    """
    base = _require_bank(dir)
    if (failure_class is not None
            and failure_class not in D.VALID_FAILURE_CLASSES):
        raise ValueError(
            f"failure_class must be one of {D.VALID_FAILURE_CLASSES}"
        )
    query_keys = D.extract_keywords(task)
    scored: list[dict] = []
    for md in sorted(base.rglob("*.md")):
        if D.validate_dossier(md):
            continue
        entry = D.build_index_entry(md, base)
        if failure_class and entry.get("failure_class") != failure_class:
            continue
        total, sig_n, task_n, _fix_b, _ins_b = recall_score(query_keys, entry)
        scored.append({
            "id": entry["id"],
            "task": entry["task"],
            "score": total,
            "signature": entry["signature"],
            "matched_terms": [k for k in query_keys
                              if k in entry["keywords"]],
            "signature_matches": sig_n,
            "task_matches": task_n,
            "confirmed_fixes": entry["confirmed_fixes"],
            "confirmed_insights": entry["confirmed_insights"],
            "failure_class": entry["failure_class"],
            "origin": entry["origin"],
            "path": entry["path"],
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
                 dir: str | None = None) -> dict:
    """Confirm a dossier: bump confirmed_fixes (or insights) and re-index."""
    base = _require_bank(dir)
    field = "confirmed_insights" if insight else "confirmed_fixes"
    try:
        path, new_count = D.confirm_dossier(base, id, field=field)
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


server.tool(
    name="garm_recall",
    description=(
        "Rank past failure dossiers for a task description. LEXICAL "
        "scoring (keyword overlap, NOT semantic): signature-term matches "
        "count double, task-term matches single, confirmed dossiers gain "
        "up to +5 each. Returns a JSON array of ranked dossiers with "
        "scores, signatures, matched terms, and confirm counts."
    ),
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
)(init_impl)

server.tool(
    name="garm_validate",
    description=(
        "Validate a dossier file. Returns valid=true/false plus a list of "
        "errors. Rejects dossiers that are missing required sections or "
        "still contain untouched template placeholder text."
    ),
)(validate_impl)

server.tool(
    name="garm_confirm",
    description=(
        "Confirm a dossier by id: bump its confirmed_fixes counter and "
        "rebuild the index. Use insight=true instead when the dossier's "
        "analysis generated a genuinely new idea in open-ended work with "
        "no verifiable fix."
    ),
)(confirm_impl)

server.tool(
    name="garm_list",
    description=(
        "List all valid dossiers in the bank as a JSON array: id, task, "
        "failure class, confirm counts, origin, and outcome."
    ),
)(list_impl)


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
