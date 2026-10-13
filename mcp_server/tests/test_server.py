"""Tests for the Garm MCP server (mcp_server/).

Skipped automatically when the `mcp` package is not installed, so the
core suite stays green on stdlib-only machines. Run with an `mcp`-
capable interpreter from the repo root:

    python -m unittest discover -s mcp_server/tests -t .
"""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from mcp_server import server as S
    from garm import dossier as D
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

FULL_SECTIONS = {
    "what was tried": "Tried X, then Y.",
    "root cause": "The actual reason.",
    "failure signature": "a-pattern: match rule here.",
    "blocking constraint": "The blocking fact.",
    "what retrieval would have changed": "Skip turn 3; do Z instead.",
    "confidence": "Medium.",
}


def filled_dossier(path: Path, task: str = "Example task",
                   agent: str = "mcp-agent",
                   failure_class: str = "search") -> None:
    text = D.render_template(task=task, agent=agent,
                             failure_class=failure_class,
                             sections=FULL_SECTIONS)
    path.write_text(text, encoding="utf-8")


@unittest.skipUnless(MCP_AVAILABLE, "mcp package not installed")
class ServerRegistrationTest(unittest.TestCase):
    def test_nine_tools_registered(self):
        tools = asyncio.run(S.server.list_tools())
        names = sorted(t.name for t in tools)
        self.assertEqual(names, [
            "garm_autopsy", "garm_confirm", "garm_init", "garm_list",
            "garm_premise_add", "garm_premise_kill", "garm_premise_list",
            "garm_recall", "garm_validate",
        ])

    def test_tool_schemas_have_expected_params(self):
        tools = {t.name: t for t in asyncio.run(S.server.list_tools())}
        recall_props = tools["garm_recall"].input_schema["properties"]
        self.assertIn("task", recall_props)
        self.assertIn("task", tools["garm_recall"].input_schema["required"])
        init_props = tools["garm_init"].input_schema["properties"]
        for p in ("task", "agent", "failure_class"):
            self.assertIn(p, init_props)
        confirm_props = tools["garm_confirm"].input_schema["properties"]
        self.assertIn("id", confirm_props)
        self.assertIn("insight", confirm_props)
        kill_props = tools["garm_premise_kill"].input_schema["properties"]
        self.assertIn("evidence", kill_props)

    def test_tools_have_descriptions(self):
        for t in asyncio.run(S.server.list_tools()):
            self.assertTrue(t.description, f"{t.name} has no description")


@unittest.skipUnless(MCP_AVAILABLE, "mcp package not installed")
class ServerRoundTripTest(unittest.TestCase):
    def test_init_validate_confirm_recall_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "bank"

            # init scaffolds a file; scaffold must NOT validate
            r = S.init_impl(task="Avoid retry storms", agent="mcp-agent",
                            failure_class="knowledge-gap", dir=str(bank))
            self.assertTrue(r["path"].endswith(".md"))
            v = S.validate_impl(r["path"])
            self.assertFalse(v["valid"])
            self.assertTrue(v["errors"])

            # fill it in -> validates
            filled_dossier(Path(r["path"]), task="Avoid retry storms",
                           agent="mcp-agent", failure_class="knowledge-gap")
            v = S.validate_impl(r["path"])
            self.assertTrue(v["valid"], v["errors"])

            # confirm bumps fixes and re-indexes
            c = S.confirm_impl(r["id"], dir=str(bank))
            self.assertEqual(c["field"], "confirmed_fixes")
            self.assertEqual(c["new_count"], 1)
            self.assertEqual(c["indexed"], 1)

            # insight confirm bumps the other counter
            c2 = S.confirm_impl(r["id"], insight=True, dir=str(bank))
            self.assertEqual(c2["field"], "confirmed_insights")
            self.assertEqual(c2["new_count"], 1)

            # recall finds it
            hits = json.loads(S.recall_impl("retry storm deploy", dir=str(bank)))
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["id"], r["id"])
            self.assertGreater(hits[0]["score"], 0)
            self.assertEqual(hits[0]["confirmed_fixes"], 1)
            self.assertEqual(hits[0]["confirmed_insights"], 1)
            self.assertIn("matched_terms", hits[0])

            # list shows it
            rows = json.loads(S.list_impl(dir=str(bank)))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], r["id"])
            self.assertEqual(rows[0]["confirmed_fixes"], 1)

    def test_init_rejects_bad_failure_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                S.init_impl(task="t", agent="a",
                            failure_class="vibes", dir=tmp)

    def test_autopsy_full_draft_validates_and_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "bank"
            r = S.autopsy_impl(
                task="Avoid retry storms", agent="mcp-agent",
                failure_class="knowledge-gap",
                answers={
                    "what_was_tried": ["Doubled the timeout", "Added jitter"],
                    "root_cause": "Thundering herd on deploy.",
                    "failure_signature": "retry-storm: deploy-time latency "
                                         "spike -> pull this.",
                    "blocking_constraint": "No backoff in the deploy path.",
                    "what_retrieval_would_have_changed": "Skip the timeout "
                                                         "doubling; add "
                                                         "jitter first.",
                    "confidence": "High.",
                },
                dir=str(bank))
            self.assertTrue(r["valid"], r["errors"])
            self.assertEqual(r["indexed"], 1)
            self.assertEqual(r["warnings"], [])
            # answers landed verbatim; blank optionals stripped
            sections = D.read_dossier(r["path"])["sections"]
            self.assertIn("- Doubled the timeout", sections["what was tried"])
            self.assertNotIn("open questions", sections)
            # recall finds the drafted dossier
            hits = json.loads(
                S.recall_impl("retry storm deploy", dir=str(bank)))
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["id"], r["id"])

    def test_autopsy_partial_draft_reports_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "bank"
            r = S.autopsy_impl(
                task="Half autopsy", agent="mcp-agent",
                failure_class="reasoning-error",
                answers={"root_cause": "Something broke."},
                dir=str(bank))
            self.assertFalse(r["valid"])
            self.assertTrue(r["errors"])
            self.assertEqual(r["indexed"], 0)
            self.assertTrue(Path(r["path"]).exists(),
                            "draft is still written for finishing")

    def test_autopsy_rejects_bad_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                S.autopsy_impl(task="t", agent="a",
                               failure_class="vibes", dir=tmp)
            with self.assertRaises(ValueError):
                S.autopsy_impl(task="t", agent="a",
                               failure_class="knowledge-gap",
                               answers={"bogus_key": "x"}, dir=tmp)

    def test_confirm_unknown_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "bank"
            bank.mkdir()
            with self.assertRaises(ValueError):
                S.confirm_impl("no-such-id", dir=str(bank))

    def test_missing_bank_raises(self):
        with self.assertRaises(ValueError):
            S.recall_impl("anything", dir="/no/such/dir/xyz")

    def test_recall_failure_class_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "bank"
            bank.mkdir()
            filled_dossier(bank / "a.md", task="search task",
                           failure_class="knowledge-gap")
            filled_dossier(bank / "b.md", task="search task",
                           failure_class="reasoning-error")
            hits = json.loads(S.recall_impl("search task",
                                              failure_class="reasoning-error",
                                              dir=str(bank)))
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["failure_class"], "reasoning-error")


if __name__ == "__main__":
    unittest.main()
