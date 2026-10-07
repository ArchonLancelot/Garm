"""Read, write, and validate v0.1 failure dossiers. Stdlib only.

A dossier is a Markdown file: a simple ``key: value`` frontmatter block
between ``---`` delimiters, then ``##`` sections. Validation is structural —
it checks that the required fields and sections exist and are non-empty. It
does not (and cannot) check whether the analysis is true.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

DOSSIER_VERSION = "0.1"

REQUIRED_FRONTMATTER_FIELDS = (
    "dossier_version",
    "id",
    "created",
    "agent",
    "task",
    "outcome",
)
VALID_OUTCOMES = ("failed", "recovered")

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

    if frontmatter.get("dossier_version") not in (DOSSIER_VERSION,):
        if frontmatter.get("dossier_version"):
            errors.append(
                f"frontmatter: dossier_version is "
                f"{frontmatter['dossier_version']!r}, expected {DOSSIER_VERSION!r}"
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
    created: str | None = None,
    id_: str | None = None,
    sections: dict[str, str] | None = None,
) -> str:
    """Render a dossier. ``sections`` maps lowercase titles to content; any
    section not given gets a short guidance line (a scaffold, not a dossier)."""
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
    keywords = extract_keywords(fm["task"] + " " + signature_text)
    return {
        "id": fm["id"],
        "task": fm["task"],
        "signature": signature_line[:140],
        "keywords": keywords,
        "outcome": fm["outcome"],
        "path": str(dossier_path.relative_to(base_dir)),
        "created": fm["created"],
    }


def load_index_entries(index_path: Path) -> list[dict]:
    """Read back an index.jsonl file written by ``autopsy index``."""
    entries = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries
