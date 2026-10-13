---
dossier_version: "0.2"
id: 2026-10-12-find-baillie-psw-pseudoprime-via-wieferich-anchore
created: 2026-10-12
agent: hsin
task: "Find Baillie-PSW pseudoprime via Wieferich-anchored non-squarefree search"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Find Baillie-PSW pseudoprime via Wieferich-anchored non-squarefree search

## What was tried
Pass 11 — first v0.2.4-framework pass. Directly inverted the pass-7
(squarefree theorem) blocking constraint "restrict to squarefree n,
permanently": pass 7 proved p^2 | n + strong-Fermat pass ==> p is
Wieferich, so the non-squarefree region the theorem leaves ajar is
exactly n = p^2 * m for the two known Wieferich primes 1093, 3511.
Tested n = p^2 * m for odd m in [1, 10^7], both p: 10,000,000 n total,
full Baillie-PSW test each (script: builds/bpsw/pass11.py). Every n is
composite by construction (p^2 | n), so any probable-prime hit would
have been a genuine pseudoprime. Also counted strong-Fermat-only
survivors as a mechanism check. Result: 0 BPSW hits; 18/10,000,000
passed strong Fermat (16 at p=1093, 2 at p=3511).

## Root cause
The anchor opens the region but gives no leverage inside it. The
Wieferich property clears the Fermat obstruction mod p^2, yet only
18 in 10M passed even the Fermat side — the cofactor m's prime factors
are as hard as random composites, and the anchor does nothing for
them. The binding wall is the Lucas side: it needs Wall-Sun-Sun-type
behavior at 1093/3511 for the Selfridge D, and none is known. So this
search could only succeed by simultaneously discovering the first
WSS-type prime behavior — a second open problem hiding inside the
first. The region is allowed by the theorem but not favored by it.

## Failure signature
Name: anchor-without-leverage. A theorem opens a search region by
removing one obstruction (here: non-squarefree n at Wieferich primes),
but the remaining obstructions are unchanged and still binding. The
mechanism check tells you: if the favored-side survivor rate shows no
enrichment (18/10M here — no better than unfavored ground), the region
is permitted, not promising. Distinguish "the theorem allows it" from
"the theorem points at it."

## Blocking constraint
Two unknowns must align: p Wieferich (known: 1093, 3511) AND p
Wall-Sun-Sun-type for the Selfridge D of n (known: none, for any D).
The search tested the only two anchors that exist; a hit required an
independent major discovery on the Lucas side. Bounded at m <= 10^7
per p — the premise survives this negative result.

## Challengeable premises
- "The Lucas side is the binding constraint." What if the mod-p^2
  Fermat condition imposes a congruence on m that focuses the search
  (instead of uniform m)? A focused m-set could beat the 18/10M rate.
- "1093 and 3511 are the only anchors." A third Wieferich prime would
  open a third anchor; none known below ~10^9, but the search bound
  moves.
- "Uniform m is the right sampling." What if m itself should be
  prime (n = p^2*q, minimal non-squarefree shape)? The pass tested
  all odd m, which includes that shape — but a q-prime-only run would
  reach larger q for the same budget.

## What retrieval would have changed
This pass EXISTS because of retrieval: the pass-7 dossier's blocking
constraint ("restrict to squarefree n, permanently") was read, and its
negation became the idea. A run without the bank would have either
skipped non-squarefree n entirely or searched it blindly without the
Wieferich-anchor focusing. The v0.2.4 premise registry then recorded
the new big claim (P-20261012-004) explicitly, so a future kill
propagates.

## Open questions
- Is the strong-Fermat survivor rate at Wieferich anchors (1.8e-6 here)
  actually above the rate for random composites of the same size? A
  baseline run would tell whether the anchor enriches anything at all.
- Does the mod-p^2 strong-Fermat condition cut m to a thin
  congruence class? If yes, the search should target that class, not
  uniform m.
- n = p^2 with m=1 was tested (no hit) — but is there any m for which
  the Lucas side's Selfridge D picks a D where 1093/3511 is
  accidentally WSS-type? That is the precise needle.

## Premises
P-20261012-004
P-20261012-001

## Confidence
High on the negative result (10M direct tests, scripts deterministic).
High that the premise correctly stays open — a bounded search cannot
kill an existence claim. Medium on the "anchor-without-leverage"
diagnosis: the Fermat survivor rate is measured, but the random
baseline for comparison wasn't run.
