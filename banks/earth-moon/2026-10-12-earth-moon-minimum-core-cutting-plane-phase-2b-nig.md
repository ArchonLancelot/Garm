---
dossier_version: "0.2"
id: 2026-10-12-earth-moon-minimum-core-cutting-plane-phase-2b-nig
created: 2026-10-12
agent: hsin
task: "Earth-Moon: minimum-core cutting-plane phase 2b (night shift)"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: minimum-core cutting-plane phase 2b (night shift)

## What was tried
- Ran phase2b_sat.py (minimum-core cutting plane: multi-start shrink 18.4->~13, 20 verified automorphisms, orbit-image clauses) across three seeds: seed 20261012 (iter 4950, 207k cores, killed by VM restart), seed 777001 (iter 2450, 102k cores, killed by VM restart), seed 555003 (3300 iters, 140k cores, 6000s budget, clean timeout). Combined: ~450k distinct minimal cores learned, min core 9 (K3,3 subdivision), batch core mean ~17-18 and rising throughout every run.
## Root cause
Same non-convergence pattern as the plain cutting plane, at larger scale: every iteration learns ~42 fresh orbit-image clauses, batch core mean rises as small cores get ruled out, and the clause space shows no sign of exhaustion. Minimum cores (mean ~13 vs 18.4 greedy) and orbit images only moved the wall outward; the method is enumerating a vast core space, not converging. 450k cores with linear growth = no decision in sight.
## Failure signature
Cutting-plane non-convergence, strengthened variant. Match rule: if 400k+ distinct minimal cores across multiple seeds still show linear growth with rising batch means and zero partitions proposed, the method is dead for this graph -- stronger conflicts do not fix a fundamentally enumerative search.
## Blocking constraint
C7[K4]'s minimal non-planar core space is too large: even minimum (multi-start shrunk) cores with orbit-image multiplication cannot cover it. Each SAT proposal is still an essentially random 76-78 edge split; planarity guidance never materializes.
## Challengeable premises
- 'Minimum cores fix the cutting plane.' (They shrank mean core 18.4->13.2 but changed nothing about convergence.)
- 'C7[K4] is biplanar.' (Trunk still open -- correctly; failed searches are not disproofs.)
## What retrieval would have changed
A second run would not launch a fourth cutting-plane variant. It would go straight to candidate switch (Phase 3): the graph may simply not be biplanar, and the search budget is better spent on other 10-chromatic candidates.
## Open questions
- Is there any core-strengthening (e.g. MaxSAT-minimum, symmetry-canonical) that changes the convergence picture? Evidence says no.
- Which alternative 10-chromatic candidate has the most headroom under 6n-12?
## Premises
_Optional: premise ids this approach rested on, one per line (see `garm premise list`). A premise is a load-bearing claim a whole family of approaches assumes; if any listed premise is killed (`garm premise kill`), this dossier becomes a dead route and recall skips it._

## Premises
- P-20261011-007

## Tokens
n/a
## Confidence
High on the non-convergence (450k cores, 3 seeds, consistent linear growth, machine-measured). High that further cutting-plane variants are exhausted. Medium on the trunk -- C7[K4] may still be biplanar; we just cannot find the partition this way.