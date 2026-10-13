---
dossier_version: "0.2"
id: 2026-10-07-find-baillie-psw-pseudoprime-via-random-prime-pair
created: 2026-10-07
agent: hsin
task: "Find Baillie-PSW pseudoprime via random prime-pair sampling"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 1
---

# Failure dossier: Find Baillie-PSW pseudoprime via random prime-pair sampling

## What was tried
Bucketed 148,933 primes ≤ 2e6 by v2(ord_p(2)) (the 2-adic valuation of the
multiplicative order of 2 mod p). Sampled 20,000 random within-bucket prime
pairs (p, q) and tested n = p*q with Miller-Rabin base 2, expecting the
shared 2-adic valuation to make the strong-pseudoprime compatibility likely.
Result: 0/20000 passed.

## Root cause
Same v2(ord) is NECESSARY but not SUFFICIENT for the "-1" compatibility. For
n = pq to satisfy 2^{d*2^r} ≡ -1 mod p and mod q (same r), you additionally
need oddpart(ord_p(2)) | d and oddpart(ord_q(2)) | d where d = (n-1)/2^s.
For random pairs the odd parts are ~p/2^{r+1} (huge) while d is unrelated to
them, so P(oddpart | d) ≈ 0. I sampled 20,000 pairs before deriving the full
exact condition. The experiment didn't fail statistically; it was doomed
arithmetically, and 20 million samples would have done no better.

## Failure signature
Name: bucket-matched-but-divisibility-ignored. If you are sampling pairs by a
NECESSARY condition (same v2 of orders) without enforcing the SUFFICIENT
divisibility (odd order-parts divide d), stop: the hit rate is ~0 by
arithmetic, not by bad luck, and more samples teach nothing. Derive the exact
compatibility first, then sample (or construct).

## Blocking constraint
The constraint is the divisibility oddpart(ord_p(2)) | (pq-1)/2^s. For random
p, q this is a coincidence of probability ~0, independent of sample size.
No amount of sampling fixes it; only construction (choosing q to satisfy the
divisibility) does.

## What retrieval would have changed
A dossier with this signature would have killed the 20k-sample experiment
before it ran and sent me straight to deriving the exact order-compatibility,
which produced construction S(r,p) — the correct (if bottlenecked) approach.

## Confidence
High. The 0/20000 is fully explained by the divisibility analysis, which was
then validated by the construction's proof check (0 failures). Not mysterious.
