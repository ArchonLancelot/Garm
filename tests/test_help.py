"""The recall help text must be honest about v0.2 ranking."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecallHelpTest(unittest.TestCase):
    def test_help_states_keyword_overlap_not_semantic(self):
        r = subprocess.run(
            [sys.executable, "-m", "garm", "recall", "--help"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0)
        text = " ".join(r.stdout.lower().split())
        self.assertIn("keyword overlap", text)
        self.assertIn("not semantic", text)

    def test_top_level_help_lists_all_commands(self):
        r = subprocess.run(
            [sys.executable, "-m", "garm", "--help"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0)
        for cmd in ("init", "validate", "confirm", "index", "recall", "list"):
            self.assertIn(cmd, r.stdout)


if __name__ == "__main__":
    unittest.main()
