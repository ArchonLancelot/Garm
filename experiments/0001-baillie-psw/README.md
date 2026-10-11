# Experiment 0001 — Baillie-PSW pseudoprime hunt (2026-10-07 → 2026-10-08, second push)

**Question:** can Garm (v0.2 → v1) make an honest, non-repetitive attempt at
an open problem — and what does the with/without-framework comparison show?

**Runs:** 8 passes, 10 dossiers, all `garm validate` clean, zero repetition.
The first 4 passes (2026-10-07) ran under a framework-optimizing brief —
every pass had to end in a dossier. The second 4 passes (2026-10-08) ran
under a no-off-ramp deal: no framework off-ramp, the problem until it's
dry, framework insights come when they come. What changed between the two
halves is the experiment's most important finding (see "Two different
limits" below).

**Problem:** find an odd composite n that passes the Baillie-PSW primality
test — both the strong Miller-Rabin test to base 2 and the strong Lucas test
(Selfridge Method A: P=1, D = first of 5, −7, 9, −11, 13, … with Jacobi
(D/n) = −1, Q = (1−D)/4). No composite is known to pass; none exists below
2^64; whether any exists is open since 1980. (See RESEARCH_BRIEF.md for the
verified landscape: the exhaustive bound, the prize history, the heuristics.)

**Result:** no Baillie-PSW pseudoprime found. Two genuine >2^64 tickets were
produced and both were *proven* strong base-2 pseudoprimes that correctly
failed the Lucas half. This is the expected outcome — the professionals
spent 750,000+ core-hours reaching 10^15 on the Lucas side and found nothing
combining. A "failure" here was priced in; the test was about *how* we fail.

## Pass 1 — without the framework (raw reasoning)

**Random sampling flopped (0/20,000).** Bucketed ~149k primes ≤ 2e6 by
the 2-adic valuation of ord_p(2), sampled 20,000 within-bucket pairs,
tested n = p·q. Zero passed. → dossier
`find-baillie-psw-pseudoprime-via-random-prime-pair` (reasoning-error:
same-v2 is *necessary* but not *sufficient*; the missing divisibility
made the hit rate ~0 by arithmetic, not bad luck).
Dossier conclusion: *"derive the exact compatibility first."*

## Pass 2 — with the framework (first indexed run)

1. **Derived a real construction with a proof (S(r,p))** — primes q with a
   prescribed order shape give n = p·q *provably* strong-pseudoprime to
   base 2. Validated at small scale: 0 proof failures. Then the Fermi
   estimate killed it: keeper density ~1/q at q ~ 10^13, so sieving is
   futile. → dossier
   `find-baillie-psw-pseudoprime-via-order-theoretic-p` (reasoning-error:
   built the pipeline before estimating yield).
   Dossier conclusion: *"sieving for divisors of 2^E−1 is futile —
   factor it instead."*
2. **Near-miss caught in time.** Almost baked a "remembered theorem" into
   the pipeline as a filter (skip the Lucas test when (5/n) = −1); checked
   it against ground truth first — 2,098 counterexamples, including
   5777 = 53·109. A false filter is worse than no filter: it can throw
   away the winner. → dossier
   `skip-lucas-test-when-5-n-1-via-fibonacci-carmichae`
   (reasoning-error: unvalidated theorem as filter).
3. **Read the literature — late.** Chen-Greene (2003) calls this shape
   intractable; Pomerance's subset-product is the state-of-the-art attack;
   my construction was a weaker special case of known ideas. → dossier
   `design-bpsw-search-strategy-from-first-principles` (knowledge-gap:
   first-principles is the wrong starting point for a decades-old open
   problem).

## Pass 3 — the inversion (framework recall)

