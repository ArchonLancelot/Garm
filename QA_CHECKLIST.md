# QA checklist — Garm v0.2.12 (working)

Standing rule: nothing ships untested. Run this whole list before any release
tag or public push. Check each box only after verifying, not before.

## v0.2.12: coverage-gap batch (2026-11-10)

- [x] Verdict thresholds calibrated by measuring, not guessed: on the
      three shipped banks (bpsw/earth-moon/imo), 29 in-bank queries
      (top 15.34–44.54, margins 4.50–32.11, sig match 28/29) vs 27
      off-topic/generic queries (12 cleared 1.0, top up to 13.62,
      margins 0.05–4.74, sig match often 1 via aliases). Margin 5.0
      gives zero false COVERED on the measured set; cost is 4/29
      genuine queries flagged THIN (still served).
- [x] `garm recall` prints a verdict line first on stdout in all cases
      with live entries: COVERED (sig match + margin ≥ 5.0), THIN
      (served but flagged weak), UNCOVERED (nothing clears
      `--min-score`; names best score and closest miss). Empty bank
      still prints "no dossiers found" with no verdict (absence, not
      a verdict). Ranking order unchanged (roundtrip + v0.2 tests
      green after shifting their line indices past the verdict line).
- [x] UNCOVERED recall appends one terms-only line to
      `coverage-log.jsonl` (ts, terms, best, closest, matched — never
      the full prompt); `--no-coverage-log` and
      `GARM_NO_COVERAGE_LOG=1` both suppress it; COVERED/THIN never
      log; recall never fails when the log can't be written.
- [x] `garm coverage`: per-class counts include the zeros; signature-
      term clusters drop boilerplate (terms in >75% of dossiers) and
      numeric fragments (<2 letters); thin spots list 0–1-dossier
      classes and singleton terms (capped at 10, "+N more"); "file
      next" ranks thin spots by log rhymes (same-term or alias) and
      lists zero-dossier classes separately; `--clear` empties the log
      and reports the count; empty bank and missing dir handled.
- [x] Hook injects "Garm checked its failure memory for this task and
      found nothing relevant (best match scored X). No past failure
      applies — proceed without it." on UNCOVERED instead of silence;
      hits still inject as before; no verdict line (old recall, empty
      bank) stays silent; recall failure stays silent.
- [x] `garm version` / `garm --version` both print `garm 0.2.12`
      (version bumped in `garm/__init__.py` and `pyproject.toml`).
- [x] README: version bumped to v0.2.12, recall bullet rewritten for
      the verdict, new Coverage bullet; `DOSSIER_SPEC.md` retrieval
      section gains the v0.2.12 verdict subsection with the
      calibration numbers; recall `--help` updated (verdict + log).
- [x] Suites, all green: core 180/180 (skipped=1 on this machine —
      fastembed absent; 17 new v0.2.12 tests), hook 11/11, MCP 14/14.
      Clean-checkout simulation (`python3 -S`, no site-packages):
      core 180 tests, 0 errors, exactly 3 skips (fastembed test + 2
      mcp tests). Semantic lane untouched (stays experimental).
- [x] NOT PUSHED: local tree only; push waits for Armando's explicit
      word after the green report.

## v0.2.12 addendum: signature-weight trial, measured and REJECTED (2026-11-25)

- [x] Trial: signature weight 2x -> 3x in `garm/retrieval.py`
      (`SIGNATURE_WEIGHT`, also the semantic lane's shape) to sharpen
      the BPSW "Lucas test first" probe, which sat THIN at margin 2.43
      because a "skip the Lucas test" dossier scores 6.11 on generic
      task words against the right dossier's 5.83 signature lead.
      Measured on the live 17-dossier BPSW bank: Lucas went THIN ->
      COVERED (13.82/2.43 -> 19.65/6.98) and factoring THIN -> COVERED
      (10.27/3.96 -> 12.83/6.21) — but the trial FAILED calibration:
      false COVERED on off-topic "chromatic number of a graph"
      (11.01/7.45, single generic term "number") and "random prime
      pairs" regressed COVERED -> THIN (13.58/5.09 -> 14.76/3.29; its
      evidence lives in the body, not the signature). Every field-weight
      tweak helps one probe and hurts another: the four probes' evidence
      lives in different fields, so 2x/1x/1x is already near the balance
      point. Trial REVERTED; the 2x weight is now a named constant
      (`SIGNATURE_WEIGHT = 2`) with the rejection recorded in its
      comment. The Lucas THIN is the calibrated system working as
      designed (right answer, honestly weak evidence), not a defect.
