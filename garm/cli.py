"""Command-line interface for Garm, the failure-memory framework. Stdlib only.

v0.2: ``init`` takes a failure class, ``confirm`` records dossiers that
earned their keep, and ``recall`` ranks by weighted overlap (signature
terms count double) plus a small boost for confirmed dossiers.
v0.2.1: ``confirm --insight`` records dossiers whose analysis generated a
new approach — the signal for open-ended work with no verifiable "fix".
v1.1: ``import``/``export`` share dossier banks between agents; ``origin``
tracks provenance.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import dossier as D
from . import premise as PR

# Recall scoring: signature-term overlap counts double (the signature is the
# retrieval key), task-term overlap counts single, and each confirmed fix
# or confirmed insight adds 1 point up to a cap of 5 each, so one veteran
# dossier can't swamp new ones.
CONFIRMED_BOOST_CAP = 5


def recall_score(query_keys: list[str], entry: dict) -> tuple[int, int, int, int, int]:
    """Return (total, sig_overlap, task_overlap, fix_boost, insight_boost)."""
    sig_keys = entry.get("sig_keywords") or []
    task_keys = [k for k in entry.get("keywords", []) if k not in sig_keys]
    sig_overlap = sum(1 for k in query_keys if k in sig_keys)
    task_overlap = sum(1 for k in query_keys if k in task_keys)
    fix_boost = min(int(entry.get("confirmed_fixes", 0) or 0), CONFIRMED_BOOST_CAP)
    insight_boost = min(int(entry.get("confirmed_insights", 0) or 0), CONFIRMED_BOOST_CAP)
    total = 2 * sig_overlap + task_overlap + fix_boost + insight_boost
    return total, sig_overlap, task_overlap, fix_boost, insight_boost


def cmd_premise_add(args: argparse.Namespace) -> int:
    """Register a load-bearing claim the bank's approaches rest on."""
    base = Path(args.dir)
    base.mkdir(parents=True, exist_ok=True)
    deps = [d.strip() for d in (args.depends_on or "").split(",") if d.strip()]
    try:
        pid = PR.add_premise(base, args.statement, depends_on=deps)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"registered: {pid}")
    if deps:
        print(f"  depends on: {', '.join(deps)}")
    print(f"  {args.statement.strip()}")
    return 0


def cmd_premise_kill(args: argparse.Namespace) -> int:
    """Kill a premise: every approach resting on it (transitively) dies."""
    base = Path(args.dir)
    if not base.is_dir():
        print(f"error: directory not found: {base}", file=sys.stderr)
        return 1
    try:
        result = PR.kill_premise(base, args.id, args.by,
                                 evidence=args.evidence)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if result["already_killed"]:
        print(f"already killed: {args.id}")
        return 0
    killed = result["killed"]
    ev = f" [evidence: {args.evidence}]" if args.evidence else ""
    print(f"killed: {args.id} (by {args.by}){ev}")
    for pid in killed:
        if pid != args.id:
            print(f"  inherited kill: {pid}")
    print(f"closed {len(killed)} premise(s) — re-indexing to mark dead routes")
    n, skipped = D.rebuild_index(base)
    print(f"indexed {n} dossiers -> {base / 'index.jsonl'}"
          + (f" ({skipped} invalid skipped)" if skipped else ""))
    return 0


