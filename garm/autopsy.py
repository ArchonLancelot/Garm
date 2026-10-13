"""Assisted autopsy drafting: a closing-ceremony interview that turns
answers into a pre-filled dossier draft.

v0.2.5. The blank page is the friction: ``garm init`` scaffolds the
structure, but the agent still has to write every section from nothing.
``garm autopsy`` instead asks a short series of sharp questions — what
broke, what took too long, what assumption failed, what retrieval would
have changed — and writes the answers into the dossier sections.

The CLI never invents analysis. Answers go into the sections verbatim
(light formatting only: multi-line attempt lists become bullets). Any
section left unanswered keeps the scaffold's guidance text; a draft with
empty *required* sections fails ``validate`` by design, and the command
says exactly which sections still need writing. Optional sections left
blank are stripped from the draft entirely, so the file only ever
contains real content. The draft is printed for review before it is
saved, and it is only indexed when it validates.

Three ways to drive it:
  interactive   answer the questions at the prompts (flags pre-answer)
  --answers     non-interactive: a JSON file mapping answer keys to text
  MCP           ``garm_autopsy`` takes the same answers as a dict

Answer keys for --answers / MCP (values are strings, or lists of strings
for ``what_was_tried`` and ``premises``):
  task, agent, failure_class, outcome,
  what_was_tried, root_cause, failure_signature, blocking_constraint,
  challengeable_premises, what_retrieval_would_have_changed,
  open_questions, tokens, premises, confidence
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from . import dossier as D
from . import premise as PR

# Sections asked about, in dossier order. "key" is the --answers/MCP answer
# key; "section" is the dossier section title it fills. Frontmatter fields
# come first (kind "text"/"choice"); the rest are section questions.
QUESTIONS: list[dict] = [
    {
        "key": "task",
        "frontmatter": True,
        "prompt": "What were you trying to do? (one line)",
        "required": True,
    },
    {
        "key": "agent",
        "frontmatter": True,
        "prompt": "Which agent ran this? (e.g. claude-code)",
        "required": True,
    },
    {
        "key": "failure_class",
        "frontmatter": True,
        "kind": "choice",
        "choices": D.VALID_FAILURE_CLASSES,
        "prompt": "What kind of failure was this?",
        "required": True,
    },
    {
        "key": "outcome",
        "frontmatter": True,
        "kind": "choice",
        "choices": D.VALID_OUTCOMES,
        "default": "failed",
        "prompt": "Outcome?",
        "required": True,
    },
    {
        "key": "what_was_tried",
        "section": "What was tried",
        "multiline": True,
        "required": True,
        "prompt": "Walk me through what you tried, in order — "
                  "one attempt per line, blank line when done.",
    },
    {
        "key": "root_cause",
        "section": "Root cause",
        "required": True,
        "prompt": "What was the actual reason it failed — not the surface "
                  "error, the real cause?",
    },
    {
        "key": "failure_signature",
        "section": "Failure signature",
        "required": True,
        "prompt": "Name the reusable pattern and give a match rule: "
                  "'if you see X in the first few turns, stop and pull "
                  "this dossier.'",
    },
    {
        "key": "blocking_constraint",
        "section": "Blocking constraint",
        "required": True,
        "prompt": "What fact about the repo, environment, or task made the "
                  "approaches fail?",
    },
    {
        "key": "challengeable_premises",
        "section": "Challengeable premises",
        "required": False,
        "prompt": "What assumptions did the attempts rest on? Phrase each so "
                  "a reader can ask 'what if this is false?' "
                  "(Enter to skip)",
    },
    {
        "key": "what_retrieval_would_have_changed",
        "section": "What retrieval would have changed",
        "required": True,
        "prompt": "Concretely: which early turn would a second run skip, "
                  "and what would it do instead?",
    },
    {
        "key": "open_questions",
        "section": "Open questions",
        "required": False,
        "prompt": "What precise questions did this failure leave open for a "
                  "future run? (Enter to skip)",
    },
    {
        "key": "tokens",
        "section": "Tokens",
        "required": False,
        "prompt": "What took the longest, and roughly how many tokens did "
                  "the failed approaches burn? (Enter to skip)",
    },
    {
        "key": "premises",
        "section": "Premises",
        "required": False,
        "prompt": "Any premise ids this approach rested on? "
                  "Comma-separated, from `garm premise list`. "
                  "(Enter to skip)",
    },
    {
        "key": "confidence",
        "section": "Confidence",
        "required": True,
        "prompt": "How confident are you in this autopsy, and what would "
                  "change your mind?",
    },
]

# Answer keys that must be present and non-empty (frontmatter only — a
# missing task means there is no dossier to name; a missing section just
# means the draft won't validate yet).
REQUIRED_FRONTMATTER_KEYS = ("task", "agent", "failure_class", "outcome")


def _read_line(prompt: str) -> str:
    """One answer line; EOF (piped stdin closed) reads as empty."""
    try:
        return input(prompt + "\n> ").strip()
    except EOFError:
        print()
        return ""


def _read_multiline(prompt: str) -> list[str]:
    """Attempt list: one per line, blank line (or EOF) finishes."""
    print(prompt)
    print("(one attempt per line, blank line when done)")
    lines: list[str] = []
    try:
        while True:
            line = input("> ").rstrip()
            if not line:
                break
            lines.append(line.strip())
    except EOFError:
        print()
    return lines


def _ask_choice(question: dict) -> str:
    """Numbered menu; accepts a number or the exact name."""
    choices = list(question["choices"])
    default = question.get("default")
    print(question["prompt"])
    for i, choice in enumerate(choices, 1):
        mark = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{mark}")
    while True:
        try:
            raw = input("> ").strip()
        except EOFError:
            print()
            raw = ""
        if not raw and default:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        if raw in choices:
            return raw
        if not raw:
            return ""  # EOF with no default: caller decides
        print(f"  pick 1-{len(choices)} or one of: {', '.join(choices)}")


def _ask_question(question: dict) -> str | list[str]:
    """Ask one question; returns the answer (list for multiline)."""
    if question.get("kind") == "choice":
        return _ask_choice(question)
    if question.get("multiline"):
        return _read_multiline(question["prompt"])
    answer = _read_line(question["prompt"])
    if not answer and question.get("required"):
        # One nudge, then accept the blank: the draft will fail validate
        # and say exactly what still needs writing. The interview guides;
        # it doesn't interrogate.
        retry = _read_line(
            "This section is required for a valid dossier — answer now, "
            "or press Enter again to leave it for later."
        )
        return retry
    return answer


def collect_interactive(prefill: dict) -> dict:
    """Ask for every question not already answered in ``prefill``."""
    answers = dict(prefill)
    for question in QUESTIONS:
        key = question["key"]
        if answers.get(key):
            continue
        answers[key] = _ask_question(question)
    return answers


def validate_raw_answers(raw: dict) -> dict:
    """Check a raw answers mapping (from --answers JSON or MCP).

    Unknown keys, non-string values, missing required frontmatter, and bad
    failure_class/outcome values are all hard errors — a draft built from
    garbage answers is worse than no draft. Returns ``raw`` unchanged.
    """
    if not isinstance(raw, dict):
        raise ValueError("answers must be an object of answer keys")
    known = {q["key"] for q in QUESTIONS}
    unknown = [k for k in raw if k not in known]
    if unknown:
        raise ValueError(
            f"unknown answer key(s): {', '.join(sorted(unknown))}; "
            f"known keys: {', '.join(sorted(known))}"
        )
    for key, value in raw.items():
        if isinstance(value, list):
            if not all(isinstance(v, str) for v in value):
                raise ValueError(
                    f"answer {key!r}: list values must all be strings"
                )
        elif not isinstance(value, str):
            raise ValueError(
                f"answer {key!r} must be a string or list of strings"
            )
    missing = [k for k in REQUIRED_FRONTMATTER_KEYS if not raw.get(k)]
    if missing:
        raise ValueError(
            f"missing required answer key(s): {', '.join(missing)}"
        )
    failure_class = raw.get("failure_class", "")
    if failure_class not in D.VALID_FAILURE_CLASSES:
        raise ValueError(
            f"failure_class {failure_class!r} must be one of "
            f"{D.VALID_FAILURE_CLASSES}"
        )
    outcome = raw.get("outcome", "")
    if outcome not in D.VALID_OUTCOMES:
        raise ValueError(
            f"outcome {outcome!r} must be one of {D.VALID_OUTCOMES}"
        )
    return raw


def load_answers_file(path: str | Path) -> dict:
    """Read --answers JSON. Must be an object; values are strings or lists
    of strings. Raises ValueError on any structural problem."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read answers file: {exc}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"answers file is not valid JSON: {exc}") from None
    return validate_raw_answers(raw)


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines if line)


