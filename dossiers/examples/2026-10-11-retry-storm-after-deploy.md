---
dossier_version: "0.2"
id: 2026-10-11-retry-storm-after-deploy
created: 2026-10-11
agent: claude-code
task: "Stop retry storm that took down the API after a deploy"
outcome: recovered
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
---

# Failure dossier: Stop retry storm that took down the API after a deploy

> **Illustrative example** — synthetic, written to demonstrate the v0.2.3 format.

## What was tried
- Saw 5xx spike right after deploy; assumed the new code was broken and rolled back. Spike continued.
- Added more API replicas. The storm scaled with them — worse, not better.
- Read the client logs: every client retried immediately on 5xx with no backoff. The deploy had only changed an error message, which tripped a strict client-side string match into treating a warning as fatal.

## Root cause
Not the deploy's logic — a client that matched on an exact error string, combined with retry-with-no-backoff on every 5xx. The rollback didn't help because the trigger was the message text, present in both versions once the flag flipped. Each retry added load, which caused more 5xx, which caused more retries.

## Failure signature
Name: rollback-first-reflex. If the first move after a deploy-correlated incident is "roll back" before reading client-side logs, stop — the trigger may be in the contract between services, not in the diff.

## Blocking constraint
The retry policy lived in client config, invisible from the API repo: fixed 0ms backoff, unlimited retries, on any 5xx. No dashboard showed retry volume, only origin 5xx rate.

## Challengeable premises
- "The incident started at deploy time, so the deploy caused it." Correlation, not causation — the deploy only changed a string the client depended on.
- "More capacity fixes overload." True only if demand is exogenous; with retry amplification, capacity feeds the storm.
- "Rollback is the safe first move." Safe for bad diffs; useless (and slow) for contract breaks.

## What retrieval would have changed
Skip the rollback: read client retry logs first (turn 2 instead of turn 20), then ship a one-line client config change (exponential backoff + retry budget) instead of a revert.

## Open questions
- What is the actual retry budget across all clients? Nobody has measured total retry amplification under partial outage.
- Should error-message strings be covered by contract tests? If clients match on them, they are API surface.

## Tokens
not estimated.

## Confidence
High on the mechanism (client logs showed the loop directly). Medium on generality — other incidents may differ.
