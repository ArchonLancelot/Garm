"""Command-line interface for the v0.1 failure-dossier framework. Stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import dossier as D


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
        task=args.task, agent=args.agent, outcome=args.outcome, created=created,
        id_=path.stem,
    )
    path.write_text(text, encoding="utf-8")
    print(str(path))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    errors = D.validate_dossier(args.file)
    if errors:
        print(f"INVALID: {args.file}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"OK: {args.file}")
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
        overlap = [k for k in query_keys if k in entry["keywords"]]
        scored.append((len(overlap), overlap, entry))
    if not scored:
        print(f"no dossiers found in {base}")
        return 1
    scored.sort(key=lambda s: (-s[0], s[2]["id"]))
    top = max(1, args.top)
    for score, overlap, entry in scored[:top]:
        matched = ",".join(overlap) if overlap else "-"
        print(f"{score:3d} | {entry['id']} | {entry['task']} "
              f"[{entry['path']}] (matched: {matched})")
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
        rows.append((fm["id"], fm["outcome"], fm["task"]))
    if not rows:
        print(f"no dossiers found in {base}")
        return 0
    rows.sort(key=lambda r: r[0])
    print(f"{'ID':42} {'OUTCOME':9} TASK")
    for dossier_id, outcome, task in rows:
        task_short = task if len(task) <= 60 else task[:57] + "..."
        print(f"{dossier_id[:42]:42} {outcome:9} {task_short}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autopsy",
        description=(
            "v0.1 failure-memory CLI. Hand-operated: the agent writes the "
            "analysis; this tool handles structure, storage, validation, "
            "and retrieval."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p_init = sub.add_parser("init", help="scaffold a new dossier from the template")
    p_init.add_argument("--task", required=True, help="one-line description of the failed task")
    p_init.add_argument("--agent", required=True, help="which agent/scaffold ran it, e.g. claude-code")
    p_init.add_argument("--outcome", default="failed", choices=["failed", "recovered"],
                        help="failed (default) or recovered")
    p_init.add_argument("-o", "--out-dir", default="dossiers",
                        help="directory to write into (created if missing)")
    p_init.set_defaults(func=cmd_init)

    p_validate = sub.add_parser("validate", help="check a dossier against the v0.1 spec")
    p_validate.add_argument("file", help="dossier markdown file to check")
    p_validate.set_defaults(func=cmd_validate)

    p_index = sub.add_parser("index", help="rebuild dossiers/index.jsonl")
    p_index.add_argument("--dir", default="dossiers", help="dossier directory")
    p_index.set_defaults(func=cmd_index)

    p_recall = sub.add_parser(
        "recall",
        help="rank dossiers by keyword overlap for a task description",
        description=(
            "Rank dossiers by KEYWORD OVERLAP between your --task text and each "
            "dossier's task + failure signature. v0.1 ranking is lexical keyword "
            "overlap, NOT semantic similarity: no embeddings, no model calls, no "
            "magic. It finds dossiers that talk about the same things, which is "
            "a starting point, not a diagnosis."
        ),
    )
    p_recall.add_argument("--task", required=True, help="describe the current task")
    p_recall.add_argument("--dir", default="dossiers", help="dossier directory")
    p_recall.add_argument("--top", type=int, default=3, help="how many to show (default 3)")
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
