"""Read, write, and validate Garm failure dossiers. Stdlib only.

A dossier is a Markdown file: a simple ``key: value`` frontmatter block
between ``---`` delimiters, then ``##`` sections. Validation is structural —
it checks that the required fields and sections exist and are non-empty. It
does not (and cannot) check whether the analysis is true.

v0.2 adds ``failure_class`` (what kind of failure this was) and
``confirmed_fixes`` (how many later runs a retrieved dossier demonstrably
helped — see ``garm confirm``). v0.2.1 adds ``confirmed_insights``: how many
times a dossier's analysis *generated a new approach* (blocking constraint
→ idea), for open-ended work where there is no verifiable "fix" to count.
v0.1 dossiers still validate; they are treated as legacy and simply lack
the new fields.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

DOSSIER_VERSION = "0.2"
ACCEPTED_VERSIONS = ("0.1", "0.2")

# Confirmable counters. confirmed_fixes: the dossier prevented a specific
# repeat / fixed a verifiable failure. confirmed_insights: the dossier's
# analysis generated a new approach (its blocking constraint, inverted,
# became the next idea) — for open-ended work with no verifiable "fix".
CONFIRM_FIELDS = ("confirmed_fixes", "confirmed_insights")

REQUIRED_FRONTMATTER_FIELDS = (
    "dossier_version",
    "id",
    "created",
    "agent",
    "task",
    "outcome",
)
VALID_OUTCOMES = ("failed", "recovered")

# v0.2: what kind of failure the dossier autopsies. Pick the closest one —
# different classes fail (and get fixed) differently, so retrieval and
# review can treat them differently.
VALID_FAILURE_CLASSES = (
    "knowledge-gap",    # the agent lacked a fact it needed
    "reasoning-error",  # the facts were there; the reasoning went wrong
    "execution-slip",   # knew better; fumbled the execution (typo, wrong command)
    "tool-misuse",      # wrong tool for the job, or a tool used wrongly
    "misread-task",     # solved the wrong problem / misread the requirements
)

# Section titles, matched case-insensitively against ``##`` headers.
REQUIRED_SECTIONS = (
    "what was tried",
    "root cause",
    "failure signature",
    "blocking constraint",
    "what retrieval would have changed",
    "confidence",
)
OPTIONAL_SECTIONS = ("tokens",)

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

_STOPWORDS = frozenset(
    """
    a an the and or of to in on for with is was were are be been being
    it its this that these those as at by from into out up down over under
    about after before between during through without within against across
    such no not but only just also than then so very can could would should
    will shall may might must do does did done have has had having
    i you he she we they them their our your his her my me him us theirs
    what which who whom whose when where why how all any both each few more
    most other some too now new old own same another every
    """.split()
)


def slugify(text: str, max_len: int = 50) -> str:
    """Turn free text into a URL/file-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "dossier"


def extract_keywords(text: str) -> list[str]:
    """Lexical keywords: lowercased alphanumeric tokens, stopwords removed.

    This is deliberately dumb. v0.1 ranking is keyword overlap, not semantic
    similarity — no embeddings, no model calls.
    """
    keywords: list[str] = []
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if len(token) < 2 or token in _STOPWORDS or token in keywords:
            continue
        keywords.append(token)
    return keywords


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split ``---`` frontmatter from the body. Raises ValueError if malformed."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---' frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("missing closing '---' frontmatter delimiter") from None
    fields: dict[str, str] = {}
    for lineno, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(
                f"frontmatter line {lineno} is not 'key: value': {line!r}"
            )
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, "\n".join(lines[end + 1 :])


