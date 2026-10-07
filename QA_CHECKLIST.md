# QA checklist — fm-v01

Standing rule: nothing ships untested. Run this whole list before any release
tag or public push. Check each box only after verifying, not before.

## Format and spec

- [ ] `DOSSIER_SPEC.md` matches what the code actually enforces (field names,
      required sections, index.jsonl fields — no drift).
- [ ] `dossiers/examples/flaky-checkout-race.md` validates clean:
      `python3 -m autopsy validate dossiers/examples/flaky-checkout-race.md`
- [ ] The example is clearly marked illustrative/synthetic.

## CLI

- [ ] `python3 -m autopsy --help` lists all five commands with accurate
      one-line descriptions.
- [ ] `init` scaffolds a dossier: file created, frontmatter prefilled
      (version, id, ISO date, agent, task, outcome).
- [ ] `validate` passes a good dossier and rejects a bad one with a clear
      message naming the problem; exit codes 0/1 verified.
- [ ] `index` rebuilds `index.jsonl`; running it twice is byte-identical.
- [ ] `recall` ranks the keyword-overlapping dossier top-1; `--help` states
      plainly that ranking is keyword overlap, NOT semantic.
- [ ] `list` prints a compact, readable table.

## Tests

- [ ] `python3 -m unittest discover -s tests -t .` — all green, from the
      project root, on a clean checkout.
- [ ] Tests cover: round-trip init→validate→index→recall with top-1 ranking;
      validate rejects a missing required section; index is idempotent;
      recall help text honesty.

## Docs vs reality

- [ ] Every command in the README quickstart was copy-pasted and ran as
      documented.
- [ ] README "does NOT do" list is accurate — no auto-capture, no
      auto-autopsy, no embeddings anywhere in the code.
- [ ] The Riemann link and its caveat are present and correctly worded
      (single-source, unreleased model — motivation, not evidence).
- [ ] No claim in README or spec exceeds what the code does.

## Hygiene

- [ ] No TODOs, placeholders, FIXME, or dead code:
      `grep -riE "todo|fixme|placeholder|XXX" --include="*.py" autopsy/ tests/`
      returns nothing (excluding this checklist's own mention).
- [ ] Stdlib only: `grep -rE "^import |^from " autopsy/` shows no
      third-party imports.
- [ ] No secrets, keys, or personal data in the tree.

## When something slips through

Fix it, re-verify the full checklist, and note what the check missed so the
checklist gets better.