def normalize_answers(raw: dict) -> tuple[dict, dict]:
    """Split raw answers into (frontmatter, sections).

    ``sections`` maps lowercase section titles to content. List values
    become newline-joined text (bullets for "what was tried", one id per
    line for "premises"). Empty/blank answers are dropped — the section
    keeps the scaffold guidance (required) or is stripped (optional).
    """
    by_key = {q["key"]: q for q in QUESTIONS}
    frontmatter: dict[str, str] = {}
    sections: dict[str, str] = {}
    for key, value in raw.items():
        question = by_key.get(key)
        if question is None:
            continue
        if isinstance(value, list):
            items = [v.strip() for v in value if v.strip()]
            if not items:
                continue
            if key == "what_was_tried":
                text = _bullets(items)
            elif key == "premises":
                # list items may themselves be comma-joined ("a, b")
                ids: list[str] = []
                for item in items:
                    ids.extend(p.strip() for p in item.split(","))
                text = "\n".join(i for i in ids if i)
            else:
                text = "\n".join(items)
        else:
            text = value.strip()
            if not text:
                continue
            if key == "premises":
                ids = [p.strip() for p in text.split(",")]
                text = "\n".join(i for i in ids if i)
                if not text:
                    continue
        if question.get("frontmatter"):
            frontmatter[key] = text
        else:
            sections[question["section"].lower()] = text
    return frontmatter, sections


