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
    def test_eight_tools_registered(self):
        tools = asyncio.run(S.server.list_tools())
        names = sorted(t.name for t in tools)
        self.assertEqual(names, [
            "garm_confirm", "garm_init", "garm_list",
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
