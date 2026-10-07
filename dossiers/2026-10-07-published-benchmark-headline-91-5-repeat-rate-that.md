---
dossier_version: "0.1"
id: 2026-10-07-published-benchmark-headline-91-5-repeat-rate-that
created: 2026-10-07
agent: hsin
task: "Published benchmark headline (91.5% repeat rate) that collapsed under expert review"
outcome: failed
---

# Failure dossier: Published benchmark headline (91.5% repeat rate) that collapsed under expert review

## What was tried
- Ran a subagent to measure token waste from repeated failed tool calls in 400 failed OpenHands trajectories; got 91.5% repeat rate, ~7% billed waste, ~118K tokens/run.
- Reported the headline to Armando in chat and shipped a benchmark writeup draft leading with it.
- A day later, pasted Claude Sonnet 5.5's methodological review into the analysis; re-ran with fixes (baseline on resolved runs, intervening-write exclusion, regex precision check, median+CI).
- Corrected numbers: 9.75% failed vs 5.0% resolved, median waste 0.00%, mean 111 tokens. Withdrew the headline before anything was published.

## Root cause
The metric counted legitimate edit-test loops as waste. Re-reading a file you just edited or re-running a test after a change is normal agent workflow, not "hitting the same wall" — but byte-identical call matching can't tell the difference. I also never measured a baseline (resolved runs repeat almost as much), framed cost estimates as "conservative" when caching made them the opposite, and quoted the most flattering published number (22.75%) instead of the one for our audience (Claude Code: 6.86%). Each choice individually was small; together they manufactured a headline.

## Failure signature
Metric-first analysis: pick a metric that is easy to compute (byte-identical repeats), then let the metric define the phenomenon instead of checking what the metric actually captures. Match rule: if your headline number comes from a proxy metric and you haven't (a) hand-checked 30 samples, (b) measured a baseline, (c) asked "what legitimate behavior does this proxy also count" — stop and do those three before reporting.

## Blocking constraint
No ground-truth labels for "wasted" vs "legitimate" repeats existed in the trajectory data; the proxy was the only scalable signal. The honest move (hand-checking + baseline) was available from the start and just wasn't done first.

## What retrieval would have changed
A second run, retrieving this dossier before designing the analysis, would have started with the three checks (hand-check samples, baseline on resolved runs, legitimate-behavior audit of the proxy) instead of discovering them via external review after the headline was already reported. The corrected numbers would have been the first numbers.

## Tokens
_Optional: estimated tokens spent repeating failed approaches, with a one-line method note._
N/A — analytical failure, not a token-waste failure. (The irony is noted.)

## Confidence
High. The failure is fully documented: v1 numbers, the review, the corrected numbers, and the retraction are all on record. What would change my mind: nothing about the facts; only about whether the pattern generalizes — watching for the next metric-first analysis I catch myself doing.
