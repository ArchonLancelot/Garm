---
dossier_version: "0.2"
id: 2026-10-07-find-baillie-psw-pseudoprime-by-factoring-2-e-1-to
created: 2026-10-07
agent: hsin
task: "Find Baillie-PSW pseudoprime by factoring 2^E-1 to harvest Fermat tickets"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 1
---

# Failure dossier: Find Baillie-PSW pseudoprime by factoring 2^E-1 to harvest Fermat tickets

## What was tried
Inverted the keeper search: instead of sieving intervals for prime divisors
of 2^E-1 (futile, density ~1/q), factored 2^E-1 directly for primes p in
[50, 3000] (E = 2^{r+1}*ODD_p, capped at 800, 40s budget each) and harvested
large prime factors q > 2^64/p as keepers. Found 2 real tickets:
n1 = 1009 × 1475204679190128571777 (81 bits) and n2 = 227 × q2. Both were
PROVEN strong base-2 pseudoprimes (0 proof failures — the construction is
correct). Both failed the strong Lucas test. Run killed after ~50 min when
factoring hit hard E values (Pollard Rho stuck, 35 min CPU on one number).

## Root cause
One-sided construction. The factoring inversion solved the *Fermat* ticket
generation problem completely — I can now produce proven strong base-2
psps > 2^64 on demand. But the Lucas test is an independent, very strong
filter, and P(Lucas pass | Fermat pass) is tiny (0/31.9M below 2^64).
I optimized the wrong side: better Fermat tickets don't improve Lucas
odds. The strategy buys lottery tickets for a lottery I can't win by
buying more of the same tickets.

## Failure signature
Name: one-sided-construction. If you're constructing candidates to pass
Test A and hoping they pass Test B, and A and B are nearly independent
strong filters, stop optimizing A. You'll get perfect A-candidates that
fail B every time. The inversion is: construct for B instead (mirror
image), or construct for A∧B simultaneously. More A-tickets is not the
answer.

## Blocking constraint
The Baillie-PSW test is a conjunction of two nearly-independent conditions.
Any construction that only enforces one side leaves the other to chance,
and chance is ~10^-8 or worse. The constraint isn't "need more tickets" —
it's "need tickets for the right lottery, or for both lotteries at once."

## What retrieval would have changed
A dossier with this signature would have flagged the one-sidedness BEFORE
the 50-minute factoring run and suggested the mirror image immediately:
construct strong *Lucas* pseudoprimes first (via rank of apparition),
then test Fermat-2. Same lottery-ticket logic, other side. If that also
fails, the next inversion is two-sided construction (Pomerance-style).

## Confidence
High. The 2 tickets prove the Fermat side works; their Lucas failures
prove the one-sidedness is the problem, not the ticket quality. The
mirror-image strategy is the direct logical inversion.