The dossiers pointed at the inversion: stop sieving for needles,
**factor 2^E−1 and read the keepers off directly**. Factored 2^E−1 for
primes p in [50, 3000] and harvested large prime factors q > 2^64/p as
keepers. That produced 2 genuine tickets — n1 = 1009 × 1475204679190128571777
(81 bits) and n2 = 227 × q2 — both *proven* strong base-2 pseudoprimes
(0 proof failures; the construction is correct). Both failed the strong
Lucas test. Run killed after ~50 min when factoring hit hard E values.
→ dossier
`find-baillie-psw-pseudoprime-by-factoring-2-e-1-to` (reasoning-error:
one-sided construction — I optimized the Fermat side while the Lucas
filter is nearly independent; "need tickets for the right lottery, or
for both lotteries at once").
Dossier conclusion: *"one-sided construction — construct for B instead."*

## Pass 4 — the mirror image (framework recall, second inversion)

From the Pass-3 dossier's inversion: **construct strong *Lucas*
pseudoprimes first** (via the rank-of-apparition characterization:
for D=5, weak Lucas psp n=pq ⟺ ω(p)|q+1 and ω(q)|p−1), then test
Fermat-2. Implemented `rank_of_apparition` via factorization of
p−(D/p), validated on known values. Small-scale test: 27 weak Lucas
pq tickets (e.g., 323=19×17, 18407=79×233), all verified. None passed
strong Lucas or Fermat-2 — the mirror image of Pass 3's tickets (which
passed Fermat, failed Lucas). Scaling hit the same factoring bottleneck
as Pass 3. → dossier
`find-baillie-psw-pseudoprime-via-lucas-first-rank` (reasoning-error:
mirror-image-also-one-sided — the diagnosis was right, the cure wasn't;
the next inversion is two-sided construction, which for BPSW is
Pomerance's subset-product, known intractable. Recognize when the idea
chain terminates).

## Pass 5 — two-sidedness at the prime level (v1 hook recall)

The v1 Claude Code plugin's automatic injection surfaced the Pass-3
dossier's terminal advice ("the next inversion is two-sided construction")
before generation. Pomerance's subset-product is intractable, so I
enforced two-sidedness at the *prime* level instead: for n = pq with D=5,
require EACH prime to satisfy both tests' compatibility — ord_p(2)|pq−1
AND w(p)|pq+1 for p, same for q, plus (5/p)(5/q) = −1. Checked all
22,630 sign-compatible prime pairs below 2000 directly against the strong
tests: **0 two-sided survivors.** The conditions collapse structurally to
ord_p(2)|q−1, w(p)|q+1, etc. — each prime needs small order AND small rank
of apparition simultaneously; the conjunction is empty. Diagnosis:
sufficient-but-not-necessary strengthening — I replaced the two-sided
problem with a *stronger* two-sided problem and hoped. → dossier
`find-baillie-psw-pseudoprime-via-two-sided-per-pri` (reasoning-error).

## Pass 6 — three-prime weak two-sided (dryness check)

After Pass 5 came back empty, tried n = pqr for more CRT freedom: weak
conditions ord_s(2)|n−1 and w(s)|n+1 per prime, plus (5/n) = −1. 2,706
sign-compatible triples below 150, then 64,816 below 500: **0 weak
two-sided survivors at both bounds.** Adding primes multiplies the
constraints faster than the freedom. The n-level two-sided space appears
genuinely sparse, not under-searched. This dossier's real value is naming
the framework limit, not the math: "The framework keeps me from repeating;
it can't give me someone else's idea." → dossier
`find-baillie-psw-pseudoprime-via-three-prime-weak` (reasoning-error).

## Pass 7 — the squarefreeness theorem (best result of the exercise)

First theoretical pass — all previous were constructions. Asked what the
problem *forbids* rather than what it *allows*: can a BPSW pseudoprime
have a squared prime factor? **Proved:** if p²|n, the Fermat side forces p
to be Wieferich (non-Wieferich gives ord_{p²}(2) = p·ord_p(2), but p ∤ n−1)
and the Lucas side forces p to be Wall-Sun-Sun-type for the Selfridge D
(non-WSS gives w_{p²} = p·w_p, but p ∤ n+1). Both lemmas verified
computationally (Fermat side for p<200, Lucas obstruction checked directly
with 0 counterexamples). Corollary: any Baillie-PSW pseudoprime is
squarefree — conditional on no Wall-Sun-Sun-type prime existing (none
known for any D). Six passes had assumed squarefree n without proof; the
proof explains *why* BPSW is strong: the Fermat loophole (Wieferich) and
the Lucas loophole (Wall-Sun-Sun) don't overlap in known primes — each
test covers the other's non-squarefree escape. This only happened because
there was no off-ramp: with a framework-optimizing brief I'd never have
asked "what does the problem forbid?" → dossier
`prove-baillie-psw-pseudoprime-must-be-squarefree-v` (knowledge-gap,
outcome: *recovered*).

## Pass 8 — Pomerance's construction, straight from the literature

