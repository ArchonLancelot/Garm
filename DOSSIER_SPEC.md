# Dossier format spec — v0.2.2 (Garm)

A **dossier** is one hand-written failure autopsy: a Markdown file with a
small frontmatter block and fixed `##` sections. The analysis inside is
written by the agent (or human) using the tool. The tool only enforces
*structure* — it cannot check whether the analysis is true.

v0.2 adds two frontmatter fields: `failure_class` (what *kind* of failure
this was — required) and `confirmed_fixes` (how many later runs a retrieved
dossier demonstrably helped — starts at 0, bumped with `garm confirm`).
v0.2.1 adds `confirmed_insights` (how many times a dossier's analysis
generated a new approach — starts at 0, bumped with `garm confirm
--insight`; the signal for open-ended work with no verifiable "fix").
v0.2.2 adds two *optional* sections, `## Challengeable premises` and
`## Open questions` (see below) — motivated by the first foreign-agent
field test (2026-10-11), where negating a stated premise produced the
genuinely new idea. Nothing already written needs to change: v0.2/0.2.1
dossiers validate as before, with or without the new sections.
v0.1 dossiers remain valid; they are treated as legacy and simply lack the
new fields.

## File layout

```markdown
---
dossier_version: "0.2"
id: 2026-10-07-flaky-checkout-race
created: 2026-10-07
agent: claude-code
task: "Fix flaky test_checkout_total in the storefront test suite"
outcome: failed
failure_class: reasoning-error
confirmed_fixes: 0
confirmed_insights: 0
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
| `dossier_version` | yes | `"0.2"` (v0.1 also accepted as legacy — see below) |
| `id` | yes | slug: `[a-z0-9][a-z0-9-]*`, unique within the directory |
| `created` | yes | ISO date `YYYY-MM-DD` |
| `agent` | yes | free text, e.g. `claude-code` |
| `task` | yes | one-line description of the failed task |
| `outcome` | yes | `failed` or `recovered` |
| `failure_class` | yes for v0.2 | one of the five classes below |
| `confirmed_fixes` | no | non-negative integer, default 0 |
| `confirmed_insights` | no | non-negative integer, default 0 |
| `origin` | no | free text, default = `agent` (provenance for imported banks) |

`outcome: recovered` is for sessions that hit the wall and got past it — the
autopsy is still worth keeping.

## Failure classes

Pick the closest one. Different classes fail differently and get fixed
differently, so retrieval (`recall --class`) and review can treat them
differently:

| Class | Meaning |
|---|---|
| `knowledge-gap` | the agent lacked a fact it needed (a formula, an API behavior, a domain rule) |
| `reasoning-error` | the facts were there; the reasoning step went wrong |
| `execution-slip` | knew better; fumbled the execution (typo, wrong command, misclick) |
| `tool-misuse` | wrong tool for the job, or a tool used wrongly |
| `misread-task` | solved the wrong problem / misread the requirements |

When torn between `knowledge-gap` and `reasoning-error`, ask: would handing
the agent a textbook page have fixed it? Yes → `knowledge-gap`. No, it had
the page and still went wrong → `reasoning-error`.

## confirmed_fixes / confirmed_insights

Two counters track whether dossiers earn their keep. Written as `0` on new
dossiers; bumped with:

```bash
python3 -m garm confirm <dossier-id> --dir dossiers            # a fix
python3 -m garm confirm <dossier-id> --insight --dir dossiers   # an insight
python3 -m garm index --dir dossiers   # refresh the index afterwards
```

- `confirmed_fixes`: the dossier prevented a specific repeat / fixed a
  verifiable failure. Use `confirm` when a retrieved dossier changed what a
  run did and the run then succeeded (or avoided the documented failure).
- `confirmed_insights`: the dossier's analysis *generated a new approach* —
  its blocking constraint, inverted, became the next idea. Use `confirm
  --insight` for open-ended work where there is no verifiable "fix" to
  count, but the dossier still moved the work forward.

Don't confirm on vibes — the counters are the dossier bank's track record,
and `recall` boosts confirmed dossiers (each counter adds up to 5 points,
capped separately). A dossier with confirmed fixes or insights has earned
more trust than one with 0; the caps keep one veteran from swamping new
dossiers forever.

## origin

Where the dossier came from. Optional free text; absent resolves to the
`agent` field — a dossier you wrote is yours. It exists for imported
banks (`garm import`): when you pull in someone else's dossiers, `origin`
records whose they were, and `recall`/`list` show it, so the reader knows
whose failure they're learning from. No format is enforced — it's a
provenance label, not a key.

## Sharing banks: import / export

A dossier bank is just markdown files — already portable. Two commands
make sharing deliberate:

```bash
# pull another bank (dir or single .md) into yours:
python3 -m garm import /path/to/their-bank --dir dossiers
# copy your validated dossiers out for sharing (not the derived index):
python3 -m garm export --dir dossiers -o bank/
```

Import rules: each incoming dossier is validated first (invalid ones are
skipped with reasons); `id` collisions are renamed to
`<id>--from-<agent>` — never silently overwritten; the index rebuilds
automatically. Export copies only validated `.md` files.

Why this exists: a negative result's value is saving the *next* person
from trying it. A local-only bank caps that at one mind. Sharing is the
network effect — your agent stops making the same mistake twice, and so
does everyone else's.

## Version policy

- v0.2 dossiers: `dossier_version: "0.2"`, `failure_class` required.
- v0.2.2 dossiers: same as v0.2, plus the optional `## Challengeable
  premises` and `## Open questions` sections. `dossier_version` stays
  `"0.2"` — the new sections are additive, so nothing already written
  needs to change and old dossiers validate untouched.
