"""Calibration probe harness for Garm retrieval (not a pytest test).

Runs the genuine + off-topic probe set against a bank and checks the two
properties the verdict calibration exists to protect:

  * every genuine probe ranks the right dossier first, and
  * no off-topic query ever verdicts COVERED.

Margins and top scores are printed for the human but NOT asserted: they
move with the bank (12-dossier shipped bank vs the live 17-dossier
bank), while the two properties above must hold on either.

Usage (from the repo root):
    python3 tests/probe_calibration.py [--bank DIR]
Default bank is the shipped banks/bpsw; pass the live BPSW bank to
reproduce the numbers quoted in the comments.

Background (2026-11-25): a signature-weight trial (2x -> 3x) fixed the
"Lucas test first" probe (margin 2.43 -> 6.98) but FAILED this harness:
it created a false COVERED on "chromatic number of a graph" (margin
7.45 on the single generic term "number") and regressed "random prime
pairs" COVERED -> THIN (its evidence lives in the body, not the
signature). The trial was reverted. The lesson recorded here and in
garm/retrieval.py: the 5.0 margin bar was calibrated at 2x (Nov 10,
29 in-bank + 27 off-topic queries); any weight change must re-measure
the whole set, not one probe. Run this harness before and after any
retrieval change.

Measured 2026-11-25 on the live 17-dossier BPSW bank at 2x (baseline):
  genuine: factoring THIN 10.27/3.96, squarefree COVERED 20.99/18.43,
           Lucas THIN 13.82/2.43, random-pairs COVERED 13.58/5.09
           (all four tops correct)
  off-topic: 5 THIN, 1 UNCOVERED, 0 COVERED

With the concept bonus (v0.2.12, 2026-11-25, same bank):
  genuine: factoring THIN 10.27/3.96 (unchanged), squarefree COVERED
           20.99/18.43 (unchanged), Lucas COVERED 16.82/5.43 (the fix:
           +3.00 concept:lucas+first), random-pairs COVERED 13.58/5.09
           (unchanged)
  off-topic: 5 THIN, 1 UNCOVERED, 0 COVERED (unchanged)
  On the shipped 12-dossier bank: Lucas COVERED 17.07/7.68 (was THIN
  14.07/4.68); everything else unchanged. The bonus fires on no other
  harness query.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from garm import dossier as D
from garm import premise as PR
from garm import retrieval as RU

# (query, expected top dossier id substring)
GENUINE = [
    ("factoring 2^E-1, reading candidates off",
     "find-baillie-psw-pseudoprime-by-factoring-2-e-1-to"),
    ("prove squarefree",
     "prove-baillie-psw-pseudoprime-must-be-squarefree"),
    ("Lucas test first",
     "find-baillie-psw-pseudoprime-via-lucas-first-rank"),
    ("random prime pairs, strong base-2",
     "find-baillie-psw-pseudoprime-via-random-prime-pair"),
]

# Off-topic for the BPSW bank: must never verdict COVERED.
OFF_TOPIC = [
    "flaky test in CI pipeline",
    "how to deploy to production",
    "chromatic number of a graph",
    "my code crashes on startup",
    "best way to learn Spanish",
    "refund policy for a subscription",
]

MIN_SCORE = 1.0


def load_entries(bank: Path) -> list[dict]:
    registry = PR.load_registry(bank)
    entries = []
    for md in sorted(bank.rglob("*.md")):
        if D.validate_dossier(md):
            continue
        entries.append(D.build_index_entry(md, bank, registry))
    return entries


def verdict_for(query: str, entries: list[dict]):
    keys = D.extract_keywords(query)
    scores = RU.score_corpus(keys, entries)
    by_id = {e["id"]: e for e in entries}
    ranked = sorted(((v[0], by_id[eid]) for eid, v in scores.items()),
                    key=lambda t: -t[0])
    # coverage_verdict wants [(total, entry), ...] best-first.
    verdict, top, best, margin, matched = RU.coverage_verdict(
        keys, ranked, MIN_SCORE)
    return verdict, top, best, margin, matched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bank", type=Path, default=REPO_ROOT / "banks" / "bpsw")
    args = ap.parse_args()
    entries = load_entries(args.bank)
    print(f"bank: {args.bank} ({len(entries)} dossiers)")
    failures = 0
    print("genuine probes (top must be the expected dossier):")
    for query, expected in GENUINE:
        verdict, top, best, margin, _matched = verdict_for(query, entries)
        top_id = top["id"] if top else "-"
        ok = expected in top_id
        failures += 0 if ok else 1
        print(f"  {'PASS' if ok else 'FAIL'} {verdict:9s} best={best:6.2f} "
              f"margin={margin:5.2f} top={top_id[:60]}")
        if not ok:
            print(f"       expected top containing: {expected}")
    print("off-topic probes (must never be COVERED):")
    for query in OFF_TOPIC:
        verdict, top, best, margin, _matched = verdict_for(query, entries)
        ok = verdict != "COVERED"
        failures += 0 if ok else 1
        print(f"  {'PASS' if ok else 'FAIL'} {verdict:9s} best={best:6.2f} "
              f"margin={margin:5.2f} top={(top['id'][:60] if top else '-')}"
              f"  query={query!r}")
    print(f"{'ALL PASS' if failures == 0 else f'{failures} FAILURE(S)'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
