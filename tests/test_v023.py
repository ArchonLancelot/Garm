"""v0.2.3: scaffold rejection, import dedupe, confirm auto-index,
recall column docs, single version source."""

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


FILLED = {
    "what was tried": "Did A, then B.",
    "root cause": "C was the actual cause.",
    "failure signature": "Name: some-pattern. If you see X, stop.",
    "blocking constraint": "D blocked it.",
    "challengeable premises": "Premise 1: X holds. Premise 2: Y holds.",
    "what retrieval would have changed": "E instead.",
    "open questions": "Is there a Q?",
    "tokens": "not estimated.",
    "confidence": "High.",
}


def write_dossier(tmpdir, dirname, filename, sections):
    d = Path(tmpdir) / dirname
    d.mkdir(parents=True, exist_ok=True)
    text = D.render_template(
        task="Some task", agent="claude-code",
        failure_class="reasoning-error", sections=sections,
    )
    p = d / filename
    p.write_text(text, encoding="utf-8")
    return p


def dossier_id(path: Path) -> str:
    return D.split_frontmatter(path.read_text(encoding="utf-8"))[0]["id"]


class ScaffoldRejectionTest(unittest.TestCase):
    def test_filled_dossier_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_dossier(tmp, "dossiers", "d.md", FILLED)
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_partially_filled_scaffold_rejected(self):
        partial = dict(FILLED)
        del partial["root cause"]  # falls back to placeholder guidance
        with tempfile.TemporaryDirectory() as tmp:
            p = write_dossier(tmp, "dossiers", "d.md", partial)
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("root cause", r.stdout)
            self.assertNotIn("what was tried", r.stdout)

    def test_optional_section_placeholder_allowed(self):
        # Decided behavior: optional sections are exempt from the
        # placeholder rule (they may simply be deleted). Only required
        # sections left as placeholder fail.
        partial = dict(FILLED)
        del partial["tokens"]
        with tempfile.TemporaryDirectory() as tmp:
            p = write_dossier(tmp, "dossiers", "d.md", partial)
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_repo_example_dossiers_validate(self):
        for md in sorted((ROOT / "dossiers" / "examples").glob("*.md")):
            self.assertEqual(D.validate_dossier(md), [],
                             f"{md.name} should validate")


class ImportDedupeTest(unittest.TestCase):
    def test_reimport_identical_bank_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "a.md").write_text(
                D.render_template(task="Task A", agent="alice",
                                  failure_class="knowledge-gap",
                                  sections=dict(FILLED)),
                encoding="utf-8")
            r = garm("import", str(src), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("imported:", r.stdout)
            before = sorted((Path(tmp) / "dossiers").glob("*.md"))
            r = garm("import", str(src), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("already in bank (identical content)", r.stderr)
            after = sorted((Path(tmp) / "dossiers").glob("*.md"))
            self.assertEqual(before, after)

    def test_modified_collision_still_renamed(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            p = write_dossier(tmp, "src", "a.md", FILLED)
            local_id = dossier_id(p)
            r = garm("import", str(src), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            # same id, different content -> must rename, not skip
            text = p.read_text(encoding="utf-8").replace(
                "Did A, then B.", "Did something completely different.")
            (src / "b.md").write_text(text, encoding="utf-8")
            (src / "a.md").unlink()
            r = garm("import", str(src), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("renamed", r.stdout)
            self.assertNotIn("identical content", r.stderr)


class ConfirmAutoIndexTest(unittest.TestCase):
    def test_confirm_rebuilds_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_dossier(tmp, "dossiers", "d.md", FILLED)
            did = dossier_id(p)
            r = garm("confirm", did, "--insight", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("indexed", r.stdout)
            import json
            entries = [
                json.loads(ln)
                for ln in (Path(tmp) / "dossiers" / "index.jsonl")
                .read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["confirmed_insights"], 1)


class HelpDocsTest(unittest.TestCase):
    def test_recall_help_explains_columns(self):
        r = garm("recall", "--help", cwd=ROOT)
        self.assertEqual(r.returncode, 0)
        text = " ".join(r.stdout.lower().split())
        self.assertIn("worth 2 points", text)
        self.assertIn("1 point each", text)

    def test_top_help_shows_spec_version(self):
        r = garm("--help", cwd=ROOT)
        self.assertEqual(r.returncode, 0)
        self.assertIn(f"dossier spec v{D.SPEC_VERSION}", r.stdout)

    def test_init_help_notes_truncation_and_scaffold(self):
        r = garm("init", "--help", cwd=ROOT)
        self.assertEqual(r.returncode, 0)
        text = " ".join(r.stdout.lower().split())
        self.assertIn("truncated to 50 characters", text)
        self.assertIn("not a dossier", text)


if __name__ == "__main__":
    unittest.main()
