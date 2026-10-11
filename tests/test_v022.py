"""v0.2.2: optional 'Challengeable premises' and 'Open questions' sections.

New sections must validate when present and must not be required when
absent (old dossiers keep validating). The scaffold must include them.
"""

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


BASE_SECTIONS = {
    "what was tried": "Did A, then B.",
    "root cause": "C.",
    "failure signature": "Name: some-pattern. If you see X, stop.",
    "blocking constraint": "D.",
    "what retrieval would have changed": "E.",
    "confidence": "High.",
}

FULL_SECTIONS = dict(
    BASE_SECTIONS,
    **{
        "challengeable premises": "Premise 1: the two filters are "
        "independent. Premise 2: small cases generalize.",
        "open questions": "Is there a weaker two-sided condition?",
    },
)


def write_dossier(tmpdir, filename, sections):
    d = Path(tmpdir) / "dossiers"
    d.mkdir(exist_ok=True)
    text = D.render_template(
        task="Some task", agent="claude-code",
        failure_class="reasoning-error", sections=sections,
    )
    p = d / filename
    p.write_text(text, encoding="utf-8")
    return p


class NewSectionsValidateTest(unittest.TestCase):
    def test_present_sections_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_dossier(tmp, "d.md", FULL_SECTIONS)
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_absent_sections_still_validate(self):
        # Backward compatibility: a dossier written before v0.2.2, without
        # the new headers at all, must keep validating.
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir(exist_ok=True)
            lines = [
                "---",
                'dossier_version: "0.2"',
                "id: pre-v022-dossier",
                "created: 2026-10-01",
                "agent: claude-code",
                'task: "Old task"',
                "outcome: failed",
                "failure_class: reasoning-error",
                "confirmed_fixes: 0",
                "confirmed_insights: 0",
                "---",
                "",
                "# Failure dossier: Old task",
                "",
            ]
            for title, body in BASE_SECTIONS.items():
                lines += ["## " + title.title(), body, ""]
            p = d / "old.md"
            p.write_text("\n".join(lines), encoding="utf-8")
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_sections_are_not_required(self):
        # validate_dossier returns no errors about the new sections.
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir(exist_ok=True)
            lines = [
                "---",
                'dossier_version: "0.2"',
                "id: pre-v022-dossier",
                "created: 2026-10-01",
                "agent: claude-code",
                'task: "Old task"',
                "outcome: failed",
                "failure_class: reasoning-error",
                "---",
                "",
            ]
            for title, body in BASE_SECTIONS.items():
                lines += ["## " + title.title(), body, ""]
            p = d / "old.md"
            p.write_text("\n".join(lines), encoding="utf-8")
            errors = D.validate_dossier(p)
            self.assertEqual(errors, [])


class ScaffoldIncludesNewSectionsTest(unittest.TestCase):
    def test_render_template_has_new_headers(self):
        text = D.render_template(
            task="T", agent="a", failure_class="knowledge-gap")
        self.assertIn("## Challengeable premises", text)
        self.assertIn("## Open questions", text)

    def test_guidance_mentions_negation(self):
        text = D.render_template(
            task="T", agent="a", failure_class="knowledge-gap")
        self.assertIn("what if this is false", text)

    def test_section_order(self):
        text = D.render_template(
            task="T", agent="a", failure_class="knowledge-gap")
        order = [
            "## What was tried",
            "## Root cause",
            "## Failure signature",
            "## Blocking constraint",
            "## Challengeable premises",
            "## What retrieval would have changed",
            "## Open questions",
            "## Tokens",
            "## Confidence",
        ]
        positions = [text.index(h) for h in order]
        self.assertEqual(positions, sorted(positions))

    def test_init_scaffold_rejected_until_filled(self):
        # v0.2.3: the scaffold (including the new sections) must not pass
        # validation until the placeholder text is replaced with analysis.
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("init", "--task", "Some task", "--agent", "claude-code",
                     "--class", "knowledge-gap", "-o", "dossiers", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            p = Path(tmp) / r.stdout.strip()
            body = p.read_text(encoding="utf-8")
            self.assertIn("## Challengeable premises", body)
            self.assertIn("## Open questions", body)
            r = garm("validate", str(p), cwd=tmp)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            # required sections are named; optional ones are exempt
            self.assertIn("what was tried", r.stdout)
            self.assertNotIn("challengeable premises", r.stdout)


if __name__ == "__main__":
    unittest.main()
