---
dossier_version: "0.2"
id: 2026-10-07-induction-without-descent
created: 2026-10-07
agent: muse-wonder-max
origin: muse-wonder-max
task: "Prove the quotient is a square by strong induction on a+b using a smaller pair with the same quotient"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 1
---

# Failure dossier: Strong induction on a + b, with no way down

## What was tried
Induct on a+b. To use the hypothesis you first need a machine that turns (a,b) into a strictly smaller pair with the same k. I tried to build that machine out of gcd and Euclidean steps.

- Divide by d = gcd(a,b): (30,8) → (15,4). But (15²+4²)/(15·4+1) = 241/61 is not even an integer. Divisibility is destroyed.
- Euclidean step (a,b) → (a−b, b) and (a mod b, b): same k is not preserved; examples break immediately.
- Induct on k instead: no relation between the pair for k and the pair for k−1 exists to induct along.

## Root cause
Induction was the right instinct with the wrong descent operation. Gcd/Euclidean moves change the equation; they do not preserve the value k, so the induction hypothesis never applies. I was searching for a descent map inside arithmetic operations instead of inside the equation itself.

## Failure signature
Name: induction-without-a-descent-operation. Match rule: if your induction step needs a smaller solution with the same quotient but your reduction changes the quotient, stop — you do not have an induction, you have a wish.

## Blocking constraint
No gcd, subtraction, or remainder operation preserves k = (a²+b²)/(ab+1). A same-k descent map, if one exists, must come from the equation a² − kab + (b²−k) = 0 itself.

## Challengeable premises
- "The descent map should be a familiar arithmetic operation." Negate it: let the quadratic in one variable supply its own second root.

## What retrieval would have changed
This is the dossier that earned its keep. Its blocking constraint, inverted, is the breakthrough: "find a map (a,b) → smaller pair, same k, manufactured from the equation." That sentence is Vieta jumping before you know its name.

## Open questions
- Does the equation, read as a quadratic in a, automatically produce a partner a′ with (a′,b) giving the same k?

## Premises
- P-20261009-002
- P-20261009-005

## Tokens
~22k (est. — gcd + Euclidean variants)

## Confidence
High on the failure (counterexamples are explicit), medium that the inversion must work — it only became certain in D-05's aftermath.
