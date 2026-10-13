# Garm — v0.2.4

**A failure memory for coding agents — so the next attempt is a new idea, not a repeat.**

Named for Garm, the hound at Hel's gate.

When an agent fails a certain way, the autopsy gets written down — root
cause, the reusable pattern, what would have avoided it — and the next
attempt reads it *before* generating. The point isn't just avoiding
repeats: each autopsy's blocking constraint, inverted, becomes the next
idea. Failure memory that generates insight.

Mem0 remembers your name. Garm remembers why you failed.

*Current release: v0.2.4. Stdlib-only core; MIT.*

## What it does now

- **Dossiers** — structured failure autopsies: what was tried, root cause,
  failure signature, blocking constraint, what retrieval would have
  changed. `garm init` scaffolds one; `garm validate` checks its
  structure; `garm index` makes it retrievable.
- **Recall** — pre-generation retrieval. `garm recall --task "..."` ranks
  past autopsies by weighted keyword overlap (signature terms count
  double — the signature is written to be matched on). Lexical, honest,
  dumb.
- **Confirm** — when a dossier demonstrably helps a later run,
  `garm confirm <id>` records it, and confirmed dossiers rank higher.
  `garm confirm <id> --insight` records the open-ended counterpart: the
  dossier *generated a new approach*. This is the experience flywheel —
  the bank learns which autopsies earn their keep.
- **Premises (big routes)** — register the load-bearing claims whole
  families of approaches assume (`garm premise add --statement "..."`).
  Dossiers declare their premises in `## Premises`. Kill one
  (`garm premise kill <id> --by <dossier> --evidence
  proof|our-tests|outside-work`) and every route under it closes
  transitively; `recall` stops suggesting dead routes (listed separately;
  `--include-dead` audits them). One closed big route closes a thousand
  small routes without running them.
- **Shared banks** — `garm import` / `garm export` merge dossier banks
  between agents (validated on the way in, never overwrites, collisions
  renamed). `origin` tracks whose failure you're learning from. Negative
  results have network-effect value; now banks can merge.
- **Claude Code plugin** (`plugins/garm/`) — a `UserPromptSubmit` hook
  runs `garm recall` automatically before every prompt and injects
  matching autopsies as context. Silent on no-match, silent on error —
  it never breaks the session. `/garm:autopsy` scaffolds, validates,
  and files the dossier in one command.
- **MCP server** (`mcp_server/`) — 8 tools over stdio (recall, init,
  validate, confirm, list, premise add/kill/list), so any MCP-capable
  agent can drive a dossier bank. Needs `pip install mcp`; the core
  stays stdlib-only.

## What it deliberately does NOT do

- **No auto-capture.** Dossiers are written by hand. Nothing watches your agent.
- **No auto-autopsy.** Root-cause analysis is the author's job; the tool
  checks structure, not truth.
- **No embeddings, no semantic search.** `recall` ranks by weighted keyword
  overlap — lexical, honest, dumb. Semantic retrieval is on the roadmap.
- **No network, no accounts, no backend.** Local files. That's the point.

## How Garm differs from short-lesson tools

Scar-family tools store short lessons with auto-surfaced reminders:
what bit you, right where it bit you. Garm stores deep autopsies: why
the whole hunt failed, with the blocking constraint spelled out so its
inversion becomes the next idea. And the premise registry kills entire
families of approaches at once — one dead big route closes a thousand
small routes without running them. Different jobs: scars record the
bite, autopsies explain the failed hunt.

## Where it's going

Human-like insight for agents, built as three organs:

1. **Experience** — this repo, now. Failed approaches are autopsied and
   remembered; nothing verified is ever lost.
2. **Taste** — next. A searchable prior over "what kinds of moves work,"
   grown from accumulated dossier corpora. The confirm/insight signals
   are its training data.
3. **Restructuring** — research. The capacity to step back and re-derive
   a problem's framing.