- v0.1 dossiers (no `failure_class`): still validate and index. `validate`
  prints a note that they're legacy. In `recall` they rank normally
  (signature weighting is derived, so it applies); they are simply skipped
  when `--class` filters by a class they don't declare. Nothing breaks;
  nothing is silently upgraded.

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

7. **Challengeable premises** — the load-bearing assumptions the failed
   approaches rested on, each phrased so a future reader can ask "what if
   this is false?" Write them as short, falsifiable claims, not
   background. A premise list is a list of doors: each one negated is a
   candidate new approach. (In the 2026-10-11 field test, negating one
   such premise — "the two tests are nearly independent filters" — is
   what produced the genuinely new idea.)
8. **Open questions** — precise questions the failure left open for a
   future run to aim at. Dead ends often end on an exact unanswered
   question ("is there a two-sided condition weaker than Pomerance's?");
   capturing it turns the dossier from a warning into a target.
9. **Tokens** — estimated tokens spent repeating failed approaches, with a
   one-line method note. Optional because honest estimates aren't always
   available; never invent one.

Validation (`garm validate`) checks exactly the table and list above —
nothing more. A dossier that passes validation is *structurally* sound; the
truth of its analysis is the author's responsibility.

## index.jsonl

Derived file, rebuilt any time with `garm index --dir <dir>`. One JSON
object per line, sorted by `id`:

```json
{"id": "2026-10-07-flaky-checkout-race", "version": "0.2", "task": "Fix flaky test_checkout_total in the storefront test suite", "signature": "Name: flaky-test-chased-as-code-bug", "keywords": ["fix", "flaky", "test", "checkout", "total", "storefront", "suite", "name", "chased", "code", "bug", "match", "rule", "..."], "sig_keywords": ["name", "flaky", "test", "chased", "code", "bug", "match", "rule", "..."], "failure_class": "reasoning-error", "confirmed_fixes": 2, "outcome": "failed", "path": "examples/flaky-checkout-race.md", "created": "2026-10-07"}
```
(real output from `garm index`; `"..."` abbreviates the full keyword list)

Fields:

| Field | Meaning |
|---|---|
| `id` | dossier id |
| `version` | dossier_version from frontmatter |
| `task` | task one-liner, copied from frontmatter |
| `signature` | first non-empty line of the Failure signature section (≤140 chars) |
| `keywords` | lexical keywords from task + signature text (stopwords removed) |
| `sig_keywords` | lexical keywords from the failure signature alone (the retrieval key) |
| `failure_class` | frontmatter class, or null for legacy v0.1 dossiers |
| `confirmed_fixes` | frontmatter counter (0 if absent) |
| `confirmed_insights` | frontmatter counter (0 if absent) |
| `origin` | provenance label (defaults to `agent`) |
| `outcome` | `failed` or `recovered` |
| `path` | dossier path relative to the indexed directory |
| `created` | ISO date from frontmatter |

Because it is fully derived, `index.jsonl` can be deleted and rebuilt without
losing anything. Rebuilding is byte-identical for unchanged input.

## Retrieval ranking (v0.2.1)

`garm recall` scores each dossier as:

```
score = 2 × (query ∩ sig_keywords) + 1 × (query ∩ task_keywords)
      + min(confirmed_fixes, 5) + min(confirmed_insights, 5)
```

Signature terms count double because the failure signature is the retrieval
key — it's the part of the dossier written to be matched on. Task terms
count single. Each confirmed fix adds a point up to a cap of 5, so dossiers
with a track record rank higher without swamping new ones forever. Ties
break by confirmed fixes, then dossier id.

This is still lexical, not semantic. It finds dossiers that *talk about the
same things*, weighted toward the matchable parts and toward dossiers that
have earned trust. It does not understand meaning, and it will miss
paraphrases. That remains an honest limitation — semantic retrieval is on
the roadmap, not in the tool.

## Writing dossiers that earn their keep

Five lessons — the first four from a 20-question GPQA Diamond self-test
run by the framework's own author (16/20 without recall, 20/20 with it; every
fix traced to a dossier, zero regressions), the fifth from the first
foreign-agent field test (Hark, 2026-10-11, on the 10-dossier Baillie–PSW
bank: the agent avoided all 8 documented dead ends and produced one
genuinely new idea):

1. **Verify the corrected reasoning independently.** The best dossier in the
   test wasn't derived from the answer key — its author re-checked the
   chemistry against external references. A dossier that says "the answer
   was X" teaches nothing; a dossier that re-derives *why* teaches
   everything. Never write the correct option/answer into the dossier to
   "help" — that turns retrieval into answer lookup and the whole loop
   into theater.
2. **Quote your wrong conclusion verbatim in the failure signature.** The
   signature is a match rule for future runs: "if you find yourself
   concluding <exact wrong thing>, stop." Future-you matches on specifics,
   not vibes.
3. **Tag the failure class honestly.** In the test, 3 of 4 misses were
   `knowledge-gap` and 1 was `reasoning-error` — and they needed different
   fixes. A mislabeled dossier retrieves in the wrong context and teaches
   the wrong lesson.
4. **Confirm the ones that work.** When a retrieved dossier changes a run
   for the better, run `garm confirm`. An unconfirmed bank is a pile of
   claims; a confirmed bank is a track record.
5. **State your premises so they can be negated, and leave your open
   questions on the page.** In the field test, the new idea (the D = −7
   merge) came from negating a premise two dossiers had stated crisply —
   "the two tests are nearly independent filters" — and the attack was
   aimed at an open question a third dossier had left behind ("is there
   a two-sided condition weaker than Pomerance's?"). A dossier that only
   says what failed teaches avoidance; a dossier whose premises are crisp
   enough to challenge teaches invention. The `## Challengeable
   premises` and `## Open questions` sections exist for exactly this.
   They are optional — one field test is not proof — but they are where
   the next idea hides.
