"""Hybrid retrieval: BM25 lexical scoring over canonicalized text with
synonym aliases. v0.2.7.

Still no embeddings, no model calls, no network. Three upgrades over
pure keyword overlap:

1. Symbol canonicalization: Unicode math symbols become words *before*
   tokenizing, so ``χ(G)`` and "chromatic number" share keywords, ``x²``
   becomes the token ``x2``, and ``C₇`` matches ``C7``.
2. Synonym aliases: a curated, readable map of equivalent terms. A query
   for "flaky" matches a dossier about "intermittent" failures; "primes"
   matches "prime"; "coloring" matches "chromatic".
3. BM25 ranking (new): terms are weighted by inverse document frequency,
   so a word appearing in every dossier (like "one") barely counts while
   a rare, distinctive term counts a lot; term frequency saturates and
   scores are normalized by dossier length. This fixes the failure the
   2026-10-14 transfer test measured: generic-word noise outranking the
   relevant dossier.

What BM25 does NOT fix: it is still lexical. A paraphrase sharing no
vocabulary with the dossier ("reciprocals" vs "unit fractions") will not
match unless the synonym map covers it — that is the honest limit, and
the reason a future opt-in semantic backend would plug in at
``score_corpus()``: it is the single scoring funnel, so a ``--semantic``
flag could one day blend an embedding cosine into the total and mark it
in the display.

The scoring *shape* is unchanged (signature terms are the retrieval key
and count double, task terms single, confirms boost up to 5 each) — only
the term weighting got smarter. Recall output shows alias matches as
``query~dossier-term`` so the matching stays inspectable; nothing is
a black box.

The synonym map is data, not intelligence: hand-curated, deliberately
incomplete, and fully visible below.
"""

from __future__ import annotations

import math
import re
from collections import Counter

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


class BM25:
    """Okapi BM25 over tokenized documents. Stdlib only (``math``).

    The ranking formula is the published Okapi BM25 (Robertson et al.);
    this implementation is written fresh for Garm, informed by the
    widely-used pure-Python rank_bm25 package (dorianbrown/rank_bm25,
    MIT licence) — only the public formula is used, no code is copied.
    Documents are Counters of term -> frequency; query terms arrive as
    alias groups (frozensets), so a whole synonym group counts as one
    term: its tf is the summed frequency of its members, its df the
    number of documents containing any member.
    """

    def __init__(self, docs: list[Counter], k1: float = 1.5,
                 b: float = 0.75) -> None:
        self._tfs = docs
        self._n = len(docs)
        self._k1 = k1
        self._b = b
        total_len = sum(sum(c.values()) for c in docs)
        self._avgdl = total_len / self._n if self._n else 0.0

    def score_many(self, query_groups: list[frozenset]) -> list[float]:
        """BM25 score of every document against the query groups."""
        out = [0.0] * self._n
        if not self._n or not query_groups:
            return out
        for group in query_groups:
            tfs: list[int] = []
            df = 0
            for c in self._tfs:
                tf = sum(c.get(t, 0) for t in group)
                tfs.append(tf)
                if tf:
                    df += 1
            if not df:
                continue
            # Smoothed IDF: always >= 0, so a term in every document
            # contributes ~nothing instead of going negative.
            idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
            for i, tf in enumerate(tfs):
                if not tf:
                    continue
                dl = sum(self._tfs[i].values())
                norm = self._k1 * (1 - self._b + self._b * dl /
                                   (self._avgdl or 1))
                out[i] += idf * tf * (self._k1 + 1) / (tf + norm)
        return out


def score_corpus(query_keys: list[str], entries: list[dict],
                 confirmed_boost_cap: int = 5
                 ) -> dict[str, tuple[float, float, float, int, int]]:
    """Rank every entry with BM25. Returns
    ``{dossier_id: (total, sig_score, task_score, fix_boost, ins_boost)}``.

    Two BM25 fields preserve the v0.2 design: the failure signature is
    the retrieval key, so its BM25 subscore counts double; task-keyword
    subscores count single. Confirm boosts are unchanged (capped ints).
    Query keys are alias-expanded before scoring, exactly as the old
    per-entry scorer did — only the term weighting got smarter.

    This is the single scoring funnel: a future opt-in semantic backend
    would blend an embedding cosine into ``total`` here.
    """
    groups = [aliases_for(k) for k in query_keys]
    sig_docs: list[Counter] = []
    task_docs: list[Counter] = []
    for e in entries:
        sig = e.get("sig_keywords") or []
        sigset = set(sig)
        task = [k for k in (e.get("keywords") or []) if k not in sigset]
        sig_docs.append(Counter(sig))
        task_docs.append(Counter(task))
    sig_scores = BM25(sig_docs).score_many(groups)
    task_scores = BM25(task_docs).score_many(groups)
    out: dict[str, tuple[float, float, float, int, int]] = {}
    for e, ss, ts in zip(entries, sig_scores, task_scores):
        fix_b = min(int(e.get("confirmed_fixes", 0) or 0),
                    confirmed_boost_cap)
        ins_b = min(int(e.get("confirmed_insights", 0) or 0),
                    confirmed_boost_cap)
        out[e["id"]] = (2 * ss + ts + fix_b + ins_b, ss, ts, fix_b, ins_b)
    return out


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
