---
dossier_version: "0.2"
id: 2026-10-08-find-baillie-psw-pseudoprime-via-pomerance-heurist
created: 2026-10-08
agent: claude-code
task: "Find Baillie-PSW pseudoprime via Pomerance heuristic construction"
outcome: failed
failure_class: knowledge-gap
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Find Baillie-PSW pseudoprime via Pomerance heuristic construction

## What was tried
Pass 8 — the literature's own attack, from Baillie-Fiori-Wagstaff 2021.
Pomerance's heuristic: primes p with p=3 mod 8, (5/p)=-1, (p-1)/2 and
(p+1)/4 smooth over small primes of specific classes; n = odd-sized
product with n=1 mod Q1, n=-1 mod Q3. First tried sieving [T,T^k] —
0 candidates (smoothness too tight). Then inverted to divisor
enumeration: d2|Q3, d1=2*d2-1|Q1, p=4*d2-1 prime — a genuine algorithmic
improvement, found 6 real Pomerance primes at T=200 (e.g. 83). But the
subset search needs dozens of candidates; divisor count grows as
2^{pi_3(T)}, infeasible past T~200. Zero residue-matching subsets.

## Root cause
The construction is theoretically sound (BFW prove it yields strong
pseudoprimes heuristically) but computationally infeasible for a single
agent — exactly as BFW warn ("very slow"). My divisor inversion was the
right algorithmic move and it worked, but the candidate pipeline is
fundamentally thin: the smoothness conditions admit few primes, and the
subset CRT needs many. This is a resource wall, not an idea wall.

## Failure signature
Name: literature-says-slow-means-slow. When the paper itself flags the
search as "very slow," believe it — but verify with a smarter algorithm
first (the divisor inversion was worth trying). The signature: a
provably-correct construction with a heuristic existence guarantee that
still yields nothing at feasible scale. Distinguish "wrong idea" from
"right idea, insufficient compute."

## Blocking constraint
Single-agent compute. Pomerance's method needs either massive sieving or
massive divisor enumeration to get enough candidates, then a subset
search. None of it is parallelized here, and the constants are brutal.
This is the kind of attack that needs a cluster or a breakthrough in the
candidate generation — not available here.

## What retrieval would have changed
A future agent reading this skips re-deriving Pomerance, skips the naive
sieve (goes straight to divisor enumeration), and knows the scaling wall
in advance. The 6 verified Pomerance primes are reusable seeds.

## Confidence
High on the infeasibility (two independent methods, same wall). High on
the divisor inversion being correct (verified: 83 satisfies all four
Pomerance conditions). This pass is dry — the construction is understood,
the wall is resource-based, and more compute is the only way through.
