"""v0.2.5: assisted autopsy drafting (closing-ceremony interview).

Covers: --answers full flow (valid draft, indexed, verbatim answers),
partial drafts (written but fail validate naming the empty sections),
answers-file validation (unknown keys, bad class, missing task),
list answers -> bullets, blank optional sections stripped, premise refs
kept with warnings on unknown ids, id collision suffixing, interactive
flow via mocked input (save / discard / EOF), CLI flag pre-answers,
--help listing, and normalize_answers unit behavior.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from garm import autopsy as AU  # noqa: E402
from garm import dossier as D  # noqa: E402


def garm(*args, cwd, stdin_data=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "garm", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
        input=stdin_data,
    )


FULL_ANSWERS = {
    "task": "Fix flaky checkout race",
    "agent": "claude-code",
    "failure_class": "reasoning-error",
    "outcome": "failed",
    "what_was_tried": [
        "Reproduced with --seed 42",
        "Added retry loop around checkout",
        "Bisected the queue module",
    ],
    "root_cause": "The queue drained before the worker acked; the retry masked it.",
    "failure_signature": "flaky-checkout-race: if checkout flakes only under "
                         "parallel runs, stop and pull this dossier.",
    "blocking_constraint": "The harness runs suites in parallel on a shared queue.",
    "challengeable_premises": "Retries make flakes go away.",
    "what_retrieval_would_have_changed": "Skip the retry loop at turn 2; "
                                         "bisect the queue module first.",
    "open_questions": "Does the ack race exist in the payment queue too?",
    "tokens": "Longest: the bisect; about 40k tokens.",
    "confidence": "High; a failing parallel run with queue logs would "
                  "change my mind.",
}

REQUIRED_SECTIONS = [
    "what was tried",
    "root cause",
    "failure signature",
    "blocking constraint",
    "what retrieval would have changed",
    "confidence",
]


def write_answers(tmp, answers, name="answers.json"):
    p = Path(tmp) / name
    p.write_text(json.dumps(answers), encoding="utf-8")
    return p


class AssistedDraftFlowTest(unittest.TestCase):
    def test_full_flow_valid_and_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            answers = write_answers(tmp, FULL_ANSWERS)
            r = garm("autopsy", "--answers", str(answers),
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            md = sorted(bank.glob("*.md"))
            self.assertEqual(len(md), 1)
            self.assertEqual(D.validate_dossier(md[0]), [])
            parsed = D.read_dossier(md[0])
            fm = parsed["frontmatter"]
            self.assertEqual(fm["task"], "Fix flaky checkout race")
            self.assertEqual(fm["failure_class"], "reasoning-error")
            sections = parsed["sections"]
            # answers land verbatim in their sections
            self.assertIn("The queue drained before the worker acked",
                          sections["root cause"])
            self.assertIn("- Reproduced with --seed 42",
                          sections["what was tried"])
            self.assertIn("- Bisected the queue module",
                          sections["what was tried"])
            index = bank / "index.jsonl"
            self.assertTrue(index.exists())
            entries = D.load_index_entries(index)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["id"], fm["id"])

    def test_partial_draft_written_but_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            partial = {k: FULL_ANSWERS[k] for k in
                       ("task", "agent", "failure_class", "outcome",
                        "root_cause")}
            answers = write_answers(tmp, partial)
            r = garm("autopsy", "--answers", str(answers),
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            md = sorted(bank.glob("*.md"))
            self.assertEqual(len(md), 1, "draft is still written")
            # the report names the sections that still need writing
            for section in ("what was tried", "failure signature",
                            "blocking constraint",
                            "what retrieval would have changed",
                            "confidence"):
                self.assertIn(section, r.stdout)
            # nothing indexed: the draft is not a dossier yet
            self.assertFalse((bank / "index.jsonl").exists())

    def test_answers_rejects_unknown_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            answers = write_answers(tmp, {**FULL_ANSWERS, "bogus": "x"})
            r = garm("autopsy", "--answers", str(answers),
                     "--dir", str(Path(tmp) / "dossiers"), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("unknown answer key", r.stderr)
            self.assertEqual(list(Path(tmp).rglob("*.md")), [],
                             "nothing written on bad input")

    def test_answers_rejects_bad_failure_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(FULL_ANSWERS, failure_class="vibes")
            answers = write_answers(tmp, bad)
            r = garm("autopsy", "--answers", str(answers),
                     "--dir", str(Path(tmp) / "dossiers"), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("failure_class", r.stderr)

    def test_answers_rejects_missing_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = {k: v for k, v in FULL_ANSWERS.items() if k != "task"}
            answers = write_answers(tmp, bad)
            r = garm("autopsy", "--answers", str(answers),
                     "--dir", str(Path(tmp) / "dossiers"), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("task", r.stderr)

    def test_answers_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("{not json", encoding="utf-8")
            r = garm("autopsy", "--answers", str(p),
                     "--dir", str(Path(tmp) / "dossiers"), cwd=tmp)
            self.assertEqual(r.returncode, 1)
            self.assertIn("not valid JSON", r.stderr)

    def test_cli_flags_override_answers_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            answers = write_answers(tmp, FULL_ANSWERS)
            r = garm("autopsy", "--answers", str(answers),
                     "--task", "Override task", "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            md = sorted(bank.glob("*.md"))[0]
            self.assertEqual(D.read_dossier(md)["frontmatter"]["task"],
                             "Override task")

    def test_optional_sections_stripped_when_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            key_by_section = {q["section"].lower(): q["key"]
                              for q in AU.QUESTIONS if q.get("section")}
            required_keys = {key_by_section[s] for s in REQUIRED_SECTIONS}
            raw = {k: v for k, v in FULL_ANSWERS.items()
                   if k in required_keys
                   or k in ("task", "agent", "failure_class", "outcome")}
            answers = write_answers(tmp, raw)
            r = garm("autopsy", "--answers", str(answers),
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            md = sorted(bank.glob("*.md"))[0]
            sections = D.read_dossier(md)["sections"]
            for optional in ("challengeable premises", "open questions",
                             "tokens", "premises"):
                self.assertNotIn(optional, sections,
                                 f"blank optional section {optional!r} "
                                 f"should be stripped from the draft")
            for required in REQUIRED_SECTIONS:
                self.assertIn(required, sections)

    def test_id_collision_gets_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            answers = write_answers(tmp, FULL_ANSWERS)
            for _ in range(2):
                r = garm("autopsy", "--answers", str(answers),
                         "--dir", str(bank), cwd=tmp)
                self.assertEqual(r.returncode, 0, r.stderr)
            names = sorted(p.name for p in bank.glob("*.md"))
            self.assertEqual(len(names), 2)
            self.assertTrue(any(n.endswith("-2.md") for n in names), names)

    def test_premise_refs_kept_warn_on_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            # register one real premise, reference it plus a typo'd one
            r = garm("premise", "add", "--statement", "The queue is FIFO",
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            pid = r.stdout.split(":")[1].strip().split()[0]
            raw = dict(FULL_ANSWERS, premises=f"{pid}, P-20990101-999")
            answers = write_answers(tmp, raw)
            r = garm("autopsy", "--answers", str(answers),
                     "--dir", str(bank), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("unknown premise", r.stderr)
            md = sorted(bank.glob("20*.md"))
            sections = D.read_dossier(md[0])["sections"]
            self.assertIn(pid, sections["premises"])
            self.assertIn("P-20990101-999", sections["premises"])

    def test_help_lists_autopsy_and_answer_keys(self):
        r = garm("--help", cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0)
        self.assertIn("autopsy", r.stdout)
        r = garm("autopsy", "--help", cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0)
        self.assertIn("what_was_tried", r.stdout)
        self.assertIn("failure_signature", r.stdout)

    def test_no_task_no_tty_no_answers_errors(self):
        # stdin is not a tty in subprocess: without --task/--answers the
        # interview can't run, so it must say so, not hang on prompts.
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("autopsy", "--dir", str(Path(tmp) / "dossiers"),
                     cwd=tmp, stdin_data="")
            self.assertEqual(r.returncode, 1)
            self.assertIn("--answers", r.stderr)


class AssistedDraftInteractiveTest(unittest.TestCase):
    # Scripted answers in question order: task, agent, failure_class
    # (choice), outcome (choice), what_was_tried (multiline), root_cause,
    # failure_signature, blocking_constraint, challengeable_premises,
    # what_retrieval_would_have_changed, open_questions, tokens, premises,
    # confidence, then the save confirmation.
    SCRIPT = [
        "Flaky checkout race",            # task
        "test-agent",                     # agent
        "2",                              # failure_class -> reasoning-error
        "",                               # outcome -> default failed
        "Reproduced with --seed 42",      # what_was_tried...
        "Added retry loop",
        "",                               # ...blank line ends list
        "Queue drained before ack.",      # root_cause
        "flaky-checkout: parallel-only flakes -> pull this.",  # signature
        "Shared queue under parallel harness.",  # blocking_constraint
        "",                               # challengeable_premises (skip)
        "Skip retry loop; bisect queue first.",  # retrieval
        "",                               # open_questions (skip)
        "",                               # tokens (skip)
        "",                               # premises (skip)
        "High.",                          # confidence
    ]

    def test_interactive_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            with mock.patch("builtins.input",
                            side_effect=self.SCRIPT + ["y"]):
                rc = AU.run_autopsy(AU.collect_interactive({}), bank,
                                    interactive=True)
            self.assertEqual(rc, 0)
            md = sorted(bank.glob("*.md"))
            self.assertEqual(len(md), 1)
            self.assertEqual(D.validate_dossier(md[0]), [])
            sections = D.read_dossier(md[0])["sections"]
            self.assertIn("- Reproduced with --seed 42",
                          sections["what was tried"])
            self.assertEqual(
                D.read_dossier(md[0])["frontmatter"]["failure_class"],
                "reasoning-error")
            self.assertNotIn("challengeable premises", sections)

    def test_interactive_discard_removes_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            with mock.patch("builtins.input",
                            side_effect=self.SCRIPT + ["n"]):
                rc = AU.run_autopsy(AU.collect_interactive({}), bank,
                                    interactive=True)
            self.assertEqual(rc, 1)
            self.assertEqual(list(bank.glob("*.md")), [])

    def test_interactive_eof_aborts_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            with mock.patch("builtins.input", side_effect=EOFError):
                rc = AU.run_autopsy(AU.collect_interactive({}), bank,
                                    interactive=True)
            self.assertEqual(rc, 1, "no task -> abort, no crash")
            self.assertEqual(list(bank.glob("*.md")), [])

    def test_yes_flag_skips_confirmation(self):
        # frontmatter pre-answered via flags, so the non-tty guard passes;
        # only the section questions are scripted. No trailing confirmation
        # answer: StopIteration would raise if the code asked — proving
        # --yes skips it.
        section_script = [
            "Reproduced with --seed 42",      # what_was_tried...
            "Added retry loop",
            "",                               # ...blank line ends list
            "Queue drained before ack.",      # root_cause
            "flaky-checkout: parallel-only flakes -> pull this.",
            "Shared queue under parallel harness.",
            "",                               # challengeable_premises (skip)
            "Skip retry loop; bisect queue first.",
            "",                               # open_questions (skip)
            "",                               # tokens (skip)
            "",                               # premises (skip)
            "High.",                          # confidence
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            with mock.patch("builtins.input", side_effect=section_script):
                from garm import cli as CLI
                import argparse
                ns = argparse.Namespace(
                    task="Flaky checkout race", agent="test-agent",
                    failure_class="reasoning-error", outcome="failed",
                    answers="", yes=True, dir=str(bank))
                rc = CLI.cmd_autopsy(ns)
            self.assertEqual(rc, 0)
            self.assertEqual(len(list(bank.glob("*.md"))), 1)

    def test_choice_rejects_then_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "dossiers"
            script = ["T", "A", "bogus", "3", ""] + self.SCRIPT[4:] + ["y"]
            with mock.patch("builtins.input", side_effect=script):
                rc = AU.run_autopsy(AU.collect_interactive({}), bank,
                                    interactive=True)
            self.assertEqual(rc, 0)
            md = sorted(bank.glob("*.md"))[0]
            self.assertEqual(
                D.read_dossier(md)["frontmatter"]["failure_class"],
                "execution-slip")


class NormalizeAnswersTest(unittest.TestCase):
    def test_list_and_string_values(self):
        fm, sections = AU.normalize_answers({
            "task": "T", "agent": "A", "failure_class": "reasoning-error",
            "outcome": "failed",
            "what_was_tried": ["a", "b"],
            "root_cause": "  cause  ",
            "premises": "P-20261012-001, P-20261012-002",
            "tokens": "   ",
        })
        self.assertEqual(fm["task"], "T")
        self.assertEqual(sections["what was tried"], "- a\n- b")
        self.assertEqual(sections["root cause"], "cause")
        self.assertNotIn("tokens", sections, "blank answers are dropped")

    def test_strip_unfilled_optionals_keeps_required_guidance(self):
        text = D.render_template(task="T", agent="A",
                                 failure_class="reasoning-error",
                                 sections={"root cause": "real cause"})
        stripped = AU._strip_unfilled_optionals(
            text, {"root cause"})
        self.assertNotIn("## Tokens", stripped)
        self.assertNotIn("## Open questions", stripped)
        # required but unanswered: guidance stays so validate() flags it
        self.assertIn("## What was tried", stripped)
        self.assertIn(D._GUIDANCE_BY_TITLE["what was tried"], stripped)


if __name__ == "__main__":
    unittest.main()
