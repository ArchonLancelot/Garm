---
dossier_version: "0.2"
id: 2026-10-09-minimal-counterexample-wrong-descent
created: 2026-10-09
agent: muse-wonder-max
origin: muse-wonder-max
task: "Prove the quotient is a square by taking a minimal counterexample and descending by factoring the quotient"
outcome: recovered
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 1
---

# Failure dossier: Minimal counterexample, wrong way down

## What was tried
Assume k is a non-square, take (a,b) with a+b minimal giving that k. Then try to descend by attacking k's prime factors — divide out a prime p | k, or replace (a,b) using a factorisation of the equation.

- Let p be a prime with odd exponent in k (exists since k is a non-square). Try to show p | a and p | b, then divide through — the equation does not cooperate: at the minimal pair, p need not divide either variable.
- Try to build a smaller pair with a different, smaller k′ and induct on k — but different k is a different problem; minimality on a+b says nothing about it.
- Stare at the fixed-k equation a² − kba + (b²−k) = 0. It is a quadratic in a. I had written it as a condition for days before reading it as an object with two roots.

## Root cause
The minimal-counterexample frame was correct; the descent mechanism was wrong. I looked for descent in k's factorisation instead of in the quadratic's second root. The other root a′ = kb − a is an integer for free (sum of roots), gives the same k for free (it satisfies the same equation), and is smaller — every property I had been trying to manufacture by hand.

## Failure signature
Name: minimal-counterexample-needs-the-quadratic-other-root. Match rule: if you have a minimal counterexample to a symmetric Diophantine condition and you are descending by factoring, stop — rewrite the condition as a quadratic in one variable and take the other root.

## Blocking constraint
INVERTED → BREAKTHROUGH: I needed a smaller same-k pair and assumed it must be built from arithmetic on (a,b). It need not be built at all: for fixed b,k the quadratic x² − kbx + (b²−k) already contains a second solution a′ = kb − a = (b²−k)/a, an integer with 0 ≤ a′ < a unless a′ = 0, which forces k = b².

## Challengeable premises
- "The equation in one variable is a condition to check, not an object with its own solutions." Negating this single premise is the entire Vieta-jumping idea.

## What retrieval would have changed
This dossier, read together with the induction dossier, is the proof in embryo: the induction dossier said "the descent map must come from the equation itself"; this one said "the minimal counterexample is the right frame." Recall on attempt 6 returned both. The new approach was their conjunction.

## Open questions
- In the descent, why must a′ be non-negative — and what exactly happens at a′ = 0?

## Premises
- P-20261009-005
- P-20261009-006

## Tokens
~20k (est.)

## Confidence
High, retrospectively — this is now a verified proof (see Proof below + brute-force check to 300). At writing time: medium, which is why the Confidence section exists.

## Proof (the recovery)
The six steps of the Vieta-jumping proof this autopsy produced:

1. **Suppose k is not a square.** Fix a positive integer k that is not a perfect square, and suppose some positive integers a, b satisfy (a²+b²)/(ab+1) = k. We will derive a contradiction. `a² + b² = k(ab + 1), k ∉ {1,4,9,16,…}`
2. **Take the smallest criminal.** Among all such pairs, choose one with a+b minimal — and, swapping if needed, a ≥ b > 0. Minimality is the engine: anything strictly smaller with the same k is now forbidden.
3. **Read the equation as a quadratic.** Freeze b and k. The equation is quadratic in the other variable: x² − kb·x + (b²−k) = 0. One root is x = a. A quadratic always has a second root — call it a′. This is the step five attempts missed.
4. **Vieta's formulas hand you a′ for free.** Sum of roots: a + a′ = kb, so a′ = kb − a is an integer. Product: a·a′ = b²−k, so a′ = (b²−k)/a. And since a′ satisfies the same equation, (a′²+b²)/(a′b+1) = k as well. Same k, new pair — the induction dossier's missing descent map, delivered by algebra.
5. **a′ cannot be negative, and a′ < a.** From a′² + b² = k(a′b + 1) with k > 0, the right side must be positive, so a′b + 1 > 0, i.e. a′ ≥ 0. Also a′ = (b²−k)/a < b²/a ≤ a (using a ≥ b). So 0 ≤ a′ < a: a genuinely smaller partner — unless a′ = 0.
6. **So a′ = 0 — and k = b².** If a′ > 0, then (b, a′) is a positive pair with the same k and smaller sum, contradicting minimality. Hence a′ = 0. But then the product of roots gives 0 = b² − k, so k = b² — a perfect square, contradicting our assumption. No non-square k can ever occur. ∎
