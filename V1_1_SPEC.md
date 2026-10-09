# Garm v1.1 spec (proposal): shared dossier banks

## The aha

Six passes on Baillie-PSW. Six genuinely different approaches. Every one
ended in a *negative* result with a reusable failure signature —
"don't sieve, factor", "one-sided construction", "sufficient-but-not-
necessary-strengthening", "more-variables-same-wall".

A negative result's value is: **it saves the next person from trying it.**
But v1's dossier bank is local (`GARM_DIR`). The "next person" is me, and
I've already learned it. Eight dossiers, all mine, all read by me — the
marginal value of dossier #9 *to me* is declining.

To *someone else* attempting BPSW, dossier #3 or #5 would be gold. They'll
never see them.

**Garm's core asset is negative results, and negative results have
network-effect value. v1's local-only bank caps it at linear. v1.1
unlocks sharing.** The dossiers were designed portable (markdown +
frontmatter) — the format was already pointing here.

## What v1.1 builds

### 1. `garm import <source> --dir dossiers`

Copy dossiers from another bank (a directory, or a single `.md` file)
into yours. Rules:

- On `id` collision: keep both. Rename the incoming to
  `<id>--from-<agent>` (agent slugified). Never silently overwrite.
- Validate each incoming dossier before copying; skip invalid ones with
  a warning listing why.
- After import, re-index automatically (no separate `index` step).
- Report: `imported N dossiers (M skipped: reasons) -> dossiers/`.

### 2. `origin` frontmatter field (optional)

```yaml
origin: alice-bpsw-bank-2026-10-08
```

Defaults to the `agent` field when absent. Records where a dossier came
from so recall can show provenance. Validated as free text (no format
enforcement — it's a label, not a key).

### 3. Provenance in `recall` and `list`

- `recall` output gains the origin: `[id] (from: <origin>)`.
- `list` gains an `ORIGIN` column.
- So the reader knows *whose* failure they're learning from — matters
  because a dossier from a strong agent on a related task outranks a
  stranger's.

### 4. `garm export --dir dossiers -o bank/` (thin convenience)

Copies the validated `.md` files (not the derived `index.jsonl`) to a
directory for sharing. That's it — the format is already portable; export
is just hygiene.

## Explicitly NOT in v1.1

- No registry, no server, no accounts. Sharing is files (email, git, a
  gist). Distribution is a later problem; v1.1 is the *format and
  commands* that make distribution possible.
- No trust/rating system. Provenance (`origin`) is the whole mechanism —
  the reader judges the source.
- No merge-conflict resolution beyond the rename rule. Dossiers are
  append-only records; they don't conflict, they accumulate.

## Why this is v1.1 and not v2

It's additive and backwards-compatible: `origin` is optional, `import`
only adds files, existing banks validate unchanged. No scoring changes
(yet — a future version might weight by origin reputation, but that's
data we don't have).

## Test plan

- Unit: import with collisions (rename rule), invalid incoming (skipped
  with reasons), single-file import, auto re-index.
- Round-trip: export a bank, import it elsewhere, `recall` surfaces the
  imported dossiers with provenance.
- Dogfood: import a foreign bank into the BPSW dossiers and confirm the
  hook injects imported dossiers with `(from: ...)` shown.

## The line for the README

"Your agent stops making the same mistake twice. v1.1: so does everyone
else's."
