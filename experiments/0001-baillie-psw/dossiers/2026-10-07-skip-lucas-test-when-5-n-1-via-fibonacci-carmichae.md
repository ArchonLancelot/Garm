---
dossier_version: "0.2"
id: 2026-10-07-skip-lucas-test-when-5-n-1-via-fibonacci-carmichae
created: 2026-10-07
agent: hsin
task: "Skip Lucas test when (5/n)=-1 via Fibonacci-Carmichael filter"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
---

# Failure dossier: Skip Lucas test when (5/n)=-1 via Fibonacci-Carmichael filter

## What was tried
Had a "clean" theoretical insight: if (5/n) = -1 then Selfridge picks D=5
(Fibonacci case), and I believed the remembered theorem "strong Fibonacci
pseudoprime ⟹ Carmichael". Since n = pq (distinct primes) is never
Carmichael (Korselt), I concluded keepers with (5/n) = -1 could skip the
Lucas test entirely — they "can't" pass. Was about to bake this into the
pass-2 pipeline as a filter.

## Root cause
I applied a remembered theorem without verifying it. Empirical check before
deploying: of 2,098 A217255 (strong Lucas) terms with (5/n) = -1, ALL 2,098
are NOT Carmichael — including 5777 = 53·109, a two-prime strong Lucas
pseudoprime. The "theorem" is false (or I misremembered/misapplied it).
If I had deployed the filter, it would have DISCARDED valid tickets —
including ones shaped exactly like my keepers. A false filter is worse
than no filter: it doesn't just waste time, it can throw away the winner.

## Failure signature
Name: unvalidated-theorem-as-filter. If you are about to use a remembered
theorem to SKIP work (filter out candidates, prune a search), verify it
empirically FIRST on ground-truth data. The cheaper the filter, the more
tempting to skip validation — and the more dangerous a false one is.
(Quoted wrong conclusion verbatim: "(5/n)=-1 ⟹ n must be Carmichael to
pass, so pq can be skipped" — refuted by 5777 = 53·109.)

## Blocking constraint
None — the fix is procedural: test the filter on OEIS ground truth before
trusting it. The 2,098-term check took under a second and killed the idea
cleanly.

## What retrieval would have changed
A dossier with this signature would have forced the empirical check BEFORE
I built the filter into the pipeline, instead of after. (In this run I did
check before deploying — barely. The dossier makes "check first" the
default, not a near-miss.)

## Confidence
High. The refutation is airtight (2,098 counterexamples, mechanically
checked). Bonus true fact salvaged: two-prime strong Lucas pseudoprimes
exist (5777), so the Lucas side is not impossible for pq — the search is
a genuine lottery, not a doomed one.
