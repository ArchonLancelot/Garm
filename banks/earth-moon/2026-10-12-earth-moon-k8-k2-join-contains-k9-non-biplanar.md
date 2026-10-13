---
dossier_version: "0.2"
id: 2026-10-12-earth-moon-k8-k2-join-contains-k9-non-biplanar
created: 2026-10-12
agent: hsin
task: "Earth-Moon: K8+K2 join contains K9, non-biplanar"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: K8+K2 join contains K9, non-biplanar

## What was tried
Had the idea: K8+K2 has chi = 8+2 = 10 (join adds chromatic numbers) and 45 edges vs biplanar cap 48 -- edge-feasible. Launched SAT partition search (900s budget). Before it finished, realized the structural flaw (see Root cause) and killed the run at ~400s/1500 iters.
## Root cause
K8+K2 contains K9 as a subgraph: vertices 0..7 form K8, vertex 8 is universal to them, so {0..8} induces K9. K9 has thickness 3 (Battle-Harary-Kodama), hence is NOT biplanar. Biplanarity is subgraph-hereditary: a graph containing a non-biplanar subgraph is non-biplanar. So K8+K2 was doomed before the first SAT iteration. More generally: ANY join G+H with K8 ⊆ G contains K9 (pick h∈H, G+h ⊇ K9), so no K8-join can be biplanar. The edge-count feasibility (45 ≤ 48) was necessary but nowhere near sufficient.
## Failure signature
Join-with-K8 non-biplanarity. Match rule: if your 10-chromatic candidate is a join G+H with chi(G)+chi(H) ≥ 10 and K8 ⊆ G, stop immediately -- G plus any vertex of H contains K9, and K9 is not biplanar. Check subgraph obstructions BEFORE launching search.
## Blocking constraint
Biplanarity is subgraph-hereditary and K9 is the minimal complete obstruction. Any candidate containing K9 (or any known non-biplanar graph) as a subgraph is dead on arrival, regardless of edge counts.
## Challengeable premises
- 'Edge-count feasibility implies a partition might exist.' (K8+K2: 45 ≤ 48 but contains K9 -- structure dominates counting.)
- 'Joins are a good route to 10-chromatic biplanar.' (Only with K8-free sides, which rules out the easy 8-chromatic base.)
## What retrieval would have changed
A second run would check for K9 (and other known non-biplanar) subgraphs FIRST -- 5 lines of code -- before any partition search. The SAT run's 400s were entirely wasted.
## Open questions
- Which 8-chromatic K8-free graphs exist that could serve as a join base? (Exotic; none on hand.)
- Is K9-freeness + edge budget sufficient for any interesting 10-chromatic family?
## Premises
_Optional: premise ids this approach rested on, one per line (see `garm premise list`). A premise is a load-bearing claim a whole family of approaches assumes; if any listed premise is killed (`garm premise kill`), this dossier becomes a dead route and recall skips it._

## Premises
- P-20261012-002

## Tokens
n/a
## Confidence
High on the K9-subgraph argument (it is a one-line proof: {0..8} induces K9, K9 not biplanar, heredity). High that all K8-joins are dead. Medium on 'joins are exhausted' -- K8-free 8-chromatic bases are unexplored.