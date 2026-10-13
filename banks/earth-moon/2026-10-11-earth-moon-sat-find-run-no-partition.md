---
dossier_version: "0.2"
id: 2026-10-11-earth-moon-sat-find-run-no-partition
created: 2026-10-11
agent: hsin
task: "Earth-Moon: SAT cutting-plane find run on C7[K4] -- 20k iters, no partition"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: SAT cutting-plane find run on C7[K4] -- 20k iters, no partition

## What was tried
Ran the exact conflict-driven SAT biplanarity decider (experiments/sat_biplanar.py) on C7[K4] as a find-only search: incremental Glucose4, 76<=|A|<=78, symmetry break, 14 structural seed clauses (seven K4,4s + seven fiber-pair subgraphs), 2-3 minimal non-planar cores learned per iteration. Budget was 4h; the run hit the 20,000-iteration cap after 4,914s (~82 min): 79,604 cores learned, every proposed partition had both parts non-planar, no partition found, no UNSAT. Log: experiments/sat_c7k4.log.

## Root cause
Same non-convergence pattern as the K9 calibration, at larger scale: the minimal-core clause space for a 154-edge graph is too large for blind cutting-plane learning to cover. Each iteration forbids a few specific non-planar edge-sets, but the solver's proposals stay essentially random 76-78-edge splits -- it has no guidance toward planarity beyond the learned clauses, and 80k clauses barely dent a 2^154 space. The method is complete in theory and inert in practice here.

## Failure signature
Blind exact search on a dense graph. Match rule: if your complete method's only guidance is conflict clauses and 20k iterations still propose uniformly non-planar candidates with linearly growing clause counts, the method is enumerating, not solving -- stop and bring structure (symmetry, triangulation rigidity) or switch to proving non-existence.

## Blocking constraint
C7[K4]'s 154 edges force 76/77/78-edge parts, each a near-triangulation. Random 76-78-edge subsets of this graph are essentially never planar, so unguided propose-and-test cannot stumble into the needle. The K4,4/fiber-pair seeds (28 clauses) were valid but negligible against the space.

## Challengeable premises
- "More iterations would find it." (20k iters showed zero trend toward planarity; nothing suggests 200k would differ.)
- "C7[K4] is biplanar." (Four genuinely different methods have now failed: symmetric-exhaustive, SA, ILP cutting-plane, SAT cutting-plane. Still not a proof, but the candidate is not cooperating.)

## What retrieval would have changed
A second run would not repeat blind cutting-plane at larger budgets. It would either (a) attack non-biplanarity structurally (the trunk premise P-20261011-001 is the highest-value target left -- killing it closes every partition route at once), or (b) switch candidates entirely (naive dossier's open questions: edge-addition on 9-critical biplanar graphs, or SA over planar pairs maximizing union chi).

## Open questions
- Is C7[K4] biplanar at all? Four methods, no partition, no proof either way.
- Can the triangulation-minus-edge rigidity be turned into a non-biplanarity proof?

## Premises
- P-20261011-007

## Tokens
n/a

## Confidence
High on the run itself (machine log: 20,000 iters, 79,604 cores, zero planar parts proposed). High that more blind iterations won't help (no trend in 20k). Medium on 'the method is exhausted' -- symmetry-aware cores were never tried. What would change my mind: a partition from any method, or a non-biplanarity proof.