def get_sections(body: str) -> dict[str, str]:
    """Map lowercased ``##`` header titles to their stripped content."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        match = re.match(r"##\s+(.*)", line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = match.group(1).strip().lower()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def read_dossier(path: str | Path) -> dict:
    """Parse a dossier file. Raises ValueError on any structural problem."""
    text = Path(path).read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    return {
        "frontmatter": frontmatter,
        "sections": get_sections(body),
        "path": str(path),
    }


def validate_dossier(path: str | Path) -> list[str]:
    """Return a list of structural problems; empty list means valid."""
    errors: list[str] = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read file: {exc}"]
    try:
        frontmatter, body = split_frontmatter(text)
    except ValueError as exc:
        return [str(exc)]

    for field in REQUIRED_FRONTMATTER_FIELDS:
        if not frontmatter.get(field):
            errors.append(f"frontmatter: missing or empty field '{field}'")

    version = frontmatter.get("dossier_version", "")
    if version not in ACCEPTED_VERSIONS:
        if version:
            errors.append(
                f"frontmatter: dossier_version is {version!r}, "
                f"expected one of {ACCEPTED_VERSIONS}"
            )
    is_v02 = version == DOSSIER_VERSION

    # v0.2: failure_class is required; v0.1 dossiers predate it (legacy).
    failure_class = frontmatter.get("failure_class", "")
    if is_v02:
        if not failure_class:
            errors.append("frontmatter: missing required field 'failure_class'")
        elif failure_class not in VALID_FAILURE_CLASSES:
            errors.append(
                f"frontmatter: failure_class {failure_class!r} must be one of "
                f"{VALID_FAILURE_CLASSES}"
            )

    # confirmed_fixes / confirmed_insights are optional in the file; absent
    # means 0. Present must be a non-negative integer.
    for field in CONFIRM_FIELDS:
        confirmed_raw = frontmatter.get(field, "")
        if confirmed_raw:
            try:
                if int(confirmed_raw) < 0:
                    raise ValueError
            except ValueError:
                errors.append(
                    f"frontmatter: {field} {confirmed_raw!r} must be a "
                    f"non-negative integer"
                )

    dossier_id = frontmatter.get("id", "")
    if dossier_id and not _ID_RE.match(dossier_id):
        errors.append(
            f"frontmatter: id {dossier_id!r} must match [a-z0-9][a-z0-9-]*"
        )

    created = frontmatter.get("created", "")
    if created:
        try:
            date.fromisoformat(created)
        except ValueError:
            errors.append(
                f"frontmatter: created {created!r} is not an ISO date (YYYY-MM-DD)"
            )

    outcome = frontmatter.get("outcome", "")
    if outcome and outcome not in VALID_OUTCOMES:
        errors.append(
            f"frontmatter: outcome {outcome!r} must be one of {VALID_OUTCOMES}"
        )

    sections = get_sections(body)
    for section in REQUIRED_SECTIONS:
        if section not in sections:
            errors.append(f"section: missing required '## {section}'")
        elif not sections[section]:
            errors.append(f"section: '## {section}' is present but empty")

    return errors


_SECTION_GUIDANCE = {
    "What was tried": "_List each attempt as a bullet, in order: what was done._",
    "Root cause": "_One paragraph: the actual reason it failed, not the surface error._",
    "Failure signature": "_Name the reusable pattern and give a plain-words match rule: "
    "'if you see X in the first few turns, stop and retrieve this dossier.'_",
    "Blocking constraint": "_The fact about the repo, environment, or task that made the "
    "approaches fail — one to three sentences._",
    "What retrieval would have changed": "_Concretely: which early turn a second run would "
    "skip, and what it would do instead._",
    "Tokens": "_Optional: estimated tokens spent repeating failed approaches, "
    "with a one-line method note._",
    "Confidence": "_How confident are you in this autopsy? What would change your mind?_",
}


def render_template(
    task: str,
    agent: str,
    outcome: str = "failed",
    failure_class: str = "reasoning-error",
    created: str | None = None,
    id_: str | None = None,
    sections: dict[str, str] | None = None,
) -> str:
    """Render a dossier. ``sections`` maps lowercase titles to content; any
    section not given gets a short guidance line (a scaffold, not a dossier).

    ``failure_class`` must be one of VALID_FAILURE_CLASSES — the CLI's
    ``init`` forces an explicit choice; the default here exists so
    programmatic callers (and the test suite) aren't forced through argparse.
    """
    if failure_class not in VALID_FAILURE_CLASSES:
        raise ValueError(
            f"failure_class {failure_class!r} must be one of "
            f"{VALID_FAILURE_CLASSES}"
        )
    created = created or date.today().isoformat()
    id_ = id_ or f"{created}-{slugify(task)}"
    clean_task = task.replace('"', "'").strip()
    lines = [
        "---",
        f'dossier_version: "{DOSSIER_VERSION}"',
        f"id: {id_}",
        f"created: {created}",
        f"agent: {agent}",
        f'task: "{clean_task}"',
        f"outcome: {outcome}",
        f"failure_class: {failure_class}",
        "confirmed_fixes: 0",
        "confirmed_insights: 0",
        "---",
        "",
        f"# Failure dossier: {clean_task}",
        "",
    ]
    filled = {k.lower(): v for k, v in (sections or {}).items()}
    for title in (
        "What was tried",
        "Root cause",
        "Failure signature",
        "Blocking constraint",
        "What retrieval would have changed",
        "Tokens",
        "Confidence",
    ):
        lines.append(f"## {title}")
        lines.append(filled.get(title.lower(), _SECTION_GUIDANCE[title]))
        lines.append("")
    return "\n".join(lines)


def _confirmed_fixes_of(frontmatter: dict[str, str]) -> int:
    """confirmed_fixes as an int; absent or malformed means 0.

    Malformed values are caught by validate_dossier; the index stays lenient
    so a hand-edited file can't break ``index`` or ``recall``.
    """
    try:
        return max(0, int(frontmatter.get("confirmed_fixes", "") or 0))
    except ValueError:
        return 0


def _confirmed_insights_of(frontmatter: dict[str, str]) -> int:
    """confirmed_insights as an int; absent or malformed means 0."""
    try:
        return max(0, int(frontmatter.get("confirmed_insights", "") or 0))
    except ValueError:
        return 0


def build_index_entry(dossier_path: Path, base_dir: Path) -> dict:
    """Build one index.jsonl record from a validated dossier file."""
    parsed = read_dossier(dossier_path)
    fm = parsed["frontmatter"]
    sections = parsed["sections"]
    signature_text = sections.get("failure signature", "")
    signature_line = ""
    for line in signature_text.splitlines():
        cleaned = re.sub(r"[*_`#]", "", line).strip().rstrip(":")
        if cleaned:
            signature_line = cleaned
            break
    task_keywords = extract_keywords(fm["task"])
    sig_keywords = extract_keywords(signature_text)
    return {
        "id": fm["id"],
        "version": fm.get("dossier_version", ""),
        "task": fm["task"],
        "signature": signature_line[:140],
        "keywords": task_keywords + [k for k in sig_keywords if k not in task_keywords],
        "sig_keywords": sig_keywords,
        "failure_class": fm.get("failure_class") or None,
        "confirmed_fixes": _confirmed_fixes_of(fm),
        "confirmed_insights": _confirmed_insights_of(fm),
        "outcome": fm["outcome"],
        "path": str(dossier_path.relative_to(base_dir)),
        "created": fm["created"],
    }


def load_index_entries(index_path: Path) -> list[dict]:
    """Read back an index.jsonl file written by ``garm index``."""
    entries = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


_CONFIRMED_RE = re.compile(r'^(confirmed_fixes|confirmed_insights):\s*"?(\d+)"?\s*$')


def confirm_dossier(
    base_dir: str | Path, dossier_id: str, field: str = "confirmed_fixes"
) -> tuple[Path, int]:
    """Record that a retrieved dossier earned its keep in a later run.

    ``field`` is ``"confirmed_fixes"`` (default: the dossier prevented a
    specific repeat / fixed a verifiable failure) or
    ``"confirmed_insights"`` (the dossier's analysis generated a new
    approach — for open-ended work with no verifiable "fix").

    Finds the dossier whose frontmatter ``id`` matches, increments the
    counter (adding the field at 1 if absent), rewrites the file, and
    re-validates it. Returns (path, new_count).

    Raises ValueError if zero or more than one dossier matches the id,
    if ``field`` is not a known confirm field, or if the file fails
    validation after the bump.
    """
    if field not in CONFIRM_FIELDS:
        raise ValueError(
            f"unknown confirm field {field!r}; must be one of {CONFIRM_FIELDS}"
        )
    base = Path(base_dir)
    matches: list[Path] = []
    for md in sorted(base.rglob("*.md")):
        try:
            fm = read_dossier(md)["frontmatter"]
        except ValueError:
            continue
        if fm.get("id") == dossier_id:
            matches.append(md)
    if not matches:
        raise ValueError(f"no dossier with id {dossier_id!r} in {base}")
    if len(matches) > 1:
        raise ValueError(
            f"multiple dossiers with id {dossier_id!r}: "
            + ", ".join(str(m) for m in matches)
        )
    path = matches[0]
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"dossier {path} has malformed frontmatter")
    try:
        close_idx = lines.index("---\n", 1)
    except ValueError:
        try:
            close_idx = [l.strip() for l in lines].index("---", 1)
        except ValueError:
            raise ValueError(f"dossier {path} has malformed frontmatter") from None
    new_count = 1
    replaced = False
    for i in range(1, close_idx):
        match = _CONFIRMED_RE.match(lines[i].strip())
        if match and match.group(1) == field:
            new_count = int(match.group(2)) + 1
            lines[i] = f"{field}: {new_count}\n"
            replaced = True
            break
    if not replaced:
        lines.insert(close_idx, f"{field}: 1\n")
    path.write_text("".join(lines), encoding="utf-8")
    errors = validate_dossier(path)
    if errors:
        raise ValueError(
            f"dossier {path} failed validation after confirm: {errors}"
        )
    return path, new_count