def _strip_unfilled_optionals(text: str, filled: set[str]) -> str:
    """Remove optional sections that were left blank.

    render_template fills every section with guidance text when no content
    is given; for optional sections that guidance is a cosmetic wart in a
    finished draft, so drop the whole block (header + guidance + blank).
    Required sections keep their guidance — validate() flags them by name.
    """
    required_titles = {
        q["section"].lower() for q in QUESTIONS
        if q.get("section") and q.get("required")
    }
    out: list[str] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if (lines[i].startswith("## ")
                and lines[i][3:].strip().lower() not in required_titles
                and lines[i][3:].strip().lower() not in filled
                and i + 1 < len(lines)
                and lines[i + 1].strip()
                == D._GUIDANCE_BY_TITLE.get(
                    lines[i][3:].strip().lower(), "\0")):
            i += 2  # skip header + guidance line
            if i < len(lines) and not lines[i].strip():
                i += 1  # skip the blank line after the block
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _check_premise_refs(premises_text: str, base_dir: Path) -> list[str]:
    """Warn about premise ids that aren't in the registry, or don't look
    like premise ids at all. Unknown refs are kept (the index treats them
    as live) — but a typo'd id silently means the dead-route machinery
    won't see it, so say so loudly."""
    warnings: list[str] = []
    if not premises_text.strip():
        return warnings
    try:
        registry = PR.load_registry(base_dir)
    except ValueError as exc:
        return [f"warning: {exc} (premise refs kept, treated as live)"]
    known = set(registry.get("premises", {}))
    refs = PR.parse_premise_refs(premises_text)
    unknown = [r for r in refs if r not in known]
    if unknown:
        warnings.append(
            f"warning: unknown premise id(s) {', '.join(unknown)} — "
            f"not in the registry (see `garm premise list`); kept as live"
        )
    malformed = [
        line.strip().lstrip("-*•").strip()
        for line in premises_text.splitlines()
        if line.strip()
    ]
    malformed = [m for m in malformed if not PR.PREMISE_ID_RE.match(m)]
    if malformed:
        warnings.append(
            f"warning: premise ref(s) don't look like premise ids "
            f"(expected P-YYYYMMDD-NNN): {', '.join(malformed)} — kept as "
            f"text, ignored by the registry"
        )
    return warnings


