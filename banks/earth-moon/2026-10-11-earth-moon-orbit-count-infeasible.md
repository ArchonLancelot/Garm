---
dossier_version: "0.2"
id: 2026-10-11-earth-moon-orbit-count-infeasible
created: 2026-10-11
agent: hsin
task: "Earth-Moon: orbit-count feasibility kills canonical triangulation enumeration"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: orbit-count feasibility kills canonical triangulation enumeration

## What was tried
Orbit-count feasibility for canonical triangulation enumeration (night-shift Phase 1). Sampled 4,054 triangulations T (78 edges) subset of E(C7[K4]) via 47,250 randomized greedy maximal-planar-subgraph extractions (8.6% reach 78 edges; 1.06 triangulations/sec). Built three Aut(C7[K4])-invariant signature levels: L1 degree sequence; L2 + per-fiber intra/inter edge-count multisets; L3 + triangle counts and K4 count. Chao1 estimates: L1 ~5,206; L2 ~1,639,443 (f1=4,044, f2=5; birthday cross-check n^2/2f2 = 1.64M matches); L3 ~8,219,485 (f2=0, bias-corrected). Coverage at L2/L3 ~0.002/0.000 -- nowhere near saturated; estimates climb steeply with invariant strength. Exact planarity test on a 76-edge complement: 0.69ms mean (testing is cheap; enumeration is the blocker).

## Root cause
Too many Aut(C7[K4])-orbits of triangulations: solid floor 1.64M (L2, rock-solid statistics), likely ~8M+. Since #orbits >= #signature-classes, the finest-level estimate is a floor, and greedy sampling concentrates on 'easy' triangulations (inflating collisions), so true diversity is likely HIGHER. Canonical enumeration for a complete 78/76 decision is infeasible -- the 78/76 completeness reduction stands, but completing it by enumeration does not scale.

## Failure signature
Weak-invariant Chao1 climbing. Match rule: when estimating orbit/species counts via Chao1, if the estimates climb steeply as the invariant strengthens (5k -> 1.6M -> 8.2M) and the finest level is nowhere near saturated (coverage ~0), the enumeration is infeasible -- do not trust the coarse level. Also: always verify purported invariants under random group elements (a broken inter-fiber counter nearly corrupted this run; caught by assertion, all samples re-drawn).

## Blocking constraint
Aut(C7[K4]) has order ~6.4e10 but the triangulation orbit count (~8M est.) still exceeds any feasible exact-test budget by 4x. The 78/76 case cannot be closed by canonical enumeration.

## Challengeable premises
- "2M exact tests is the binding budget." (Tests are 0.69ms; 2M tests = 0.4 core-hours. The budget was never about testing -- enumeration is the blocker. A smarter orbit representative generator wouldn't change the orbit COUNT though.)
- "Greedy sampling is representative." (Biased toward easy triangulations; noted as conservative -- true orbits likely higher.)

## What retrieval would have changed
A second run would not attempt canonical enumeration at all. It would go straight to stronger search (minimum-core cutting plane with symmetry-multiplied clauses) or to proving 'every triangulation complement contains K3,3' as a theorem, or switch candidates.

## Open questions
- Exact orbit count still unknown (lower-bounded at 1.64M).
- Is there a smarter complete method for 78/76 than orbit enumeration?

## Premises
- P-20261012-001

## Tokens
n/a

## Confidence
High on INFEASIBLE (three converging lines: Chao1 climbing, birthday cross-check matching, conservative bias direction; the invariance bug was caught and all data re-drawn). Medium on the 8.2M point estimate (f2=0, order-of-magnitude) -- but the 1.64M floor alone kills feasibility. What would change my mind: a principled orbit count below 2M, which the data argues against.
