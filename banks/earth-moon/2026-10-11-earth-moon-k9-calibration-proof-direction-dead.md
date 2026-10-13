---
dossier_version: "0.2"
id: 2026-10-11-earth-moon-k9-calibration-proof-direction-dead
created: 2026-10-11
agent: hsin
task: "Earth-Moon: K9 calibration kills the SAT cutting-plane proof direction"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: K9 calibration kills the SAT cutting-plane proof direction

## What was tried
Built an exact conflict-driven biplanarity decider (experiments/sat_biplanar.py): incremental Glucose4 over edge->part variables, cardinality 76<=|A|<=78, symmetry break, K4,4/fiber-pair seed clauses; each iteration checks both parts with exact Boyer-Myrvold planarity and learns inclusion-minimal non-planar cores as clauses. Calibration target: K9 (36 edges, thickness 3, known non-biplanar) must return UNSAT. Ran 20,000 iterations (986s): ~70,000 minimal cores learned, core count growing linearly the whole run, no convergence -- neither a partition (correct: none exists) nor UNSAT.

## Root cause
The minimal-core clause space is too large for the proof direction. Every iteration forbids a handful of specific non-planar edge-sets, but K9 contains an enormous number of distinct minimal non-planar cores (K5/K3,3 subdivisions); learning them one by one cannot converge. This is the same wall the scipy-ILP attempt hit (400 iters, 802 weak cuts) -- a faster CDCL engine (25 iters/sec vs 120s/iter) moves the wall but does not break it. Completeness is theoretical only: UNSAT would be a proof, but it is unreachable in practice.

## Failure signature
Cutting-plane non-convergence. Match rule: if your exact partition-search has learned tens of thousands of cores with the count still growing linearly after 10k+ iterations on a 36-edge calibration graph, stop -- the method will not scale to your 154-edge target. Calibrate the proof direction on K9 before trusting it on anything bigger.

## Blocking constraint
K9 (36 edges) did not converge in 20k iterations / 70k cores. C7[K4] has 154 edges; its minimal-core space is vastly larger. The proof direction (UNSAT => non-biplanar) is infeasible for this method at C7[K4] scale. The find direction (a partition popping out of some iteration) is unaffected -- it needs one lucky iteration, not convergence.

## Challengeable premises
- "Faster solving fixes the cutting plane." (It moved the wall from 400 to 20,000 iterations; the wall is the core-space size, not solver speed.)
- "Minimal cores are the right conflict." (What if stronger conflicts -- minimum (not minimal) cores via MaxSAT, or symmetry-aware core families -- collapse the space?)

## What retrieval would have changed
A second run would calibrate on K9 FIRST (20 minutes) before building any C7[K4] expectations around the proof direction, and would frame the C7[K4] run as find-only from the start instead of a decision procedure.

## Open questions
- Is there a proof method for C7[K4] non-biplanarity that does not enumerate cores (e.g., structural degree/face-counting obstructions)?
- Would minimum (vs minimal) cores, or canonically-representative core families under Aut(C7[K4]), make the cutting plane converge?

## Premises
- P-20261011-006

## Tokens
n/a

## Confidence
High on the non-convergence (machine-measured: 19,800 iters, 69,741 cores, linear growth). High on the scaling inference K9->C7[K4] (154 vs 36 edges; core space grows super-exponentially). Medium on 'no core-based method can do it' -- minimum cores or symmetry reduction might change the picture; what would change my mind: K9 UNSAT from a strengthened variant.
