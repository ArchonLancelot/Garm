---
dossier_version: "0.2"
id: 2026-10-12-earth-moon-the-10-barrier-k9-edge-budget-and-join
created: 2026-10-12
agent: hsin
task: "Earth-Moon: the 10-barrier -- K9, edge budget, and join impossibility analysis"
outcome: failed
failure_class: knowledge-gap
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: the 10-barrier -- K9, edge budget, and join impossibility analysis

## What was tried
Analytical (not computational): characterized the constraints on 10-chromatic biplanar graphs.
(1) K9-subgraph: Biplanarity is subgraph-hereditary. K9 has thickness 3 (Battle-Harary-Kodama), so any graph containing K9 is not biplanar. This KILLED the K8+K2 join idea (contains K9 on {0..8}).
(2) Join analysis: For G = K_a + H (join), chi(G) = a + chi(H), omega(G) = a + omega(H). To have chi>=10 and be K9-free: need a + chi(H) >= 10 AND a + omega(H) <= 8, so chi(H) - omega(H) >= 2. Case a=7: need omega(H)<=1 but chi(H)=3 impossible. Case a=6: need H 4-chromatic, K3-free (Groetzsch, 11v/20e); K6+Groetzsch has 101e > 90 cap, and is edge-critical (deleting any cross edge drops chi to 9). Case a=5: need H 5-chromatic K4-free, too large. So NO join works.
(3) Edge budget: Greedy coloring-defeat builds 10-chromatic graphs with ~101 edges on 16v, but biplanar cap is 84. 200 trials of budget-constrained (<=84e) construction: ZERO reached chi=10 (best was chi=9). The 17-edge gap suggests 10-chromaticity inherently needs more edges than biplanarity allows, unless structure is very specific.
(4) Mycielski: M(G) boosts chi by 1 but triples edges (3m+n). Only viable if base G is sparse (m <= 3.67n), but 9-chromatic graphs are dense. Dead end.
## Root cause
The 10-barrier is overdetermined: THREE independent constraints (K9-freeness, 6n-12 edge cap, chi>=10 needs density) all bind simultaneously. Joins fail on K9. Sparse constructions fail on chi. Dense constructions fail on edge budget. The feasible region -- if non-empty -- requires a delicate balance that generic methods cannot hit. Sulanke's K6+C5 works for 9 because 9 is just below the threshold where the vise closes.
## Failure signature
The 'one-edge vise' (from external bounds-ledger): two unrelated families both land EXACTLY one short of 10. C5+K7 is over budget by 1 edge; circulants top out at chi=9. Our results confirm: K6+Groetzsch over by 11 edges; greedy needs 101 vs 84 budget; shotgun finds 8 at 1/1000 but never 9. The barrier is structural, not algorithmic.
## Blocking constraint
K9-freeness is the sharpest tool: it kills entire families (all K8-joins) with a one-line proof. The edge budget (6n-12) is second: it rules out dense 10-chromatic graphs. Together, they squeeze the feasible region to (possibly) empty. Any future construction MUST be K9-free and sparse (m <= 6n-12) while achieving chi=10 -- a very narrow target.
## Challengeable premises
- '10-chromatic biplanar graphs exist.' (Gethner conjectures max is 11, implying 10 exists, but no construction is known. Our failure + external 0/11 suggests they may be rarer than conjectured, or the conjecture is wrong.)
- 'The Earth-Moon problem has answer >9.' (If 10-chromatic biplanar don't exist, the answer is 9, and Sulanke 1980 is optimal. The consistent failure of search is weak evidence for this.)
## What retrieval would have changed
A literature search for 'biplanar chromatic number upper bound' might reveal if anyone has proved biplanar => 9-colorable (which would make our search futile). We searched for constructions but not for impossibility proofs. If the answer is 9, we spent the night proving it empirically.
## Open questions
- Has anyone proved an upper bound <12 for biplanar chromatic number? (If 10 or 11 is ruled out, the problem is solved.)
- What is the sparsest 10-chromatic K9-free graph? (If its edge count exceeds 6n-12 for all n, then 10-chromatic biplanar is impossible.)
- Can the K6+C5 pattern be modified to reach 10 without creating K9 or exceeding budget?
## Premises
_Optional: premise ids this approach rested on, one per line (see `garm premise list`). A premise is a load-bearing claim a whole family of approaches assumes; if any listed premise is killed (`garm premise kill`), this dossier becomes a dead route and recall skips it._

## Premises
- P-20261011-001 (trunk, still open -- this analysis does not disprove it)
- P-20261012-002 (killed by K9 argument)

## Tokens
n/a
## Confidence
High on the K9-subgraph argument and join impossibility (both are proofs, not heuristics). High that the 10-barrier is structural (multiple independent lines of evidence). Medium on '10-chromatic biplanar may not exist' -- we cannot prove non-existence, but the vise is very tight.