"""Hybrid retrieval: lexical scoring over canonicalized text with synonym
aliases. v0.2.6.

Still no embeddings, no model calls, no network. Two upgrades over pure
keyword overlap:

1. Symbol canonicalization: Unicode math symbols become words *before*
   tokenizing, so ``χ(G)`` and "chromatic number" share keywords, ``x²``
   becomes the token ``x2``, and ``C₇`` matches ``C7``.
2. Synonym aliases: a curated, readable map of equivalent terms. A query
   for "flaky" matches a dossier about "intermittent" failures; "primes"
   matches "prime"; "coloring" matches "chromatic".

The scoring *shape* is unchanged (signature terms count double, task
terms single, confirms boost up to 5 each) — the only change is WHAT
counts as a match. Recall output shows alias matches as
``query~dossier-term`` so the matching stays inspectable; nothing is
a black box.

The synonym map is data, not intelligence: hand-curated, deliberately
incomplete, and fully visible below. If a paraphrase isn't in the map,
it won't match — that's the honest limit of this approach, and the
reason a future opt-in semantic backend would plug in at ``score()``:
it is the single scoring funnel, so a ``--semantic`` flag could one day
blend an embedding cosine into the total and mark it in the display.
"""

from __future__ import annotations

import re

# Unicode symbol -> words, applied before tokenizing. Entries that would
# glue onto a preceding word character get a leading space ("x²" -> "x 2",
# "p′" -> "p prime"); everything else is split by the tokenizer anyway.
# Mappings that would only produce stopwords ("→" -> "to") are harmless:
# the stopword filter drops them.
SYMBOL_MAP: dict[str, str] = {
    # Greek letters -> names.
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta",
    "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
    "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu",
    "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi",
    "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta",
    "Ε": "epsilon", "Ζ": "zeta", "Η": "eta", "Θ": "theta",
    "Ι": "iota", "Κ": "kappa", "Λ": "lambda", "Μ": "mu",
    "Ν": "nu", "Ξ": "xi", "Ο": "omicron", "Π": "pi",
    "Ρ": "rho", "Σ": "sigma", "Τ": "tau", "Υ": "upsilon",
    "Φ": "phi", "Χ": "chi", "Ψ": "psi", "Ω": "omega",
    # Superscript / subscript digits -> spaced digits ("x²" -> "x 2").
    "⁰": " 0", "¹": " 1", "²": " 2", "³": " 3", "⁴": " 4",
    "⁵": " 5", "⁶": " 6", "⁷": " 7", "⁸": " 8", "⁹": " 9",
    "₀": " 0", "₁": " 1", "₂": " 2", "₃": " 3", "₄": " 4",
    "₅": " 5", "₆": " 6", "₇": " 7", "₈": " 8", "₉": " 9",
    # Prime marks -> the word "prime" ("p′" -> "p prime").
    "′": " prime", "″": " doubleprime", "‴": " tripleprime",
    # Logic, sets, relations -> words (or stopwords, which are dropped).
    "∀": "forall", "∃": "exists", "∈": "in", "∉": "notin",
    "∋": "contains", "⊂": "subset", "⊆": "subseteq",
    "⊃": "superset", "⊇": "supseteq",
    "∪": "union", "∩": "intersection", "∅": "emptyset",
    "∧": "and", "∨": "or", "¬": "not", "⊕": "xor", "⊗": "tensor",
    "→": "to", "⇒": "implies", "⇔": "iff", "↔": "iff",
    "≡": "equiv", "≅": "cong", "≈": "approx", "∼": "sim",
    "≠": "ne", "≤": "le", "≥": "ge",
    "∞": "infinity", "∑": "sum", "∏": "product",
    "√": "sqrt", "∂": "partial", "∇": "nabla", "∫": "integral",
    "⊥": "bot", "⊤": "top", "×": "times", "÷": "div",
    "±": "plusminus", "⌈": "ceil", "⌊": "floor",
    "ℵ": "aleph", "ℶ": "beth",
}

_SYMBOL_TABLE = {ord(k): v for k, v in SYMBOL_MAP.items()}

# Super/subscript digits that directly follow a word character glue onto it
# ("x²" -> "x2", "C₇" -> "C7") so the token survives the length filter;
# standalone ones still space out ("²" -> " 2", dropped as noise).
_DIGIT_GLYPHS = "⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉"
_DIGIT_VALUES = "0123456789" * 2
_GLUE_RE = re.compile(f"([A-Za-z0-9])([{_DIGIT_GLYPHS}]+)")
_GLUE_TABLE = {g: v for g, v in zip(_DIGIT_GLYPHS, _DIGIT_VALUES)}


