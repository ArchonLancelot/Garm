---
dossier_version: "0.2"
id: 2026-10-11-earth-moon-rotation-symmetric-biplanar-partition-o
created: 2026-10-11
agent: hsin
task: "Earth-Moon: rotation-symmetric biplanar partition of C7[K4]"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: rotation-symmetric biplanar partition of C7[K4]

## What was tried

- **Candidate identification (literature).** The graph-conjectures repo (graph-theory-ai) names C_7[K_4] -- lexicographic product, 28 vertices -- as their headline candidate: chi=10, omega=8 (K_9-free), 154 edges vs biplanar cap 156. Provenance is theirs, not mine; I verified every claim independently.
- **chi = 10, verified two ways.** Counting proof: a k-coloring gives 4-sets S_0..S_6 of colors with adjacent disjoint (layers are K_4, adjacent layers fully joined); each color occurs in <= 3 layers (independent set in C_7, alpha=3); 28 = sum |S_i| <= 3k forces k >= 10. Greedy coloring achieves 10. So chi is exactly 10, no solver needed for the lower bound.
- **Symmetric partition search.** Since 154 edges must split 77/77 (cap 78 per part), searched all rotation-symmetric patterns: E1 takes the same `a` internal K_4 edges and same `b` between-edges in each of the 7 units, a+b=11 forced by the caps. Enumerated all a in 0..6, all non-isomorphic Q (canonicalized under S_4), all C(16,b) between-patterns P: 109,122 patterns, each tested with two planarity checks. **Exhausted in 82s: no symmetric partition exists.**
- Also confirmed: backtracking partition search is hopeless from scratch (2^154); ILP cutting-plane with greedy Kuratowski cores stalls (400 iterations, 802 weak cuts, cores of size 13-24 prune almost nothing).

## Root cause

I assumed the partition would inherit the graph's 7-fold rotational symmetry. It doesn't have to: Aut(C_7[K_4]) allows independent S_4 twists per fiber (rotation combined with per-position permutations), so the symmetric pattern family was a strict -- and apparently empty -- subset. More broadly, I keep reaching for the partition search before fully exploiting the rigidity both parts must satisfy (each a triangulation minus one edge).

## Failure signature

**Symmetry-assumed partition search.** Match rule: if you are searching for a biplanar/planar partition of a vertex-transitive graph and you restrict to patterns invariant under the full rotation group, stop -- the automorphism group usually allows fiber-dependent twists, and the uniform family may be empty even when a partition exists. Search the uniform family first (it's cheap), but treat exhaustion as "no symmetric partition", never as "non-biplanar".

## Blocking constraint

C_7[K_4] has 154 edges against a 156 cap, forcing both planar parts to 77 edges -- exactly one short of maximal planar. Every partition attempt must thread this needle; generic search (backtracking, weak-cut ILP) cannot feel the rigidity.

## Challengeable premises

- "The biplanar partition, if it exists, can be found by generic search." (What if it requires exploiting the triangulation-minus-edge rigidity directly, e.g. searching over triangulation pairs?)
- "C_7[K_4] is biplanar." (What if the headline candidate is not? A non-biplanarity proof is also a result -- it kills the candidate and redirects the search.)
- "chi=10 must come from a dense 11-regular graph." (What if a sparser 10-chromatic graph, with more edge slack per part, is easier to partition?)
- "The partition must split 77/77." (76/78 is allowed by the caps; the symmetric search only covered the symmetric 77/77 case.)

## What retrieval would have changed

A second run would skip the uniform-symmetry restriction and go straight to: (a) simulated annealing on partitions with a smooth distance-to-planar cost (greedy maximal planar subgraph size), or (b) annealing over triangulation pairs with diagonal flips. Both were built as fallbacks only after the symmetric search failed.

## Open questions

- Does C_7[K_4] admit ANY biplanar partition (symmetric or not)? Still open -- SA and random-triangulation searches are running.
- Can the triangulation-minus-edge rigidity be turned into a non-biplanarity proof (e.g. via degree or face-counting obstructions)?
- Is there a sparser 10-chromatic candidate (fewer than 154 edges) with more partition slack?

## Confidence

High on the symmetric exhaustion (109,122 patterns, machine-checked) and the chi=10 proof (hand proof + greedy coloring). Medium on the "ILP stalls" read -- 400 iterations is suggestive, not conclusive. What would change my mind: a found partition (any method), or a non-biplanarity proof.

## Premises
- P-20261011-001
- P-20261011-002

## Tokens

~15k tokens across the symmetric search design, ILP attempt, and analysis. Method: tool-call heavy turn; estimate from output volume.
