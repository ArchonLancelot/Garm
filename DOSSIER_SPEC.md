# Dossier format spec — v0.2 (Garm)

A **dossier** is one hand-written failure autopsy: a Markdown file with a
small frontmatter block and fixed `##` sections. The analysis inside is
written by the agent (or human) using the tool. The tool only enforces
*structure* — it cannot check whether the analysis is true.

v0.2 adds two frontmatter fields: `failure_class` (what *kind* of failure
this was — required) and `confirmed_fixes` (how many later runs a retrieved
dossier demonstrably helped — starts at 0, bumped with `garm confirm`).
v0.1 dossiers remain valid; they are treated as legacy and simply lack the
new fields.

## File layout

```markdown
---
dossier_version: "0.2"
id: 2026-10-07-flaky-checkout-race
created: 2026-10-07
agent: claude-code
task: "Fix flaky test_checkout_total in the storefront test suite"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
---

# Failure dossier: Fix flaky test_checkout_total in the storefront test suite

## What was tried
...

## Root cause
...
```

## Frontmatter fields

| Field | Required | Format |
|---|---|---|
| `dossier_version` | yes | `"0.2"` (v0.1 also accepted as legacy — see below) |
| `id` | yes | slug: `[a-z0-9][a-z0-9-]*`, unique within the directory |
| `created` | yes | ISO date `YYYY-MM-DD` |
| `agent` | yes | free text, e.g. `claude-code` |
| `task` | yes | one-line description of the failed task |
| `outcome` | yes | `failed` or `recovered` |
| `failure_class` | yes for v0.2 | one of the five classes below |
| `confirmed_fixes` | no | non-negative integer, default 0 |

`outcome: recovered` is for sessions that hit the wall and got past it — the
autopsy is still worth keeping.

## Failure classes

Pick the closest one. Different classes fail differently and get fixed
differently, so retrieval (`recall --class`) and review can treat them
differently:

| Class | Meaning |
|---|---|
| `knowledge-gap` | the agent lacked a fact it needed (a formula, an API behavior, a domain rule) |
| `reasoning-error` | the facts were there; the reasoning step went wrong |
| `execution-slip` | knew better; fumbled the execution (typo, wrong command, misclick) |
| `tool-misuse` | wrong tool for the job, or a tool used wrongly |
| `misread-task` | solved the wrong problem / misread the requirements |

When torn between `knowledge-gap` and `reasoning-error`, ask: would handing
the agent a textbook page have fixed it? Yes → `knowledge-gap`. No, it had
the page and still went wrong → `reasoning-error`.

## confirmed_fixes

Counts the later runs a retrieved dossier demonstrably helped. Written as
`confirmed_fixes: 0` on new dossiers; bumped with:

```bash
python3 -m garm confirm <dossier-id> --dir dossiers
python3 -m garm index --dir dossiers   # refresh the index afterwards
```

Use `confirm` when a retrieved dossier changed what a run did and the run
then succeeded (or avoided the documented failure). Don't confirm on vibes —
the counter is the dossier bank's track record, and `recall` boosts confirmed
dossiers. A dossier with 5 confirmed fixes has earned more trust than one
with 0; the cap keeps one veteran from swamping new dossiers forever.

## Version policy

- v0.2 dossiers: `dossier_version: "0.2"`, `failure_class` required.
- v0.1 dossiers (no `failure_class`): still validate and index. `validate`
  prints a note that they're legacy. In `recall` they rank normally
  (signature weighting is derived, so it applies); they are simply skipped
  when `--class` filters by a class they don't declare. Nothing breaks;
  nothing is silently upgraded.

## Required sections

`##` headers, matched case-insensitively. Each must be present and non-empty.

1. **What was tried** — the attempts, in order. Name approaches, not every turn.
2. **Root cause** — the actual reason it failed, not the surface error.
3. **Failure signature** — the reusable pattern, named like a bug class, plus a
   plain-words match rule: "if you see X in the first few turns, stop and
   retrieve this dossier." This is the retrieval key.
4. **Blocking constraint** — the fact about the repo, environment, or task
   that made the approaches fail. One to three sentences.
