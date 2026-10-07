# Autopsy — v0.2

**Your agent stops making the same mistake twice.**

A hand-operated failure memory for coding agents. When a session fails a
certain way, the autopsy gets written down — root cause, the reusable
pattern, what would have avoided it — so the next session can read it
*before* it starts generating.

Mem0 remembers your name. Autopsy remembers why you failed.

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
- `autopsy confirm <id>` — when a retrieved dossier demonstrably helps a
  later run, record it. Confirmed dossiers rank higher in recall. This is
  the start of the experience flywheel: the bank learns which autopsies
  earn their keep.
- Smarter recall ranking, still stdlib-only: signature-term overlap counts
  double (the signature is the retrieval key), task terms single, plus a
  capped boost per confirmed fix. Documented honestly in `DOSSIER_SPEC.md`.
- v0.1 dossiers keep working — they validate as legacy, rank without the
  new boosts, and nothing is silently upgraded.

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
python3 -m autopsy init --task "Fix flaky checkout test" --agent claude-code \
    --class reasoning-error -o dossiers

# 2. Fill in the sections, then validate it (the filename includes today's date)
python3 -m autopsy validate dossiers/*-fix-flaky-checkout-test.md

# 3. Rebuild the index
python3 -m autopsy index --dir dossiers

# 4. Retrieve before your next run
python3 -m autopsy recall --task "checkout test fails intermittently" --dir dossiers

# 5. When a retrieved dossier demonstrably helps a later run, confirm it
python3 -m autopsy confirm <dossier-id> --dir dossiers
python3 -m autopsy index --dir dossiers   # refresh after confirming

# 6. See everything you have
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

- **v0.3:** a Claude Code Mod for in-process failure capture — no more
  hand-copying session logs; the Mod sees tool calls and failures directly.
- **Later:** assisted autopsy drafting, semantic retrieval, and the first
  Taste experiments grown from real dossier corpora.

## License

MIT. See [LICENSE](LICENSE).
