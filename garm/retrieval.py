"""Hybrid retrieval: BM25 lexical scoring over canonicalized text with
synonym aliases, plus an opt-in semantic lane. v0.2.9.

Default path (no flags): still no embeddings, no model calls, no
network. Three upgrades over pure keyword overlap:

1. Symbol canonicalization: Unicode math symbols become words *before*
   tokenizing, so ``χ(G)`` and "chromatic number" share keywords, ``x²``
   becomes the token ``x2``, and ``C₇`` matches ``C7``.
2. Synonym aliases: a curated, readable map of equivalent terms. A query
   for "flaky" matches a dossier about "intermittent" failures; "primes"
   matches "prime"; "coloring" matches "chromatic".
3. BM25 ranking (new in v0.2.7): terms are weighted by inverse document
   frequency, so a word appearing in every dossier (like "one") barely
   counts while a rare, distinctive term counts a lot; term frequency
   saturates and scores are normalized by dossier length. This fixes the
   failure the 2026-10-14 transfer test measured: generic-word noise
   outranking the relevant dossier.

Tier 2 (opt-in, ``--semantic``): a meaning lane next to BM25. An
embedding model (fastembed, Apache-2.0, ONNX, no PyTorch/GPU) turns the
query and each dossier's signature/task text into vectors; cosine
similarity finds dossiers that mean the same thing with different
words — the paraphrase case BM25 provably cannot match. In semantic
mode the meaning lane leads the ranking (``--semantic`` is an explicit
statement that lexical matching failed for the query); the BM25
subscores are still shown for inspectability. See ``garm/semantic.py``
for the lane's own rules: explicit warmup, no mid-turn downloads, no
silent fallback, inspectable subscores.

What even Tier 2 does NOT fix: it is still retrieval, not judgment. A
failing agent diagnosing its own failure (the self-diagnosis trust gap)
and cross-domain transfer are separate problems.

The scoring *shape* is unchanged (signature terms are the retrieval key
and count double, task terms single, confirms boost up to 5 each, plus
a flat concept bonus when two query terms sit adjacently in the
signature name) — only the term weighting got smarter, and the
semantic lane adds a fourth subscore. Recall output shows alias matches as ``query~dossier-term``
and meaning-lane rescues as ``[semantic]`` so the matching stays
inspectable; nothing is a black box.

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


# Signature weight: the failure signature is the retrieval key, so its
# BM25 subscore counts double; task and body count single. 2x is
# calibrated, not guessed — 2026-11-25 measured a 3x trial and REJECTED
# it: it fixed the BPSW "Lucas test first" probe (margin 2.43 -> 6.98)
# but created a false COVERED on an off-topic query ("chromatic number
# of a graph", margin 7.45 on the single generic term "number") and
# regressed the "random prime pairs" probe COVERED -> THIN (its
# evidence lives in the body, not the signature). The 5.0 margin bar
# was calibrated at 2x (Nov 10, 29 in-bank + 27 off-topic queries);
# any weight change must re-measure the whole set, not one probe.
# The semantic lane (garm/semantic.py) keeps the same shape.
SIGNATURE_WEIGHT = 2


# Concept bonus (v0.2.12, 2026-11-25): a query that names a dossier's
# concept — two of its terms adjacent in the signature NAME (the curated
# concept label, e.g. "lucas-first-rank-construction-also-one-sided")
# — is stronger evidence than the same words scattered across fields.
# Single generic words ("number", "test") match everywhere; a two-word
# concept in the name matches almost nowhere by accident. The bonus is
# a flat +3.0 on the total when any two distinct query terms are
# adjacent in the name, calibrated 2026-11-25 on the 10-query harness
# (tests/probe_calibration.py): it moves the BPSW "Lucas test first"
# probe THIN -> COVERED (margin 2.43 -> 5.43) and fires on no other
# harness query, genuine or off-topic. It is deliberately NOT applied
# to the signature prose (a "skip Lucas test" sentence contains the
# same words adjacently and would reward the wrong dossier) and NOT
# to the semantic lane (its totals are cosine-scale, roughly [-3, 3]).
# Re-measure on a wider query set before treating the constant as
# settled; the harness is the guard.
CONCEPT_BONUS = 3.0


def concept_match(query_keys: list[str], entry: dict
                  ) -> tuple[float, str]:
    """Concept bonus for a dossier whose signature NAME contains two
    distinct query terms adjacently (aliases count).

    Returns ``(bonus, label)`` — ``(CONCEPT_BONUS, "lucas+first")`` on
    a hit, ``(0.0, "")`` otherwise. Only the slug (text before the
    first period of the ``signature`` line) is examined: the prose
    after it can contain the same words in the wrong sense.
    Tokenizing is raw (no stopword filter): a stopword between two
    query terms blocks the hit, which is the conservative direction,
    and a stopword can never itself match a query term (query keys
    are stopword-filtered at extraction).
    """
    sig = entry.get("signature") or ""
    if sig.lower().startswith("name:"):
        sig = sig[5:]
    slug = sig.split(".")[0]
    tokens = re.findall(r"[a-z0-9]+", canonicalize_text(slug).lower())
    seen: set[str] = set()
    groups: list[frozenset] = []
    for k in query_keys:
        if k not in seen:
            seen.add(k)
            groups.append(aliases_for(k))
    for a, b in zip(tokens, tokens[1:]):
        ga = next((i for i, g in enumerate(groups) if a in g), None)
        gb = next((i for i, g in enumerate(groups) if b in g), None)
        if ga is not None and gb is not None and ga != gb:
            return (CONCEPT_BONUS, f"{a}+{b}")
    return (0.0, "")


def score_corpus(query_keys: list[str], entries: list[dict],
                 confirmed_boost_cap: int = 5,
                 semantic=None, query_text: str | None = None,
                 return_ranks: bool = False
                 ) -> dict[str, tuple[float, float, float, float, float, int, int, float]
                            ] | tuple[dict, dict[str, tuple[int, int]]]:
    """Rank every entry with BM25. Returns
    ``{dossier_id: (total, sig_score, task_score, body_score, sem_score,
    fix_boost, ins_boost, concept_bonus)}``.

    Three BM25 fields: the failure signature is the retrieval key, so its
    BM25 subscore counts double; task-keyword and body-keyword subscores
    count single each. On top of the fields, a flat concept bonus
    (``CONCEPT_BONUS``) is added when two distinct query terms sit
    adjacently in the dossier's signature name — the query naming the
    concept, not just sharing its words (see ``concept_match``). It is
    a bonus, not a field: it is added after the gated confirm boosts,
    and it is NOT folded into the semantic lane's totals (cosine
    scale), though it is added to the displayed BM25 totals there.

    v0.2.10 added the body field — previously only
    task and failure signature were indexed, so terms appearing only in
    Root cause / Blocking constraint / etc. could never match. Confirm
    boosts are capped ints, applied only when the base lane score is
    positive (v0.2.10: boosts amplify evidence, never manufacture it).
    Query keys are alias-expanded before scoring, exactly as the old
    per-entry scorer did — only the term weighting got smarter.

    This is the single scoring funnel. The opt-in semantic lane (Tier 2,
    v0.2.9) plugs in here: pass a ``garm.semantic.SemanticIndex`` as
    ``semantic`` (plus the raw ``query_text`` — embeddings want the raw
    query, not keyword lists). The semantic subscore is shaped like the
    BM25 total (signature cosine double, task cosine single).

    Ranking in semantic mode: the semantic lane leads. ``--semantic`` is
    an explicit statement that lexical matching failed for this query,
    so results order by semantic rank; the BM25 subscores are still
    computed and displayed (inspectability), and the ``[semantic]`` tag
    marks hits the meaning lane ranked above the BM25 lane. An earlier
    revision fused both lanes with Reciprocal Rank Fusion, but RRF gives
    equal weight to a BM25 lane that is confidently wrong on paraphrases
    — the exact failure --semantic exists to escape — so the meaning
    lane leads instead. Confirm boosts are folded into the semantic
    ranking (a capped-int boost added raw on top of rank scores would
    make boosts the entire ranking). With ``return_ranks=True`` returns
    ``(scores, {id: (bm25_rank, sem_rank)})`` as well.

    With ``semantic=None`` (the default) ``sem_score`` is 0.0 and
    fastembed is imported nowhere on this path. v0.2.10 changed the
    default path vs v0.2.7-v0.2.9: body sections are indexed, document
    term frequencies are real (not deduped to 1), and confirm boosts
    apply only on positive base scores.
    """
    from . import semantic as _sem  # local: keeps the import graph honest
    # v0.2.10: query keys stay a set (deduped) — v0.2.10 restored real term
    # frequencies on the DOCUMENT side (extract_keywords no longer dedups),
    # but query-side repeats must not double-count a term's contribution.
    seen: set[str] = set()
    uniq_keys: list[str] = []
    for k in query_keys:
        if k not in seen:
            seen.add(k)
            uniq_keys.append(k)
    groups = [aliases_for(k) for k in uniq_keys]
    sig_docs: list[Counter] = []
    task_docs: list[Counter] = []
    body_docs: list[Counter] = []
    for e in entries:
        sig = e.get("sig_keywords") or []
        sigset = set(sig)
        task = [k for k in (e.get("keywords") or []) if k not in sigset]
        sig_docs.append(Counter(sig))
        task_docs.append(Counter(task))
        # v0.2.10: body sections are indexed too (see build_index_entry).
        # Old index files predate the field — .get defaults to [].
        body_docs.append(Counter(e.get("body_keywords") or []))
    sig_scores = BM25(sig_docs).score_many(groups)
    task_scores = BM25(task_docs).score_many(groups)
    body_scores = BM25(body_docs).score_many(groups)
    boosts: dict[str, tuple[int, int]] = {}
    for e in entries:
        boosts[e["id"]] = (
            min(int(e.get("confirmed_fixes", 0) or 0), confirmed_boost_cap),
            min(int(e.get("confirmed_insights", 0) or 0),
                confirmed_boost_cap),
        )
    out: dict[str, tuple[float, float, float, float, float, int, int, float]] = {}
    ranks: dict[str, tuple[int, int]] = {}
    # Concept bonus per entry, computed once: two query terms adjacent
    # in the signature name (see concept_match). Added to the BM25
    # total (and to the displayed BM25 totals in semantic mode), never
    # to the semantic lane's cosine-scale totals.
    concept_b: dict[str, float] = {
        e["id"]: concept_match(uniq_keys, e)[0] for e in entries
    }

    def _gated_boosts(base: float, eid: str) -> tuple[int, int]:
        # v0.2.10: boosts amplify evidence of relevance; they must not
        # manufacture it. Zero base score (no overlap at all) gets no
        # boost — otherwise confirmed dossiers inject into every prompt
        # regardless of relevance (blind-agent validation 2026-10-16).
        if base <= 0:
            return (0, 0)
        return boosts[eid]

    if semantic is None:
        for e, ss, ts, bs in zip(entries, sig_scores, task_scores,
                                 body_scores):
            fix_b, ins_b = _gated_boosts(SIGNATURE_WEIGHT * ss + ts + bs, e["id"])
            cb = concept_b[e["id"]]
            out[e["id"]] = (SIGNATURE_WEIGHT * ss + ts + bs + fix_b + ins_b + cb,
                            ss, ts, bs, 0.0, fix_b, ins_b, cb)
        return (out, ranks) if return_ranks else out
    # --- semantic lane (Tier 2): meaning leads, BM25 is displayed ---
    sem_scores = semantic.score_entries(query_text or "", entries)
    bm25_totals = {}
    sem_totals = {}
    for e, ss, ts, bs in zip(entries, sig_scores, task_scores, body_scores):
        fix_b, ins_b = _gated_boosts(SIGNATURE_WEIGHT * ss + ts + bs, e["id"])
        bm25_totals[e["id"]] = (SIGNATURE_WEIGHT * ss + ts + bs + fix_b + ins_b
                                + concept_b[e["id"]])
        sem_fix_b, sem_ins_b = _gated_boosts(sem_scores[e["id"]], e["id"])
        sem_totals[e["id"]] = sem_scores[e["id"]] + sem_fix_b + sem_ins_b
    bm25_ranks = _sem.rank_ids(bm25_totals)
    sem_ranks = _sem.rank_ids(sem_totals)
    for e, ss, ts, bs in zip(entries, sig_scores, task_scores, body_scores):
        eid = e["id"]
        fix_b, ins_b = _gated_boosts(sem_scores[eid], eid)
        # Total is the semantic score plus confirm boosts: the lane the
        # user asked for leads, and the scale stays interpretable
        # (cosine-based, roughly [-3, 3] before boosts). The concept
        # bonus is carried as the 8th element for display, but is NOT
        # added to this total.
        out[eid] = (sem_totals[eid], ss, ts, bs,
                    sem_scores[eid], fix_b, ins_b, concept_b[eid])
        ranks[eid] = (bm25_ranks[eid], sem_ranks[eid])
    return (out, ranks) if return_ranks else out


def matched_terms(query_keys: list[str], entry: dict) -> list[str]:
    """Display strings for the recall output: the query key, or
    ``query~dossier-term`` when the match came through a synonym alias.
    The ``~`` is the transparency mechanism — you can see exactly which
    matches were exact and which were aliases."""
    shown: list[str] = []
    keywords = entry.get("keywords", [])
    # v0.2.10: body keywords are matchable too — check them when the
    # task/signature keywords miss.
    body_keywords = entry.get("body_keywords", [])
    for key in query_keys:
        hit = find_match(key, keywords)
        if hit is None:
            hit = find_match(key, body_keywords)
        if hit is None:
            continue
        shown.append(key if hit == key else f"{key}~{hit}")
    return shown


# v0.2.12: the coverage-gap verdict. A recall that serves a 1.05 hit
# from generic words looks identical to a recall that serves a 30-point
# hit on the exact failure signature — until you ask whether the top
# hit matched a signature term and whether it clearly beat the
# runner-up. The margin threshold is calibrated, not guessed
# (measured 2026-11-10 on the three shipped banks bpsw/earth-moon/imo,
# 29 in-bank queries + 27 off-topic/generic ones):
#   * in-bank queries: top 15.34–44.54, margins 4.50–32.11, signature
#     match 28/29.
#   * off-topic/generic queries that still cleared the 1.0 threshold:
#     top up to 13.62, margins 0.05–4.74, signature match often 1
#     (generic failure words match signatures through the alias map).
#   * margin 5.0 gives ZERO false COVERED on the measured set. The
#     cost is 4/29 genuine queries flagged THIN instead of COVERED —
#     still served, just flagged — and a false THIN is harmless while
#     a false COVERED is exactly the failure this exists to prevent.
# The margin gate is BM25-scale: in --semantic mode the totals are
# cosine-based (roughly [-3, 3]), so there the verdict uses the
# threshold + signature gates only.
COVERAGE_MARGIN = 5.0


def matched_sig_terms(query_keys: list[str], entry: dict) -> list[str]:
    """Query keys matching the entry's SIGNATURE keywords (aliases
    count, same ``~`` display as matched_terms). The signature is the
    retrieval key — a hit that matches no signature term matched only
    on task/body words, which is what makes it thin."""
    shown: list[str] = []
    sig = entry.get("sig_keywords") or []
    for key in query_keys:
        hit = find_match(key, sig)
        if hit is None:
            continue
        shown.append(key if hit == key else f"{key}~{hit}")
    return shown


def coverage_verdict(query_keys: list[str],
                     ranked: list[tuple[float, dict]],
                     min_score: float,
                     semantic: bool = False
                     ) -> tuple[str, dict | None, float, float, list[str]]:
    """The per-query coverage verdict for a ranked recall.

    ``ranked`` is ``[(total, entry), ...]`` sorted best-first (the
    same order recall prints). Returns ``(verdict, top_entry, best,
    margin, sig_terms)`` where verdict is one of:
      COVERED   top >= min_score, matches a signature term, and beats
                the runner-up by >= COVERAGE_MARGIN (BM25 path).
      THIN      top >= min_score but no signature match, or the margin
                is ~zero — served, but flagged as weak.
      UNCOVERED nothing clears min_score (top_entry is the closest
                miss, best its score).
    An empty bank has no ranked entries: that is not a verdict, it is
    absence — callers report it separately (``no dossiers found``).
    Ranking is untouched: the verdict is display + log only.
    """
    if not ranked:
        return ("UNCOVERED", None, 0.0, 0.0, [])
    best, top = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    margin = best - second
    sig_terms = matched_sig_terms(query_keys, top)
    # The 5th element is the full matched-terms display (what the
    # recall table shows); the verdict itself encodes whether a
    # signature term matched.
    matched = matched_terms(query_keys, top)
    if best < min_score:
        return ("UNCOVERED", top, best, margin, matched)
    margin_ok = True if semantic else margin >= COVERAGE_MARGIN
    if sig_terms and margin_ok:
        return ("COVERED", top, best, margin, matched)
    return ("THIN", top, best, margin, matched)
