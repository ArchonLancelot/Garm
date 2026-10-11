---
dossier_version: "0.2"
id: 2026-10-08-find-baillie-psw-pseudoprime-via-two-sided-per-pri
created: 2026-10-08
agent: claude-code
task: "Find Baillie-PSW pseudoprime via two-sided per-prime ord/omega search"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 1
---

# Failure dossier: Find Baillie-PSW pseudoprime via two-sided per-prime ord/omega search

## What was tried
Pass 5, guided by the v1 plugin's automatic injection (the UserPromptSubmit
hook surfaced the factoring dossier's terminal advice: "the next inversion
is two-sided construction"). Pomerance's subset-product is intractable, so
I enforced two-sidedness at the PRIME level instead: for n=pq with D=5,
require EACH prime to satisfy both tests' compatibility — ord_p(2)|pq-1
AND w(p)|pq+1 for p, same for q, plus (5/p)(5/q)=-1. Checked all 22,630
sign-compatible prime pairs below 2000 directly against the strong tests.
Result: 0 two-sided survivors. Not a single pair passed even the weak
per-prime conditions.

## Root cause
Per-prime two-sidedness is nearly unsatisfiable, structurally — not just
at this bound. The conditions simplify to ord_p(2)|q-1, ord_q(2)|p-1,
w(p)|q+1, w(q)|p-1 (given the sign split). So q must simultaneously have
small multiplicative order (q | 2^d-1 for small d) AND small rank of
apparition (q | F_d for small d) AND sit in specific residue classes.
Each condition alone is thin; the conjunction is empty at this scale and
structurally thin in general. I strengthened the requirement past what the
problem needs: weak pseudoprimality only needs the divisibilities at the
n level, and my per-prime version, while sufficient, is far from necessary.

## Failure signature
Name: sufficient-but-not-necessary-strengthening. If you can't solve the
two-sided problem, don't replace it with a stronger two-sided problem and
hope. Check whether your "tractable version" preserved the solution set —
here it collapsed it to empty. The signature: 0 survivors with a clean
structural explanation (not a bound artifact) means the strengthening was
too strong, not that the search was too small.

## Blocking constraint
Pomerance-style two-sided construction is intractable, and the obvious
tractable restriction (per-prime two-sidedness) is over-constrained to
emptiness. The remaining space — n-level two-sidedness without per-prime
two-sidedness — has no known constructive characterization. That's the
actual wall: the only known two-sided method is intractable, and the
tractable relaxation kills the solutions.

## What retrieval would have changed
The v1 hook did this automatically — no manual recall. It injected the
factoring dossier (score 9) whose terminal advice pointed at two-sided
construction, plus the two earlier dossiers. A second run with the plugin
gets the same injection for free and skips straight to asking: "is there
a two-sided characterization weaker than Pomerance but stronger than
one-sided?" — which is now the precise open question this pass isolated.

## Confidence
High on the negative result (direct check, structural explanation).
Medium on the "over-strengthened" diagnosis — it rests on the
sufficient-vs-necessary distinction, which is sound logic but the
n-level two-sided search it points to is uncharted.
