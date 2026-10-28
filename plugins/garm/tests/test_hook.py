"""Tests for the garm UserPromptSubmit hook (plugins/garm/hooks/garm_recall.py).

Each test feeds the hook a synthetic hook payload on stdin and asserts on
the stdout envelope / exit code. The hook must never break the session:
every failure mode degrades to exit 0 with empty stdout.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
HOOK = PLUGIN_ROOT / "hooks" / "garm_recall.py"
# fm-v02 project root: plugins/garm -> fm-v02
GARM_HOME = PLUGIN_ROOT.parents[1]


def make_dossier(d, name, task, signature, changed):
    body = textwrap.dedent(f"""\
        ---
        dossier_version: "0.2"
        id: {name}
        created: 2026-10-08
        agent: test
        task: "{task}"
        outcome: failed
        failure_class: reasoning-error
        confirmed_fixes: 0
        confirmed_insights: 0
        ---

        # Failure dossier: {task}

        ## What was tried
        Tried the thing.

        ## Root cause
        The cause.

        ## Failure signature
        Name: {signature}

        ## Blocking constraint
        The constraint.

        ## What retrieval would have changed
        {changed}

        ## Confidence
        High.
        """)
    p = d / f"{name}.md"
    p.write_text(body, encoding="utf-8")
    return p


def garm(*args, cwd, env_extra=None):
    env = dict(os.environ, PYTHONPATH=str(GARM_HOME))
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "garm", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def run_hook(payload, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return r


def base_payload(prompt, cwd):
    return {
        "session_id": "sess-test",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
        "cwd": cwd,
    }


class HookProtocolTest(unittest.TestCase):
    def test_malformed_stdin_is_silent(self):
        r = subprocess.run([sys.executable, str(HOOK)], input="not json{{{",
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_empty_prompt_is_silent(self):
        r = run_hook(base_payload("   ", "/tmp"))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_missing_dossier_dir_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"GARM_DIR": os.path.join(tmp, "nope"),
                   "GARM_HOME": str(GARM_HOME)}
            r = run_hook(base_payload("deploy widgets", tmp), env)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")

    def test_broken_garm_bin_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            env = {"GARM_DIR": str(d), "GARM_BIN": "/nonexistent/garm-xyz"}
            r = run_hook(base_payload("deploy widgets", tmp), env)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")

    def test_match_injects_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            make_dossier(d, "2026-10-08-widget-deploy-flake",
                         "deploy widgets to staging",
                         "flaky-widget-deploy",
                         "Check the staging deploy lock before retrying.")
            r = garm("index", "--dir", str(d), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            env = {"GARM_DIR": str(d), "GARM_HOME": str(GARM_HOME)}
            r = run_hook(base_payload("deploy widgets to staging again", tmp), env)
            self.assertEqual(r.returncode, 0, r.stderr)
            envelope = json.loads(r.stdout)
            ctx = envelope["hookSpecificOutput"]["additionalContext"]
            self.assertEqual(
                envelope["hookSpecificOutput"]["hookEventName"],
                "UserPromptSubmit")
            self.assertIn("2026-10-08-widget-deploy-flake", ctx)
            self.assertIn("Check the staging deploy lock", ctx)
            self.assertLessEqual(len(ctx), 8000)

    def test_no_match_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            make_dossier(d, "2026-10-08-widget-deploy-flake",
                         "deploy widgets to staging",
                         "flaky-widget-deploy",
                         "Check the staging deploy lock before retrying.")
            r = garm("index", "--dir", str(d), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            env = {"GARM_DIR": str(d), "GARM_HOME": str(GARM_HOME)}
            r = run_hook(base_payload("bake sourdough bread recipe", tmp), env)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")

    def test_min_score_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            make_dossier(d, "2026-10-08-widget-deploy-flake",
                         "deploy widgets to staging",
                         "flaky-widget-deploy",
                         "Check the staging deploy lock before retrying.")
            r = garm("index", "--dir", str(d), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            env = {"GARM_DIR": str(d), "GARM_HOME": str(GARM_HOME),
                   "GARM_MIN_SCORE": "999"}
            r = run_hook(base_payload("deploy widgets to staging again", tmp), env)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")

    def test_low_min_score_passes_through_to_recall(self):
        # v0.2.11: the hook must pass --min-score explicitly. A single-doc
        # bank scores ~0.58 on this query — below the CLI's 1.0 default,
        # above a user-set 0.5. Without pass-through, the 0.5 case would
        # silently lose the hit to the CLI default.
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            make_dossier(d, "2026-10-08-alpha-gamma",
                         "Task alpha gamma",
                         "unrelated signature words",
                         "Check the thing first.")
            r = garm("index", "--dir", str(d), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            env = {"GARM_DIR": str(d), "GARM_HOME": str(GARM_HOME),
                   "GARM_MIN_SCORE": "0.5"}
            r = run_hook(base_payload("alpha gamma", tmp), env)
            self.assertEqual(r.returncode, 0)
            envelope = json.loads(r.stdout)
            ctx = envelope["hookSpecificOutput"]["additionalContext"]
            self.assertIn("2026-10-08-alpha-gamma", ctx)
            # And the default (1.0) genuinely clips this hit.
            env = {"GARM_DIR": str(d), "GARM_HOME": str(GARM_HOME)}
            r = run_hook(base_payload("alpha gamma", tmp), env)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")

    def test_brackets_in_task_do_not_misparse_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            make_dossier(d, "2026-10-08-widget-deploy-flake",
                         "deploy [urgent] widgets to staging",
                         "flaky-widget-deploy",
                         "Check the staging deploy lock before retrying.")
            r = garm("index", "--dir", str(d), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            env = {"GARM_DIR": str(d), "GARM_HOME": str(GARM_HOME)}
            r = run_hook(base_payload("deploy urgent widgets staging", tmp), env)
            self.assertEqual(r.returncode, 0, r.stderr)
            envelope = json.loads(r.stdout)
            ctx = envelope["hookSpecificOutput"]["additionalContext"]
            # the "what retrieval would have changed" section must be found,
            # i.e. the path was parsed correctly despite [urgent] in the task
            self.assertIn("Check the staging deploy lock", ctx)

    def test_injected_context_shows_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "dossiers"
            d.mkdir()
            p = make_dossier(d, "2026-10-08-widget-deploy-flake",
                             "deploy widgets to staging",
                             "flaky-widget-deploy",
                             "Check the staging deploy lock before retrying.")
            text = p.read_text(encoding="utf-8").replace(
                "confirmed_insights: 0",
                "confirmed_insights: 0\norigin: alice-bank")
            p.write_text(text, encoding="utf-8")
            r = garm("index", "--dir", str(d), cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            env = {"GARM_DIR": str(d), "GARM_HOME": str(GARM_HOME)}
            r = run_hook(base_payload("deploy widgets to staging again", tmp), env)
            self.assertEqual(r.returncode, 0, r.stderr)
            envelope = json.loads(r.stdout)
            ctx = envelope["hookSpecificOutput"]["additionalContext"]
            self.assertIn("(from: alice-bank)", ctx)

    def test_diagnostics_never_on_stdout(self):
        # even the quiet-failure path must not print diagnostics to stdout
        with tempfile.TemporaryDirectory() as tmp:
            env = {"GARM_DIR": os.path.join(tmp, "missing"),
                   "GARM_HOME": str(GARM_HOME)}
            r = run_hook(base_payload("anything", tmp), env)
            self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()
