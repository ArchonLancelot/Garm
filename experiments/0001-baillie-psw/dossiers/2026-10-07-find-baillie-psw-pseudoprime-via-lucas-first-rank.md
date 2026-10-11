---
dossier_version: "0.2"
id: 2026-10-07-find-baillie-psw-pseudoprime-via-lucas-first-rank
created: 2026-10-07
agent: hsin
task: "Find Baillie-PSW pseudoprime via Lucas-first rank-of-apparition construction"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
---

# Failure dossier: Find Baillie-PSW pseudoprime via Lucas-first rank-of-apparition construction

## What was tried
Mirror image of Pass 2, generated directly from the one-sided-construction
dossier's inversion ("construct for B instead"). For D=5 (Fibonacci),
n=pq with (5/p)=+1, (5/q)=-1: derived that weak Lucas psp ⟺ ω(p)|q+1 and
ω(q)|p-1 (rank of apparition). Implemented rank_of_apparition via
factorization of p-(D/p), validated on known values. Small-scale test:
found 27 weak Lucas pq tickets (e.g., 323=19×17, 18407=79×233), all
verified. None passed strong Lucas or Fermat-2 — mirror image of Pass 2's
tickets (which passed Fermat, failed Lucas). Attempted to scale via
factoring Fibonacci numbers F_d for q's >2^64/p; hit the same factoring
bottleneck as Pass 2.

## Root cause
Symmetric one-sidedness. Pass 2 constructed Fermat tickets hoping for
Lucas; Pass 3 constructs Lucas tickets hoping for Fermat. Both work as
one-sided generators, both fail the other side. The mirror image was the
correct next idea (it completed the exploration of one-sided strategies),
but it confirms the diagnosis rather than curing it: the two conditions
are nearly independent, and one-sided construction cannot bridge them.

## Failure signature
Name: mirror-image-also-one-sided. If the dossier says "construct for B
instead" and you do, and B-tickets fail A just as A-tickets failed B,
the problem isn't which side you construct for — it's the one-sidedness
itself. The next inversion is two-sided construction (satisfy both
simultaneously), which for BPSW is Pomerance's subset-product —
known intractable (Chen-Greene). Recognize when the idea chain terminates.

## Blocking constraint
Two nearly-independent strong filters. One-sided construction (either
side) yields candidates that pass one filter and fail the other with
probability ~1. Two-sided construction is the only principled next step,
and it's intractable with known methods. The idea generator has done its
job — it produced three genuinely different approaches — but the problem
is harder than the generator.

## What retrieval would have changed
Nothing further — this IS what retrieval produced. The dossier chain
(Pass 1 → Pass 2 → Pass 3) demonstrates the framework's idea generation
working correctly: each blocking constraint inverted into a novel
approach. The chain terminates here not because the framework failed,
but because the problem's difficulty exceeds what any single-agent
idea chain can bridge.

## Confidence
High. Three genuinely different constructions, all validated, all hitting
the same fundamental wall from different sides. The framework generated
the ideas; the problem resisted them. That's the honest result.