5. **What retrieval would have changed** — concretely: which early turn a
   second run would skip, and what it would do instead.
6. **Confidence** — how confident the author is, and what would change their mind.

Optional:

7. **Tokens** — estimated tokens spent repeating failed approaches, with a
   one-line method note. Optional because honest estimates aren't always
   available; never invent one.

Validation (`garm validate`) checks exactly the table and list above —
nothing more. A dossier that passes validation is *structurally* sound; the
truth of its analysis is the author's responsibility.

## index.jsonl

Derived file, rebuilt any time with `garm index --dir <dir>`. One JSON
object per line, sorted by `id`:

```json
{"id": "2026-10-07-flaky-checkout-race", "version": "0.2", "task": "Fix flaky test_checkout_total in the storefront test suite", "signature": "Name: flaky-test-chased-as-code-bug", "keywords": ["fix", "flaky", "test", "checkout", "total", "storefront", "suite", "name", "chased", "code", "bug", "match", "rule", "..."], "sig_keywords": ["name", "flaky", "test", "chased", "code", "bug", "match", "rule", "..."], "failure_class": "reasoning-error", "confirmed_fixes": 2, "outcome": "failed", "path": "examples/flaky-checkout-race.md", "created": "2026-10-07"}
```
(real output from `garm index`; `"..."` abbreviates the full keyword list)

Fields:

| Field | Meaning |
|---|---|
| `id` | dossier id |
| `version` | dossier_version from frontmatter |
| `task` | task one-liner, copied from frontmatter |
| `signature` | first non-empty line of the Failure signature section (≤140 chars) |
| `keywords` | lexical keywords from task + signature text (stopwords removed) |
| `sig_keywords` | lexical keywords from the failure signature alone (the retrieval key) |
| `failure_class` | frontmatter class, or null for legacy v0.1 dossiers |
| `confirmed_fixes` | frontmatter counter (0 if absent) |
| `outcome` | `failed` or `recovered` |
| `path` | dossier path relative to the indexed directory |
| `created` | ISO date from frontmatter |

Because it is fully derived, `index.jsonl` can be deleted and rebuilt without
losing anything. Rebuilding is byte-identical for unchanged input.

## Retrieval ranking (v0.2)

`garm recall` scores each dossier as:

```
score = 2 × (query ∩ sig_keywords) + 1 × (query ∩ task_keywords) + min(confirmed_fixes, 5)
```

Signature terms count double because the failure signature is the retrieval
key — it's the part of the dossier written to be matched on. Task terms
count single. Each confirmed fix adds a point up to a cap of 5, so dossiers
with a track record rank higher without swamping new ones forever. Ties
break by confirmed fixes, then dossier id.

This is still lexical, not semantic. It finds dossiers that *talk about the
same things*, weighted toward the matchable parts and toward dossiers that
have earned trust. It does not understand meaning, and it will miss
paraphrases. That remains an honest limitation — semantic retrieval is on
the roadmap, not in the tool.

## Writing dossiers that earn their keep

Four lessons from the first real test — a 20-question GPQA Diamond self-test
run by the framework's own author (16/20 without recall, 20/20 with it; every
fix traced to a dossier, zero regressions):

1. **Verify the corrected reasoning independently.** The best dossier in the
   test wasn't derived from the answer key — its author re-checked the
   chemistry against external references. A dossier that says "the answer
   was X" teaches nothing; a dossier that re-derives *why* teaches
   everything. Never write the correct option/answer into the dossier to
   "help" — that turns retrieval into answer lookup and the whole loop
   into theater.
2. **Quote your wrong conclusion verbatim in the failure signature.** The
   signature is a match rule for future runs: "if you find yourself
   concluding <exact wrong thing>, stop." Future-you matches on specifics,
   not vibes.
3. **Tag the failure class honestly.** In the test, 3 of 4 misses were
   `knowledge-gap` and 1 was `reasoning-error` — and they needed different
   fixes. A mislabeled dossier retrieves in the wrong context and teaches
   the wrong lesson.
4. **Confirm the ones that work.** When a retrieved dossier changes a run
   for the better, run `garm confirm`. An unconfirmed bank is a pile of
   claims; a confirmed bank is a track record.
