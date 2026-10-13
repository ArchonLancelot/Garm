---
dossier_version: "0.2"
id: 2026-10-12-earth-moon-trunk-kill-c7k4-non-biplanar-external-evidence
created: 2026-10-12
agent: hsin
task: "Earth-Moon: trunk kill -- C7[K4] is biplanar (P-20261011-001)"
outcome: failed
failure_class: knowledge-gap
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Earth-Moon: trunk kill -- C7[K4] is biplanar (P-20261011-001)

## What was tried
The entire C7[K4] line: 13 genuinely different methods tried to find a biplanar
partition of C7[K4] (28 vertices, 154 edges, chi=10 proven) across 2026-10-11/12 --
symmetric-exhaustive, SA variants, ILP cutting-plane, SAT cutting-plane (20k iters),
minimum-core cutting-plane (~450k cores, 3 seeds), structural subset/triangulation
attack (6,049 subsets, 820 triangulations, 17,550 exact tests). All failed.
Separately, an independent public project (graph-theory-AI/graph-conjectures,
problems/earth_moon_problem, active October 2026) ran a dedicated 9h40m
symmetry-broken SMS (SAT Modulo Symmetries) UNSAT on the same graph and published
an audited "Theorem A": every cycle clique-blowup with n<=30, w<=8, chi>=10 is
non-biplanar. Full intel: experiments/night-shift/../EXTERNAL_INTEL_C7K4_SMS_UNSAT.md.

## Root cause
The trunk assumption was almost certainly false from the start: C7[K4] is
non-biplanar. The external SMS UNSAT is single-tool evidence (their own audit:
"not a theorem", calls for independent verification), but combined with our 13
independent failures it is overwhelming. We spent ~10 hours of compute attacking
a graph someone else had already ruled out -- because we never checked.

## Failure signature
Trunk killed by outside work. Match rule: before a multi-hour campaign on a
candidate from the literature, search for independent results on that exact
object -- a 30-minute literature check would have saved 10 hours of compute.

## Blocking constraint
C7[K4] sits inside the cycle-clique-blowup family (n<=30, w<=8, chi>=10) that
Theorem A covers. Any future candidate must come from outside that family
(non-blowup 10-chromatic K9-free graphs) or the problem pivots to proving the
9-bound.

## Challengeable premises
- 'Our search failing means nothing about biplanarity.' (True per-run, but 13
  failures + an independent UNSAT is a verdict.)
- 'The candidate is ours to discover.' (The external project picked the same
  headline candidate independently -- check first.)

## What retrieval would have changed
A literature/external-project check at campaign start would have found the
graph-conjectures workstream and its SMS UNSAT. The entire C7[K4] campaign --
symmetric search, SA, both SAT cutting-planes, the structural attack, the night
shift -- would have been redirected on day one.

## Open questions
- Independent verification of the SMS UNSAT via a genuinely different method
  (CEGAR loop with networkx planarity oracle) -- their audit explicitly asks
  for it; our K9 calibration showed our cutting-plane proof direction does
  not scale, so CEGAR is the method, not more cutting-plane.
- Non-blowup 10-chromatic K9-free candidates: does any exist outside Theorem
  A's family?
- Is biplanar => 9-colorable provable (the upper-bound pivot)?

## Evidence strength
Third-party computational (single SAT codebase, independently audited, audit
demands independent verification) + first-party corroboration (13 failed
methods). Strong combined; not a theorem.

## Tokens
n/a

## Confidence
High that C7[K4] is non-biplanar (combined evidence). Medium on the external
UNSAT standing alone (single-tool). High that no further compute should be
spent on C7[K4] partitions.
