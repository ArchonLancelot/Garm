---
dossier_version: "0.2"
id: 2026-10-11-earth-moon-sa-partition-search-plateaus-cost-funct
created: 2026-10-11
agent: hsin
task: "Earth-Moon: SA partition search plateaus; cost function rank-dependent"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: SA partition search plateaus; cost function rank-dependent

## What was tried

- **SA v1:** Simulated annealing on 77/77 edge partitions. Cost = sum over parts of (|E| - |greedy maximal planar subgraph|). Random swap moves. Cost 40 -> 33, then plateau.
- **SA v2:** Added targeted repair moves (swap edges rejected by the greedy planarization). Cost 40 -> 20 across 3 seeds, then plateau at 20-23. Significant improvement from targeting, but stuck.
- **Rank-dependence discovered:** The SAME partition scores cost 30, 31, 38, 40, 40 under 5 different greedy edge orders. The cost function is highly order-dependent -- SA was optimizing a noisy signal.
- **SA v3:** Rank-averaged cost (mean over 3 fixed orders) for stable guidance. Slower (0.5s/iter vs 0.3s) but consistent. Currently at cost ~30 after 280 iters, improving very slowly.

## Root cause

Two compounding issues. (1) The greedy-maxplanar proxy for "distance to planar" is order-dependent, so v1/v2's cost was noisy; comparisons within a run were fair (fixed rank) but the absolute cost was meaningless across runs, and the guidance was weak. (2) Even with a stable cost (v3), the landscape has deep local minima around cost 20-30; targeted moves help but can't escape. The underlying problem (biplanar partition of a 154-edge graph with 77/77 rigidity) may simply be too hard for local search, or no partition exists.

## Failure signature

**Noisy-proxy SA.** Match rule: if your SA cost function involves a greedy/order-dependent subroutine, test the cost variance on a FIXED solution across different orders BEFORE running. If variance is high (>20% of range), the SA is optimizing noise -- fix the cost first (average over orders, or find an order-independent proxy).

## Blocking constraint

C_7[K_4]'s 154 edges force a 77/77 (or 76/78) split with each part a triangulation-minus-edge. Local search cannot "see" this global rigidity; it just sees a 154-dimensional binary space with a bumpy proxy cost.

## Challengeable premises

- "A better cost function will unstick the SA." (What if the issue is not the cost but the search itself -- local moves can't traverse the space?)
- "C_7[K_4] is biplanar." (What if all this search is failing because there's nothing to find?)
- "77/77 is the right balance." (76/78 not yet tried with SA.)
- "The partition must be found by search." (What if it requires a constructive proof or a different candidate graph?)

## What retrieval would have changed

A second run would test cost-function variance FIRST (5 minutes), then either fix it or abandon SA for a different method (e.g., exact backtracking with strong seeding, or a constructive approach). It would not burn hours on v1/v2 with a noisy cost.

## Open questions

- Is C_7[K_4] actually biplanar? Still unknown -- all searches inconclusive.
- Can the triangulation-pair formulation (find T1,T2 with |intersection|=2) be made to work with better triangulation-finding?
- Is there a sparser 10-chromatic candidate with more partition slack?

## Confidence

High on the rank-dependence (machine-measured: 30-40 variance). High on v2 plateau (3 seeds). Medium on "local search can't do it" -- v3 is still running and might break through, but the trend is not encouraging. What would change my mind: a found partition (any method), or a non-biplanarity proof.

## Premises
- P-20261011-001
- P-20261011-003

## Tokens

~25k tokens across SA v1/v2/v3 design, implementation, and debugging. Method: iterative development with testing; estimate from output volume.