def _glue_digits(match: re.Match[str]) -> str:
    return match.group(1) + "".join(_GLUE_TABLE[c] for c in match.group(2))


def canonicalize_text(text: str) -> str:
    """Replace Unicode math symbols with words before tokenizing."""
    text = _GLUE_RE.sub(_glue_digits, text)
    return text.translate(_SYMBOL_TABLE)


# Groups of equivalent single tokens. Every member of a group matches every
# other member: a query for one matches a dossier containing any of them.
# Curated from the shipped banks' vocabulary plus common failure words.
# Deliberately incomplete — this is a dictionary, not understanding.
SYNONYM_GROUPS: list[frozenset[str]] = [
    # --- math (Baillie-PSW / Earth-Moon vocab) ---
    frozenset({"prime", "primes", "primality"}),
    frozenset({"composite", "composites"}),
    frozenset({"pseudoprime", "pseudoprimes"}),
    frozenset({"millerrabin", "miller", "rabin"}),
    frozenset({"squarefree", "square"}),
    frozenset({"chi", "chromatic", "coloring", "colouring",
               "colorable", "colourable"}),
    frozenset({"biplanar", "planar", "planarity"}),
    frozenset({"graph", "graphs"}),
    frozenset({"vertex", "vertices"}),
    frozenset({"edge", "edges"}),
    frozenset({"clique", "cliques"}),
    frozenset({"fiber", "fibers", "fibre", "fibres"}),
    frozenset({"triangulation", "triangulations"}),
    frozenset({"partition", "partitions", "partitioned"}),
    frozenset({"component", "components"}),
    frozenset({"conjecture", "conjectures"}),
    frozenset({"theorem", "theorems", "lemma", "lemmas",
               "proposition", "propositions"}),
    frozenset({"proof", "proofs", "proved", "prove"}),
    frozenset({"bound", "bounds", "bounded"}),
    frozenset({"sieve", "sieves"}),
    frozenset({"modular", "modulo", "congruence", "congruent"}),
    frozenset({"divisor", "divisors", "factor", "factors"}),
    frozenset({"multiple", "multiples"}),
    frozenset({"residue", "residues"}),
    frozenset({"counterexample", "counterexamples"}),
    # --- general failure words ---
    frozenset({"flaky", "intermittent", "nondeterministic", "sporadic"}),
    frozenset({"bug", "bugs", "defect", "defects", "fault", "faults"}),
    frozenset({"crash", "crashes", "crashed", "hang", "hangs",
               "freeze", "freezes"}),
    frozenset({"slow", "slowness", "latency", "sluggish"}),
    frozenset({"timeout", "timeouts", "timed"}),
    frozenset({"retry", "retries", "retried", "retrying"}),
    frozenset({"race", "races", "racing", "racy"}),
    frozenset({"deadlock", "deadlocks", "livelock", "livelocks"}),
    frozenset({"leak", "leaks", "leaking"}),
    frozenset({"error", "errors", "failure", "failures", "failed",
               "failing", "fail"}),
    frozenset({"exception", "exceptions"}),
    frozenset({"wrong", "incorrect", "mistaken"}),
    frozenset({"missing", "absent"}),
    frozenset({"duplicate", "duplicates", "dedupe"}),
    frozenset({"stale"}),
    frozenset({"empty"}),
    frozenset({"corrupt", "corruption", "corrupted"}),
    frozenset({"regression", "regressions"}),
    frozenset({"bottleneck", "bottlenecks"}),
    # --- testing / debugging ---
    frozenset({"test", "tests", "testing", "tested"}),
    frozenset({"reproduce", "reproduces", "reproduced", "reproducible",
               "repro"}),
    frozenset({"bisect", "bisected", "bisecting"}),
    frozenset({"verify", "verifies", "verified", "verification",
               "validate", "validates", "validated", "validation"}),
    frozenset({"harness", "harnesses"}),
    frozenset({"suite", "suites"}),
    frozenset({"fixture", "fixtures"}),
    frozenset({"mock", "mocks", "mocking", "stub", "stubs"}),
    frozenset({"seed", "seeds", "seeded"}),
    frozenset({"random", "randomness"}),
    frozenset({"deterministic"}),
    # --- building / shipping ---
    frozenset({"build", "builds", "building"}),
    frozenset({"deploy", "deploys", "deployment", "deploying"}),
    frozenset({"rollback", "rollbacks"}),
    frozenset({"migration", "migrations", "migrate"}),
    frozenset({"schema", "schemas"}),
    frozenset({"config", "configs", "configuration"}),
    # --- runtime / infra ---
    frozenset({"queue", "queues", "queued", "enqueue", "dequeue"}),
    frozenset({"cache", "caches", "caching", "cached"}),
    frozenset({"worker", "workers"}),
    frozenset({"thread", "threads"}),
    frozenset({"process", "processes"}),
    frozenset({"connection", "connections"}),
    frozenset({"request", "requests"}),
    frozenset({"response", "responses"}),
    frozenset({"concurrent", "concurrency", "parallel", "parallelism"}),
    frozenset({"async", "asynchronous"}),
    frozenset({"auth", "authentication", "login"}),
    frozenset({"memory", "oom"}),
    frozenset({"api", "apis"}),
    frozenset({"endpoint", "endpoints"}),
    frozenset({"token", "tokens"}),
    # --- data ---
    frozenset({"index", "indexes", "indices", "indexed", "indexing"}),
    frozenset({"search", "searches", "searching", "query", "queries"}),
    frozenset({"match", "matches", "matching", "matched"}),
    frozenset({"filter", "filters", "filtering"}),
    frozenset({"sort", "sorting", "sorted"}),
    frozenset({"parse", "parses", "parsing", "parser"}),
    frozenset({"serialize", "serializes", "serialization"}),
    # --- agent / model ---
    frozenset({"agent", "agents"}),
    frozenset({"model", "models"}),
    frozenset({"prompt", "prompts"}),
    frozenset({"context", "contexts"}),
    frozenset({"session", "sessions"}),
]

