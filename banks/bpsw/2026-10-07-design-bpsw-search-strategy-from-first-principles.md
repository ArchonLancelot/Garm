---
dossier_version: "0.2"
id: 2026-10-07-design-bpsw-search-strategy-from-first-principles
created: 2026-10-07
agent: hsin
task: "Design BPSW search strategy from first principles without reading literature"
outcome: failed
failure_class: knowledge-gap
confirmed_fixes: 0
confirmed_insights: 1
---

# Failure dossier: Design BPSW search strategy from first principles without reading literature

## What was tried
Attacked the Baillie-PSW problem (open since 1980, $620 prize) by pure
first-principles reasoning: implemented the test, tried random sampling,
derived an order-theoretic construction. Only AFTER building all this did
I read the literature (via a research subagent). Found: Chen-Greene (2003)
already showed this shape "appears to be intractable" (2^1500 search
space); Pomerance's subset-product is the state-of-the-art attack;
Gilchrist's 2^64 bound used Pinch's tabulation (31.9M strong psps,
Lucas-tested each); Arnault (1995) already constructed two-prime strong
psps to base 2; no necessary conditions (squarefree, >=3 factors) are
proven, so pq was never ruled out.

## Root cause
Knowledge gap, not reasoning gap: I didn't know the problem's
well-characterized difficulty landscape. First-principles is the wrong
starting point for a decades-old open problem — you reinvent weaker
versions of known ideas (my construction S ≈ a special case of known
order/CRT methods) and miss the known-good tools (Pinch's tabulation,
Pomerance's subset-product framing). The literature didn't hand me a
feasible algorithm, but it immediately told me which shapes are
intractable, which saved further wasted construction.

## Failure signature
Name: first-principles-before-literature. If you are attacking a
decades-old open problem and have not read the survey papers, stop:
you are probably reinventing a known-intractable approach. Read
Chen-Greene / Baillie-Fiori-Wagstaff / Shallue-Webster FIRST, then
decide whether your idea is actually new. (Quoted wrong conclusion
verbatim: "same-v2 buckets should make compatibility likely" — the
divisibility analysis later showed this was never true.)

## Blocking constraint
The literature is the constraint map. Without it you can't distinguish
"hard because I haven't thought enough" from "hard because it's proven
intractable in this shape" — and you burn effort on the latter.

## What retrieval would have changed
Would have started from Pomerance's subset-product framing and Pinch's
tabulation idea instead of random sampling, and would have known from the
start that two-prime constructions face the keeper-density wall
(Chen-Greene's intractability), focusing effort on yield estimation first.

## Confidence
High. The literature facts are sourced (papers + URLs in the research
report). Caveat, stated plainly: knowing the intractability didn't produce
a feasible algorithm — it produced a better failure mode (informed
pessimism with numbers, not blind optimism).
