"""Round trip: init -> validate -> index -> recall.

Recall must rank the dossier whose task+signature overlaps the query
at the top.
"""

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


TASK_A = "Fix flaky checkout total race condition in parallel test workers"
TASK_B = "Resolve dependency version conflict breaking the deploy build"

SECTIONS_A = {
    "what was tried": "Re-ran the failing test six times; added retries; bisected commits.",
    "root cause": "Race condition: shared mutable cart fixture across parallel workers.",
    "failure signature": "flaky-test-chased-as-code-bug: intermittent failure, "
                         "re-runs without inspecting fixtures or parallelism.",
    "blocking constraint": "Module-scoped mutable fixture with -n 4 parallel workers.",
    "what retrieval would have changed": "Skip re-runs; inspect conftest fixture scope first.",
    "confidence": "High on the mechanism.",
}

SECTIONS_B = {
    "what was tried": "Reinstalled dependencies three times; pinned versions by hand.",
    "root cause": "Resolver picked an incompatible transitive dependency version.",
    "failure signature": "dependency-version-guess-loop: repeated installs without a lockfile.",
    "blocking constraint": "No lockfile committed for the deploy environment.",
    "what retrieval would have changed": "Generate a lockfile before the second install attempt.",
    "confidence": "High.",
}


def fill_dossier(path: Path, task: str, agent: str, sections: dict) -> None:
    """Rewrite an init-scaffolded dossier, keeping its id/created frontmatter."""
    frontmatter, _ = D.split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(
        D.render_template(
            task=task, agent=agent,
            failure_class=frontmatter.get("failure_class", "reasoning-error"),
            id_=frontmatter["id"], created=frontmatter["created"],
            sections=sections,
        ),
        encoding="utf-8",
    )


class RoundTripTest(unittest.TestCase):
    def test_init_validate_index_recall(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = autopsy("init", "--task", TASK_A, "--agent", "claude-code",
                        "--class", "reasoning-error",
                        "-o", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            path_a = Path(tmp) / r.stdout.strip()
            self.assertTrue(path_a.is_file())

            r = autopsy("init", "--task", TASK_B, "--agent", "claude-code",
                        "--class", "tool-misuse",
                        "-o", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            path_b = Path(tmp) / r.stdout.strip()

            fill_dossier(path_a, TASK_A, "claude-code", SECTIONS_A)
            fill_dossier(path_b, TASK_B, "claude-code", SECTIONS_B)

            for p in (path_a, path_b):
                r = autopsy("validate", str(p), cwd=tmp)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("OK", r.stdout)

            r = autopsy("index", "--dir", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            index_path = Path(tmp) / "dossiers" / "index.jsonl"
            self.assertTrue(index_path.is_file())
            self.assertEqual(len(index_path.read_text().strip().splitlines()), 2)

            r = autopsy("recall", "--task",
                        "checkout test flaky intermittent parallel workers race",
                        "--dir", "dossiers", "--top", "2", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
            self.assertGreaterEqual(len(lines), 2)
            id_a = D.split_frontmatter(path_a.read_text())[0]["id"]
            id_b = D.split_frontmatter(path_b.read_text())[0]["id"]
            self.assertIn(id_a, lines[0], f"expected {id_a} ranked top, got: {lines}")
            self.assertIn(id_b, lines[1], f"expected {id_b} ranked second, got: {lines}")


if __name__ == "__main__":
    unittest.main()
