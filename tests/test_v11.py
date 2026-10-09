"""v1.1 behavior: origin provenance, import/export of shared banks."""

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


def make_bank(tmpdir, dirname, tasks, agent="claude-code"):
    """Build a foreign bank dir with one dossier per task. Returns the dir."""
    d = Path(tmpdir) / dirname
    d.mkdir(parents=True, exist_ok=True)
    for i, task in enumerate(tasks):
        text = D.render_template(task=task, agent=agent,
                                 failure_class="reasoning-error",
                                 sections=dict(SECTIONS))
        (d / f"d{i}.md").write_text(text, encoding="utf-8")
    return d


def dossier_id(path: Path) -> str:
    return D.split_frontmatter(path.read_text(encoding="utf-8"))[0]["id"]


class OriginTest(unittest.TestCase):
    def test_origin_defaults_to_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_bank(tmp, "dossiers", ["alpha task"])
            p = next(d.glob("*.md"))
            fm = D.read_dossier(p)["frontmatter"]
            self.assertNotIn("origin", fm)
            self.assertEqual(D._origin_of(fm), "claude-code")
            r = garm("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            entries = D.load_index_entries(Path(tmp) / "dossiers" / "index.jsonl")
            self.assertEqual(entries[0]["origin"], "claude-code")

    def test_explicit_origin_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_bank(tmp, "dossiers", ["alpha task"])
            p = next(d.glob("*.md"))
            text = p.read_text(encoding="utf-8").replace(
                "confirmed_insights: 0",
                "confirmed_insights: 0\norigin: alice-bank")
            p.write_text(text, encoding="utf-8")
            self.assertEqual(garm("validate", str(p), cwd=tmp).returncode, 0)
            fm = D.read_dossier(p)["frontmatter"]
            self.assertEqual(D._origin_of(fm), "alice-bank")

    def test_recall_shows_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_bank(tmp, "dossiers", ["deploy widgets"])
            r = garm("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = garm("recall", "--task", "deploy widgets",
                     "--dir", "dossiers", "--top", "1", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("from:claude-code", r.stdout)


class ImportTest(unittest.TestCase):
    def test_import_copies_and_reindexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_bank(tmp, "dossiers", ["local task"])
            foreign = make_bank(tmp, "foreign", ["remote widgets task"],
                                agent="alice")
            r = garm("import", str(foreign), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("imported:", r.stdout)
            self.assertIn("indexed 2 dossiers", r.stdout)
            # imported dossier is recallable with provenance
            r = garm("recall", "--task", "remote widgets",
                     "--dir", "dossiers", "--top", "1", cwd=tmp)
            self.assertIn("from:alice", r.stdout)

    def test_import_collision_renames_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_d = make_bank(tmp, "dossiers", ["same task"])
            local_p = next(local_d.glob("*.md"))
            local_id = dossier_id(local_p)
            local_text = local_p.read_text(encoding="utf-8")

            foreign = Path(tmp) / "foreign"
            foreign.mkdir()
            # craft a foreign dossier with the SAME id but different content
            import re as _re
            text = D.render_template(task="same task", agent="alice",
                                     failure_class="knowledge-gap",
                                     sections=dict(SECTIONS))
            text = _re.sub(r"^id: [a-z0-9][a-z0-9-]*", f"id: {local_id}",
                           text, count=1, flags=_re.MULTILINE)
            (foreign / "dup.md").write_text(text, encoding="utf-8")

            r = garm("import", str(foreign), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("renamed", r.stdout)
            # original untouched
            self.assertEqual(local_p.read_text(encoding="utf-8"), local_text)
            # renamed copy validates and has the new id
            renamed = [p for p in local_d.glob("*.md") if p != local_p]
            self.assertEqual(len(renamed), 1)
            new_id = dossier_id(renamed[0])
            self.assertTrue(new_id.startswith(local_id + "--from-alice"),
                            new_id)
            self.assertEqual(
                garm("validate", str(renamed[0]), cwd=tmp).returncode, 0)

    def test_import_skips_invalid_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_bank(tmp, "dossiers", ["local task"])
            foreign = Path(tmp) / "foreign"
            foreign.mkdir()
            (foreign / "bad.md").write_text("no frontmatter here\n", encoding="utf-8")
            (foreign / "good.md").write_text(
                D.render_template(task="good remote task", agent="bob",
                                  failure_class="tool-misuse",
                                  sections=dict(SECTIONS)),
                encoding="utf-8")
            r = garm("import", str(foreign), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("skipped: bad.md", r.stderr)
            self.assertIn("imported:", r.stdout)
            self.assertIn("indexed 2 dossiers", r.stdout)

    def test_import_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_bank(tmp, "dossiers", ["local task"])
            foreign = make_bank(tmp, "foreign", ["single remote task"],
                                agent="carol")
            f = next(foreign.glob("*.md"))
            r = garm("import", str(f), "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("indexed 2 dossiers", r.stdout)

    def test_import_missing_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_bank(tmp, "dossiers", ["local task"])
            r = garm("import", str(Path(tmp) / "nope"), "--dir", "dossiers",
                     cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("not found", r.stderr)


class ExportTest(unittest.TestCase):
    def test_export_copies_md_not_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_bank(tmp, "dossiers", ["task one", "task two"])
            r = garm("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = str(Path(tmp) / "bank")
            r = garm("export", "--dir", "dossiers", "-o", out, cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("exported 2 dossiers", r.stdout)
            outp = Path(out)
            self.assertEqual(len(list(outp.glob("*.md"))), 2)
            self.assertFalse((outp / "index.jsonl").exists())

    def test_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_bank(tmp, "dossiers", ["roundtrip task"], agent="dave")
            out = str(Path(tmp) / "bank")
            r = garm("export", "--dir", "dossiers", "-o", out, cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            # import the export into a fresh bank
            fresh = Path(tmp) / "fresh"
            fresh.mkdir()
            r = garm("import", out, "--dir", str(fresh), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = garm("recall", "--task", "roundtrip task",
                     "--dir", str(fresh), "--top", "1", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("from:dave", r.stdout)


if __name__ == "__main__":
    unittest.main()
