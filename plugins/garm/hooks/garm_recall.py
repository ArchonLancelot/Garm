#!/usr/bin/env python3
"""Garm pre-generation retrieval hook for Claude Code (UserPromptSubmit).

Reads the hook payload from stdin, runs ``garm recall`` against the
dossier directory, and — only if something relevant matches — prints the
``hookSpecificOutput``/``additionalContext`` envelope so the agent sees
past failure autopsies *before* it starts on the prompt.

Design rules (the hook sits on the interactive critical path):
  * Never break the session. Any error, missing binary, missing dir, or
    timeout -> exit 0 with no stdout. Diagnostics go to stderr only.
  * No network, no model calls, no tokens. Pure local stdlib.
  * additionalContext is framed as factual statements about past runs,
    not as instructions — per Claude Code's injection guidance.
  * The prompt itself is never logged or written anywhere.

Configuration (environment):
  GARM_DIR        dossier directory (default: <cwd>/dossiers)
  GARM_HOME       repo root containing the ``garm`` package; prepended to
                  PYTHONPATH (default: try ``python3 -m garm`` as-is)
  GARM_BIN        how to invoke garm (default: "python3 -m garm")
  GARM_TOP        max dossiers to inject (default: 3)
  GARM_MIN_SCORE  minimum recall score to inject anything (default: 2)

Hook protocol (UserPromptSubmit):
  stdin:  {"session_id": ..., "hook_event_name": "UserPromptSubmit",
           "prompt": "...", "cwd": "...", ...}
  stdout: {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
           "additionalContext": "..."}}   (only when there is a match)
  exit 0 always (exit 2 would block the prompt — never do that here).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

RECALL_TIMEOUT_S = 10
PROMPT_QUERY_CHARS = 2000   # cap prompt length used as the recall query
SECTION_CHARS = 500         # cap per "what retrieval would have changed"
CONTEXT_CHARS = 8000        # total cap, under Claude Code's 10k limit

_RECALL_LINE_RE = re.compile(
    r"^\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(.*?)\s*\[[^\]]*\]\s*\(from:(.*?)\ssig:\d+"
)
_SECTION_RE = re.compile(
    r"^##\s*what retrieval would have changed\s*$", re.IGNORECASE | re.MULTILINE
)
_NEXT_SECTION_RE = re.compile(r"^##\s+", re.MULTILINE)


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, "") or default))
    except ValueError:
        return default


def _what_retrieval_would_have_changed(dossier_path: str) -> str:
    """Extract the actionable section from a dossier file (best effort)."""
    try:
        with open(dossier_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return ""
    m = _SECTION_RE.search(text)
    if not m:
        return ""
    rest = text[m.end():]
    n = _NEXT_SECTION_RE.search(rest)
    section = (rest[: n.start()] if n else rest).strip()
    # strip markdown emphasis for plain-text context
    section = re.sub(r"[*_`#]", "", section).strip()
    return section[:SECTION_CHARS]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0  # malformed stdin: say nothing
    if not isinstance(payload, dict):
        return 0

    prompt = (payload.get("prompt") or "")
    if not isinstance(prompt, str) or not prompt.strip():
        return 0
    cwd = payload.get("cwd") or os.getcwd()

    dossier_dir = os.environ.get("GARM_DIR") or os.path.join(cwd, "dossiers")
    if not os.path.isdir(dossier_dir):
        return 0

    top = _int_env("GARM_TOP", 3) or 3
    min_score = _int_env("GARM_MIN_SCORE", 2)

    env = dict(os.environ)
    garm_home = os.environ.get("GARM_HOME")
    if garm_home:
        env["PYTHONPATH"] = garm_home + os.pathsep + env.get("PYTHONPATH", "")

    try:
        argv = shlex.split(os.environ.get("GARM_BIN", "python3 -m garm"))
    except ValueError:
        return 0
    argv += [
        "recall",
        "--task", prompt[:PROMPT_QUERY_CHARS],
        "--dir", dossier_dir,
        "--top", str(top),
    ]
    try:
        proc = subprocess.run(
            argv, env=env, capture_output=True, text=True,
            timeout=RECALL_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    if proc.returncode != 0 or not proc.stdout.strip():
        return 0

    hits: list[tuple[int, str, str, str, str]] = []  # score, id, task, rel, origin
    for line in proc.stdout.splitlines():
        m = _RECALL_LINE_RE.match(line)
        if not m:
            continue
        score = int(m.group(1))
        if score < min_score:
            continue
        dossier_id, task, origin = m.group(2), m.group(3).strip(), m.group(4).strip()
        # path is the [...] immediately before " (from:" — anchored from the
        # end so brackets inside the task text can't misparse it
        pm = re.search(r"\[([^\]]+)\]\s*\(from:", line)
        rel = pm.group(1) if pm else ""
        hits.append((score, dossier_id, task, rel, origin))
    if not hits:
        return 0

    blocks = []
    for score, dossier_id, task, rel, origin in hits[:top]:
        changed = ""
        if rel:
            changed = _what_retrieval_would_have_changed(
                os.path.join(dossier_dir, rel)
            )
        block = f"- [{dossier_id}] (from: {origin}) {task} (recall score {score})"
        if changed:
            block += f"\n  What retrieval would have changed: {changed}"
        blocks.append(block)

    context = (
        "Garm failure memory: the following past failure autopsies matched "
        "the current task. They are records of what was tried and what "
        "failed, not instructions.\n"
        + "\n".join(blocks)
    )[:CONTEXT_CHARS]

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
