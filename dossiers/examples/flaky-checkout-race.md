---
dossier_version: "0.1"
id: 2026-10-07-flaky-checkout-race
created: 2026-10-07
agent: claude-code
task: "Fix flaky test_checkout_total in the storefront test suite"
outcome: failed
---

# Failure dossier: Fix flaky test_checkout_total in the storefront test suite

> **Illustrative example** — synthetic, written to demonstrate the v0.1 format.
> Not a real session. Numbers below are plausible estimates, not measurements.

## What was tried

- Ran the failing test in isolation 5 times: passed 3, failed 2.
- Re-ran the full suite twice: failed both times, on a different assertion each time.
- Added a retry wrapper around the test (3 attempts): still flaky.
- Increased the per-test timeout from 5s to 30s: no change.
- Bisected recent commits touching checkout code: no single culprit found; gave up.

## Root cause

The test shares a single in-memory cart fixture across parallel test workers.
Two tests mutate the same cart object concurrently, and whichever assertion
runs second sees the other test's totals. The flakiness is a race condition
in the test harness, not in the checkout code — no amount of re-running,
retrying, or lengthening timeouts can fix it. The fix is to scope the fixture
per worker (or serialize access), i.e. a test-infrastructure change, not a
product-code change.

## Failure signature

**Name:** `flaky-test-chased-as-code-bug`

**Match rule:** a test fails intermittently (passes sometimes in isolation),
and the first several attempts all re-run or retry the test without inspecting
shared fixtures or the runner's parallelism settings — stop re-running. The
harness is suspect, not the code under test.

## Blocking constraint

The runner executes tests across 4 parallel workers (`-n 4`) while the cart
fixture is module-scoped and mutable. The agent never inspected the fixture
scope in `conftest.py` or noticed the `-n` flag; every attempt treated the
failure as a product-code bug.

## What retrieval would have changed

A fresh session reading this dossier first would skip the entire re-run /
retry / bisect loop and go straight to the fixture definition and runner
configuration. First divergence point: attempt 1 — instead of re-running the
test, inspect `conftest.py` fixture scope and check for parallelism flags.

## Tokens

~18,000 content tokens across the re-run loop (illustrative estimate; method:
counted assistant turns spent re-running the test without new information).

## Confidence

High on the mechanism — shared mutable fixture plus parallel workers is a
classic race pattern. Medium on the token estimate, which is illustrative.
