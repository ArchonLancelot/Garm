---
dossier_version: "0.2"
id: 2026-10-08-fourth-power-divisor-reduction
created: 2026-10-08
agent: muse-wonder-max
origin: muse-wonder-max
task: "Prove the quotient is a square by reducing ab+1 divides a²+b² to ab+1 divides a⁴+1 and b⁴+1"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Reduce to a⁴ + 1 and b⁴ + 1 divisibility

## What was tried
A genuinely pretty move: multiply by b² and use ab ≡ −1 (mod ab+1) to get ab+1 | b⁴+1, symmetrically ab+1 | a⁴+1. Then… nothing. The trail goes cold.

- From ab+1 | b⁴+1, try to bound: ab+1 ≤ b⁴+1 is true and useless — it holds for every pair, square k or not.
- Try to iterate: ab+1 | a⁴+1 and ab+1 | b⁴+1 suggest studying a⁴ ≡ b⁴ ≡ −1, i.e. 8th roots of unity mod ab+1 — rich structure, no path to "k is a square".
- Try gcd(a⁴+1, b⁴+1) manipulations to force ab+1 itself to be a square — false: (a,b)=(8,2) gives ab+1 = 17, not a square, while k = 4 is.

## Root cause
The reduction is true but information-losing: ab+1 | b⁴+1 is far weaker than the original condition. I polished a necessary condition until it no longer implied the conclusion, then tried to prove the conclusion from it anyway.

## Failure signature
Name: true-but-too-weak-reduction. Match rule: if your clever divisibility reduction also holds for pairs where the conclusion fails, stop — you have proved a weaker theorem and are trying to spend it as the stronger one.

## Blocking constraint
ab+1 | b⁴+1 carries no square-ness information about k (witness ab+1 = 17 at (8,2)). Any route through fourth powers alone cannot distinguish k = 4 from a hypothetical non-square k.

## Challengeable premises
- "A sufficiently clever necessary condition must eventually be sufficient." Negated by (8,2): the condition holds, the hoped-for intermediate claim (ab+1 square) is false.

## What retrieval would have changed
A second run would keep the ab ≡ −1 trick in its pocket (it is useful algebra) but refuse to build the proof on it, and would test any proposed reduction against (8,2) and (30,8) before investing.

## Open questions
- Which transformations of the condition are reversible — i.e. preserve exactly the same k?

## Premises
- P-20261009-004

## Tokens
~12k (est.)

## Confidence
High — explicit witnesses. The reduction is a dead end for this conclusion, however beautiful.
