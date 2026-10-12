"""Premise registry: close big routes (v0.2.4). Stdlib only.

A dossier records *what* was tried; a premise records *what the attempts
rested on* — the load-bearing claims a whole family of approaches assumes.
Premises live in ``premises.json`` in the bank directory:

    {"version": "0.2.4",
     "premises": {"P-20261011-001": {
         "statement": "C7[K4] has a biplanar edge partition",
         "depends_on": [],
         "status": "open",          # or "killed"
         "killed_by": null,         # dossier id (or text) that killed it
         "created": "2026-10-11"}}}

Premises form a tree: a premise may ``depends_on`` parent premises, meaning
it assumes the parents hold. A big route is a premise other premises depend
on. Closing a big route closes every smaller route under it, transitively.
A dossier declares the premises it rests on in an optional ``## Premises``
section; it is a *dead route* when ANY of those premises is dead
(transitively). Recall excludes dead routes by default — one closed big
route closes a thousand small routes without running them.

Semantics are deliberately conservative: premises are *necessary*
assumptions (if the claim is false, the approach cannot work), so ANY dead
premise kills the dossier. A dossier with no Premises section is
unaffected. Unknown premise ids are treated as live (a dossier should
validate standalone) but produce a warning when the index is rebuilt.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

REGISTRY_FILENAME = "premises.json"
REGISTRY_VERSION = "0.2.4"

PREMISE_ID_RE = re.compile(r"^P-\d{8}-\d{3}$")

VALID_STATUSES = ("open", "killed")

# How strong the evidence was when a premise died. Plain words:
#   proof        -- we proved the claim false (a theorem, a structural kill)
#   our-tests    -- our own experiments ruled it out
#   outside-work -- someone else's published result killed it
VALID_EVIDENCE = ("proof", "our-tests", "outside-work")


def registry_path(base_dir: str | Path) -> Path:
    return Path(base_dir) / REGISTRY_FILENAME


def load_registry(base_dir: str | Path) -> dict:
    """Load the premise registry; an absent file means no premises yet."""
    path = registry_path(base_dir)
    if not path.exists():
        return {"version": REGISTRY_VERSION, "premises": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read premise registry {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(
        data.get("premises"), dict
    ):
        raise ValueError(f"premise registry {path} is malformed")
    return data


def save_registry(base_dir: str | Path, data: dict) -> None:
    path = registry_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _premises(data: dict) -> dict:
    return data.setdefault("premises", {})


def _next_id(data: dict, created: str) -> str:
    """Next free id of the form P-YYYYMMDD-NNN for ``created``."""
    prefix = "P-" + created.replace("-", "")
    used = {
        pid
        for pid in _premises(data)
        if isinstance(pid, str) and pid.startswith(prefix)
    }
    n = 1
    while f"{prefix}-{n:03d}" in used:
        n += 1
    return f"{prefix}-{n:03d}"


def _would_cycle(premises: dict, child: str, parent: str) -> bool:
    """True if making ``child`` depend on ``parent`` would create a cycle."""
    seen = set()
    stack = [parent]
    while stack:
        cur = stack.pop()
        if cur == child:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(premises.get(cur, {}).get("depends_on", []) or [])
    return False


def add_premise(
    base_dir: str | Path,
    statement: str,
    depends_on: list[str] | None = None,
    created: str | None = None,
) -> str:
    """Register a premise; returns its id. Raises ValueError on bad input.

    ``depends_on`` lists existing premise ids this premise assumes hold
    (the big routes it rests on). A premise cannot depend on itself, on unknown
    ids, or in a way that creates a cycle.
    """
    statement = (statement or "").strip()
    if not statement:
        raise ValueError("premise statement must not be empty")
    created = created or date.today().isoformat()
    deps = list(depends_on or [])
    data = load_registry(base_dir)
    premises = _premises(data)
    for dep in deps:
        if not isinstance(dep, str) or dep not in premises:
            raise ValueError(f"unknown parent premise {dep!r}")
    new_id = _next_id(data, created)
    for dep in deps:
        if _would_cycle(premises, new_id, dep):
            raise ValueError(
                f"depends_on {dep!r} would create a dependency cycle"
            )
    premises[new_id] = {
        "statement": statement,
        "depends_on": deps,
        "status": "open",
        "killed_by": None,
        "created": created,
    }
    data["version"] = REGISTRY_VERSION
    save_registry(base_dir, data)
    return new_id


def is_dead(data: dict, premise_id: str) -> bool:
    """True if the premise is killed directly or via a killed ancestor."""
    premises = data.get("premises", {})
    seen = set()
    stack = [premise_id]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        entry = premises.get(cur)
        if entry is None:
            continue  # unknown premise: treated as live (warned at index time)
        if entry.get("status") == "killed":
            return True
        stack.extend(entry.get("depends_on", []) or [])
    return False


def descendants(data: dict, premise_id: str) -> set[str]:
    """All premise ids that (transitively) depend on ``premise_id``."""
    premises = data.get("premises", {})
    found: set[str] = set()
    changed = True
    while changed:
        changed = False
        for pid, entry in premises.items():
            if pid == premise_id or pid in found:
                continue
            deps = set(entry.get("depends_on", []) or [])
            if premise_id in deps or deps & found:
                found.add(pid)
                changed = True
    return found


def kill_premise(
    base_dir: str | Path,
    premise_id: str,
    killed_by: str,
    evidence: str | None = None,
) -> dict:
    """Kill a premise. Returns {"killed": [ids closed transitively],
    "already_killed": bool}.

    The premise itself plus every descendant premise counts as killed.
    ``killed_by`` is the dossier id (or a short text note) recording what
    proved the claim false. ``evidence`` is how strong the evidence was:
    one of "proof", "our-tests", "outside-work" (see VALID_EVIDENCE); it
    is recorded on the premise and inherited by every premise closed
    transitively. Killing an already-killed premise is a no-op that
    reports ``already_killed``.
    """
    if not killed_by or not str(killed_by).strip():
        raise ValueError("killed_by must name the dossier (or note) that killed it")
    if evidence is not None and evidence not in VALID_EVIDENCE:
        raise ValueError(
            f"evidence must be one of {VALID_EVIDENCE}: "
            "proof (we proved it false), our-tests (our experiments ruled "
            "it out), outside-work (someone else's result)"
        )
    data = load_registry(base_dir)
    premises = data.get("premises", {})
    entry = premises.get(premise_id)
    if entry is None:
        raise ValueError(f"unknown premise {premise_id!r}")
    if entry.get("status") == "killed":
        return {"killed": [], "already_killed": True}
    entry["status"] = "killed"
    entry["killed_by"] = str(killed_by).strip()
    if evidence is not None:
        entry["evidence"] = evidence
    killed = {premise_id}
    for pid in descendants(data, premise_id):
        premises[pid]["status"] = "killed"
        if not premises[pid].get("killed_by"):
            premises[pid]["killed_by"] = f"inherited from {premise_id}"
        if evidence is not None and not premises[pid].get("evidence"):
            premises[pid]["evidence"] = evidence
        killed.add(pid)
    save_registry(base_dir, data)
    return {"killed": sorted(killed), "already_killed": False}


def list_premises(base_dir: str | Path) -> list[dict]:
    """All premises as dicts with computed ``dead`` flag, sorted by id."""
    data = load_registry(base_dir)
    rows = []
    for pid in sorted(data.get("premises", {})):
        entry = data["premises"][pid]
        rows.append(
            {
                "id": pid,
                "statement": entry.get("statement", ""),
                "depends_on": entry.get("depends_on", []) or [],
                "status": entry.get("status", "open"),
                "killed_by": entry.get("killed_by"),
                "evidence": entry.get("evidence"),
                "created": entry.get("created", ""),
                "dead": is_dead(data, pid),
            }
        )
    return rows


def parse_premise_refs(section_text: str) -> list[str]:
    """Extract premise ids from a ``## Premises`` section.

    One id per line: a bullet (``-``/``*``/``•``) or a bare id. Lines that
    don't match ``P-...`` are ignored — the section stays human-readable.
    """
    refs: list[str] = []
    for line in (section_text or "").splitlines():
        stripped = line.strip().lstrip("-*•").strip()
        if PREMISE_ID_RE.match(stripped) and stripped not in refs:
            refs.append(stripped)
    return refs


def dossier_dead_premises(data: dict, premise_refs: list[str]) -> list[str]:
    """The subset of a dossier's premise refs that are dead (transitively)."""
    return [pid for pid in premise_refs if is_dead(data, pid)]