# token -> the full alias set (every group containing it, unioned).
_ALIAS_INDEX: dict[str, frozenset[str]] = {}
for _group in SYNONYM_GROUPS:
    for _token in _group:
        _ALIAS_INDEX[_token] = _ALIAS_INDEX.get(_token, frozenset()) | _group


def aliases_for(keyword: str) -> frozenset[str]:
    """The alias set for a query keyword: itself plus every synonym in the
    curated map. Unknown words match only themselves."""
    return _ALIAS_INDEX.get(keyword, frozenset({keyword}))


def find_match(query_key: str, keywords: list[str]) -> str | None:
    """The dossier keyword a query key matches, or None.

    Prefers the exact keyword; otherwise the first alias (in alias-set
    order) present in the dossier's keywords. Deterministic: alias sets
    are iterated sorted for a stable pick.
    """
    key_set = set(keywords)
    if query_key in key_set:
        return query_key
    for alias in sorted(aliases_for(query_key)):
        if alias in key_set:
            return alias
    return None


def score(query_keys: list[str], entry: dict,
          confirmed_boost_cap: int = 5) -> tuple[int, int, int, int, int]:
    """Alias-aware recall scoring. Same shape as the old keyword-overlap
    score: (total, sig_overlap, task_overlap, fix_boost, insight_boost).

    A query key matches when it *or any alias* appears in the dossier's
    keywords. Signature-term matches still count double; the confirm
    boosts are unchanged. This is the single scoring funnel — a future
    opt-in semantic backend would blend in here.
    """
    sig_keys = entry.get("sig_keywords") or []
    task_keys = [k for k in entry.get("keywords", []) if k not in sig_keys]
    sig_overlap = sum(1 for k in query_keys if find_match(k, sig_keys))
    task_overlap = sum(1 for k in query_keys if find_match(k, task_keys))
    fix_boost = min(int(entry.get("confirmed_fixes", 0) or 0),
                    confirmed_boost_cap)
    insight_boost = min(int(entry.get("confirmed_insights", 0) or 0),
                        confirmed_boost_cap)
    total = 2 * sig_overlap + task_overlap + fix_boost + insight_boost
    return total, sig_overlap, task_overlap, fix_boost, insight_boost


def matched_terms(query_keys: list[str], entry: dict) -> list[str]:
    """Display strings for the recall output: the query key, or
    ``query~dossier-term`` when the match came through a synonym alias.
    The ``~`` is the transparency mechanism — you can see exactly which
    matches were exact and which were aliases."""
    shown: list[str] = []
    keywords = entry.get("keywords", [])
    for key in query_keys:
        hit = find_match(key, keywords)
        if hit is None:
            continue
        shown.append(key if hit == key else f"{key}~{hit}")
    return shown
