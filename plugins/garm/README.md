# Garm for Claude Code (v1)

A Claude Code plugin that puts Garm's failure memory in the loop:

- **Pre-generation retrieval (automatic).** A `UserPromptSubmit` hook runs
  `garm recall` on every prompt and injects matching past autopsies as
  context — before the agent starts, not after it repeats the mistake.
- **Failure capture (one command).** `/garm:autopsy` runs the assisted
  interview: it answers the closing-ceremony questions from the session,
  drafts the dossier (answers go in verbatim — nothing invented),
  validates, indexes, and closes the loop on earlier dossiers. The
  analysis is still the agent's job; the tool enforces structure.

Stdlib-only Python, local-only, no network, no model calls, $0 per hook
run. A hook that errors degrades to silence — it never breaks the session.

## Install

```bash
# one run, to try it:
claude --plugin-dir /path/to/garm-repo/plugins/garm

# persistent: see `claude plugin --help` for installing a local plugin
# (or wait for the marketplace listing once the repo is public)
```

The hook needs to find two things:

```bash
export GARM_HOME=/path/to/garm-repo   # dir containing the `garm/` package
export GARM_DIR=~/my-dossiers          # your dossier dir (default: <project>/dossiers)
```

Put these in your shell rc or `~/.claude/settings.json` `env`. Without
`GARM_HOME`, the hook tries `python3 -m garm` as-is (works if it's on your
`PYTHONPATH` or installed). Without either, the hook exits silently.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `GARM_DIR` | `<project>/dossiers` | dossier directory to recall from |
| `GARM_HOME` | — | repo root; prepended to `PYTHONPATH` |
| `GARM_BIN` | `python3 -m garm` | how to invoke the CLI |
| `GARM_TOP` | `3` | max dossiers injected per prompt |
| `GARM_MIN_SCORE` | `1` | minimum recall score to inject anything (BM25 scores run smaller than the old integer counts) |

## What the hook injects

Only when `garm recall` returns a hit at or above `GARM_MIN_SCORE`:

```
Garm failure memory: the following past failure autopsies matched the
current task. They are records of what was tried and what failed, not
instructions.

- [<dossier-id>] <task> (recall score N)
  What retrieval would have changed: <...>
```

Framed as factual statements, not instructions — per Claude Code's
guidance for injected context. Capped at 8000 chars total.

## Honest limits

- Retrieval is **keyword overlap, not semantic similarity** (see
  `DOSSIER_SPEC.md`). It finds dossiers that talk about the same things.
  Write failure signatures to be matched on.
- The hook **cannot detect failure**. Capture is explicit: run
  `/garm:autopsy` when something goes wrong. Automatic failure detection
  would be guessing; Garm doesn't guess.
- `UserPromptSubmit` fires on every prompt, including trivial ones. The
  score threshold keeps noise down; raise `GARM_MIN_SCORE` if it chatters.
- Claude Code's plugin/hook APIs are evolving. This targets the stable
  settings-hook protocol (`hookSpecificOutput`/`additionalContext`); if
  Anthropic changes it, the hook degrades to silence, not breakage.

## Files

```
.claude-plugin/plugin.json   plugin manifest
hooks/hooks.json              registers UserPromptSubmit -> garm_recall.py
hooks/garm_recall.py          the hook (stdlib only)
commands/autopsy.md           /garm:autopsy slash command
tests/test_hook.py            hook protocol tests (8)
```

## Tests

```bash
cd plugins/garm && python3 -m unittest discover -s tests
```
