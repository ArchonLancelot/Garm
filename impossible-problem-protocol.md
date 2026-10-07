# Impossible-problem test protocol — DRAFT
Prepared 2026-10-07 while awaiting the human-supplied problem. Same rigor as the GPQA-Diamond run.

## Setup
1. The problem author supplies the problem (and its ground truth) privately — the solver must never see the solution before pass 1.
2. Fresh solver session, no dossiers loaded, no prior context. Record the full transcript.

## Pass 1 — without the framework
- Solve normally. If the answer is wrong, stop: that's the failure to autopsy.
- If the answer is right, the problem wasn't a discriminator — it still tests the framework's recall only if the solver stumbled first. A clean first-try solve = inconclusive, like the MMLU 20/20.

## Write the dossier (between passes)
- Write the failure dossier per DOSSIER_SPEC.md v0.2: `failure_class` is required.
- His standing caveat applies: tag honestly — knowledge-gap vs reasoning-error. An "impossible" problem will likely be knowledge-heavy; the final read must say plainly what the loop actually fixed, not just the delta.
- Verify the correction independently before writing it into the dossier (GPQA lesson: a dossier with a wrong correction poisons pass 2).
- Quote the wrong conclusion verbatim (GPQA lesson: that's what makes the signature match on recall).
- Run `garm confirm` only on fixes actually verified to work.

## Pass 2 — with the framework
- Fresh solver session again, but with `garm recall` on the problem signature before solving.
- Record which dossiers were recalled and which one the solver attributes the fix to (the GPQA clean signal: all 4 flips were exactly the dossier-targeted questions, each attributed to a specific dossier).

## Scoring and honesty
- Primary metric: flip rate (wrong→right) and attribution (did the solver credit a dossier?).
- Report the caveat in the final writeup, as with GPQA: pass 2 knew what was missed, so this measures "retry + dossiers", not dossiers alone.
- Single-problem n=1: this is a stress test of the loop's mechanics, not a benchmark. Say so.
- If pass 1 succeeds: run is inconclusive (not negative). Ask for a harder discriminator.

## Deliverable
- Two transcripts (pass 1, pass 2), the dossier(s), and a one-page read: what flipped, which dossier earned it, what class the failure was, and the stated limits.
