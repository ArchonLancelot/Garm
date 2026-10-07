"""index rebuild must be idempotent: same bytes on repeat runs."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autopsy import dossier as D  # noqa: E402


def autopsy(*args, cwd):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "autopsy", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


SECTIONS = {
    "what was tried": "Did A, then B.",
    "root cause": "C.",
    "failure signature": "sig-one: match rule.",
    "blocking constraint": "D.",
    "what retrieval would have changed": "E.",
    "confidence": "High.",
}


class IndexTest(unittest.TestCase):
    def test_index_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            for task in ("First task about widgets", "Second task about gadgets"):
                (d / f"{D.slugify(task)}.md").write_text(
                    D.render_template(task=task, agent="claude-code",
                                      sections=SECTIONS),
                    encoding="utf-8",
                )
            r = autopsy("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            index_path = d / "index.jsonl"
            first = index_path.read_bytes()

            r = autopsy("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            second = index_path.read_bytes()

            self.assertEqual(first, second, "index rebuild was not byte-identical")

            lines = first.decode().strip().splitlines()
            self.assertEqual(len(lines), 2)
            entries = D.load_index_entries(index_path)
            self.assertEqual(len(entries), 2)
            for entry in entries:
                for key in ("id", "task", "signature", "keywords",
                            "outcome", "path", "created"):
                    self.assertIn(key, entry)


if __name__ == "__main__":
    unittest.main()
