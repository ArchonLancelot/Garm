# QA checklist — Garm v0.2

Standing rule: nothing ships untested. Run this whole list before any release
tag or public push. Check each box only after verifying, not before.

## Format and spec

- [ ] `DOSSIER_SPEC.md` matches what the code actually enforces (field names,
      required sections, index.jsonl fields, recall scoring formula — no drift).
- [ ] `dossiers/examples/flaky-checkout-race.md` validates clean and carries
      `dossier_version: "0.2"` with a real `failure_class`.
- [ ] A legacy v0.1 dossier (no `failure_class`) still validates with a
      non-fatal note, indexes, and is recalled.
- [ ] The example is clearly marked illustrative/synthetic.
- [ ] New optional sections `## Challengeable premises` and
      `## Open questions` validate whether present or absent (old dossiers
      unaffected); `init` scaffolds them with guidance; the spec documents
      both and the "earn their keep" lesson behind them.

## CLI

- [ ] `python3 -m garm --help` lists all six commands with accurate
      one-line descriptions.
- [ ] `init` requires `--class` (exits 2 without it) and scaffolds a dossier:
      file created, frontmatter prefilled (version 0.2, id, ISO date, agent,
      task, outcome, failure_class, confirmed_fixes: 0, confirmed_insights: 0).
- [ ] `init` rejects an invalid `--class` with the valid choices listed.
- [ ] `validate` passes a good v0.2 dossier, rejects a bad `failure_class`
      and a negative `confirmed_fixes` / `confirmed_insights`, with clear
      messages; exit codes 0/1.
- [ ] `confirm <id>` increments `confirmed_fixes`, keeps the file valid,
      errors clearly on unknown/duplicate ids; re-running `index` shows the
      new count.
- [ ] `confirm <id> --insight` increments `confirmed_insights` independently
      of `confirmed_fixes`; both survive `validate` and appear in `index`,
      `recall`, and `list`.
- [ ] `index` rebuilds `index.jsonl`; running it twice is byte-identical;
      entries carry `version`, `failure_class`, `confirmed_fixes`,
      `confirmed_insights`, `sig_keywords`.
- [ ] `recall` ranks the signature-overlapping dossier top-1; a confirmed
      dossier outranks an otherwise identical unconfirmed one (both fix and
      insight confirms boost); `--class` filters; `--help` documents the
      scoring formula and states plainly the ranking is NOT semantic.
- [ ] `list` prints a compact table including class, fix, and insight counts.

## Tests

- [ ] `python3 -m unittest discover -s tests -t .` — all green, from the
      project root, on a clean checkout.
- [ ] Tests cover: v0.2 round-trip init→validate→index→recall→confirm;
      failure_class enum enforced; legacy v0.1 still validates; confirm
      increments and survives re-validation; recall prefers signature
      overlap and confirmed dossiers.

## Docs vs reality

- [ ] Every command in the README quickstart was copy-pasted and ran as
      documented.
- [ ] README "does NOT do" list is accurate — no auto-capture, no
      auto-autopsy, no embeddings anywhere in the code.
- [ ] The "what v0.2 changed and why" section matches the GPQA self-test
      outcome (16/20 → 20/20, caveats stated) — no claim exceeds the run.
- [ ] The Riemann link and its caveat are present and correctly worded
      (single-source, unreleased model — motivation, not evidence).
- [ ] No claim in README or spec exceeds what the code does.

## Hygiene

- [ ] No TODOs, placeholders, FIXME, or dead code:
      `grep -riE "todo|fixme|placeholder|XXX" --include="*.py" garm/ tests/ plugins/`
      returns nothing (excluding this checklist's own mention).
- [ ] Stdlib only: `grep -rE "^import |^from " garm/ plugins/garm/hooks/`
      shows no third-party imports.
- [ ] No secrets, keys, or personal data in the tree.
- [ ] No stale product-name references: `grep -rn "Autopsy" --include="*.py"
      --include="*.md" .` returns nothing (`autopsy` lowercase survives only
      as generic prose — "failure autopsy", "auto-autopsy").

## v1 plugin (plugins/garm/)

- [ ] `plugin.json` and `hooks/hooks.json` are valid JSON with the required keys.
- [ ] `python3 -m unittest discover -s plugins/garm/tests` — all green.
- [ ] Hook never exits nonzero and never prints diagnostics to stdout
      (covered by tests: malformed stdin, missing dir, broken GARM_BIN).
- [ ] End-to-end: real dossier dir + matching prompt yields the
      `hookSpecificOutput` envelope with the dossier's "what retrieval would
      have changed"; non-matching prompt yields empty stdout.
- [ ] `/garm:autopsy` command file has valid frontmatter and the commands it
      tells the agent to run actually work (init/validate/index/confirm).
- [ ] Hook's recall-output parser tracks the current `recall` format
      (regression: the v1.1 `from:` addition broke it; hook tests caught it).

## v1.1 sharing (import/export/origin)

- [ ] `python3 -m unittest discover -s tests` covers: collision rename,
      invalid skipped with reasons, single-file import, auto re-index,
      export copies .md only, origin defaults to agent, recall shows origin.
- [ ] `import` never overwrites: colliding ids renamed `<id>--from-<agent>`.
- [ ] Round-trip: export a bank, import elsewhere, dossiers recallable with
      provenance intact.

## When something slips through

Fix it, re-verify the full checklist, and note what the check missed so the
checklist gets better.
