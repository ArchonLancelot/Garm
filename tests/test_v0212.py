"""v0.2.12: the coverage-gap batch (2026-11-10).

Covers: the per-query verdict (COVERED / THIN / UNCOVERED) on `garm
recall` with its calibrated margin gate, the uncovered-query log
(terms only, opt-out), the `garm coverage` bank view (per-class counts
including zeros, signature-term clusters, thin spots, ranked "file
next"), and the hook's explicit "checked, nothing relevant" line. The
margin threshold (5.0) was calibrated on the three shipped banks
(bpsw/earth-moon/imo): in-bank margins min 4.50, off-topic/generic
max 4.74 — 5.0 gives zero false COVERED on the measured set.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from garm import dossier as D  # noqa: E402
from garm import retrieval as RU  # noqa: E402


def garm(*args, cwd, env_extra=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "garm", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def make_dossier(tmpdir, filename, task, signature, failure_class,
                 body="The deploy test failed with an error."):
    d = Path(tmpdir) / "dossiers"
    d.mkdir(exist_ok=True)
    text = D.render_template(task=task, agent="test",
                             failure_class=failure_class, sections={
                                 "what was tried": "Did A, then B.",
                                 "root cause": body,
                                 "failure signature": signature,
                                 "blocking constraint": "D.",
                                 "what retrieval would have changed": "E.",
                                 "confidence": "High.",
                             })
    p = d / filename
    p.write_text(text, encoding="utf-8")
    return p


def _entry(eid, sig_keywords, keywords=(), body_keywords=()):
    return {"id": eid, "sig_keywords": list(sig_keywords),
            "keywords": list(keywords),
            "body_keywords": list(body_keywords)}


class VerdictUnitTest(unittest.TestCase):
    def test_covered_needs_signature_match_and_margin(self):
        top = _entry("a", ["lucas", "pseudoprime"],
                     ["lucas", "pseudoprime", "find"])
        second = _entry("b", ["sourdough"], ["sourdough"])
        verdict, top_e, best, margin, _ = RU.coverage_verdict(
            ["lucas", "pseudoprime"], [(20.0, top), (5.0, second)], 1.0)
        self.assertEqual(verdict, "COVERED")
        self.assertIs(top_e, top)
        self.assertEqual((best, margin), (20.0, 15.0))

    def test_thin_when_no_signature_match(self):
        # Top score is huge and the margin is real, but the match came
        # only from task/body words — the signature never matched.
        top = _entry("a", ["unrelated"], ["lucas", "pseudoprime"],
                     ["lucas"])
        second = _entry("b", ["sourdough"], ["sourdough"])
        verdict, _, _, _, _ = RU.coverage_verdict(
            ["lucas", "pseudoprime"], [(20.0, top), (5.0, second)], 1.0)
        self.assertEqual(verdict, "THIN")

    def test_thin_when_margin_is_zero(self):
        # Signature matched, but the runner-up is right behind it — the
        # bank can't tell the two apart, so the verdict stays weak.
        top = _entry("a", ["lucas"], ["lucas"])
        second = _entry("b", ["lucas"], ["lucas"])
        verdict, _, _, margin, _ = RU.coverage_verdict(
            ["lucas"], [(20.0, top), (19.5, second)], 1.0)
        self.assertEqual(verdict, "THIN")
        self.assertAlmostEqual(margin, 0.5)

    def test_margin_boundary_is_covered(self):
        top = _entry("a", ["lucas"], ["lucas"])
        second = _entry("b", ["sourdough"], ["sourdough"])
        verdict, _, _, _, _ = RU.coverage_verdict(
            ["lucas"], [(20.0, top), (15.0, second)], 1.0)
        self.assertEqual(verdict, "COVERED")

    def test_uncovered_below_threshold(self):
        top = _entry("a", ["lucas"], ["lucas"])
        verdict, top_e, best, _, matched = RU.coverage_verdict(
            ["xyzzy"], [(0.5, top)], 1.0)
        self.assertEqual(verdict, "UNCOVERED")
        self.assertIs(top_e, top)  # closest miss, for the verdict line
        self.assertEqual(best, 0.5)
        self.assertEqual(matched, [])

    def test_empty_ranked_is_uncovered_with_no_top(self):
        verdict, top_e, best, margin, matched = RU.coverage_verdict(
            ["lucas"], [], 1.0)
        self.assertEqual((verdict, top_e, best, margin, matched),
                         ("UNCOVERED", None, 0.0, 0.0, []))

    def test_semantic_mode_skips_the_margin_gate(self):
        # The margin is calibrated on BM25 totals; cosine totals live on
        # a different scale, so --semantic uses threshold + signature
        # only. A tiny margin must not downgrade a semantic hit.
        top = _entry("a", ["lucas"], ["lucas"])
        second = _entry("b", ["lucas"], ["lucas"])
        verdict, _, _, _, _ = RU.coverage_verdict(
            ["lucas"], [(2.9, top), (2.85, second)], 1.0, semantic=True)
        self.assertEqual(verdict, "COVERED")


class RecallVerdictTest(unittest.TestCase):
    def _bank(self, tmp):
        a = make_dossier(
            tmp, "a.md", "deploy widgets to staging",
            "flaky widget deploy retry loop staging lock timeout "
            "parallel workers",
            "reasoning-error")
        make_dossier(tmp, "b.md", "bake sourdough bread",
                     "sourdough starter feeding schedule",
                     "knowledge-gap")
        r = garm("index", "--dir", "dossiers", cwd=tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        return a

    def test_strong_signature_match_is_covered(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("recall", "--task",
                     "flaky widget deploy retry loop staging lock timeout "
                     "parallel workers",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("verdict: COVERED", r.stdout)
            self.assertIn("deploy widgets to staging", r.stdout)

    def test_generic_query_is_thin_not_covered(self):
        # "error failure test" matches only generic words (error~fail,
        # failure~fail, test) with no margin over the runner-up: served,
        # but flagged weak.
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("recall", "--task", "error failure test",
                     "--dir", "dossiers", "--min-score", "0.5", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("verdict: THIN", r.stdout)
            self.assertNotIn("verdict: COVERED", r.stdout)

    def test_uncovered_logs_terms_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("recall", "--task", "xyzzy plugh quux",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("verdict: UNCOVERED", r.stdout)
            log = Path(tmp) / "dossiers" / "coverage-log.jsonl"
            self.assertTrue(log.is_file())
            lines = log.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            rec = json.loads(lines[0])
            self.assertEqual(rec["terms"], ["xyzzy", "plugh", "quux"])
            self.assertEqual(rec["best"], 0.0)
            self.assertEqual(rec["matched"], [])
            self.assertTrue(rec["closest"])  # closest miss id, not empty
            self.assertIn("ts", rec)
            # No full prompt text anywhere in the log record.
            self.assertNotIn("prompt", rec)

    def test_uncovered_log_opt_outs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            d = Path(tmp) / "dossiers"
            r = garm("recall", "--task", "xyzzy plugh quux",
                     "--dir", "dossiers", "--no-coverage-log", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((d / "coverage-log.jsonl").exists())
            r = garm("recall", "--task", "xyzzy plugh quux",
                     "--dir", "dossiers", cwd=tmp,
                     env_extra={"GARM_NO_COVERAGE_LOG": "1"})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((d / "coverage-log.jsonl").exists())

    def test_covered_recall_does_not_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("recall", "--task",
                     "flaky widget deploy retry loop staging lock timeout "
                     "parallel workers",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(
                (Path(tmp) / "dossiers" / "coverage-log.jsonl").exists())


class CoverageCommandTest(unittest.TestCase):
    def _bank(self, tmp):
        a = make_dossier(
            tmp, "a.md", "deploy widgets to staging",
            "flaky widget deploy retry loop staging lock timeout "
            "parallel workers",
            "reasoning-error")
        make_dossier(tmp, "b.md", "bake sourdough bread",
                     "sourdough starter feeding schedule",
                     "knowledge-gap")
        return a

    def test_counts_include_zeros_and_thin_spots(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("coverage", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("reasoning-error: 1", r.stdout)
            self.assertIn("knowledge-gap: 1", r.stdout)
            self.assertIn("execution-slip: 0", r.stdout)
            self.assertIn("tool-misuse: 0", r.stdout)
            self.assertIn("misread-task: 0", r.stdout)
            self.assertIn("Signature-term clusters", r.stdout)
            self.assertIn("widget: 1", r.stdout)
            self.assertIn("Thin spots", r.stdout)
            self.assertIn("execution-slip: 0 dossiers", r.stdout)
            self.assertIn('signature term "flaky" appears in 1 dossier',
                          r.stdout)
            self.assertIn("(+4 more singleton terms)", r.stdout)

    def test_file_next_ranks_from_the_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            d = Path(tmp) / "dossiers"
            # Seed the log the way an UNCOVERED recall would: one query
            # rhyming with the widget signature, one rhyming with nothing.
            with open(d / "coverage-log.jsonl", "w",
                      encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": "2026-11-10T00:00:00+00:00",
                                     "terms": ["widget", "flaky"],
                                     "best": 0.0, "closest": "x",
                                     "matched": []}) + "\n")
                fh.write(json.dumps({"ts": "2026-11-10T00:00:00+00:00",
                                     "terms": ["xyzzy"],
                                     "best": 0.0, "closest": "x",
                                     "matched": []}) + "\n")
            r = garm("coverage", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("from 2 uncovered queries", r.stdout)
            self.assertIn('"widget": 1 uncovered query rhymed with it',
                          r.stdout)
            self.assertIn('"flaky": 1 uncovered query rhymed with it',
                          r.stdout)

    def test_clear_empties_the_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            d = Path(tmp) / "dossiers"
            log = d / "coverage-log.jsonl"
            log.write_text('{"terms": ["xyzzy"]}\n{"terms": ["plugh"]}\n',
                           encoding="utf-8")
            r = garm("coverage", "--dir", "dossiers", "--clear", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("cleared 2 logged uncovered queries", r.stdout)
            self.assertFalse(log.exists())
            r = garm("coverage", "--dir", "dossiers", "--clear", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("cleared 0 logged uncovered queries", r.stdout)

    def test_empty_bank_still_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "dossiers").mkdir()
            r = garm("coverage", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("0 dossiers", r.stdout)
            for cls in ("knowledge-gap", "reasoning-error",
                        "execution-slip", "tool-misuse", "misread-task"):
                self.assertIn(f"{cls}: 0", r.stdout)

    def test_missing_dir_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("coverage", "--dir", "nope", cwd=tmp)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("directory not found", r.stderr)


if __name__ == "__main__":
    unittest.main()
