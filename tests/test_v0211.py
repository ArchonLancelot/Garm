"""v0.2.11: field-test fix batch (LMArena Agent Mode dogfood, 2026-10-28).

Covers: `garm version` / `--version`, recall `--min-score` (default 1.0,
matching the hook) with stdout silence below threshold and the appended
actionable section, the TTY guard hole (--task + closed stdin), the
--answers draft-before-saving print, premise attach + kill reporting,
the 500-char confirm-note cap, word-boundary slug truncation, the
DOSSIER_SPEC formula, optional-extra test skips (see test_semantic.py),
the export count split, and the widened `list` task column.
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
from garm import premise as PR  # noqa: E402


def garm(*args, cwd, stdin=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "garm", *args],
        cwd=cwd, capture_output=True, text=True, env=env, stdin=stdin,
    )


SECTIONS = {
    "what was tried": "Did A, then B.",
    "root cause": "C.",
    "failure signature": "sig-key: flaky checkout race parallel workers.",
    "blocking constraint": "D.",
    "what retrieval would have changed": "Skip the retry loop; bisect first.",
    "confidence": "High.",
}


def make_dossier(tmpdir, filename, task, sections=None):
    d = Path(tmpdir) / "dossiers"
    d.mkdir(exist_ok=True)
    text = D.render_template(task=task, agent="claude-code",
                             failure_class="reasoning-error",
                             sections=sections or dict(SECTIONS))
    p = d / filename
    p.write_text(text, encoding="utf-8")
    return p


def dossier_id(path: Path) -> str:
    return D.split_frontmatter(path.read_text(encoding="utf-8"))[0]["id"]


class VersionTest(unittest.TestCase):
    def test_version_subcommand(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("version", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "garm 0.2.11")

    def test_version_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("--version", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "garm 0.2.11")


class RecallThresholdTest(unittest.TestCase):
    def _bank(self, tmp):
        make_dossier(tmp, "a.md", "Flaky checkout race in parallel workers")
        r = garm("index", "--dir", "dossiers", cwd=tmp)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_nonsense_query_prints_nothing_on_stdout(self):
        # The field test's "xyzzy plugh quux" case: a 0.00 "hit" is noise.
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("recall", "--task", "xyzzy plugh quux",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")
            self.assertIn("min-score", r.stderr)

    def test_weak_hit_suppressed_by_default_shown_with_zero(self):
        # Single-doc corpus: "alpha gamma" scores ~0.58, below default.
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "a.md", "Task alpha gamma",
                         sections={
                             "what was tried": "Did A.",
                             "root cause": "C.",
                             "failure signature": "sig-key: unrelated.",
                             "blocking constraint": "D.",
                             "what retrieval would have changed": "E.",
                             "confidence": "High.",
                         })
            r = garm("recall", "--task", "alpha gamma",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")
            r = garm("recall", "--task", "alpha gamma",
                     "--dir", "dossiers", "--min-score", "0", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("alpha gamma", r.stdout)

    def test_strong_hit_shows_and_appends_actionable_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("recall", "--task",
                     "flaky checkout race parallel workers",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Flaky checkout race", r.stdout)
            self.assertIn("What retrieval would have changed",
                          r.stdout)
            self.assertIn("Skip the retry loop; bisect first.", r.stdout)

    def test_explicit_min_score_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank(tmp)
            r = garm("recall", "--task",
                     "flaky checkout race parallel workers",
                     "--dir", "dossiers", "--min-score", "999", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")


class TtyGuardTest(unittest.TestCase):
    def test_task_plus_closed_stdin_refuses_without_writing(self):
        # v0.2.11: the old guard only covered the no---task case; --task
        # + closed stdin printed every question and left a bare scaffold.
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("autopsy", "--task", "Flaky checkout race",
                     "--agent", "test-agent", "--class", "reasoning-error",
                     "--dir", "dossiers", cwd=tmp,
                     stdin=subprocess.DEVNULL)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("terminal", r.stderr)
            self.assertFalse((Path(tmp) / "dossiers").exists())

    def test_no_task_plus_closed_stdin_still_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("autopsy", "--dir", "dossiers", cwd=tmp,
                     stdin=subprocess.DEVNULL)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("terminal", r.stderr)
            self.assertFalse((Path(tmp) / "dossiers").exists())


class AnswersDraftTest(unittest.TestCase):
    def test_answers_prints_draft_before_saving(self):
        with tempfile.TemporaryDirectory() as tmp:
            answers = {
                "task": "Flaky checkout race",
                "agent": "test-agent",
                "failure_class": "reasoning-error",
                "outcome": "failed",
                "what_was_tried": ["Tried A, then B."],
                "root_cause": "The race.",
                "failure_signature": "sig: checkout race.",
                "blocking_constraint": "No lock.",
                "what_retrieval_would_have_changed": "Check lock first.",
                "confidence": "High.",
            }
            apath = Path(tmp) / "answers.json"
            apath.write_text(json.dumps(answers), encoding="utf-8")
            r = garm("autopsy", "--answers", str(apath),
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("--- draft ---", r.stdout)
            self.assertIn("The race.", r.stdout)
            self.assertIn("draft:", r.stdout)
            written = list((Path(tmp) / "dossiers").glob("*.md"))
            self.assertEqual(len(written), 1)
            self.assertIn("The race.", written[0].read_text(encoding="utf-8"))


class PremiseAttachTest(unittest.TestCase):
    def test_attach_kill_reports_and_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "a.md", "Task one")
            did = dossier_id(p)
            r = garm("premise", "add", "--statement", "Trunk holds",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            import re
            pid = re.search(r"P-\d{8}-\d{3}", r.stdout).group(0)
            # Kill with nothing attached: must warn, not silently succeed.
            r = garm("premise", "kill", pid, "--by", did,
                     "--evidence", "our-tests", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("declares this premise: 0", r.stdout)
            self.assertIn("warning: no dossier declares", r.stderr)
            # Reopen, attach, kill again: now it must report the link.
            r = garm("premise", "reopen", pid, "--by", "test",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = garm("premise", "attach", pid, "--dossier", did,
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("attached:", r.stdout)
            text = p.read_text(encoding="utf-8")
            self.assertIn("## Premises", text)
            self.assertIn(pid, text)
            self.assertEqual(D.validate_dossier(p), [])
            # Re-attach is a no-op that says so.
            r = garm("premise", "attach", pid, "--dossier", did,
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("already attached", r.stdout)
            r = garm("premise", "kill", pid, "--by", "test-note",
                     "--evidence", "our-tests", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("declares this premise: 1", r.stdout)
            self.assertIn("dead routes now: 1", r.stdout)
            self.assertNotIn("warning: no dossier declares", r.stderr)

    def test_attach_rejects_unknown_premise_and_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "a.md", "Task one")
            r = garm("premise", "attach", "P-20260101-001",
                     "--dossier", "no-such-dossier",
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("unknown premise", r.stderr)

    def test_autopsy_asks_for_premises(self):
        # The interactive interview must offer the premises question so
        # dossiers can declare premises at birth (field test claimed it
        # never asks — it does; this guards the question).
        from garm import autopsy as AU
        keys = [q["key"] for q in AU.QUESTIONS]
        self.assertIn("premises", keys)
        q = [q for q in AU.QUESTIONS if q["key"] == "premises"][0]
        self.assertIn("premise", q["prompt"].lower())


class ConfirmNoteCapTest(unittest.TestCase):
    def test_500_char_note_ok_501_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "a.md", "Task one")
            did = dossier_id(p)
            r = garm("confirm", did, "--note", "x" * 501,
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("max is 500", r.stderr)
            r = garm("confirm", did, "--note", "x" * 500,
                     "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)


class SlugBoundaryTest(unittest.TestCase):
    def test_no_mid_word_cut(self):
        # The field test's id ended in "for-a": the cut landed mid-word.
        slug = D.slugify(
            "implement dst correct next fire computation for a scheduler")
        self.assertEqual(
            slug, "implement-dst-correct-next-fire-computation-for-a")
        # Cut landing mid-word backs up to the last complete word.
        slug2 = D.slugify(
            "one two three four five six seven eight nine ten eleven "
            "twelve")
        self.assertEqual(
            slug2, "one-two-three-four-five-six-seven-eight-nine-ten")
        # A single word longer than the cap still hard-cuts.
        self.assertEqual(D.slugify("x" * 60), "x" * 50)
        # Short slugs unchanged.
        self.assertEqual(D.slugify("short task"), "short-task")


class SpecFormulaTest(unittest.TestCase):
    def test_spec_documents_body_lane_and_threshold(self):
        text = (ROOT / "DOSSIER_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("body_keywords", text)
        self.assertIn("2 × BM25(query, sig_keywords)", text)
        self.assertIn("min-score", text)


class ExportCountTest(unittest.TestCase):
    def test_premises_file_not_counted_as_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "a.md", "Task one")
            make_dossier(tmp, "b.md", "Task two")
            PR.add_premise(Path(tmp) / "dossiers", "Trunk holds",
                           created="2026-10-28")
            out = str(Path(tmp) / "bank")
            r = garm("export", "--dir", "dossiers", "-o", out, cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("exported 2 dossiers, 1 premises file(s)", r.stdout)
            self.assertNotIn("exported 3 dossiers", r.stdout)


class ListWidthTest(unittest.TestCase):
    def test_long_task_not_truncated_at_40(self):
        long_task = ("Fix flaky checkout total race condition in parallel "
                     "test workers today")
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "a.md", long_task)
            r = garm("list", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(long_task, r.stdout)


if __name__ == "__main__":
    unittest.main()
