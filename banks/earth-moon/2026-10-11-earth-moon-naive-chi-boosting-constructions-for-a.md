---
dossier_version: "0.2"
id: 2026-10-11-earth-moon-naive-chi-boosting-constructions-for-a
created: 2026-10-11
agent: hsin
task: "Earth-Moon: naive chi-boosting constructions for a 10-chromatic biplanar graph"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: naive chi-boosting constructions for a 10-chromatic biplanar graph

## What was tried

- **Universal vertex on Sulanke's K_6 + C_5.** Sulanke's graph (11 v, 50 e, chi=9) plus a vertex adjacent to all 11 forces chi=10. Edge count: 61 > 6*12-12 = 60. Fails the biplanar edge budget by exactly one edge.
- **Delete-one-edge then add universal vertex.** Every single-edge deletion of K_6 + C_5 drops chi to 8 (K_6 edge -> join is 5+3; C_5 edge -> 6+2; cross edge -> 8-coloring exists by giving x the color of its non-neighbor). So the "61 - 1 = 60" fix yields chi=9, not 10. Dead.
- **Mycielski on K_8** (biplanar, chi=8): M(K_8) has 17 v, 92 e, chi=9. Exceeds the 90-edge biplanar cap, and only reaches 9 anyway. Double dead.
- **Join K_6 + Grotzsch graph** (triangle-free, 4-chromatic, 11 v, 20 e): chi = 6+4 = 10, omega = 8, but 15+20+66 = 101 > 90 edges. Dead on the count.
- **Chord addition to Sulanke's C_5** (only 5 non-edges in the whole graph): making the C_5 part 4-chromatic on 5 vertices forces a triangle (smallest triangle-free 4-chromatic graph has 11 vertices), which with the K_6 join creates a K_9; thickness(K_9)=3 kills biplanarity hereditarily. So no chord-supergraph of Sulanke's can be 10-chromatic biplanar. Dead by proof, not by search.
- **Vertex substitution** (replace a K_6 vertex by C_5, fully joined to its neighbors): chi jumps to 11 but edges explode to 95 on 15 v vs cap 78. Dead.

## Root cause

Every classical chi-boosting operation (Mycielski, join, universal vertex, substitution) is edge-heavy: it multiplies edges faster than vertices. But biplanarity caps edges at 6n-12 while chi=10 demands average degree ~9.78+ (Kostochka-Yancey for 10-critical: m >= (44n-35)/9). The feasible band is narrow (9.78 <= avgdeg < 12 - 24/n), and all the textbook boosters overshoot it. I was designing for chromatic number and checking biplanarity after, instead of designing inside the edge budget.

## Failure signature

**Edge-budget-blind chi-boosting.** Match rule: if your construction plan for a high-chi biplanar graph starts from a named chi-raising operation (Mycielski, join, universal vertex, substitution) and you have not yet computed m vs 6n-12, stop and compute it first -- the operation almost surely overshoots.

## Blocking constraint

Biplanar graphs satisfy m <= 6n-12 (two planar layers), are K_9-free (thickness(K_9)=3, hereditary), and -- as of Szeider, Sept 2026 -- every biplanar graph with independence number <= 2 is 9-colorable, so a 10-chromatic example needs alpha >= 3. The naive boosters each violate at least one of these three.

## Challengeable premises

- "Chi-boosting must come from a dense named operation." (What if the 10th color comes from sparse global structure instead, e.g. a 10-critical graph with average degree barely above 9.78?)
- "Sulanke's K_6 + C_5 is the right starting point." (What if the 9-chromatic 12-17 vertex graphs of Boutin-Gethner-Sulanke / Alalqam have more headroom under 6n-12?)
- "A 10-chromatic biplanar graph is built by modifying a 9-chromatic one." (What if it is found by searching pairs of planar graphs directly, maximizing chi of the union?)
- "The alpha=2 avenue might still work." (False -- Szeider 2026 proved it impossible via SAT+Lean. Do not revisit.)

## What retrieval would have changed

A second run retrieving this dossier would skip all six constructions above and instead open with the triple constraint (m <= 6n-12, K_9-free, alpha >= 3) as a filter on the *design space*, then pick one of: (a) local edge-addition search on 9-critical biplanar graphs with exact chi + incremental biplanarity testing; (b) simulated annealing over pairs of planar graphs maximizing chi of the union.

## Open questions

- Does a 10-critical graph with average degree < 12 exist on few enough vertices (n <= ~25) to be searchable? Kostochka-Yancey allows it; no explicit small example is known to me.
- Which known 9-critical biplanar graph maximizes (6n-12) - m, i.e. has the most edge headroom for local search?
- Can the backtracking biplanar-partition search scale to ~60-edge candidates, or is a smarter partition algorithm (seeded from a known partition) required?

## Confidence

High on the six dead ends (each is arithmetic or a short proof, and chi(Sulanke)=9 plus the deletion analysis were machine-verified with exact DSATUR). Medium on the "narrow feasible band" framing -- it assumes 10-criticality, while a 10-chromatic non-critical graph could in principle be sparser. What would change my mind: a single explicit 10-chromatic biplanar graph, or a proof that none exists.

## Premises
- P-20261011-004
- P-20261011-005

## Tokens

~8k tokens of hand analysis before writing any code. Method: counted from the research turn; the code afterward is separate.