Also on the roadmap: semantic retrieval, a public bank registry, and
**assisted autopsy drafting** — a closing-ceremony step at session end
that interviews the agent ("what broke? what took too long?") and drafts
the dossier for human review. The judgment stays manual; the blank page
goes away.

## Field-tested, honestly

- **GPQA Diamond (v0.2):** 20 questions, answered once with no framework
  (16/20), failures autopsied, then answered again with `recall` before
  each (20/20 — every fix traced to a dossier). Caveats: 3 of 4 misses
  were knowledge gaps; n=20, one run. Encouraging shakedown, not proof.
- **Baillie–PSW (v0.2 → v0.2.4):** an open 1980 problem attacked across
  12 passes / 12 dossiers — no pseudoprime found, but zero repeated
  approaches, and each dossier's blocking constraint, inverted, became
  the next idea. The v0.2.4 revisit (passes 11–12) ran the bank-to-idea
  pipeline end to end: imported the old bank, declared premises for the
  big claims, and generated both new approaches from prior dossiers.
  Honest gap found: lexical recall missed the most relevant dossier on
  one query — the mechanism works, the retrieval is still dumb.
- **Earth–Moon biplanar coloring (v0.2.4):** 13 genuinely different
  methods, 10 premises killed (including a trunk kill on external
  evidence), 12 dossiers — the premise registry's first field trial.

## Quickstart

A dossier takes a few minutes to write: the scaffold handles the
structure, you supply the judgment. (In Claude Code, `/garm:autopsy`
does it in one command.)

```bash
# 0. (Optional) Start from a field-tested bank instead of an empty one
python3 -m garm import banks/bpsw --dir dossiers   # or banks/earth-moon

# 1. Scaffold a dossier for a failed task (class is required — pick honestly)
python3 -m garm init --task "Fix flaky checkout test" --agent claude-code \
    --class reasoning-error -o dossiers

# 2. Fill in the sections, then validate it (the filename includes today's date)
python3 -m garm validate dossiers/*-fix-flaky-checkout-test.md

# 3. Rebuild the index
python3 -m garm index --dir dossiers

# 4. Retrieve before your next run
python3 -m garm recall --task "checkout test fails intermittently" --dir dossiers

# 5. When a retrieved dossier demonstrably helps a later run, confirm it
python3 -m garm confirm <dossier-id> --dir dossiers
python3 -m garm index --dir dossiers   # refresh after confirming

# 6. See everything you have
python3 -m garm list --dir dossiers

# 7. Close a big route: register what the attempts assumed, kill it when false
python3 -m garm premise add --statement "The API returns JSON" --dir dossiers
python3 -m garm premise kill P-20261012-001 --by <dossier-id> --evidence our-tests --dir dossiers

# Run the test suite
python3 -m unittest discover -s tests -t .
```

## Origin story

In August 2026, an Anthropic staff member asked Claude to take a real stab at
the Riemann hypothesis. Claude generated 650 ideas — every one failed — then
ran ~60 subagents for 36 hours (31M output tokens) and improved a longstanding
lower bound from 41.6% to 67.2%. All 650 dead ideas were thrown away; nothing
was remembered about *why* they failed.

Read it yourself: https://www.anthropic.com/research/riemann-zeta

Caveat, stated plainly: that is a single-source account — Anthropic's own
research note, about an unreleased model, not peer-reviewed. It is the
*motivation* for this project, not evidence for any claim this project makes.

## Honesty and caveats

- The valuable part — good autopsies — is human (or agent) judgment. The
  tool does bookkeeping.
- `recall` finds dossiers that talk about the same things. It does not
  understand your problem. Read what it returns before trusting it.
- Validation checks structure, not truth. A dossier can validate clean and
  still be wrong about the root cause. The `Confidence` section exists for
  exactly this reason — use it.
- The worked example is synthetic and marked as such.

## Spec & tests

- `DOSSIER_SPEC.md` — the dossier format, index fields, and recall
  scoring, documented honestly.
- `QA_CHECKLIST.md` — the per-release verification list. Nothing ships
  untested.

## License

MIT. See [LICENSE](LICENSE).
