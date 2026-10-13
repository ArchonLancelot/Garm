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
v1.1 adds ``origin`` (optional): where the dossier came from, for imported
banks — see ``garm import``. Absent means the dossier is yours; it resolves
to the ``agent`` field.
v0.2.2 adds two optional sections, ``## Challengeable premises`` and
``## Open questions``: the load-bearing assumptions (phrased to be
negatable) and the precise questions the failure left open. Motivated by
the first foreign-agent field test (2026-10-11), where negating a stated
premise produced the genuinely new idea.
v0.2.3: ``validate`` rejects sections left as the scaffold's placeholder
guidance text (a scaffold is not a dossier — found by the same field
test's machinery run); ``import`` skips byte-identical duplicates instead
of renaming them.
v0.2.4: premise registry (``premises.json``) and big-route closing. A dossier may
declare an optional ``## Premises`` section listing the premise ids its
approach rests on (see ``garm/premise.py``). A premise is a load-bearing
claim a whole family of approaches assumes; closing a big route (a premise
other premises depend on) closes every premise under it transitively, and
every dossier resting on a dead premise becomes a dead route. The index
records each dossier's premises
and a ``premise_dead`` flag; ``recall`` excludes dead routes by default.
v0.2.5: assisted autopsy drafting (``garm/autopsy.py``, ``garm autopsy``):
a closing-ceremony interview that writes answers into a pre-filled
dossier draft. The dossier format itself is unchanged.
v0.2.6: hybrid retrieval (``garm/retrieval.py``): recall matches over
canonicalized text (Unicode math symbols become words) with a curated
synonym map, so paraphrases match. Still lexical — no embeddings. The
dossier format itself is unchanged.
v0.1 dossiers still validate; they are treated as legacy and simply lack
the new fields.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from . import retrieval as RU

SPEC_VERSION = "0.2.6"
DOSSIER_VERSION = "0.2"
ACCEPTED_VERSIONS = ("0.1", "0.2")

# Confirmable counters. confirmed_fixes: the dossier prevented a specific
# repeat / fixed a verifiable failure. confirmed_insights: the dossier's
CONFIRM_NOTE_MAX_LEN = 140
_NOTE_RE = re.compile(r"^confirm_note_(\d+):")
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
# v0.2.2: two more optional sections. "Challengeable premises" lists the
# load-bearing assumptions phrased so a reader can negate them (negating one
# produced the new idea in the first foreign-agent field test); "Open
# questions" captures the precise questions the failure left behind.
OPTIONAL_SECTIONS = ("tokens", "challengeable premises", "open questions", "premises")

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

    v0.2.6: Unicode math symbols are canonicalized to words first (see
    ``garm/retrieval.py``), so "χ(G)" and "chromatic number" share
    keywords. Still no embeddings, no model calls — just smarter
    tokenizing. Synonym expansion happens at match time, not here.
    """
    keywords: list[str] = []
    for token in re.findall(r"[a-z0-9]+", RU.canonicalize_text(text).lower()):
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

    # v0.2.3: a scaffold is not a dossier. A *required* section whose
    # content is still exactly the template's placeholder guidance text
    # fails — otherwise `init` output would validate untouched and banks
    # could fill with blank autopsies that all pass. (Optional sections
    # are exempt: they may simply be deleted, so placeholder text there
    # is a cosmetic wart, not an empty autopsy.)
    for section in REQUIRED_SECTIONS:
        content = sections.get(section, "")
        guidance = _GUIDANCE_BY_TITLE.get(section)
        if guidance and content.strip() == guidance:
            errors.append(
                f"section: '## {section}' still has the scaffold placeholder "
                f"text — fill it in honestly (a template is not a dossier)"
            )

    return errors


_SECTION_GUIDANCE = {
    "What was tried": "_List each attempt as a bullet, in order: what was done._",
    "Root cause": "_One paragraph: the actual reason it failed, not the surface error._",
    "Failure signature": "_Name the reusable pattern and give a plain-words match rule: "
    "'if you see X in the first few turns, stop and retrieve this dossier.'_",
    "Blocking constraint": "_The fact about the repo, environment, or task that made the "
    "approaches fail — one to three sentences._",
    "Challengeable premises": "_The load-bearing assumptions the attempts rested on, "
    "each phrased so a future reader can ask 'what if this is false?' Negating "
    "one is often the next idea._",
    "What retrieval would have changed": "_Concretely: which early turn a second run would "
    "skip, and what it would do instead._",
    "Open questions": "_Precise questions this failure left open for a future run to "
    "aim at — not background, but targets._",
    "Premises": "_Optional: premise ids this approach rested on, one per line "
    "(see `garm premise list`). A premise is a load-bearing claim a whole "
    "family of approaches assumes; if any listed premise is killed "
    "(`garm premise kill`), this dossier becomes a dead route and recall "
    "skips it._",
    "Tokens": "_Optional: estimated tokens spent repeating failed approaches, "
    "with a one-line method note._",
    "Confidence": "_How confident are you in this autopsy? What would change your mind?_",
}


# Lowercase section title -> stripped placeholder guidance text, for the
# v0.2.3 scaffold check in validate_dossier.
_GUIDANCE_BY_TITLE = {
    title.lower(): guidance.strip() for title, guidance in _SECTION_GUIDANCE.items()
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
        "Challengeable premises",
        "What retrieval would have changed",
        "Open questions",
        "Premises",
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


def _origin_of(frontmatter: dict[str, str]) -> str:
    """Where the dossier came from. Optional ``origin`` field; absent (or
    empty) resolves to the ``agent`` field — a dossier you wrote is yours.
    Free text, no format enforced: it's a provenance label, not a key.
    """
    return frontmatter.get("origin") or frontmatter.get("agent") or ""


def build_index_entry(dossier_path: Path, base_dir: Path,
                      registry: dict | None = None) -> dict:
    """Build one index.jsonl record from a validated dossier file.

    ``registry`` is the loaded premise registry (see ``garm/premise.py``);
    when given, the entry records the dossier's premise refs and whether
    any of them is dead (transitively) — the big-route flag that
    ``recall`` uses to skip dead routes.
    """
    from . import premise as P

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
    premise_refs = P.parse_premise_refs(sections.get("premises", ""))
    dead_premises: list[str] = []
    if registry is not None and premise_refs:
        dead_premises = P.dossier_dead_premises(registry, premise_refs,
                                               dossier_id=fm["id"])
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
        "origin": _origin_of(fm),
        "outcome": fm["outcome"],
        "path": str(dossier_path.relative_to(base_dir)),
        "created": fm["created"],
        "premises": premise_refs,
        "premise_dead": bool(dead_premises),
    }


def rebuild_index(base_dir: str | Path) -> tuple[int, int]:
    """Rebuild ``index.jsonl`` in ``base_dir``. Returns (indexed, skipped).

    The index is fully derived from the dossier files: invalid ones are
    skipped with a warning on stderr. Rebuilding is byte-identical for
    unchanged input.
    """
    base = Path(base_dir)
    entries = []
    skipped = 0
    try:
        from . import premise as P
        registry = P.load_registry(base)
    except ValueError as exc:
        print(f"warning: {exc}", file=sys.stderr)
        registry = {"premises": {}}
    known = set(registry.get("premises", {}))
    for md in sorted(base.rglob("*.md")):
        errors = validate_dossier(md)
        if errors:
            print(f"warning: skipping invalid dossier {md}", file=sys.stderr)
            skipped += 1
            continue
        entry = build_index_entry(md, base, registry)
        unknown = [pid for pid in entry["premises"] if pid not in known]
        if unknown:
            print(
                f"warning: dossier {entry['id']} references unknown "
                f"premise(s) {', '.join(unknown)} (treated as live)",
                file=sys.stderr,
            )
        entries.append(entry)
    entries.sort(key=lambda e: e["id"])
    index_path = base / "index.jsonl"
    with index_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return len(entries), skipped


def init_dossier(
    task: str,
    agent: str,
    failure_class: str,
    outcome: str = "failed",
    out_dir: str | Path = "dossiers",
    created: str | None = None,
) -> Path:
    """Scaffold a new dossier file in ``out_dir``. Returns the file path.

    The id is ``<created>-<task-slug>`` (slug truncated to 50 chars),
    with ``-2``, ``-3``... appended on filename collision. ``created``
    defaults to the machine's local date. A scaffold is not a dossier:
    fill every section honestly, then validate (placeholder text fails).
    """
    if failure_class not in VALID_FAILURE_CLASSES:
        raise ValueError(
            f"failure_class {failure_class!r} must be one of "
            f"{VALID_FAILURE_CLASSES}"
        )
    if outcome not in VALID_OUTCOMES:
        raise ValueError(
            f"outcome {outcome!r} must be one of {VALID_OUTCOMES}"
        )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    created = created or date.today().isoformat()
    dossier_id = f"{created}-{slugify(task)}"
    path = out / f"{dossier_id}.md"
    n = 2
    while path.exists():
        path = out / f"{dossier_id}-{n}.md"
        n += 1
    text = render_template(
        task=task, agent=agent, outcome=outcome,
        failure_class=failure_class, created=created, id_=path.stem,
    )
    path.write_text(text, encoding="utf-8")
    return path


def load_index_entries(index_path: Path) -> list[dict]:
    """Read back an index.jsonl file written by ``garm index``."""
    entries = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


_CONFIRMED_RE = re.compile(r'^(confirmed_fixes|confirmed_insights):\s*"?(\d+)"?\s*$')


def confirm_dossier(
    base_dir: str | Path, dossier_id: str, field: str = "confirmed_fixes",
    note: str | None = None,
) -> tuple[Path, int]:
    """Record that a retrieved dossier earned its keep in a later run.

    ``field`` is ``"confirmed_fixes"`` (default: the dossier prevented a
    specific repeat / fixed a verifiable failure) or
    ``"confirmed_insights"`` (the dossier's analysis generated a new
    approach — for open-ended work with no verifiable "fix").

    ``note`` is optional: a one-line description of what the fix was
    (max 140 chars), stored as ``confirm_note_N`` in the frontmatter so the
    track record is auditable — a reader can see what each confirm was for,
    not just the count. Notes don't verify the fix; they document the
    claim.

    Finds the dossier whose frontmatter ``id`` matches, increments the
    counter (adding the field at 1 if absent), rewrites the file, and
    re-validates it. Returns (path, new_count).

    Raises ValueError if zero or more than one dossier matches the id,
    if ``field`` is not a known confirm field, if the note is empty or too
    long, or if the file fails validation after the bump.
    """
    if field not in CONFIRM_FIELDS:
        raise ValueError(
            f"unknown confirm field {field!r}; must be one of {CONFIRM_FIELDS}"
        )
    clean_note: str | None = None
    if note is not None:
        clean_note = " ".join(str(note).split())
        if not clean_note:
            raise ValueError("confirm note must not be empty")
        if len(clean_note) > CONFIRM_NOTE_MAX_LEN:
            raise ValueError(
                f"confirm note is {len(clean_note)} chars; "
                f"max is {CONFIRM_NOTE_MAX_LEN}"
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
    if clean_note is not None:
        max_n = 0
        for i in range(1, close_idx):
            m = _NOTE_RE.match(lines[i].strip())
            if m:
                max_n = max(max_n, int(m.group(1)))
        lines.insert(close_idx, f'confirm_note_{max_n + 1}: "{clean_note}"\n')
    path.write_text("".join(lines), encoding="utf-8")
    errors = validate_dossier(path)
    if errors:
        raise ValueError(
            f"dossier {path} failed validation after confirm: {errors}"
        )
    return path, new_count


_ID_LINE_RE = re.compile(r"^id:\s*([a-z0-9][a-z0-9-]*)", re.MULTILINE)


def _rewrite_id(text: str, new_id: str) -> str:
    """Replace the frontmatter ``id:`` line. The file was validated, so the
    line exists exactly once in the frontmatter block."""
    return _ID_LINE_RE.sub(f"id: {new_id}", text, count=1)


def _unique_import_id(wanted: str, agent: str, taken: set[str]) -> str:
    """Rename on collision: ``<id>--from-<agent>``, with -2, -3... if that
    also collides. Never silently overwrites an existing dossier."""
    if wanted not in taken:
        return wanted
    base = f"{wanted}--from-{slugify(agent or 'unknown')}"
    cand, n = base, 2
    while cand in taken:
        cand = f"{base}-{n}"
        n += 1
    return cand


def import_dossiers(
    source: str | Path, dest_dir: str | Path
) -> dict[str, list]:
    """Import dossiers from another bank into ``dest_dir``.

    ``source`` is a directory (every ``*.md`` in it, non-recursive) or a
    single ``.md`` file. Each incoming dossier is validated first; invalid
    ones are skipped with their reasons. Id collisions are renamed via
    ``_unique_import_id`` — never overwritten. Files already living at
    their destination path (self-import) are skipped.

    Returns ``{"imported": [(old_id, new_id, dest_path_str)], "skipped":
    [(source_name, reason)], "premises": {"added": [ids], "skipped":
    [(id, reason)]}}``. Does not re-index; the caller does that.

    The source bank's ``premises.json`` is merged into the destination's
    registry when present (never overwrites — colliding ids with different
    statements are kept local and reported).
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    src = Path(source)

    if src.is_file():
        candidates = [src]
    elif src.is_dir():
        candidates = sorted(src.glob("*.md"))
    else:
        raise ValueError(f"import source not found: {src}")
    if src.is_dir() and src.resolve() == dest.resolve():
        raise ValueError(
            f"import source is the destination directory itself: {src}"
        )

    taken: set[str] = set()
    by_id: dict[str, Path] = {}
    for md in sorted(dest.rglob("*.md")):
        try:
            did = read_dossier(md)["frontmatter"].get("id", "")
        except ValueError:
            continue
        if did:
            taken.add(did)
            by_id.setdefault(did, md)
    taken.discard("")

    imported: list[tuple[str, str, str]] = []
    skipped: list[tuple[str, str]] = []
    premises_merged: dict[str, list] = {"added": [], "skipped": []}
    if src.is_dir():
        reg_file = src / "premises.json"
        if reg_file.exists():
            from . import premise as P

            try:
                incoming = json.loads(reg_file.read_text(encoding="utf-8"))
                premises_merged = P.merge_registry(dest, incoming)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                skipped.append(("premises.json", f"registry not merged: {exc}"))
    for cand_path in candidates:
        errors = validate_dossier(cand_path)
        if errors:
            skipped.append(
                (cand_path.name, "; ".join(errors[:3]))
            )
            continue
        fm = read_dossier(cand_path)["frontmatter"]
        old_id = fm.get("id", "")
        dest_path = dest / f"{old_id}.md"
        try:
            if dest_path.resolve() == cand_path.resolve():
                skipped.append((cand_path.name, "already in bank"))
                continue
        except OSError:
            pass
        # v0.2.3: an id collision with byte-identical content is a
        # re-import, not a new dossier — skip it instead of renaming.
        existing = by_id.get(old_id)
        if existing is not None and existing.read_bytes() == cand_path.read_bytes():
            skipped.append((cand_path.name, "already in bank (identical content)"))
            continue
        new_id = _unique_import_id(old_id, fm.get("agent", ""), taken)
        text = cand_path.read_text(encoding="utf-8")
        if new_id != old_id:
            text = _rewrite_id(text, new_id)
            # re-validate after the rename (id format is enforced)
            fm2, _ = split_frontmatter(text)
            if not _ID_RE.match(fm2.get("id", "")):
                skipped.append(
                    (cand_path.name, f"renamed id {new_id!r} is invalid")
                )
                continue
        final_path = dest / f"{new_id}.md"
        final_path.write_text(text, encoding="utf-8")
        taken.add(new_id)
        by_id.setdefault(new_id, final_path)
        imported.append((old_id, new_id, str(final_path)))
    return {
        "imported": imported,
        "skipped": skipped,
        "premises": premises_merged,
    }


def export_bank(
    src_dir: str | Path, out_dir: str | Path
) -> dict[str, list]:
    """Copy validated dossier ``.md`` files (not the derived index.jsonl)
    to ``out_dir`` for sharing. The premise registry (``premises.json``) is
    copied too, when present. Returns ``{"copied": [names], "skipped":
    [(name, reason)]}``.
    """
    src = Path(src_dir)
    out = Path(out_dir)
    if not src.is_dir():
        raise ValueError(f"dossier directory not found: {src}")
    out.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[tuple[str, str]] = []
    reg = src / "premises.json"
    if reg.exists():
        (out / "premises.json").write_text(
            reg.read_text(encoding="utf-8"), encoding="utf-8"
        )
        copied.append("premises.json")
    for md in sorted(src.rglob("*.md")):
        if md.name == "index.jsonl":
            continue
        errors = validate_dossier(md)
        if errors:
            skipped.append((md.name, "; ".join(errors[:3])))
            continue
        try:
            rel = md.relative_to(src)
        except ValueError:
            rel = Path(md.name)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append(str(rel))
    return {"copied": copied, "skipped": skipped}
