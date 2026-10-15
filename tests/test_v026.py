"""v0.2.6: hybrid retrieval — symbol canonicalization + synonym aliases.

Covers: canonicalize_text (Greek, superscripts/subscripts, operators),
extract_keywords sharing tokens across notations ("χ(G)" vs "chromatic"),
alias matching in recall (paraphrase query finds the dossier, shown as
``query~dossier-term``), exact matches still preferred and scored
identically to before, plurals, no false positives from unrelated words,
deterministic alias picks, index rebuild determinism, CLI end-to-end,
and the MCP matched_terms display.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from garm import dossier as D  # noqa: E402
from garm import retrieval as RU  # noqa: E402


def garm(*args, cwd):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "garm", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def make_bank(tmp, dossiers):
    """dossiers: list of (task, signature, extra_sections). Returns bank dir."""
    bank = Path(tmp) / "bank"
    bank.mkdir(parents=True, exist_ok=True)
    for i, (task, signature, extra) in enumerate(dossiers):
        sections = {
            "what was tried": f"Tried thing {i}.",
            "root cause": f"Cause {i}.",
            "failure signature": signature,
            "blocking constraint": f"Constraint {i}.",
            "what retrieval would have changed": f"Change {i}.",
            "confidence": "High.",
        }
        sections.update(extra or {})
        text = D.render_template(
            task=task, agent="test-agent", failure_class="reasoning-error",
            sections=sections, id_=f"2026-10-12-dossier-{i:02d}",
            created="2026-10-12",
        )
        (bank / f"dossier-{i:02d}.md").write_text(text, encoding="utf-8")
    return bank


class CanonicalizationTest(unittest.TestCase):
    def test_greek_letters_become_names(self):
        self.assertIn("chi", D.extract_keywords("χ(G) = 10"))
        self.assertIn("chromatic",
                      D.extract_keywords("the chromatic number is 10"))
        self.assertIn("lambda", D.extract_keywords("λ-calculus"))
        self.assertIn("pi", D.extract_keywords("π ≈ 3.14"))

    def test_superscript_subscript_digits(self):
        # glued onto the preceding word char so the token survives
        kw = D.extract_keywords("x² + y² = r²")
        self.assertIn("x2", kw)
        self.assertIn("y2", kw)
        self.assertIn("r2", kw)
        kw = D.extract_keywords("C₇[K₄]")
        self.assertIn("c7", kw)
        self.assertIn("k4", kw)
        # standalone digits are still noise
        self.assertNotIn("2", D.extract_keywords("²"))
        # multi-digit runs glue as a whole
        self.assertIn("1012", D.extract_keywords("10¹²"))

    def test_operators_become_words(self):
        kw = D.extract_keywords("∑_{i=1}^n i = n(n+1)/2")
        self.assertIn("sum", kw)
        kw = D.extract_keywords("A ∪ B vs A ∩ B")
        self.assertIn("union", kw)
        self.assertIn("intersection", kw)

    def test_prime_marks(self):
        kw = D.extract_keywords("p′ is prime")
        self.assertIn("prime", kw)

    def test_plain_text_unchanged(self):
        # canonicalization must not disturb ordinary prose
        self.assertEqual(
            D.extract_keywords("the quick brown fox"),
            ["quick", "brown", "fox"],
        )

    def test_canonicalize_is_deterministic(self):
        text = "χ(G) ≤ 10 → ∑ x² ∈ ∅"
        self.assertEqual(RU.canonicalize_text(text),
                         RU.canonicalize_text(text))


class AliasMatchingTest(unittest.TestCase):
    def test_paraphrase_query_finds_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "Fix checkout flakes",
                "intermittent-checkout: if the suite flakes under load, "
                "stop and pull this dossier.",
                None,
            )])
            entry = D.build_index_entry(
                bank / "dossier-00.md", bank, {"premises": {}})
            scores = RU.score_corpus(["flaky", "checkout"], [entry])
            total, sig_n, task_n, sem_n, _, _ = scores[entry["id"]]
            # flaky~intermittent and checkout, both in the signature:
            # BM25 subscores are positive floats, sig outweighs task here
            self.assertGreater(sig_n, 0)
            self.assertEqual(task_n, 0)
            self.assertGreater(total, 0)
            shown = RU.matched_terms(["flaky", "checkout"], entry)
            self.assertIn("flaky~intermittent", shown)
            self.assertIn("checkout", shown)

    def test_exact_match_preferred_over_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "Fix checkout flakes",
                "flaky-checkout: intermittent failures under load; "
                "stop and pull this.",
                None,
            )])
            entry = D.build_index_entry(
                bank / "dossier-00.md", bank, {"premises": {}})
            shown = RU.matched_terms(["flaky"], entry)
            self.assertEqual(shown, ["flaky"])

    def test_plurals_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "Prime search",
                "prime-sieve: if the sieve misses a prime, stop.",
                None,
            )])
            entry = D.build_index_entry(
                bank / "dossier-00.md", bank, {"premises": {}})
            scores = RU.score_corpus(["primes"], [entry])
            total, sig_n, _, sem_n, _, _ = scores[entry["id"]]
            self.assertGreater(sig_n, 0)
            self.assertGreater(total, 0)

    def test_math_paraphrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "Color the graph",
                "chromatic-blowup: if coloring needs more colors than "
                "vertices allow, stop.",
                None,
            )])
            entry = D.build_index_entry(
                bank / "dossier-00.md", bank, {"premises": {}})
            # "χ(G)" canonicalizes to chi; chi ~ chromatic via aliases
            scores = RU.score_corpus(
                D.extract_keywords("χ(G) needs too many colors"), [entry])
            total, sig_n, _, sem_n, _, _ = scores[entry["id"]]
            self.assertGreater(sig_n, 0, "chi should alias to chromatic")
            self.assertGreater(total, 0)

    def test_no_false_positives(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "Fix checkout flakes",
                "intermittent-checkout: flakes under load.",
                None,
            )])
            entry = D.build_index_entry(
                bank / "dossier-00.md", bank, {"premises": {}})
            scores = RU.score_corpus(["banana", "xylophone"], [entry])
            total, sig_n, task_n, sem_n, _, _ = scores[entry["id"]]
            self.assertEqual((total, sig_n, task_n), (0, 0, 0))
            self.assertEqual(RU.matched_terms(["banana"], entry), [])

    def test_alias_pick_is_deterministic(self):
        entry = {"keywords": ["intermittent", "sporadic"],
                 "sig_keywords": ["intermittent"]}
        first = RU.find_match("flaky", entry["keywords"])
        for _ in range(10):
            self.assertEqual(RU.find_match("flaky", entry["keywords"]),
                             first)

    def test_unknown_word_matches_only_itself(self):
        self.assertEqual(RU.aliases_for("wieferich"), {"wieferich"})
        self.assertIn("intermittent", RU.aliases_for("flaky"))

    def test_scoring_shape_bm25(self):
        # BM25 shape: 2*sig + 1*task + confirms (capped at 5).
        # A second dossier sharing the query terms dilutes IDF, so the
        # assertions below use one corpus and check structure, not values.
        entry = {
            "id": "d1",
            "keywords": ["alpha", "beta"],
            "sig_keywords": ["alpha"],
            "confirmed_fixes": 7,
            "confirmed_insights": 2,
        }
        scores = RU.score_corpus(["alpha", "beta"], [entry])
        total, sig_n, task_n, sem_n, fix_b, ins_b = scores["d1"]
        self.assertEqual((fix_b, ins_b), (5, 2))
        # sig counts double: removing the sig term drops more than removing
        # the task term
        no_sig = RU.score_corpus(["beta"], [entry])["d1"][0]
        no_task = RU.score_corpus(["alpha"], [entry])["d1"][0]
        self.assertGreater(no_task, no_sig)
        self.assertAlmostEqual(total, 2 * sig_n + task_n + 5 + 2)


class HybridRecallEndToEndTest(unittest.TestCase):
    def test_cli_shows_alias_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "Fix checkout flakes",
                "intermittent-checkout: if the suite flakes under load, "
                "stop and pull this dossier.",
                None,
            )])
            r = garm("recall", "--task", "flaky checkout failure",
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("flaky~intermittent", r.stdout)

    def test_cli_exact_still_ranks_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [
                ("Unrelated docs task",
                 "docs-typo: if prose has a typo, fix it.",
                 None),
                ("Fix checkout flakes",
                 "intermittent-checkout: flakes under load.",
                 None),
            ])
            r = garm("recall", "--task", "intermittent checkout flakes",
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [ln for ln in r.stdout.splitlines() if "|" in ln]
            self.assertIn("dossier-01", lines[0],
                          "exact+alias dossier must outrank the unrelated one")

    def test_index_rebuild_stays_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "χ(G) coloring",
                "chromatic-blowup: χ(G) exceeds the bound; stop.",
                None,
            )])
            r1 = garm("index", "--dir", str(bank), cwd=tmp)
            first = (bank / "index.jsonl").read_bytes()
            r2 = garm("index", "--dir", str(bank), cwd=tmp)
            self.assertEqual(r1.returncode, 0)
            self.assertEqual(r2.returncode, 0)
            self.assertEqual(first, (bank / "index.jsonl").read_bytes())


class BM25Test(unittest.TestCase):
    def test_idf_weights_rare_terms_above_common_ones(self):
        docs = [Counter(["one", "test"]), Counter(["one", "test"]),
                Counter(["one", "test"]), Counter(["zwitterion"])]
        scores = RU.BM25(docs).score_many(
            [frozenset({"one"}), frozenset({"test"}),
             frozenset({"zwitterion"})])
        # the rare-term doc outscores the common-term docs despite
        # matching fewer query terms overall
        self.assertGreater(scores[3], scores[0])
        self.assertGreater(scores[3], scores[1])
        self.assertGreater(scores[3], scores[2])

    def test_common_word_noise_does_not_outrank_distinctive_match(self):
        # Regression for the 2026-10-14 transfer test: a paraphrase query
        # whose only shared word was "one" ranked BPSW noise above the
        # relevant dossier. Under BM25, "one" appears in most dossiers so
        # it barely counts; the distinctive term decides.
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [
                ("Unrelated task words here",
                 "base-one-check: if one base test fails, stop and pull.",
                 None),
                ("Unrelated task words here",
                 "prime-one-check: if one prime test fails, stop and pull.",
                 None),
                ("Unrelated task words here",
                 "sieve-one-check: if one sieve test fails, stop and pull.",
                 None),
                ("Unrelated task words here",
                 "zwitterion-trap: zwitterion handling collapses; stop.",
                 None),
            ])
            entries = [
                D.build_index_entry(bank / f"dossier-{i:02d}.md", bank,
                                    {"premises": {}})
                for i in range(4)
            ]
            scores = RU.score_corpus(["one", "test", "zwitterion"], entries)
            ranked = sorted(scores, key=lambda i: -scores[i][0])
            self.assertEqual(ranked[0], entries[3]["id"],
                             "distinctive-term dossier must outrank "
                             "\"one\"-matching noise")

    def test_cli_ranks_distinctive_match_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [
                ("Unrelated task words here",
                 "base-one-check: if one base test fails, stop and pull.",
                 None),
                ("Unrelated task words here",
                 "prime-one-check: if one prime test fails, stop and pull.",
                 None),
                ("Unrelated task words here",
                 "sieve-one-check: if one sieve test fails, stop and pull.",
                 None),
                ("Unrelated task words here",
                 "zwitterion-trap: zwitterion handling collapses; stop.",
                 None),
            ])
            r = garm("recall", "--task", "one test zwitterion",
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [ln for ln in r.stdout.splitlines() if "|" in ln]
            self.assertIn("dossier-03", lines[0])

    def test_known_score_regression_anchor(self):
        # the v0.2.5 Chernick drill dossier: under BM25 it must still
        # rank first for its query (the old integer anchor of 7 no longer
        # applies — BM25 weights by rarity instead of counting)
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [(
                "Sweep Chernick Carmichael numbers through the strong "
                "Lucas test",
                "chernick-lucas-sweep: if a parametric family passes "
                "Korselt but dies on Lucas, stop generating more of the "
                "family and pull this dossier.",
                None,
            )])
            r = garm("recall",
                     "--task", "chernick carmichael lucas pseudoprime sweep",
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            first = r.stdout.splitlines()[0]
            self.assertIn("dossier-00", first)


if __name__ == "__main__":
    unittest.main()
