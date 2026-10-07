"""validate must reject dossiers with structural problems."""

import re
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


FULL_SECTIONS = {
    "what was tried": "Tried X, then Y.",
    "root cause": "The actual reason.",
    "failure signature": "a-pattern: match rule here.",
    "blocking constraint": "The blocking fact.",
    "what retrieval would have changed": "Skip turn 3; do Z instead.",
    "confidence": "Medium.",
}


def write_dossier(path: Path, drop_section: str | None = None) -> None:
    sections = {k: v for k, v in FULL_SECTIONS.items() if k != drop_section}
    text = D.render_template(
        task="Example task", agent="claude-code", sections=sections,
    )
    if drop_section is not None:
        # render_template always emits every section; strip the dropped one
        # by skipping lines from its ## header to the next ## header.
        lines = text.splitlines(keepends=True)
        out, skip = [], False
        for line in lines:
            if re.match(r"##\s+", line):
                skip = line.strip().lower() == "## " + drop_section
            if not skip:
                out.append(line)
        text = "".join(out)
    path.write_text(text, encoding="utf-8")


class ValidateTest(unittest.TestCase):
    def test_rejects_missing_required_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.md"
            write_dossier(bad, drop_section="root cause")
            r = garm("validate", str(bad), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("root cause", r.stdout.lower())

    def test_rejects_missing_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.md"
            bad.write_text("## What was tried\nSomething.\n", encoding="utf-8")
            r = garm("validate", str(bad), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("frontmatter", r.stdout.lower())

    def test_rejects_bad_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.md"
            text = D.render_template(task="T", agent="a", sections=FULL_SECTIONS)
            text = text.replace("outcome: failed", "outcome: exploded")
            p.write_text(text, encoding="utf-8")
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("outcome", r.stdout.lower())

    def test_accepts_valid_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "good.md"
            write_dossier(p)
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