def cmd_premise_list(args: argparse.Namespace) -> int:
    base = Path(args.dir)
    rows = PR.list_premises(base)
    if not rows:
        print(f"no premises registered in {base}")
        return 0
    print(f"{'ID':16} {'STATUS':7} {'DEPS':22} STATEMENT")
    for row in rows:
        status = "KILLED" if row["dead"] else "open"
        deps = ",".join(row["depends_on"]) if row["depends_on"] else "-"
        killed_by = f" (by {row['killed_by']})" if row["killed_by"] else ""
        ev = f" [evidence: {row['evidence']}]" if row["evidence"] else ""
        stmt = row["statement"]
        stmt = stmt if len(stmt) <= 60 else stmt[:57] + "..."
        print(f"{row['id']:16} {status:7} {deps[:22]:22} {stmt}{killed_by}{ev}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    path = D.init_dossier(
        task=args.task, agent=args.agent, outcome=args.outcome,
        failure_class=args.failure_class, out_dir=args.out_dir,
    )
    print(str(path))
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    """Record that dossier <id> earned its keep in a later run.

    Default: the dossier prevented a specific repeat / fixed a verifiable
    failure (increments confirmed_fixes). With --insight: the dossier's
    analysis generated a new approach — its blocking constraint, inverted,
    became the next idea (increments confirmed_insights). Use --insight for
    open-ended work where there is no verifiable "fix" to count.
    """
    field = "confirmed_insights" if args.insight else "confirmed_fixes"
    try:
        path, new_count = D.confirm_dossier(args.dir, args.id, field=field)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    label = "confirmed insights" if args.insight else "confirmed fixes"
    print(f"confirmed: {args.id} ({label}: {new_count}) [{path}]")
    base = Path(args.dir)
    n, skipped = D.rebuild_index(base)
    print(f"indexed {n} dossiers -> {base / 'index.jsonl'}"
          + (f" ({skipped} invalid skipped)" if skipped else ""))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    errors = D.validate_dossier(args.file)
    if errors:
        print(f"INVALID: {args.file}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"OK: {args.file}")
    try:
        fm = D.read_dossier(args.file)["frontmatter"]
    except ValueError:
        return 0  # validated above; unreachable
    if fm.get("dossier_version") == "0.1":
        print("note: legacy v0.1 dossier (no failure_class); "
              "still usable, ranks without class filtering", file=sys.stderr)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    base = Path(args.dir)
    if not base.is_dir():
        print(f"error: directory not found: {base}", file=sys.stderr)
        return 1
    n, skipped = D.rebuild_index(base)
    print(f"indexed {n} dossiers -> {base / 'index.jsonl'}"
          + (f" ({skipped} invalid skipped)" if skipped else ""))
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """Import dossiers from another bank. Shared negative results are the
    network effect: your bank learns from other agents' failures."""
    base = Path(args.dir)
    try:
        result = D.import_dossiers(args.source, base)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for old_id, new_id, _ in result["imported"]:
        if old_id == new_id:
            print(f"imported: {new_id}")
        else:
            print(f"imported: {old_id} -> {new_id} (id collision, renamed)")
    for name, reason in result["skipped"]:
        print(f"skipped: {name} ({reason})", file=sys.stderr)
    premises = result.get("premises", {}) or {}
    for pid in premises.get("added", []):
        print(f"premise imported: {pid}")
    for pid, reason in premises.get("skipped", []):
        print(f"premise skipped: {pid} ({reason})", file=sys.stderr)
    n, _ = D.rebuild_index(base)
    print(f"indexed {n} dossiers -> {base / 'index.jsonl'}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Copy validated dossiers (not the derived index) to a directory for
    sharing. The format is already portable; this is just hygiene."""
    try:
        result = D.export_bank(args.dir, args.out)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for name, reason in result["skipped"]:
        print(f"skipped: {name} ({reason})", file=sys.stderr)
    print(f"exported {len(result['copied'])} dossiers -> {args.out}")
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    base = Path(args.dir)
    if not base.is_dir():
        print(f"error: directory not found: {base}", file=sys.stderr)
        return 1
    query_keys = D.extract_keywords(args.task)
    try:
        registry = PR.load_registry(base)
    except ValueError as exc:
        print(f"warning: {exc}", file=sys.stderr)
        registry = {"premises": {}}
    scored = []
    dead = []
    for md in sorted(base.rglob("*.md")):
        if D.validate_dossier(md):
            continue
        entry = D.build_index_entry(md, base, registry)
        if args.failure_class and entry.get("failure_class") != args.failure_class:
            continue
        if entry.get("premise_dead") and not args.include_dead:
            dead.append(entry)
            continue
        total, sig_n, task_n, fix_b, ins_b = recall_score(query_keys, entry)
        overlap = [k for k in query_keys if k in entry["keywords"]]
        scored.append((total, sig_n, task_n, fix_b, ins_b, overlap, entry))
    if dead:
        print(f"dead routes (premise killed), skipped: {len(dead)}")
        for entry in dead:
            dead_p = PR.dossier_dead_premises(
                registry, entry.get("premises", []))
            shown = ", ".join(dead_p[:2]) + ("…" if len(dead_p) > 2 else "")
            print(f"  - {entry['id']} | {entry['task']} "
                  f"(premise {shown} dead)")
        if not scored:
            print("no live dossiers for this task")
            return 1
        print()
    if not scored:
        print(f"no dossiers found in {base}")
        return 1
    scored.sort(key=lambda s: (-s[0], -(s[3] + s[4]), s[6]["id"]))
    top = max(1, args.top)
    for total, sig_n, task_n, fix_b, ins_b, overlap, entry in scored[:top]:
        matched = ",".join(overlap) if overlap else "-"
        fixes = entry.get("confirmed_fixes", 0)
        insights = entry.get("confirmed_insights", 0)
        origin = entry.get("origin") or "?"
        dead_mark = " [premise-dead]" if entry.get("premise_dead") else ""
        print(f"{total:3d} | {entry['id']} | {entry['task']} "
              f"[{entry['path']}] (from:{origin} sig:{sig_n} task:{task_n} "
              f"fix:{fixes} insight:{insights} matched: {matched}){dead_mark}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    base = Path(args.dir)
    if not base.is_dir():
        print(f"error: directory not found: {base}", file=sys.stderr)
        return 1
    rows = []
    for md in sorted(base.rglob("*.md")):
        if D.validate_dossier(md):
            continue
        fm = D.read_dossier(md)["frontmatter"]  # validated above; cannot fail
        rows.append((
            fm["id"],
            D._origin_of(fm),
            fm.get("failure_class") or "-",
            D._confirmed_fixes_of(fm),
            D._confirmed_insights_of(fm),
            fm["outcome"],
            fm["task"],
        ))
    if not rows:
        print(f"no dossiers found in {base}")
        return 0
    rows.sort(key=lambda r: r[0])
    print(f"{'ID':40} {'ORIGIN':18} {'CLASS':15} {'FIX':4} {'INS':4} "
          f"{'OUTCOME':9} TASK")
    for dossier_id, origin, failure_class, fixes, insights, outcome, task in rows:
        task_short = task if len(task) <= 40 else task[:37] + "..."
        print(f"{dossier_id[:40]:40} {origin[:18]:18} "
              f"{failure_class[:15]:15} {fixes:<4} {insights:<4} "
              f"{outcome:9} {task_short}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garm",
        description=(
            f"Garm failure-memory CLI (dossier spec v{D.SPEC_VERSION}). "
            "Hand-operated: the agent writes "
            "the analysis; this tool handles structure, storage, validation, "
            "and retrieval."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p_init = sub.add_parser(
        "init",
        help="scaffold a new dossier from the template",
        description=(
            "Scaffold a new dossier from the template. The id is derived "
            "from the date and task slug (truncated to 50 characters); "
            "`created` is the machine's local date. A scaffold is not a "
            "dossier: fill in every section honestly, then validate — "
            "`validate` rejects sections left as the template's placeholder "
            "text."
        ),
    )
    p_init.add_argument("--task", required=True, help="one-line description of the failed task")
    p_init.add_argument("--agent", required=True, help="which agent/scaffold ran it, e.g. claude-code")
    p_init.add_argument("--outcome", default="failed", choices=["failed", "recovered"],
                        help="failed (default) or recovered")
    p_init.add_argument("--class", dest="failure_class", required=True,
                        choices=D.VALID_FAILURE_CLASSES,
                        help="what kind of failure this was "
                             f"({', '.join(D.VALID_FAILURE_CLASSES)})")
    p_init.add_argument("-o", "--out-dir", default="dossiers",
                        help="directory to write into (created if missing)")
    p_init.set_defaults(func=cmd_init)

    p_validate = sub.add_parser("validate", help="check a dossier against the spec")
    p_validate.add_argument("file", help="dossier markdown file to check")
    p_validate.set_defaults(func=cmd_validate)

    p_confirm = sub.add_parser(
        "confirm",
        help="record that a dossier earned its keep in a later run",
        description=(
            "Increment a dossier's confirm counter. By default this is "
            "confirmed_fixes: use it when a retrieved dossier prevented a "
            "specific repeat or fixed a verifiable failure. With --insight, "
            "it increments confirmed_insights instead: use it when a "
            "dossier's analysis generated a new approach — its blocking "
            "constraint, inverted, became the next idea. That's the signal "
            "for open-ended work where there is no verifiable 'fix' to "
            "count. Confirmed dossiers rank higher in recall — this is how "
            "the dossier bank learns which autopsies earn their keep. "
            "The index is rebuilt automatically."
        ),
    )
    p_confirm.add_argument("id", help="dossier id (frontmatter `id:` value)")
    p_confirm.add_argument("--dir", default="dossiers", help="dossier directory")
    p_confirm.add_argument("--insight", action="store_true",
                           help="count a generated approach, not a fixed failure")
    p_confirm.set_defaults(func=cmd_confirm)

    p_index = sub.add_parser("index", help="rebuild dossiers/index.jsonl")
    p_index.add_argument("--dir", default="dossiers", help="dossier directory")
    p_index.set_defaults(func=cmd_index)

    p_recall = sub.add_parser(
        "recall",
        help="rank dossiers for a task description",
        description=(
            "Rank dossiers by a weighted lexical score: signature-term "
            "overlap counts DOUBLE (the failure signature is the retrieval "
            "key), task-term overlap counts single, and each confirmed fix "
            "or confirmed insight adds 1 point up to a cap of "
            f"{CONFIRMED_BOOST_CAP} each. Ties break by total confirms, then "
            "dossier id. This is still keyword overlap, NOT semantic "
            "similarity: no embeddings, no model calls, no magic. It finds "
            "dossiers that talk about the same things, weighted toward the "
            "parts of a dossier written to be matched on and toward dossiers "
            "with a track record. "
            "Output columns per hit: TOTAL | id | task [path] "
            "(from:origin sig:<n> task:<n> fix:<n> insight:<n> "
            "matched: <terms>). sig: counts matched signature terms (each "
            "worth 2 points); task: counts matched task terms (1 point "
            "each); fix:/insight: show the dossier's confirmed counters "
            "(each adds up to 5 points, already included in TOTAL)."
        ),
    )
    p_recall.add_argument("--task", required=True, help="describe the current task")
    p_recall.add_argument("--dir", default="dossiers", help="dossier directory")
    p_recall.add_argument("--top", type=int, default=3, help="how many to show (default 3)")
    p_recall.add_argument("--class", dest="failure_class",
                          choices=D.VALID_FAILURE_CLASSES, default=None,
                          help="only consider dossiers of this failure class")
    p_recall.add_argument("--include-dead", action="store_true",
                          help="also rank dead routes (premise killed), "
                               "marked [premise-dead]; by default they are "
                               "listed separately and excluded from ranking")
    p_recall.set_defaults(func=cmd_recall)

    p_list = sub.add_parser("list", help="compact table of dossiers")
    p_list.add_argument("--dir", default="dossiers", help="dossier directory")
    p_list.set_defaults(func=cmd_list)

    p_import = sub.add_parser(
        "import",
        help="import dossiers from another bank (shared failures)",
        description=(
            "Copy dossiers from another bank (a directory or a single .md "
            "file) into this one. Each incoming dossier is validated "
            "first; invalid ones are skipped with reasons. Id collisions "
            "are renamed to <id>--from-<agent> — never overwritten — "
            "unless the incoming file is byte-identical to the one "
            "already banked, in which case it is skipped as already in "
            "bank. The index is rebuilt automatically. This is the network "
            "effect: your bank learns from other agents' failures."
        ),
    )
    p_import.add_argument("source", help="dossier bank directory or .md file")
    p_import.add_argument("--dir", default="dossiers",
                          help="dossier directory to import into")
    p_import.set_defaults(func=cmd_import)

    p_export = sub.add_parser(
        "export",
        help="copy validated dossiers to a directory for sharing",
        description=(
            "Copy validated dossier .md files (not the derived index.jsonl) "
            "to a directory for sharing. The format is already portable; "
            "this is just hygiene."
        ),
    )
    p_export.add_argument("-o", "--out", required=True,
                          help="output directory (created if missing)")
    p_export.add_argument("--dir", default="dossiers", help="dossier directory")
    p_export.set_defaults(func=cmd_export)

    # v0.2.4: premise registry — close big routes. A premise is a load-bearing
    # claim a whole family of approaches assumes. Register it once, declare
    # it in dossiers' ## Premises sections, and kill it when the evidence
    # says it's false: every approach resting on it (transitively) dies.
    p_premise = sub.add_parser(
        "premise",
        help="register, kill, or list load-bearing premises",
        description=(
            "Close big routes. `garm premise add` registers a "
            "load-bearing claim a family of approaches assumes "
            "(--depends-on names the big routes it rests on). Dossiers "
            "declare their premises in an optional ## Premises section. "
            "`garm premise kill <id> --by <dossier>` marks the claim "
            "false: the premise and everything under it dies transitively, "
            "the index is rebuilt, and recall stops suggesting dead "
            "routes. One closed big route closes a thousand small routes."
        ),
    )
    p_sub = p_premise.add_subparsers(dest="premise_command", required=True,
                                     metavar="premise-command")

    p_add = p_sub.add_parser("add", help="register a premise")
    p_add.add_argument("--statement", required=True,
                       help="the load-bearing claim, e.g. 'C7[K4] is biplanar'")
    p_add.add_argument("--depends-on", default="",
                       help="comma-separated parent premise ids this "
                            "premise assumes hold (the big routes it rests on)")
    p_add.add_argument("--dir", default="dossiers", help="dossier directory")
    p_add.set_defaults(func=cmd_premise_add)

    p_kill = p_sub.add_parser(
        "kill", help="kill a premise (close the big route)",
        description=(
            "Close the big route: mark a premise false. The premise and "
            "everything under it dies transitively; the index is rebuilt "
            "and recall stops suggesting the dead routes. --by names the "
            "dossier (or note) that killed it; --evidence records how "
            "strong the evidence was (proof, our-tests, outside-work)."
        ))
    p_kill.add_argument("id", help="premise id, e.g. P-20261011-001")
    p_kill.add_argument("--by", required=True,
                        help="dossier id (or short note) that killed it")
    p_kill.add_argument("--evidence", default=None,
                        choices=["proof", "our-tests", "outside-work"],
                        help="how strong the evidence was: proof (we proved "
                             "it false), our-tests (our experiments ruled it "
                             "out), outside-work (someone else's result)")
    p_kill.add_argument("--dir", default="dossiers", help="dossier directory")
    p_kill.set_defaults(func=cmd_premise_kill)

    p_plist = p_sub.add_parser("list", help="list registered premises")
    p_plist.add_argument("--dir", default="dossiers", help="dossier directory")
    p_plist.set_defaults(func=cmd_premise_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
