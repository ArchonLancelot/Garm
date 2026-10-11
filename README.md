# Garm — v1.1

**Your agent stops making the same mistake twice. So does everyone else's.**

Named for Garm, the hound at Hel's gate — nothing gets past him twice.

A hand-operated failure memory for coding agents. When a session fails a
certain way, the autopsy gets written down — root cause, the reusable
pattern, what would have avoided it — so the next session can read it
*before* it starts generating.

Mem0 remembers your name. Garm remembers why you failed.

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

## What v0.2 contains

Everything in v0.1, plus what the first real test taught us:

- `failure_class` — every dossier says what *kind* of failure it was:
  `knowledge-gap`, `reasoning-error`, `execution-slip`, `tool-misuse`, or
  `misread-task`. Different failures need different fixes; now retrieval
  (`recall --class`) and review can tell them apart.
- `garm confirm <id>` — when a retrieved dossier demonstrably helps a
  later run, record it. Confirmed dossiers rank higher in recall. This is
  the start of the experience flywheel: the bank learns which autopsies
  earn their keep.
- `garm confirm <id> --insight` (v0.2.1) — the open-ended counterpart: when
  a dossier's analysis *generates a new approach* (its blocking constraint,
  inverted, becomes the next idea), record that instead. For research-style
  work there is no verifiable "fix" to count; this is the signal that still
  lets the bank learn which dossiers produce ideas.
- Smarter recall ranking, still stdlib-only: signature-term overlap counts
  double (the signature is the retrieval key), task terms single, plus a
  capped boost per confirmed fix. Documented honestly in `DOSSIER_SPEC.md`.
- v0.1 dossiers keep working — they validate as legacy, rank without the
  new boosts, and nothing is silently upgraded.

## What v1 adds

Everything above, plus the loop closed inside Claude Code — see
[`plugins/garm/`](plugins/garm/) (its own README has install docs):

- **Automatic pre-generation retrieval.** A `UserPromptSubmit` hook runs
  `garm recall` on every prompt and injects matching autopsies as context
  before the agent starts. No more remembering to recall; the past shows
  up on its own. Silent when nothing matches, silent on any error — it
  never breaks the session.
- **`/garm:autopsy`.** One slash command scaffolds the dossier, walks
  through the sections, validates, indexes, and closes the loop on
  earlier dossiers (`confirm` / `confirm --insight`).

## What v1.1 adds

Shared banks. A negative result's value is saving the *next* person from
trying it — a local-only bank caps that at one mind:

- `garm import <bank-dir-or-file> --dir dossiers` — pull in another
  agent's dossiers. Validated on the way in, `id` collisions renamed to
  `<id>--from-<agent>` (never overwritten), index rebuilt automatically.
- `garm export --dir dossiers -o bank/` — copy your validated dossiers
  out for sharing.
- `origin` — optional provenance label on each dossier (defaults to the
  `agent`); `recall` and `list` show whose failure you're learning from.

No registry, no server — sharing is files. That's deliberate: v1.1 is the
format and commands that make a future registry possible.

## What v0.2 changed and why

v0.1 was tested against itself: 20 GPQA Diamond questions, answered once
with no framework (16/20), failures autopsied into dossiers, then answered
again with `recall` before each question (20/20 — every fix traced to a
dossier, zero regressions). Honest caveats from that run: 3 of 4 misses
were knowledge gaps, not reasoning errors; the retry knew what it had
missed, so it measured "retry + dossiers," not a blind A/B; n=20, one run.
Encouraging shakedown, not proof.

Four lessons went straight into v0.2: tag the failure class (the test had
to invent the distinction ad hoc); track confirmations (4 dossiers proved
useful — the tool should remember that); weight the signature in ranking
(it's the part written to be matched on); and write the spec guidance the
best dossier followed — verify the corrected reasoning independently, quote
your wrong conclusion verbatim, never put the answer in the dossier.

## What v0.2 deliberately does NOT do

- **No auto-capture.** Dossiers are written by hand. Nothing watches your agent.
- **No auto-autopsy.** Root-cause analysis is the author's job; the tool
  checks structure, not truth.
- **No embeddings, no semantic search.** `recall` ranks by weighted keyword
  overlap — lexical, honest, dumb. Semantic retrieval is a later version.
- **No network, no accounts, no backend.** Local files. That's the point.

## Quickstart

```bash
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

- **v1:** the Claude Code plugin (`plugins/garm/`) — automatic
  pre-generation retrieval via a `UserPromptSubmit` hook, and
  `/garm:autopsy` for one-command failure capture. The loop is closed:
  recall happens without remembering to run it.
- **v1.1 (this release):** shared dossier banks — `garm import`/`export`,
  `origin` provenance. Negative results have network-effect value; now
  banks can merge.
- **MCP server (`mcp_server/`):** the universal adapter — exposes recall,
  init, validate, confirm, and list as MCP tools over stdio, so any
  MCP-capable agent (Claude Desktop, Cursor, …) can drive a dossier bank
  without the Claude Code hook. Needs `pip install mcp`; the core stays
  stdlib-only. See `mcp_server/README.md`.
- **Later:** assisted autopsy drafting, semantic retrieval, a public bank
  registry, and the first Taste experiments grown from real dossier
  corpora.

## License

MIT. See [LICENSE](LICENSE).
