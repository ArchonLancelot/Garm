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
import json
import sys
from datetime import date
from pathlib import Path

from . import dossier as D

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


def cmd_init(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created = date.today().isoformat()
    dossier_id = f"{created}-{D.slugify(args.task)}"
    path = out_dir / f"{dossier_id}.md"
    n = 2
    while path.exists():
        path = out_dir / f"{dossier_id}-{n}.md"
        n += 1
    text = D.render_template(
        task=args.task, agent=args.agent, outcome=args.outcome,
        failure_class=args.failure_class, created=created,
        id_=path.stem,
    )
    path.write_text(text, encoding="utf-8")
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
    print("hint: run `garm index` to refresh index.jsonl", file=sys.stderr)
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


def _rebuild_index(base: Path) -> tuple[int, int]:
    """Rebuild index.jsonl. Returns (indexed, skipped)."""
    entries = []
    skipped = 0
    for md in sorted(base.rglob("*.md")):
        errors = D.validate_dossier(md)
        if errors:
            print(f"warning: skipping invalid dossier {md}", file=sys.stderr)
            skipped += 1
            continue
        entries.append(D.build_index_entry(md, base))
    entries.sort(key=lambda e: e["id"])
    index_path = base / "index.jsonl"
    with index_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return len(entries), skipped


def cmd_index(args: argparse.Namespace) -> int:
    base = Path(args.dir)
    if not base.is_dir():
        print(f"error: directory not found: {base}", file=sys.stderr)
        return 1
    n, skipped = _rebuild_index(base)
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
    n, _ = _rebuild_index(base)
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
    scored = []
    for md in sorted(base.rglob("*.md")):
        if D.validate_dossier(md):
            continue
        entry = D.build_index_entry(md, base)
        if args.failure_class and entry.get("failure_class") != args.failure_class:
            continue
        total, sig_n, task_n, fix_b, ins_b = recall_score(query_keys, entry)
        overlap = [k for k in query_keys if k in entry["keywords"]]
        scored.append((total, sig_n, task_n, fix_b, ins_b, overlap, entry))
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
        print(f"{total:3d} | {entry['id']} | {entry['task']} "
              f"[{entry['path']}] (from:{origin} sig:{sig_n} task:{task_n} "
              f"fix:{fixes} insight:{insights} matched: {matched})")
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
            "Garm v0.2 failure-memory CLI. Hand-operated: the agent writes "
            "the analysis; this tool handles structure, storage, validation, "
            "and retrieval."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p_init = sub.add_parser("init", help="scaffold a new dossier from the template")
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
            "Re-run `index` after."
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
            "with a track record."
        ),
    )
    p_recall.add_argument("--task", required=True, help="describe the current task")
    p_recall.add_argument("--dir", default="dossiers", help="dossier directory")
    p_recall.add_argument("--top", type=int, default=3, help="how many to show (default 3)")
    p_recall.add_argument("--class", dest="failure_class",
                          choices=D.VALID_FAILURE_CLASSES, default=None,
                          help="only consider dossiers of this failure class")
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
            "are renamed to <id>--from-<agent> — never overwritten. "
            "The index is rebuilt automatically. This is the network "
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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