def write_draft(task: str, agent: str, outcome: str, failure_class: str,
                sections: dict[str, str], out_dir: str | Path,
                created: str | None = None) -> tuple[Path, str]:
    """Render the draft, strip blank optional sections, and write it with
    collision-safe naming (same ``<date>-<slug>`` scheme as ``init``).
    Returns (path, text)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    created = created or date.today().isoformat()
    dossier_id = f"{created}-{D.slugify(task)}"
    path = out / f"{dossier_id}.md"
    n = 2
    while path.exists():
        path = out / f"{dossier_id}-{n}.md"
        n += 1
    text = D.render_template(
        task=task, agent=agent, outcome=outcome,
        failure_class=failure_class, created=created, id_=path.stem,
        sections=sections,
    )
    filled = {k.lower() for k in sections}
    text = _strip_unfilled_optionals(text, filled)
    path.write_text(text, encoding="utf-8")
    return path, text


def run_autopsy(raw_answers: dict, base_dir: str | Path,
                interactive: bool = False,
                confirm_save: bool = True) -> int:
    """Full assisted-draft flow. Returns a process exit code.

    0: draft written, valid, indexed. 1: draft written but not yet valid
    (says which sections need writing), or a fatal input problem.
    """
    if not interactive:
        try:
            raw_answers = validate_raw_answers(raw_answers)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    base = Path(base_dir)
    frontmatter, sections = normalize_answers(raw_answers)
    for key in REQUIRED_FRONTMATTER_KEYS:
        if not frontmatter.get(key):
            print(f"error: no {key} given — aborting, nothing written",
                  file=sys.stderr)
            return 1
    task = frontmatter["task"]
    agent = frontmatter["agent"]
    premises_text = sections.get("premises", "")
    for warning in _check_premise_refs(premises_text, base):
        print(warning, file=sys.stderr)

    path, text = write_draft(
        task=task, agent=agent, outcome=frontmatter["outcome"],
        failure_class=frontmatter["failure_class"], sections=sections,
        out_dir=base,
    )

    if interactive and confirm_save:
        print()
        print("--- draft ---")
        print(text)
        print("--- end draft ---")
        try:
            ok = input(f"Save this dossier to {path}? [Y/n] ").strip().lower()
        except EOFError:
            ok = "y"
        if ok not in ("", "y", "yes"):
            path.unlink()
            print("discarded — nothing written.")
            return 1
    else:
        print(f"draft: {path}")

    errors = D.validate_dossier(path)
    if errors:
        print(f"draft needs work: {path}")
        for error in errors:
            print(f"  - {error}")
        print("Fill in the sections above, then run:")
        print(f"  python3 -m garm validate {path}")
        print(f"  python3 -m garm index --dir {base}")
        return 1
    print(f"OK: {path}")
    n, skipped = D.rebuild_index(base)
    print(f"indexed {n} dossiers -> {base / 'index.jsonl'}"
          + (f" ({skipped} invalid skipped)" if skipped else ""))
    return 0
