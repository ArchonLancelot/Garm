# Dossier format spec — v0.1

A **dossier** is one hand-written failure autopsy: a Markdown file with a
small frontmatter block and fixed `##` sections. The analysis inside is
written by the agent (or human) using the tool. The tool only enforces
*structure* — it cannot check whether the analysis is true.

## File layout

```markdown
---
dossier_version: "0.1"
id: 2026-10-07-flaky-checkout-race
created: 2026-10-07
agent: claude-code
task: "Fix flaky test_checkout_total in the storefront test suite"
outcome: failed
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
| `dossier_version` | yes | `"0.1"` exactly |
| `id` | yes | slug: `[a-z0-9][a-z0-9-]*`, unique within the directory |
| `created` | yes | ISO date `YYYY-MM-DD` |
| `agent` | yes | free text, e.g. `claude-code` |
| `task` | yes | one-line description of the failed task |
| `outcome` | yes | `failed` or `recovered` |

`outcome: recovered` is for sessions that hit the wall and got past it — the
autopsy is still worth keeping.

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

Validation (`autopsy validate`) checks exactly the table and list above —
nothing more. A dossier that passes validation is *structurally* sound; the
truth of its analysis is the author's responsibility.

## index.jsonl

Derived file, rebuilt any time with `autopsy index --dir <dir>`. One JSON
object per line, sorted by `id`:

```json
{"id": "20261007-flaky-checkout-race", "task": "Fix flaky test_checkout_total in the storefront test suite", "signature": "Name: flaky-test-chased-as-code-bug", "keywords": ["fix", "flaky", "test", "checkout", "total", "storefront", "suite", "name", "chased", "code", "bug", "match", "rule", "..."], "outcome": "failed", "path": "examples/flaky-checkout-race.md", "created": "2026-10-07"}
```
(real output from `autopsy index`; `"..."` abbreviates the full keyword list)

Fields:

| Field | Meaning |
|---|---|
| `id` | dossier id |
| `task` | task one-liner, copied from frontmatter |
| `signature` | first non-empty line of the Failure signature section (≤140 chars) |
| `keywords` | lexical keywords from task + signature text (stopwords removed) |
| `outcome` | `failed` or `recovered` |
| `path` | dossier path relative to the indexed directory |
| `created` | ISO date from frontmatter |

Because it is fully derived, `index.jsonl` can be deleted and rebuilt without
losing anything. Rebuilding is byte-identical for unchanged input.

## Retrieval ranking (v0.1)

`autopsy recall` scores each dossier by **keyword overlap**: the number of
query keywords (from `--task`) also present in the dossier's keyword list
(built from its task + failure signature). Ties break by dossier id.

This is lexical, not semantic. It finds dossiers that *talk about the same
things*. It does not understand meaning, and it will miss paraphrases. That
is an honest v0.1 limitation — semantic retrieval is on the roadmap, not in
the tool.
