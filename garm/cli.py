"""Command-line interface for Garm, the failure-memory framework. Stdlib only.

v0.2: ``init`` takes a failure class, ``confirm`` records dossiers that
demonstrably helped a later run, and ``recall`` ranks by weighted overlap
(signature terms count double) plus a small boost for confirmed dossiers.
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
# adds 1 point up to a cap of 5 so one veteran dossier can't swamp new ones.
CONFIRMED_BOOST_CAP = 5


def recall_score(query_keys: list[str], entry: dict) -> tuple[int, int, int, int]:
    """Return (total, sig_overlap, task_overlap, boost) for one index entry."""
    sig_keys = entry.get("sig_keywords") or []
    task_keys = [k for k in entry.get("keywords", []) if k not in sig_keys]
    sig_overlap = sum(1 for k in query_keys if k in sig_keys)
    task_overlap = sum(1 for k in query_keys if k in task_keys)
    boost = min(int(entry.get("confirmed_fixes", 0) or 0), CONFIRMED_BOOST_CAP)
    return 2 * sig_overlap + task_overlap + boost, sig_overlap, task_overlap, boost


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
    """Record that dossier <id> demonstrably helped a later run.

    Use this when a retrieved dossier changed what a run did and the run
    then succeeded (or avoided the documented failure). It is the start of
    the experience flywheel: dossiers that earn their keep rank higher.
    """
    try:
        path, new_count = D.confirm_dossier(args.dir, args.id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"confirmed: {args.id} (confirmed fixes: {new_count}) [{path}]")
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


def cmd_index(args: argparse.Namespace) -> int:
    base = Path(args.dir)
    if not base.is_dir():
        print(f"error: directory not found: {base}", file=sys.stderr)
        return 1
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
    print(f"indexed {len(entries)} dossiers -> {index_path}"
          + (f" ({skipped} invalid skipped)" if skipped else ""))
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
        total, sig_n, task_n, boost = recall_score(query_keys, entry)
        overlap = [k for k in query_keys if k in entry["keywords"]]
        scored.append((total, sig_n, task_n, boost, overlap, entry))
    if not scored:
        print(f"no dossiers found in {base}")
        return 1
    scored.sort(key=lambda s: (-s[0], -s[5].get("confirmed_fixes", 0), s[5]["id"]))
    top = max(1, args.top)
    for total, sig_n, task_n, boost, overlap, entry in scored[:top]:
        matched = ",".join(overlap) if overlap else "-"
        fixes = entry.get("confirmed_fixes", 0)
        print(f"{total:3d} | {entry['id']} | {entry['task']} "
              f"[{entry['path']}] (sig:{sig_n} task:{task_n} confirmed:{fixes} "
              f"matched: {matched})")
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
            fm.get("failure_class") or "-",
            D._confirmed_fixes_of(fm),
            fm["outcome"],
            fm["task"],
        ))
    if not rows:
        print(f"no dossiers found in {base}")
        return 0
    rows.sort(key=lambda r: r[0])
    print(f"{'ID':40} {'CLASS':15} {'FIX':4} {'OUTCOME':9} TASK")
    for dossier_id, failure_class, fixes, outcome, task in rows:
        task_short = task if len(task) <= 52 else task[:49] + "..."
        print(f"{dossier_id[:40]:40} {failure_class[:15]:15} {fixes:<4} "
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
        help="record that a dossier demonstrably helped a later run",
        description=(
            "Increment a dossier's confirmed_fixes counter. Use it when a "
            "retrieved dossier changed what a run did and the run then "
            "succeeded (or avoided the documented failure). Confirmed "
            "dossiers rank higher in recall — this is how the dossier bank "
            "learns which autopsies earn their keep. Re-run `index` after."
        ),
    )
    p_confirm.add_argument("id", help="dossier id (frontmatter `id:` value)")
    p_confirm.add_argument("--dir", default="dossiers", help="dossier directory")
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
            f"adds 1 point up to a cap of {CONFIRMED_BOOST_CAP}. Ties break "
            "by confirmed fixes, then dossier id. This is still keyword "
            "overlap, NOT semantic similarity: no embeddings, no model calls, "
            "no magic. It finds dossiers that talk about the same things, "
            "weighted toward the parts of a dossier written to be matched on "
            "and toward dossiers with a track record."
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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