- [x] New regression harness `tests/probe_calibration.py` (standalone,
      not a pytest test): 4 genuine BPSW probes (top must be the right
      dossier) + 6 off-topic queries (must never verdict COVERED).
      Passes on both banks after the trial revert: shipped `banks/bpsw`
      (12 dossiers) ALL PASS, live 17-dossier BPSW bank ALL PASS
      (baseline numbers reproduced exactly: tests 177 passed, 3 skipped).
      Run it before and after any retrieval change.
- [x] The harness caught a real staleness bug on first run: the shipped
      `banks/bpsw` lucas-first dossier still had its October signature
      ("mirror-image-also-one-sided"), while the live bank got the Nov 22
      signature fix ("lucas-first-rank-construction-also-one-sided",
      `confirmed_insights: 1`). Synced the shipped copy from the live
      bank (byte-identical after copy); harness then passes on both
      banks. The Nov 10 calibration numbers stand: the sync changes one
      dossier's signature text, and the harness's two properties hold on
      the shipped bank after it.

## v0.2.12 addendum: concept bonus, measured and KEPT (2026-11-25)

- [x] Concept bonus (`CONCEPT_BONUS = 3.0`, `concept_match` in
      `garm/retrieval.py`): flat +3.00 on the BM25 total when two
      distinct query terms sit adjacently in a dossier's signature NAME
      (the curated concept label), aliases count, shown as
      `concept:<a>+<b>` on the hit. Only the slug (before the first
      period) is examined — never the prose, where a "skip Lucas test"
      sentence would reward the wrong dossier. Not folded into the
      semantic lane's cosine-scale totals. Score tuple extended to 8
      elements (concept bonus last); CLI, MCP server, and all tests
      updated; hook regex unaffected (it only reads through `sig:`).
- [x] Measured on `tests/probe_calibration.py` (both banks, ALL PASS):
      live 17-dossier bank — Lucas THIN 13.82/2.43 -> COVERED
      16.82/5.43 (`concept:lucas+first`); factoring, squarefree,
      random-pairs, and all 6 off-topic verdicts UNCHANGED (0 false
      COVERED). Shipped 12-dossier bank — Lucas THIN 14.07/4.68 ->
      COVERED 17.07/7.68; everything else unchanged. The bonus fires
      on no other harness query. 6 new unit tests in
      `tests/test_v026.py` (bigram, single-term, non-adjacent,
      prose-exclusion, alias, no-signature).
- [x] Suites, all green after the change: core 183 passed, 3 skipped
      (177 + 6 new concept tests; fastembed absent so semantic tests
      run on stubs), hook 11/11, MCP 14/14 (mcp package installed in
      the test venv to run them). README Recall bullet documents the
      bonus; harness docstring records the before/after numbers.
      The 3.0 constant is calibrated on the 10-query harness, not the
      56-query Nov 10 set (not stored as a fixture) — re-measure on a
      wider set before treating it as settled.
- [x] NOT PUSHED: local tree only; push waits for Armando's explicit
      word after the green report.

## v0.2.11: field-test fix batch (LMArena Agent Mode dogfood, 2026-10-28)

- [x] `garm version` and `garm --version` both print `garm 0.2.11`
      (version bumped in `garm/__init__.py` and `pyproject.toml`).
- [x] `recall --min-score` defaults to 1.0, matching the hook's
      `GARM_MIN_SCORE` default: a 0.00 query prints NOTHING on stdout
      (short stderr note, exit 0); `--min-score 0` restores the old
      behavior; strong hits still print the table.
- [x] At/above threshold, recall appends the top hit's "What retrieval
      would have changed" section after the table; the hook's table
      regex ignores those lines (hook suite green).
- [x] Hook passes `--min-score` explicitly, so a user-set
      `GARM_MIN_SCORE` below 1.0 still surfaces weak hits (new hook test:
      0.58-score hit injects at 0.5, stays silent at default 1.0).
- [x] TTY guard: `--task` + closed stdin refuses (exit 1, clear stderr
      error, NO file or directory written) — the pre-fix repro wrote a
      bare scaffold. No-`--task` path still refuses. `--answers` is the
      non-interactive route.
- [x] `--answers` prints `--- draft ---` before saving, non-blocking
      (no confirmation prompt); interactive path still asks.
- [x] `premise attach <id> --dossier <dossier-id>` edits/creates the
      dossier's `## Premises` section, re-indexes, is idempotent
      ("already attached"), and rejects unknown premises/dossiers.
      `premise kill` reports "declares this premise: N" and "dead
      routes now: M", and warns on stderr when zero dossiers declare
      it. Killer exemption honored: a dossier is never a dead route
      via a premise it killed itself.
