---
dossier_version: "0.2"
id: 2026-10-12-earth-moon-phase-3-candidate-switch-eight-approach
created: 2026-10-12
agent: hsin
task: "Earth-Moon Phase 3: candidate switch -- eight approaches, 10-barrier holds"
outcome: failed
failure_class: knowledge-gap
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon Phase 3: candidate switch -- eight approaches, 10-barrier holds

## What was tried
EIGHT distinct approaches to find a 10-chromatic biplanar graph (Phase 3, 02:15-06:30 EDT):
(3a v1) SA over planar pairs, clique-lb objective -- stuck at lb=5 after 38k iters, killed.
(3b) Sulanke chord addition: only 5 non-edges exist; all 31 subsets fail biplanar insert.
(3c) K8+K2 join (chi=10, 45e<=48 cap) -- KILLED STRUCTURALLY before SAT finished: contains K9 as subgraph ({0..8} induces K9), K9 not biplanar (thickness 3), heredity kills it. Generalizes to all K8-joins.
(3a v2) SA with K8-planted init (chi=8 start), exact DSATUR objective -- 706k iters, ZERO improvement, killed.
(3d) Shotgun: 12,000 random triangulation pairs (n=14), exact DSATUR -- max chi=8 (rate ~1/1000), zero reach 9.
(3e) Local SA on Sulanke (chi=9 start) -- 171k+ iters, stuck at 9.
(3f) Systematic vertex-addition to Sulanke: 561 neighborhoods (sizes 10->7) -- zero reach chi>=10.
(external) C5+(K7-e) (chi=9, 60e=cap): SAT partition search timed out 600s.
Also: independently verified Sulanke's 27/23 biplanar partition (chi=9) from external certificate.
## Root cause
No single root cause -- the 10-barrier is robust across methods. Contributing factors: (a) chi is a step function, giving no gradient for local search; (b) 10-chromatic graphs need 10-critical subgraphs which are dense, but biplanarity caps density AND forbids K9; (c) the feasible region (K9-free, m<=6n-12, chi>=10) may be empty or vanishingly small; (d) random/annealed search cannot perform the qualitative structural leaps needed (e.g., Sulanke's K6+C5 was hand-designed, not found by search).
## Failure signature
The 10-barrier. Match rule: if your method is (i) local/random search over biplanar graphs, (ii) edge/vertex addition to a 9-chromatic base, or (iii) joins with dense sides -- expect to hit 9 and stall. The barrier held against SAT, SA (3 variants), exhaustive local enumeration, and 12k random samples.
## Blocking constraint
Biplanarity caps edges at 6n-12 and forbids K9 (subgraph-hereditary). 10-chromaticity needs a 10-critical subgraph (dense). These pull in opposite directions; the intersection may be empty. K9-freeness is the binding structural constraint (killed the most elegant idea, K8+K2).
## Challengeable premises
- 'Generic search can find 10-chromatic biplanar if they exist.' (8 methods failed; the feasible region may be too small/structured for blind search.)
- 'Starting from 9-chromatic and adding is the right direction.' (Sulanke + chords failed, + vertex failed 561/561, local SA stuck.)
- 'Joins are promising.' (Only with K8-free sides; the natural K8-join is dead by K9.)
## What retrieval would have changed
Knowing about the external bounds-ledger workstream earlier would have saved re-deriving the C5+K7 analysis, but their 0/11 result CONFIRMED the barrier rather than breaking it. Their Sulanke certificate saved us a partition search (we verified it independently). A literature search for KNOWN 9-chromatic biplanar constructions (beyond Sulanke) should precede any future search -- we need more diverse starting points.
## Open questions
- What 9-chromatic biplanar graphs exist besides Sulanke's? (Need diverse bases.)
- Can the K6+C5 pattern be generalized to chi=10? (Algebraic construction, not search.)
- Is the Earth-Moon answer actually YES (biplanar => 9-colorable)? The consistent search failure is weak evidence.
- What is the true density of 9-chromatic (not 10) in random biplanar graphs? (Our shotgun: 0/12000 reached 9 -- even 9 is rare randomly.)
## Premises
_Optional: premise ids this approach rested on, one per line (see `garm premise list`). A premise is a load-bearing claim a whole family of approaches assumes; if any listed premise is killed (`garm premise kill`), this dossier becomes a dead route and recall skips it._

## Premises
- P-20261011-001 (trunk, still open)
- P-20261011-003 (weakened)
- P-20261012-002 (killed by 3c)

## Tokens
n/a
## Confidence
High that generic search is exhausted for this problem (8 methods, consistent barrier). High on the K8+K2 structural kill (one-line proof). Medium that 10-chromatic biplanar graphs are rare vs non-existent -- we cannot distinguish. Low on what construction WOULD work -- that needs graph-theoretic insight, not more compute.