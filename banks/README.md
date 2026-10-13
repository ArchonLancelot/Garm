# Seed banks

Field-tested dossier banks, shipped with Garm so a new bank doesn't start
empty. Import one (or both) into your own bank:

```bash
python3 -m garm import banks/bpsw --dir dossiers
python3 -m garm import banks/earth-moon --dir dossiers
```

Import validates every dossier on the way in, never overwrites your own,
renames id collisions to `<id>--from-<agent>`, merges premise registries,
and rebuilds the index. See `garm import --help`.

## What's here

- **`bpsw/`** — 12 dossiers + 5 premises from the Baillie–PSW campaign
  (Oct 7–12, 2026): hunting an odd composite that passes both the
  base-2 Miller-Rabin and strong Lucas tests. No pseudoprime found;
  12 genuinely different approaches, zero repeats. Includes the
  squarefreeness theorem (pass 7) and the v0.2.4 revisit (passes 11–12).
- **`earth-moon/`** — 12 dossiers + 10 premises from the Earth–Moon
  biplanar-coloring trial (Oct 11–12, 2026): hunting a biplanar graph
  with chromatic number 10–12. No valid graph found; 13 dead routes.
  All 10 premises are killed — including a big-route kill on outside
  evidence — so this bank also demonstrates dead-route filtering:
  `garm recall` skips the dead routes unless passed `--include-dead`.

Both banks are real field history, kept verbatim (v0.2-era dossiers
validate as legacy). Their blocking constraints are the seeds: invert
one, and you have your next idea.
