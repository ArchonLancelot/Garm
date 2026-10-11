---
dossier_version: "0.2"
id: 2026-10-07-find-baillie-psw-pseudoprime-via-order-theoretic-p
created: 2026-10-07
agent: hsin
task: "Find Baillie-PSW pseudoprime via order-theoretic pq construction"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
---

# Failure dossier: Find Baillie-PSW pseudoprime via order-theoretic pq construction

## What was tried
Derived construction S(r,p) with full proof: for prime p with
ord_p(2) = 2^{r+1}*m (m odd), sieve primes q ≡ 1 mod 2^{r+1}*m, keep q with
ord_q(2) | 2^{r+1}*ODD_p and exact 2-adic valuation r+1 (two-powmod test, no
factoring needed). Then n = p*q PROVABLY satisfies 2^{d*2^r} ≡ -1 mod p and
mod q (r < s shown automatic), i.e., n is a strong Fermat pseudoprime to
base 2 by construction. Validated at small scale: every keeper passed the
direct Miller-Rabin test (0 proof failures), segmented sieve verified
against brute force. Then analyzed the keeper yield at real scale
(q > 2^64/p): keepers q are prime divisors of the FIXED number 2^E-1
(E ~ p), so keeper density at q ~ 10^13 is ~1/q ~ 10^-13. Sieving for them
is futile; finding them needs factoring 2^E-1.

## Root cause
Correct construction, infeasible search. I built the whole pipeline
(sieve + two-powmod keeper test + proof validation) before doing the
5-minute Fermi estimate of keeper density. The estimate kills it: to find
ONE keeper at q ~ 10^13 you must test ~10^13 candidates. The construction
is mathematically right and computationally useless as a sieve. The error
was sequencing: build first, estimate later. (The density analysis itself,
done during dossier writing, immediately suggested the fix: don't sieve
for prime divisors of 2^E-1 — factor 2^E-1 and read them off.)

## Failure signature
Name: correct-construction-zero-yield. If your construction's keepers are
prime divisors of a fixed huge number 2^E-1 and you need them in a specific
range above 2^64/p, stop sieving: density ~1/q makes it futile. Either
factor 2^E-1 directly (feasible only for small E) or change the
construction. Always Fermi-estimate the yield BEFORE building the pipeline.

## Blocking constraint
Per fixed p, the keeper set is finite (divisors of 2^E-1, E ~ p) and
thinly spread up to 2^E. Sieving intervals above 2^64/p has expected yield
~0 for any feasible interval width. The constraint is information-theoretic:
sieving can't find what isn't densely there.

## What retrieval would have changed
Would have forced the density estimate before the implementation, saving
the sieve/powmod pipeline work, and pointed directly at the factoring
inversion (pass 2's approach): for small E, factor 2^E-1 and harvest its
large prime divisors as keepers.

## Confidence
High on the construction's correctness (proof + 0 validation failures).
High on the infeasibility (the 1/q density argument is robust; the
literature independently calls this shape intractable — Chen-Greene 2003).
