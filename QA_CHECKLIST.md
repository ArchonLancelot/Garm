# QA checklist — Garm v0.2.8

Standing rule: nothing ships untested. Run this whole list before any release
tag or public push. Check each box only after verifying, not before.

## v0.2.8: MCP tool annotations (M8ven flag)

- [ ] All 10 tools in `mcp_server/server.py` declare `annotations` with
      all four hints as booleans (readOnly/destructive/idempotent/
      openWorld), values verified against actual behavior (kill/reopen
      idempotent per their no-op-on-repeat docstrings; nothing destructive;
      nothing touches the network).
- [ ] Hints serialize with camelCase names on the wire (`readOnlyHint`).
- [ ] `garm_recall` MCP description no longer says "keyword overlap,
      v0.2.6" — now BM25, v0.2.7.
- [ ] MCP suite 14/14 green (3 new annotation tests); core 131/131 and
      hook 10/10 still green.

## v0.2.7: BM25 retrieval

- [ ] `garm/retrieval.py`: `BM25` implements the Okapi formula (smoothed
      IDF, tf saturation, length norm); `score_corpus` scores the whole
      bank in one pass, sig subscore ×2 + task subscore + confirms (cap 5);
      alias groups count as one term (summed tf, OR'd df).
- [ ] Stopword-noise regression: a bank where "one" appears in most
      dossiers ranks the distinctive-term dossier first for a query
      containing "one" (the 2026-10-14 transfer-test failure, now fixed).
- [ ] Pure-paraphrase honest limit still holds: a query sharing NO
      vocabulary with the relevant dossier does not surface it — BM25 is
      still lexical; the noise just scores low instead of winning.
- [ ] Hook: `garm_recall.py` parses float scores; `GARM_MIN_SCORE` default
      recalibrated 2 → 1 (BM25 scores run smaller); hook tests 10/10.
- [ ] MCP recall returns float scores; `matched_terms` display unchanged.
- [ ] Old-vs-new drill on the shipped banks: exact rankings don't invert,
      dead-route exclusion still works, confirms still boost.
- [ ] `DOSSIER_SPEC.md` retrieval section documents BM25 + its limit;
      README recall bullet + transfer-test note updated.
- [ ] Full suite green: core 131/131, hook 10/10.

## v0.2.6: hybrid retrieval

- [ ] `garm/retrieval.py`: `canonicalize_text` maps Greek letters to names,
      glues super/subscript digits onto word chars (`x²`→`x2`, `C₇`→`C7`),
      turns operators into words; `aliases_for` returns the curated group
      or the word itself; `find_match` prefers exact, picks deterministically.
- [ ] Recall end-to-end: a paraphrase query (`flaky`) finds the
      `intermittent` dossier with `flaky~intermittent` in `matched:`; exact
      matches still display bare and rank first; plurals match.
- [ ] Scoring shape unchanged: 2/sig + 1/task + confirms (cap 5) —
      verified by the exact-match regression anchor (Chernick drill = 7).
- [ ] No false positives: unrelated query words match nothing; the synonym
      map is the only source of aliases (no algorithmic stemming).
- [ ] `garm index` rebuild stays byte-identical; canonicalized keywords land
      in `index.jsonl`.
- [ ] `garm_recall` MCP description + `matched_terms` use the alias display.
- [ ] Old-vs-new drill on the shipped banks: paraphrase scores move, exact
      rankings don't invert, dead-route exclusion still works.
- [ ] Honest-limit drill documented: the hybrid does NOT surface
      conceptually-related-but-v differently-worded dossiers (Wieferich
      query vs squarefree theorem) — paraphrase only, not meaning.
- [ ] `DOSSIER_SPEC.md` retrieval section documents the hybrid and its
      limit; version policy has the v0.2.6 entry (`dossier_version` stays
      `"0.2"`).
- [ ] README: v0.2.6 title/release line, recall bullet, roadmap marks
      semantic retrieval as future opt-in.
- [ ] `SPEC_VERSION` is `"0.2.6"` in exactly one place (`garm/dossier.py`).

## v0.2.5: assisted autopsy drafting

- [ ] `garm autopsy --answers` full flow: valid draft written, answers
      verbatim in their sections, `what_was_tried` list becomes bullets,
      blank optional sections stripped, file validates clean, index rebuilt.
- [ ] `garm autopsy --answers` partial flow: draft still written, exit 1,
      report names exactly the sections that need writing, nothing indexed.
- [ ] Bad answers rejected before anything is written: unknown keys, bad
      `failure_class`, missing `task`, malformed JSON.
- [ ] Premise refs: comma-joined ids normalized to one per line; unknown ids
      warn loudly on stderr but are kept; malformed ids warn too.
- [ ] Interactive flow (mocked stdin): full interview → draft printed →
      save confirm `y` writes+indexes; `n` discards the draft; immediate EOF
      aborts cleanly with no crash and nothing written.
- [ ] `garm autopsy` with no `--task`/`--answers` on a non-tty errors with a
      pointer to `--answers` instead of hanging on prompts.
- [ ] `garm_autopsy` MCP tool: 9 tools registered; full answers → valid +
      indexed; partial → invalid with named sections; bad class/keys raise.
- [ ] `DOSSIER_SPEC.md` documents the answer keys and the four honesty
      rules; version policy has the v0.2.5 entry (`dossier_version` stays
      `"0.2"` — format unchanged).
- [ ] README: v0.2.5 title/release line, autopsy in capabilities + quickstart,
      roadmap marks assisted drafting shipped, "No auto-autopsy" bullet still
      accurate (interview formats answers; diagnosis stays the author's job).
- [ ] `SPEC_VERSION` is `"0.2.5"` in exactly one place (`garm/dossier.py`).

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
- [ ] v0.2.3: `validate` rejects a fresh `init` scaffold (placeholder
      guidance text) naming the unfilled sections; a fully-filled dossier
      passes. `import` of an identical bank skips with "already in bank
      (identical content)" and changes nothing; modified colliding ids
      still rename. `confirm` rebuilds the index by itself (no manual
      re-index). `--help` shows the spec version from one constant and
      `recall --help` explains the output columns.
- [ ] v0.2.4: `premise add` generates `P-YYYYMMDD-NNN` ids and rejects
      unknown parents/empty statements; `premise list` shows status;
      `premise kill <id> --by <dossier> [--evidence proof|our-tests|outside-work]`
      closes the big route and all descendants transitively and re-indexes. A dossier with
      `## Premises` listing a dead premise indexes with `premise_dead`
      true; `recall` excludes it (dead-routes block names the killer
      premise) and `--include-dead` ranks it marked `[premise-dead]`.
      `export` copies `premises.json`; `import` merges it without
      overwriting (collision with different statement keeps local).
      `garm_recall`/`garm_premise_add`/`garm_premise_kill`/
      `garm_premise_list` live-check over stdio.
- [ ] premise reopen: `premise reopen <id> --by <who>` revives a killed premise
      and everything that died only because of its kill (independently
      killed premises stay dead); `premise list` shows `reopened by`;
      recall includes the revived routes again. `garm_premise_reopen`
      registered (10 tools).
- [ ] killer-dossier exemption: a dossier whose id is the recorded killer
      of a dead premise it lists is NOT a dead route via that premise
      (direct kill or `inherited from` chain); other dossiers resting on
      the dead premise still are. `recall` ranks the killer dossier by
      default.
- [ ] kill --by validation: a `--by` shaped like a dossier id
      (`YYYY-MM-DD-...`) is rejected when no dossier with that id is in
      the bank (typo guard); plain-text notes still accepted. Premise
      stays open on rejection.

## CLI

- [ ] `python3 -m garm --help` lists all seven commands with accurate
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
- [ ] `confirm <id> --note "..."` stores `confirm_note_N` (max 140 chars,
      rejects empty/overlong); file stays valid; note-free confirms add no
      keys.
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
      shows no third-party imports. (`mcp_server/` is the deliberate
      exception: it needs the `mcp` SDK. `garm/` itself stays stdlib-only.)
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

## MCP server (mcp_server/)

- [ ] With `mcp` 2.x installed (`pip install mcp`):
      `python -m unittest discover -s mcp_server/tests -t .` — all green.
- [ ] On stdlib-only Python the same command skips (8 skipped), never fails.
- [ ] `/garm:autopsy`-style live check: real MCP client over stdio —
      initialize, list_tools shows the 8 tools, and a full
      init → validate → confirm → recall → list round trip works, plus
      premise_add → premise_kill → recall (dead route excluded) →
      recall(include_dead=true) → premise_list.
- [ ] `garm_recall`/`garm_list` return one JSON array in a single text
      block (the SDK unrolls Python lists into multiple blocks).
- [ ] Confirming a scaffold fails cleanly (validate-first, like the CLI).
- [ ] `mcp_server/README.md` config snippets (Claude Desktop, Cursor)
      reference `python -m mcp_server` from the repo root.
- [ ] `mcp_server/requirements.txt` pins `mcp>=2,<3`.

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
