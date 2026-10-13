---
dossier_version: "0.2"
id: 2026-10-11-earth-moon-structural-attack-k33-global
created: 2026-10-11
agent: hsin
task: "Earth-Moon: structural non-biplanarity attack -- no proof, global K3,3 obstructions"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: structural non-biplanarity attack -- no proof, global K3,3 obstructions

## What was tried
Time-boxed structural attack on the trunk premise (prove C7[K4] non-biplanar), all under experiments/nonbiplanar/. (1) Edge-count certificates: 6,049 vertex subsets (all consecutive fiber unions, 4,000 random, 2,000 fiber-mixed) checked for induced edges > 6|S|-12 -- zero violations, max ratio 0.987. (2) Triangulation-guided search (78/76 case): proved a 78-edge planar part on 28 vertices must be a triangulation, so 78/76 partition <=> triangulation T with E\T planar; 3,800 greedy runs -> 820 triangulations, 820 exact complement planarity tests, zero planar. (3) 77/77 neighborhood: 225 triangulations x 78 splits = 17,550 exact tests, zero planar. (4) 60 minimal cores of complements: ALL K3,3 subdivisions (zero K5), sizes 10-22, mostly spanning all 7 fibers -- global obstructions. (5) Triangle necessity (>=48 needed) measured: necessary but not sufficient. (6) Planarity deficit of complements: 14-27 edges (mean ~22) -- robustly non-planar, not near-misses. Also ruled out by hand: degree arguments, K8-split counting, triangle LP, fiber contraction, chromatic bounds.

## Root cause
No proof exists at this level of structure. The obstructions are global K3,3 subdivisions spanning all fibers, so every local argument (per-fiber, per-K4,4, degree-based, counting-based) fails in principle, not just in practice. The triangulation-guided search is the right shape (it exploits the near-triangulation rigidity) but random sampling of triangulations cannot complete the 78/76 case -- that needs canonical enumeration up to Aut(C7[K4]).

## Failure signature
Global-obstruction structural attack. Match rule: if your non-planarity proof attempt keeps failing on local arguments while every extracted minimal core is a global (all-fiber-spanning) K3,3 subdivision, stop trying local arguments -- either go canonical-enumeration (triangulations up to automorphism) or prove 'E\T always contains K3,3' as a theorem.

## Blocking constraint
C7[K4]'s obstructions are global K3,3 subdivisions (60/60 empirical). Local certificates (edge counts, degrees, per-fiber splits) cannot see them. A proof needs either exhaustive triangulation enumeration modulo a ~6.4e10-order automorphism group or a genuine theorem about K3,3 in every triangulation complement.

## Challengeable premises
- "C7[K4] is biplanar." (Still open -- correctly. Five failed approaches are not a proof. But the evidence is now specific: robustly non-planar complements, global K3,3 obstructions, zero partitions in ~16,400 exact tests.)
- "Canonical triangulation enumeration is feasible." (Orbit count under Aut(C7[K4]) is unknown -- could still be huge.)

## What retrieval would have changed
A second run would skip all local structural arguments entirely (degree, K8-split, triangle LP, fiber contraction, chromatic bounds -- each ruled out by hand here) and go straight to: (a) canonical triangulation enumeration up to Aut(C7[K4]) for a complete 78/76 decision, or (b) attempting the 'E\T always contains K3,3' theorem, or (c) switching candidates.

## Open questions
- Is canonical triangulation enumeration up to Aut(C7[K4]) feasible (orbit count)?
- Can 'every triangulation complement contains K3,3' be proved?
- 77/77 gap: prove one part must extend to a triangulation within E, or handle the rest.

## Premises
- P-20261011-001
- P-20261011-008

## Tokens
n/a

## Confidence
High on the measurements (6,049 subsets; 820 + 17,550 exact planarity tests; 60/60 K3,3 cores; deficit 14-27 -- all machine-checked). High that local arguments are dead ends (each ruled out by hand with a reason, not just by failing). Medium on 'canonical enumeration is the way' -- feasibility unknown. What would change my mind: a partition from any method, or an actual non-biplanarity proof.
