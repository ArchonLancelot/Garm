---
dossier_version: "0.2"
id: 2026-10-08-prove-baillie-psw-pseudoprime-must-be-squarefree-v
created: 2026-10-08
agent: claude-code
task: "Prove Baillie-PSW pseudoprime must be squarefree via Wieferich/Wall-Sun-Sun"
outcome: recovered
failure_class: knowledge-gap
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Prove Baillie-PSW pseudoprime must be squarefree via Wieferich/Wall-Sun-Sun

## What was tried
Pass 7 — first theoretical pass (all previous were constructions/searches).
Asked what the problem *forbids* rather than what it *allows*: can a BPSW
pseudoprime have a squared prime factor? Proved: if p^2 | n, then the
Fermat side forces p Wieferich (ord_{p^2}(2) = p*ord_p(2) for non-Wieferich,
but p does not divide n-1), and the Lucas side forces p Wall-Sun-Sun-type
for the Selfridge D (w_{p^2} = p*w_p for non-WSS-type, but p does not
divide n+1). Both lemmas verified computationally (p<200, p<100); the Lucas
obstruction checked directly with 0 counterexamples. Corollary: no known
prime satisfies both, so any BPSW pseudoprime is squarefree (conditional
on no Wall-Sun-Sun-type prime existing — none known for any D).

## Root cause
(N/A — this pass succeeded as a theorem; the "failure" is that it
eliminates rather than constructs.) The knowledge gap was real: six
passes assumed squarefree n without justification. The justification
turns out to be a clean two-line argument per side, and it reveals
*why* BPSW is strong: the Fermat loophole (Wieferich) and the Lucas
loophole (Wall-Sun-Sun) don't overlap in known primes — each test covers
the other's non-squarefree escape.

## Failure signature
Name: assume-then-prove-later. Six passes ran on "n is squarefree" as an
unexamined assumption (it felt obvious). When the constructive space ran
dry, proving the assumption became the most productive move. The
signature: if you've been assuming a structural fact for N passes without
proof, proving it is a pass in itself — and the proof may explain *why*
the constructions kept failing.

## Blocking constraint
The theorem is conditional (no Wall-Sun-Sun-type prime). If such a prime
existed, p^2 | n would be possible and the whole squarefree restriction
collapses. But finding one would be a major independent discovery. For
search purposes: restrict to squarefree n, permanently.

## What retrieval would have changed
This pass came from the new deal (no framework off-ramp, push the problem).
Retrieval didn't generate it — the *absence* of a next construction did.
A future agent reading this dossier skips all non-squarefree search
immediately and knows why.

## Confidence
High on the proofs (elementary, verified). Medium on novelty — the
argument is simple enough that experts likely know it; derived
independently here. The value is the derivation, not the priority claim.
