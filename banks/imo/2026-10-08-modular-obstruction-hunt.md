---
dossier_version: "0.2"
id: 2026-10-08-modular-obstruction-hunt
created: 2026-10-08
agent: muse-wonder-max
origin: muse-wonder-max
task: "Prove the quotient is a square by finding a modulus where non-square quotients are impossible"
outcome: failed
failure_class: knowledge-gap
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Hunt for a modulus that kills non-squares

## What was tried
Look for m such that a²+b² ≡ k(ab+1) (mod m) has no solutions when k is a non-square — a local obstruction that rules out k = 2, 3, 5, 6, … in one stroke.

- Mod 3, 4, 8: squares are restricted, but k = 2, 3, 5 all still occur as residues of the equation — e.g. solutions mod m exist for every small non-square k tried.
- Quadratic reciprocity on the discriminant Δ = k²b² − 4(b²−k): forcing Δ to be a square mod p constrains k mod p, never k itself.
- Brute force mod m ≤ 200: for each non-square k ≤ 20, some (a,b) mod m satisfies the congruence. No separating modulus exists in range.

## Root cause
A congruence can only forbid what is locally impossible. This equation is locally solvable for non-square k — the obstruction is global (integrality + minimality), not local. I was looking for a finite check for a theorem whose content is an infinite descent.

## Failure signature
Name: local-obstruction-for-a-global-theorem. Match rule: if you are hunting for a modulus or congruence that separates square quotients from non-square quotients, stop — check local solvability first; if solutions exist mod m, no modulus will save you.

## Blocking constraint
For every modulus searched, non-square k admit solutions to a²+b² ≡ k(ab+1) (mod m). There is no local obstruction; the square-ness of k is a global, descent-type fact.

## Challengeable premises
- "Some finite modulus sees the difference between square and non-square k." The brute-force search says no modulus ≤ 200 does.

## What retrieval would have changed
A second run would run the 10-minute local-solvability check before investing in reciprocity, kill the whole modular family, and redirect to global structure — minimality, size, descent.

## Open questions
- What global property distinguishes the integer solutions from the merely congruence solutions?

## Premises
- P-20261009-003

## Tokens
~15k (est. — reciprocity + search scripts)

## Confidence
Medium-high — the search is finite (m ≤ 200, k ≤ 20) but the pattern is decisive. A cleverer modulus is conceivable; the burden of proof is now on it.
