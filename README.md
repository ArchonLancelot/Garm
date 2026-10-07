# failure-memory — v0.1

A hand-operated failure memory for coding agents. When a session fails a
certain way, the autopsy gets written down — root cause, the reusable
pattern, what would have avoided it — so the next session can read it
*before* it starts generating.

Mem0 remembers your name. We remember why you failed.

## The three organs

Human-like insight for agents, built as three organs:

1. **Experience** — this repo. Failed approaches are autopsied and remembered;
   nothing verified is ever lost.
2. **Taste** — later. A searchable prior over "what kinds of moves work,"
   grown from accumulated dossiers.
3. **Restructuring** — later. The capacity to step back and re-derive a
   problem's framing.

v0.1 is Organ 1's minimum: the dossier format plus a CLI to write, validate,
index, and retrieve dossiers. Taste and Restructuring are research; this is
the foundation they would be built on.

## What v0.1 contains

- `DOSSIER_SPEC.md` — the format: frontmatter + fixed sections + `index.jsonl`.
- `autopsy/` — Python package (stdlib only). CLI: `init`, `validate`,
  `index`, `recall`, `list`.
- `dossiers/examples/` — one worked example dossier (illustrative, synthetic).
- `tests/` — round-trip, validation, index-idempotence, and help-text tests.

## What v0.1 deliberately does NOT do

- **No auto-capture.** Dossiers are written by hand. Nothing watches your agent.
- **No auto-autopsy.** Root-cause analysis is the author's job; the tool
  checks structure, not truth.
- **No embeddings, no semantic search.** `recall` ranks by keyword overlap —
  lexical, honest, dumb. Semantic retrieval is a later version.
- **No network, no accounts, no backend.** Local files. That's the point.

## Quickstart

```bash
# 1. Scaffold a dossier for a failed task
python3 -m autopsy init --task "Fix flaky checkout test" --agent claude-code -o dossiers

# 2. Fill in the sections, then validate it (the filename includes today's date)
python3 -m autopsy validate dossiers/*-fix-flaky-checkout-test.md

# 3. Rebuild the index
python3 -m autopsy index --dir dossiers

# 4. Retrieve before your next run
python3 -m autopsy recall --task "checkout test fails intermittently" --dir dossiers

# 5. See everything you have
python3 -m autopsy list --dir dossiers

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

- v0.1 is a **skeleton**. The valuable part — good autopsies — is human (or
  agent) judgment. The tool does bookkeeping.
- `recall` finds dossiers that talk about the same things. It does not
  understand your problem. Read what it returns before trusting it.
- Validation checks structure, not truth. A dossier can validate clean and
  still be wrong about the root cause. The `Confidence` section exists for
  exactly this reason — use it.
- The worked example is synthetic and marked as such.

## Roadmap

- **v0.2:** a Claude Code Mod for in-process failure capture — no more
  hand-copying session logs; the Mod sees tool calls and failures directly.
- **Later:** assisted autopsy drafting, semantic retrieval, and the first
  Taste experiments grown from real dossier corpora.

## License

MIT. See [LICENSE](LICENSE).
