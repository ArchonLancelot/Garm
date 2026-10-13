---
dossier_version: "0.2"
id: 2026-10-12-find-baillie-psw-pseudoprime-via-chernick-carmicha
created: 2026-10-12
agent: hsin
task: "Find Baillie-PSW pseudoprime via Chernick Carmichael Lucas sweep"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Find Baillie-PSW pseudoprime via Chernick Carmichael Lucas sweep

## What was tried
Pass 12 — second v0.2.4-framework pass. Genuinely new family: no banked
pass ever Lucas-tested Carmichael numbers (the fibonacci-carmichael
dossier was about a false skip-filter, not a search). Chernick (1939):
(6m+1)(12m+1)(18m+1) all prime ==> Carmichael (Korselt). Generator
verified: all 1,447 hits in a 200k pilot satisfied Korselt, 0 failures.
Swept m in [1, 3x10^7] with deterministic Miller-Rabin (bases 2,7,61):
81,720 Carmichael numbers (largest ~3.5x10^25, above 2^64 — the region
Pinch/Gilchrist exhausted for strong-2-psps), full Baillie-PSW test on
each (script: builds/bpsw/pass12.py, 93s). Result: 11,898 passed strong
base-2 (~14.6%), 0 passed strong Lucas. Zero BPSW hits.

## Root cause
One-sided family. Carmichael numbers are Fermat pseudoprimes to every
base by construction (Korselt), so they arrive pre-filtered on the
Fermat side — and indeed 14.6% even pass the STRONG base-2 test. But
the family carries no Lucas-side advantage whatsoever: the strong Lucas
test filtered 100% of the 11,898 survivors. Generating many tickets
that satisfy one test does not move the needle when the other test is
the binding constraint. The pass confirmed the campaign's recurring
shape: every construction clears one side and dies on the other.

## Failure signature
Name: one-sided family. If your candidate family is constructed to
satisfy test A (here: Korselt ==> Fermat), its yield on test B is the
only number that matters — and a 0% rate on B at 12k survivors means
the family has no B-leverage, not that you undersampled. Distinguish
"many candidates" from "candidates with two-sided potential." The
Fermat survivor count (11,898) looks like progress; it isn't — it's the
family doing what it was built to do.

## Blocking constraint
No known parametric family targets the Lucas side. Chernick targets
Fermat; Pomerance's subset-product targets both but is intractable
(pass 8); per-prime two-sidedness is empty (passes 5-6). The Lucas test
remains a pure filter with ~0 pass rate on every generatable family.
This is the same wall as passes 2, 3, 5, 6, 8 — one side is always
free, the other never is.

## Challengeable premises
- "Chernick is representative of Carmichael numbers." Other
  constructions (Alford-Granville-Pomerance subset method, pinwheel
  families) produce different prime-factor distributions — but all
  satisfy Korselt, so all share the one-sidedness. The challengeable
  part is whether distribution matters for the Lucas side.
- "m <= 3x10^7 suffices." The family is infinite; but 0/11,898 on the
  Lucas side is a rate statement, not a sampling artifact — more m
  won't change the shape.
- "14.6% strong-Fermat rate is uninteresting." What if the strong
  base-2 survivors among Carmichaels were THEMSELVES Lucas-tested at
  larger m with a smarter Lucas-first ordering? Ordering doesn't
  change the 0 rate.

## What retrieval would have changed
Recall surfaced the fibonacci-carmichael-skip dossier (matched:
carmichael, lucas, test) — its lesson (the false filter would have
DISCARDED valid tickets) confirmed this pass should test, not filter.
The pass-7 squarefree theorem confirmed all Chernick n are squarefree
(product of distinct primes), so no effort was wasted on shapes the
theorem restricts. A rerun skips the pilot verification (generator
already proven) and goes straight to the sweep.

## Open questions
- Is there ANY parametric family with two-sided potential, or is the
  one-sided wall structural? (Passes 5-6 suggest structural for the
  known characterizations.)
- Do Euler pseudoprimes (a^((n-1)/2) = (a/n) mod n) behave better on
  the Lucas side than Carmichael numbers? Untested family.
- The 11,898 strong-Fermat Carmichael survivors: any shared structure
  (factor sizes, m residues)? A post-hoc analysis could reveal a
  sub-family — likely noise, but cheap to check.

## Premises
P-20261012-005
P-20261012-001

## Confidence
High on the negative result (81,720 direct tests, generator verified
via Korselt). High that the premise correctly stays open — the family
is infinite and the search was bounded. High on the one-sided-family
diagnosis: 0/11,898 on the Lucas side is decisive for this family at
this scale.
