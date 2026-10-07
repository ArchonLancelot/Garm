"""v0.2 behavior: failure_class, confirm, weighted recall, legacy v0.1."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from garm import dossier as D  # noqa: E402


def garm(*args, cwd):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "garm", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


SECTIONS = {
    "what was tried": "Did A, then B.",
    "root cause": "C.",
    "failure signature": "sig-key: some distinctive signature words here.",
    "blocking constraint": "D.",
    "what retrieval would have changed": "E.",
    "confidence": "High.",
}


def make_dossier(tmpdir, filename, task, failure_class="reasoning-error",
                 signature=None):
    d = Path(tmpdir) / "dossiers"
    d.mkdir(exist_ok=True)
    sections = dict(SECTIONS)
    if signature is not None:
        sections["failure signature"] = signature
    text = D.render_template(task=task, agent="claude-code",
                             failure_class=failure_class, sections=sections)
    p = d / filename
    p.write_text(text, encoding="utf-8")
    return p


def dossier_id(path: Path) -> str:
    return D.split_frontmatter(path.read_text(encoding="utf-8"))[0]["id"]


class InitClassTest(unittest.TestCase):
    def test_init_requires_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("init", "--task", "T", "--agent", "a",
                        "-o", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 2, r.stderr)

    def test_init_rejects_bad_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("init", "--task", "T", "--agent", "a",
                        "--class", "vibes", "-o", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 2)
            self.assertIn("knowledge-gap", r.stderr)

    def test_init_scaffold_is_valid_v02(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("init", "--task", "Some task", "--agent", "claude-code",
                        "--class", "knowledge-gap", "-o", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            p = Path(tmp) / r.stdout.strip()
            fm = D.split_frontmatter(p.read_text(encoding="utf-8"))[0]
            self.assertEqual(fm["dossier_version"], "0.2")
            self.assertEqual(fm["failure_class"], "knowledge-gap")
            self.assertEqual(fm["confirmed_fixes"], "0")
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class ValidateV02Test(unittest.TestCase):
    def test_rejects_bad_failure_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "d.md", "Task one")
            text = p.read_text(encoding="utf-8").replace(
                "failure_class: reasoning-error", "failure_class: vibes")
            p.write_text(text, encoding="utf-8")
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("failure_class", r.stdout)

    def test_rejects_negative_confirmed_fixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "d.md", "Task one")
            text = p.read_text(encoding="utf-8").replace(
                "confirmed_fixes: 0", "confirmed_fixes: -1")
            p.write_text(text, encoding="utf-8")
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("confirmed_fixes", r.stdout)

    def test_rejects_missing_failure_class_on_v02(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "d.md", "Task one")
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines()
                     if not ln.startswith("failure_class:")]
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("failure_class", r.stdout)

    def test_legacy_v01_still_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "d.md", "Task one")
            lines = []
            for ln in p.read_text(encoding="utf-8").splitlines():
                if ln.startswith("failure_class:") or ln.startswith("confirmed_fixes:"):
                    continue
                if ln.startswith('dossier_version:'):
                    ln = 'dossier_version: "0.1"'
                lines.append(ln)
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("OK", r.stdout)
            self.assertIn("legacy", r.stderr.lower())

    def test_render_template_rejects_bad_class(self):
        with self.assertRaises(ValueError):
            D.render_template(task="T", agent="a", failure_class="nope",
                              sections=SECTIONS)


class ConfirmTest(unittest.TestCase):
    def test_confirm_increments_and_stays_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "d.md", "Task one")
            did = dossier_id(p)
            r = garm("confirm", did, "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("confirmed fixes: 1", r.stdout)
            r = garm("confirm", did, "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("confirmed fixes: 2", r.stdout)
            text = p.read_text(encoding="utf-8")
            self.assertIn("confirmed_fixes: 2", text)
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            # index picks up the new count
            r = garm("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            entries = D.load_index_entries(Path(tmp) / "dossiers" / "index.jsonl")
            self.assertEqual(entries[0]["confirmed_fixes"], 2)

    def test_confirm_unknown_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "d.md", "Task one")
            r = garm("confirm", "no-such-id", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("no dossier", r.stderr)

    def test_confirm_duplicate_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "a.md", "Task one")
            (Path(tmp) / "dossiers" / "b.md").write_text(
                p.read_text(encoding="utf-8"), encoding="utf-8")
            r = garm("confirm", dossier_id(p), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("multiple", r.stderr)


class RecallV02Test(unittest.TestCase):
    def test_signature_overlap_outranks_task_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "a.md", "widgets deployment pipeline",
                         signature="sig-key: checkout flaky race parallel workers.")
            make_dossier(tmp, "b.md", "checkout flaky race parallel workers investigation",
                         signature="sig-key: unrelated widgets deployment habits.")
            r = garm("recall", "--task", "checkout flaky race parallel workers",
                        "--dir", "dossiers", "--top", "2", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
            self.assertIn(dossier_id(Path(tmp) / "dossiers" / "a.md"), lines[0])
            self.assertIn("sig:5", lines[0])

    def test_confirmed_dossier_wins_ties(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = make_dossier(tmp, "a.md", "widgets deploy")
            make_dossier(tmp, "b.md", "the widgets deploy")
            r = garm("confirm", dossier_id(a), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = garm("recall", "--task", "widgets deploy",
                        "--dir", "dossiers", "--top", "2", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
            self.assertIn(dossier_id(a), lines[0])
            self.assertIn("confirmed:1", lines[0])

    def test_class_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "a.md", "Task alpha gamma", failure_class="knowledge-gap")
            make_dossier(tmp, "b.md", "Task alpha gamma delta", failure_class="reasoning-error")
            r = garm("recall", "--task", "alpha gamma", "--class", "knowledge-gap",
                        "--dir", "dossiers", "--top", "5", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
            self.assertEqual(len(lines), 1)
            self.assertIn(dossier_id(Path(tmp) / "dossiers" / "a.md"), lines[0])


class IndexV02Test(unittest.TestCase):
    def test_index_carries_new_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_dossier(tmp, "d.md", "Task one", failure_class="tool-misuse")
            r = garm("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            entries = D.load_index_entries(Path(tmp) / "dossiers" / "index.jsonl")
            self.assertEqual(len(entries), 1)
            e = entries[0]
            for key in ("version", "failure_class", "confirmed_fixes",
                        "sig_keywords", "keywords", "id", "task"):
                self.assertIn(key, e)
            self.assertEqual(e["version"], "0.2")
            self.assertEqual(e["failure_class"], "tool-misuse")
            self.assertEqual(e["confirmed_fixes"], 0)
            self.assertIn("distinctive", e["sig_keywords"])


class ListV02Test(unittest.TestCase):
    def test_list_shows_class_and_fixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = make_dossier(tmp, "d.md", "Task one", failure_class="knowledge-gap")
            r = garm("confirm", dossier_id(p), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = garm("list", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("knowledge-gap", r.stdout)
            header, row = r.stdout.splitlines()[0], r.stdout.splitlines()[1]
            self.assertIn("CLASS", header)
            self.assertIn("FIX", header)
            self.assertIn("1", row.split()[2])


if __name__ == "__main__":
    unittest.main()