- [x] Interactive autopsy asks for premises (optional, comma-separated)
      — verified present in `QUESTIONS`; the field test's "never asks"
      claim was wrong on this point (repro confirmed the question).
- [x] Confirm-note cap 500 chars: 500 accepted, 501 rejected
      ("max is 500").
- [x] Slug truncation breaks at a word boundary within the 50-char cap
      (field-test "for-a" case now yields the full "for-a"); single
      long word still hard-cuts at 50.
- [x] `DOSSIER_SPEC.md` formula matches the implementation
      (2×sig + task + body + gated boosts, `--min-score` note); recall
      `--help` keeps "worth 2 points" / "1 point each" / "bm25" /
      "not semantic" phrasing.
- [x] Clean-checkout simulation (`python3 -S`, no site-packages):
      core suite 163 tests, 0 errors, exactly 3 skips (fastembed test
      + 2 mcp tests); the deliberate-absence guard test still runs.
- [x] `export` reports dossiers and premises separately ("exported 2
      dossiers, 1 premises file(s)"); never folds premises.json into
      the dossier count.
- [x] `list` task column widened to 80 chars (IDs to 64); a 60-char
      task prints in full.
- [x] README: version bumped to v0.2.11, one-line positioning note
      (one dossier per painful failure, not per task), `--answers`
      wording clarified (draft printed for review, no blocking prompt).
- [x] Suites, all green: core 163/163 (skipped=1 on this machine —
      fastembed absent; mcp present so its tests run), hook 11/11,
      MCP 14/14. Semantic lane untouched (stays experimental).
- [x] NOT PUSHED: local tree only; push waits for Armando's explicit
      word after the green report.

## v0.2.9: Tier 2 opt-in semantic lane

- [x] `garm/semantic.py`: lazy fastembed import (never on the default
      path — verified `fastembed not in sys.modules` after default-path
      scoring); `SemanticError` messages always name the fixing command
      (`pip install garm[semantic]` / `garm semantic warmup`).
- [x] `score_corpus` default path byte-identical to v0.2.7: 25-entry
      randomized check, total == 2*sig + task + fix + ins and sem == 0.0
      on all 25; fastembed never imported.
- [x] Semantic ranking: stub-backend test proves the meaning lane leads
      in semantic mode (order follows semantic ranks; the BM25 winner
      does not veto). Design note: an earlier revision fused both lanes
      with RRF, but RRF gives equal weight to a BM25 lane that is
      confidently wrong on paraphrases — the exact failure --semantic
      exists to escape — so the lane the user asked for leads instead.
      Boosts fold into the semantic ranking (adding capped ints raw on
      top of rank scores would make boosts the entire ranking).
- [x] Cache: `.garm/embeddings.json` keyed by id+model+content-hash;
      hit avoids re-embed, edit invalidates (hash mismatch recomputes).
- [x] Guards: fastembed genuinely hidden -> error names the install;
      unwarmed model -> error names `garm semantic warmup`; warmed ->
      no raise. `model_is_cached()` validates file sizes against
      fastembed's own metadata (a partial download reads as
      not-cached); recall path sets `HF_HUB_OFFLINE=1` so a cache
      problem raises instead of downloading mid-turn.
- [x] Durable model cache: fastembed >= 0.9 defaults to
      `tempfile/fastembed_cache` (ephemeral!); Garm pins
      `~/.cache/fastembed` unless `FASTEMBED_CACHE_PATH` is set.
- [x] Wiring: CLI `--semantic` + `semantic warmup` parse; MCP
      `garm_recall(semantic=true)` returns `semantic_score` /
      `semantic_lane_first`; hook `GARM_SEMANTIC=1` appends `--semantic`
      (threshold stays 1.0 — semantic totals are cosine-based on a
      similar scale); hook line regex still parses the new `sem:` column.
- [x] Suites: core 146/146 (131 existing + 15 new), hook 10/10, MCP
      14/14 — all green.
- [x] SHIP GATE (2026-10-15, drill bank = 29 seed dossiers + faithful
      P2-autopsy reconstruction): the transfer test's paraphrase
      ("five different whole numbers whose reciprocals total one…")
      ranks the P2 autopsy #3 with `--semantic` (BM25 alone: #15,
      absent from top-3 — the measured failure, reproduced). Honest
      margin note: bge-small still prefers two noise dossiers (#1-2);
      the lane lifts the autopsy #15 -> #3 but the model's
      discrimination on short math texts is the binding constraint.

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