def merge_registry(
    dest_dir: str | Path, incoming: dict
) -> dict[str, list]:
    """Merge an imported ``premises.json`` into the destination bank.

    Never overwrites: ids that already exist are kept (collisions with a
    *different* statement are skipped and reported). Returns
    ``{"added": [ids], "skipped": [(id, reason)]}``.
    """
    dest = load_registry(dest_dir)
    dest_p = _premises(dest)
    added: list[str] = []
    skipped: list[tuple[str, str]] = []
    for pid, entry in (incoming.get("premises") or {}).items():
        if not isinstance(pid, str) or not PREMISE_ID_RE.match(pid):
            skipped.append((str(pid), "malformed premise id"))
            continue
        if not isinstance(entry, dict):
            skipped.append((pid, "malformed premise entry"))
            continue
        if pid in dest_p:
            if dest_p[pid].get("statement") == entry.get("statement"):
                skipped.append((pid, "already registered (identical)"))
            else:
                skipped.append(
                    (pid, "id collision with different statement — kept local")
                )
            continue
        if entry.get("status") not in VALID_STATUSES:
            skipped.append((pid, "unknown status"))
            continue
        if entry.get("evidence") is not None and entry.get("evidence") not in VALID_EVIDENCE:
            skipped.append((pid, "unknown evidence value"))
            continue
        dest_p[pid] = {
            "statement": entry.get("statement", ""),
            "depends_on": list(entry.get("depends_on", []) or []),
            "status": entry.get("status", "open"),
            "killed_by": entry.get("killed_by"),
            "evidence": entry.get("evidence"),
            "created": entry.get("created", ""),
        }
        added.append(pid)
    dest["version"] = REGISTRY_VERSION
    save_registry(dest_dir, dest)
    return {"added": sorted(added), "skipped": skipped}