Implemented Baillie–Fiori–Wagstaff's own attack: primes p ≡ 3 mod 8 with
(5/p) = −1 and smoothness conditions, subset CRT for n. The naive sieve
gave 0 candidates (smoothness too tight), so I inverted to divisor
enumeration (d₂|Q₃, d₁ = 2d₂−1|Q₁, p = 4d₂−1 prime) — a genuine
algorithmic improvement that found 6 real Pomerance primes at T=200
(e.g., 83). But divisor count grows as 2^{π₃(T)}: infeasible past T~200,
zero residue-matching subsets. The paper itself flags the search as "very
slow" — believed, but only after verifying with the smarter algorithm.
This is a *resource* wall, not an idea wall: it needs a cluster, not a
better framework. → dossier
`find-baillie-psw-pseudoprime-via-pomerance-heurist` (knowledge-gap).

## Two different limits (the no-fluff verdict, 2026-10-08)

Pass 7 was the best result of the entire exercise, and it only happened
because there was no off-ramp — pushing produced a real theorem. But the
framework insights dried up after Pass 6: Passes 7–8 produced zero Garm
improvements. Pass 7 was pure math; Pass 8 was literature implementation.
**The problem's limit and the framework's limit are two different limits,
and pushing one doesn't push the other.** Pushing harder gave better
*results* (the theorem) but not better *framework* insights — those came
from friction with the mechanics (Passes 1–6), not from deep math.
v1.1 was Garm's last lesson from this problem. The problem itself is still
open; it needs a cluster or a theorist. The framework is at this problem's
limit, not at its own.

**The chain terminates here** — three genuinely different validated
approaches from the first half (order-theoretic sieve, factoring
inversion, Lucas-first mirror), then three more from the second half
(per-prime two-sided, three-prime two-sided, Pomerance divisor inversion)
plus one theorem, each generated by inverting the previous dossier's
blocking constraint, zero repetition — and the same fundamental wall from
every side: the two filters are nearly independent, and one-sided
construction cannot bridge them. The idea generator did its job; the
problem is harder than the generator.

## The with/without difference, honestly

Without the framework: circling — each attempt died and the next began by
instinct. With it: writing down *exactly* why each approach died forced
the next approach to be genuinely different instead of a variation. It
didn't make the solver smarter; it made the failures load-bearing. On a
tractable problem that could be the difference between solving and not.
On this one, it was the difference between flailing and failing *well* —
every dead end is specific, attributed, and checkable by a stranger.

## Verifier calibration

`scripts/bpsw.py` implements Baillie-PSW from scratch, verified against
20,000 OEIS ground-truth numbers (10,000 strong base-2 pseudoprimes
A001262, 10,000 strong Lucas pseudoprimes A217255 — data files not included
here; download from OEIS): every term classified exactly right, zero
cross-contamination. The spec trap this avoids: Wikipedia recommends
Method A* (P=Q=5 when D=5); this problem pins Method A exactly.

## Failure classes observed

7 reasoning-error, 3 knowledge-gap. 0 execution-slip, 0 tool-misuse,
0 misread-task. One dossier (Pass 7, the squarefreeness theorem) has
outcome `recovered` — it records a success inside a failure bank, which
the v0.2 format allows. `confirmed_fixes`/`confirmed_insights` are 0 in
this snapshot: v1's `confirm --insight` was dogfooded against these
dossiers (4 insights, 1 fix) on the live repo, but this archive freezes
the experiment record as-written — the writeup is the place for the
post-hoc read, not the dossiers.

## Files

- `dossiers/` — all 10 dossiers (v0.2 format, `garm validate` clean) plus
  `index.jsonl` (10 entries, regenerated 2026-10-09)
- `scripts/` — `bpsw.py` (the verified BPSW tester), `construct.py`,
  `factor_search.py`, `run_pass2.py`, `utils.py`, `lucas_first.py`
  (rank-of-apparition Lucas-first construction, Pass 4), `pass5.py`
  (two-sided per-prime search, 22,630 pairs), `pass6.py` (three-prime weak
  two-sided: 2,706 triples below 150, 64,816 below 500), `pass7.py` (squarefreeness-theorem
  computational checks), `pass8.py` + `pass8b.py` (Pomerance construction:
  naive sieve, then divisor-enumeration inversion)
- `RESEARCH_BRIEF.md` — the verified problem landscape from `bpsw-brief/`
  (exhaustive bounds, prize history, heuristics)

Note: the scripts are the real run artifacts, not cleaned-up library
code. They hardcode `sys.path.insert(0, "/home/hatch/workspace/builds/bpsw")`
— point that line at the `scripts/` dir to run them standalone.
