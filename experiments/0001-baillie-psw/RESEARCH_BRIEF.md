# Baillie-PSW pseudoprime — research brief

Prepared 2026-10-07 (research stage, for the Garm impossible-problem test).
All claims verified via web search the same day; sources at the bottom.

## The verified bound (exhaustive search is closed below 2^64)

- No composite below 2^64 passes the standard Baillie-PSW test. Separately
  verified by Charles Greathouse (June 2011). [0]
- Baillie–Fiori–Wagstaff (2020, "Strengthening the Baillie-PSW primality
  test", arXiv:2006.14425): of the **118,968,378** base-2 Fermat pseudoprimes
  below 2^64, **none** is a Lucas pseudoprime (or V-pseudoprime). [1,2]
- Implication: a search cannot piggyback on known strong base-2
  pseudoprimes below 2^64 — every one of them fails the Lucas half. Any
  feasible hunt starts at 2^64 and up.

## The prize (real, but small)

- 1980: Pomerance, Selfridge, Wagstaff offered **$30** for a counterexample
  or a proof none exists. Per Pomerance's 1984 note, Selfridge raised his
  $10 share tenfold → **$120** total. [0, 7]
- A Purdue lecture deck claims the reward has since been raised to **$620**
  — single secondary source, treat as unconfirmed. [5]
- Separate **$2000** bounty exists for the *strengthened/enhanced* version
  of the test (Baillie–Fiori–Wagstaff). [0,1]
- A find would still be a publishable result regardless of the money.

## Heuristics and conjectures (why this is genuinely hard)

- Pomerance (1984): heuristic argument that **infinitely many**
  counterexamples exist. [0,7]
- Greg Martin (weak conjecture, via Math::Prime::Util docs): **none under
  10,000 digits**. [5b]
- Combined read: counterexamples probably exist but the first one is
  astronomically large — this is a hunt for *structure*, not a sieve.
  Exhaustive scanning will never reach it.

## Near-misses worth knowing (search strategy fuel)

- **n = 5777** is a strong pseudoprime to base 76 AND a strong Lucas
  pseudoprime. [0] It passes strong-Fermat-plus-strong-Lucas — just with
  the wrong Fermat base. Exactly the near-miss structure to study: what
  makes base 2 special here?
- The 2020 paper found only **five** "V-pseudoprimes" below 10^15 (for the
  enhanced test, Method A*): 913 = 11·83, 150267335403,
  430558874533, 14760229232131, 936916995253453. [1] None of them passes
  the base-2 half, but they are extreme Lucas-side edge cases — good
  verifier test vectors.
- Smallest strong Lucas pseudoprimes (OEIS A217255) start 5459, 5777, ...;
  smallest strong base-2 pseudoprimes (OEIS A001262) start 2047, 3277,
  4033, 4681, ... — use these as verifier calibration: each must pass its
  own half and fail the other.

## Verifier spec trap to avoid

- Wikipedia's standard-test writeup recommends **Method A*** (if D = 5,
  use P = Q = 5 instead of P = 1, Q = −1). [0] **Our problem pins Method A
  exactly**: P = 1, Q = (1 − D)/4. A verifier following Wikipedia's
  recommendation would test the wrong thing. Match the problem spec
  verbatim.

## Honest framing for the dossiers

- Realistic best case was already stated: organized, non-repetitive
  partial progress. The facts above sharpen it — the professionals spent
  750,000+ core-hours to reach 10^15 on the Lucas side and found nothing
  combining. A "failure" here is the expected outcome; the test of Garm
  is whether the dead ends stay dead and stay specific.

## Sources

- [0] https://en.wikipedia.org/wiki/Baillie–PSW_primality_test
- [1] http://arxiv.org/pdf/2006.14425v1 (Baillie, Fiori, Wagstaff 2020)
- [2] https://www.cs.uleth.ca/~fiori/Docs/bfw-accepted.pdf (same paper, accepted version)
- [5] https://www.cs.purdue.edu/homes/ssw/cs655/bigp.pdf (Purdue lecture slides; $620 claim)
- [5b] https://metacpan.org/release/DANAJ/Math-Prime-Util-GMP-0.08/view/lib/Math/Prime/Util/GMP.pm (Martin 10,000-digit conjecture)
- [7] https://pseudoprime.com/dopo.pdf (Pomerance 1984; prize history, exhaustive search to 25·10^9)
