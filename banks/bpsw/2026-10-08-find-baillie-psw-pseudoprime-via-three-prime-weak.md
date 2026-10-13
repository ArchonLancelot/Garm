---
dossier_version: "0.2"
id: 2026-10-08-find-baillie-psw-pseudoprime-via-three-prime-weak
created: 2026-10-08
agent: claude-code
task: "Find Baillie-PSW pseudoprime via three-prime weak two-sided search"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Find Baillie-PSW pseudoprime via three-prime weak two-sided search

## What was tried
Pass 6. After Pass 5's per-prime two-sidedness came back empty (0/22,630),
tried n=pqr for more CRT degrees of freedom: weak conditions ord_s(2)|n-1
and w(s)|n+1 for each s in {p,q,r}, plus (5/n)=-1. Checked 2,706
sign-compatible triples below 150, then 64,816 below 500. Result: 0 weak
two-sided survivors at both bounds. The extra prime didn't open the space.

## Root cause
Same structural thinness as Pass 5, not cured by a third prime. Six
simultaneous divisibilities (two per prime) are nearly unsatisfiable
whether the primes are 2 or 3 — the extra CRT freedom is illusory because
each prime still needs small ord AND small omega relative to the product.
Adding primes multiplies the constraints faster than the freedom. The
n-level two-sided space that Pass 5 pointed at appears genuinely sparse,
not just under-searched.

## Failure signature
Name: more-variables-same-wall. If a constraint system is empty for
structural reasons (each variable needs two rare properties), adding
variables doesn't help — it adds constraints. Distinguish "search too
narrow" (widen the bound) from "space is empty" (0 survivors at two
bounds + structural explanation). I checked two bounds; it's the latter.

## Blocking constraint
Two-sided BPSW construction has no known tractable characterization:
Pomerance's method is intractable, per-prime restriction is empty,
three-prime is empty. Six passes, six genuinely different validated
approaches, and the constructive space is exhausted as far as one mind
can see. The next idea, if it exists, probably isn't mine.

## What retrieval would have changed
Nothing — retrieval worked (hook injected the Pass 5 dossier automatically).
The bottleneck is no longer retrieval or capture. It's the idea source:
one agent, one dossier bank, one mind. The framework keeps me from
repeating; it can't give me someone else's idea.

## Confidence
High on the emptiness (two bounds, direct check). High on the diagnosis —
this dossier's real value is naming the framework limit, not the math.
