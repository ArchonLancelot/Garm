"""v0.2.4: premise registry and trunk kills.

Covers: premise add (ids, deps, cycles), kill with transitive
inheritance, dossier ## Premises parsing, premise_dead in the index,
recall excluding dead routes (and --include-dead), import/export of the
registry, and validate's tolerance of the new optional section."""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from garm import dossier as D  # noqa: E402
from garm import premise as PR  # noqa: E402


def garm(*args, cwd):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-m", "garm", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


FILLED = {
    "what was tried": "Tried X.",
    "root cause": "Y was the cause.",
    "failure signature": "Name: pattern-x. If you see X, stop.",
    "blocking constraint": "Z blocked it.",
    "challengeable premises": "Premise 1 holds.",
    "what retrieval would have changed": "W instead.",
    "open questions": "Is there a Q?",
    "tokens": "n/a",
    "confidence": "High.",
}


def write_dossier(tmpdir, dirname, filename, sections, id_):
    d = Path(tmpdir) / dirname
    d.mkdir(parents=True, exist_ok=True)
    text = D.render_template(
        task=f"Task for {id_}", agent="claude-code",
        failure_class="reasoning-error", sections=sections,
        id_=id_, created="2026-10-11",
    )
    p = d / filename
    p.write_text(text, encoding="utf-8")
    return p


class PremiseRegistryTest(unittest.TestCase):
    def test_add_generates_sequential_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = PR.add_premise(tmp, "trunk holds", created="2026-10-11")
            b = PR.add_premise(tmp, "branch holds", depends_on=[a],
                               created="2026-10-11")
            self.assertEqual(a, "P-20261011-001")
            self.assertEqual(b, "P-20261011-002")

    def test_add_rejects_empty_statement(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                PR.add_premise(tmp, "   ")

    def test_add_rejects_unknown_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                PR.add_premise(tmp, "x", depends_on=["P-20261011-999"])

    def test_add_rejects_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = PR.add_premise(tmp, "a", created="2026-10-11")
            b = PR.add_premise(tmp, "b", depends_on=[a], created="2026-10-11")
            # manufacture a would-be cycle: c depends on b, then check
            # that making b depend on c trips the detector at add time is
            # not possible via add alone; instead check _would_cycle direct.
            data = PR.load_registry(tmp)
            self.assertTrue(
                PR._would_cycle(data["premises"], a, b))
            self.assertFalse(
                PR._would_cycle(data["premises"], b, a))
            # a self-dependency is impossible (id doesn't exist yet), but a
            # hand-built cycle is detected by is_dead traversal termination:
            self.assertFalse(PR.is_dead(data, b))

    def test_kill_is_transitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            trunk = PR.add_premise(tmp, "trunk", created="2026-10-11")
            mid = PR.add_premise(tmp, "mid", depends_on=[trunk],
                                 created="2026-10-11")
            leaf = PR.add_premise(tmp, "leaf", depends_on=[mid],
                                  created="2026-10-11")
            other = PR.add_premise(tmp, "unrelated", created="2026-10-11")
            res = PR.kill_premise(tmp, trunk, "dossier-x")
            self.assertFalse(res["already_killed"])
            self.assertEqual(sorted(res["killed"]), sorted([trunk, mid, leaf]))
            data = PR.load_registry(tmp)
            self.assertTrue(PR.is_dead(data, leaf))   # via mid and trunk
            self.assertTrue(PR.is_dead(data, mid))
            self.assertFalse(PR.is_dead(data, other))
            # killing a leaf does not kill its trunk
            res2 = PR.kill_premise(tmp, other, "dossier-y")
            self.assertEqual(res2["killed"], [other])
            data2 = PR.load_registry(tmp)
            self.assertTrue(PR.is_dead(data2, trunk))  # still dead from before
            self.assertFalse(PR.is_dead(data2, "P-20261011-999"))  # unknown
            # idempotent kill
            res3 = PR.kill_premise(tmp, trunk, "dossier-x")
            self.assertTrue(res3["already_killed"])

    def test_kill_unknown_and_empty_by_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                PR.kill_premise(tmp, "P-20261011-001", "d-x")
            pid = PR.add_premise(tmp, "x", created="2026-10-11")
            with self.assertRaises(ValueError):
                PR.kill_premise(tmp, pid, "  ")


class PremiseReopenTest(unittest.TestCase):
    def test_reopen_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            trunk = PR.add_premise(tmp, "trunk", created="2026-10-11")
            mid = PR.add_premise(tmp, "mid", depends_on=[trunk],
                                 created="2026-10-11")
            leaf = PR.add_premise(tmp, "leaf", depends_on=[mid],
                                  created="2026-10-11")
            PR.kill_premise(tmp, trunk, "dossier-x")
            res = PR.reopen_premise(tmp, trunk, "reviewer")
            self.assertFalse(res["already_open"])
            self.assertEqual(sorted(res["reopened"]),
                             sorted([trunk, mid, leaf]))
            data = PR.load_registry(tmp)
            for pid in (trunk, mid, leaf):
                self.assertFalse(PR.is_dead(data, pid))
                self.assertEqual(data["premises"][pid]["status"], "open")
                self.assertEqual(data["premises"][pid]["reopened_by"],
                                 "reviewer")
                self.assertNotIn("killed_by", data["premises"][pid])

    def test_reopen_revives_only_inherited(self):
        with tempfile.TemporaryDirectory() as tmp:
            trunk = PR.add_premise(tmp, "trunk", created="2026-10-11")
            leaf = PR.add_premise(tmp, "leaf", depends_on=[trunk],
                                  created="2026-10-11")
            PR.kill_premise(tmp, leaf, "dossier-independent")
            PR.kill_premise(tmp, trunk, "dossier-x")
            res = PR.reopen_premise(tmp, trunk, "reviewer")
            self.assertEqual(res["reopened"], [trunk])  # leaf stays dead
            data = PR.load_registry(tmp)
            self.assertFalse(PR.is_dead(data, trunk))
            self.assertTrue(PR.is_dead(data, leaf))
            self.assertEqual(data["premises"][leaf]["killed_by"],
                             "dossier-independent")

    def test_reopen_open_is_noop_and_bad_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid = PR.add_premise(tmp, "x", created="2026-10-11")
            res = PR.reopen_premise(tmp, pid, "reviewer")
            self.assertTrue(res["already_open"])
            self.assertEqual(res["reopened"], [])
            with self.assertRaises(ValueError):
                PR.reopen_premise(tmp, "P-20261011-999", "reviewer")
            PR.kill_premise(tmp, pid, "d-x")
            with self.assertRaises(ValueError):
                PR.reopen_premise(tmp, pid, "  ")

    def test_cli_reopen_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("premise", "add", "--statement", "trunk holds",
                     "--dir", "d", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            pid = re.search(r"P-\d{8}-\d{3}", r.stdout).group(0)
            r = garm("premise", "kill", pid, "--by", "d-x",
                     "--dir", "d", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = garm("premise", "reopen", pid, "--by", "reviewer",
                     "--dir", "d", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(f"reopened: {pid}", r.stdout)
            self.assertIn("re-indexing to restore routes", r.stdout)
            r = garm("premise", "list", "--dir", "d", cwd=tmp)
            self.assertNotIn("KILLED", r.stdout)
            # --by is required
            r = garm("premise", "reopen", pid, "--dir", "d", cwd=tmp)
            self.assertNotEqual(r.returncode, 0)


class PremiseRefParsingTest(unittest.TestCase):
    def test_parse_bullets_and_bare(self):
        text = "- P-20261011-001\n* P-20261011-002\n  P-20261011-003  \n"
        self.assertEqual(
            PR.parse_premise_refs(text),
            ["P-20261011-001", "P-20261011-002", "P-20261011-003"])

    def test_ignores_prose_lines(self):
        text = "This approach rested on P-20261011-001 and hope.\n"
        self.assertEqual(PR.parse_premise_refs(text), [])

    def test_dedupes(self):
        text = "- P-20261011-001\n- P-20261011-001\n"
        self.assertEqual(PR.parse_premise_refs(text), ["P-20261011-001"])


class DossierPremisesTest(unittest.TestCase):
    def test_template_renders_premises_section(self):
        text = D.render_template(task="T", agent="a",
                                 failure_class="reasoning-error")
        self.assertIn("## Premises", text)

    def test_validate_accepts_premises_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = dict(FILLED)
            s["premises"] = "- P-20261011-001\n- P-20261011-002"
            p = write_dossier(tmp, "d", "d.md", s, "2026-10-11-prem")
            self.assertEqual(D.validate_dossier(p), [])

    def test_index_marks_dead_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            trunk = PR.add_premise(tmp + "/d", "trunk holds",
                                   created="2026-10-11")
            branch = PR.add_premise(tmp + "/d", "branch holds",
                                    depends_on=[trunk], created="2026-10-11")
            s1 = dict(FILLED)
            s1["premises"] = f"- {branch}"
            d1 = write_dossier(tmp, "d", "one.md", s1, "2026-10-11-one")
            s2 = dict(FILLED)  # no premises section: unaffected
            d2 = write_dossier(tmp, "d", "two.md", s2, "2026-10-11-two")
            s3 = dict(FILLED)
            s3["premises"] = f"- {branch}"
            d3 = write_dossier(tmp, "d", "three.md", s3, "2026-10-11-three")
            n, skipped = D.rebuild_index(Path(tmp) / "d")
            self.assertEqual((n, skipped), (3, 0))
            entries = {
                e["id"]: e
                for e in D.load_index_entries(Path(tmp) / "d" / "index.jsonl")
            }
            self.assertEqual(entries["2026-10-11-one"]["premises"], [branch])
            self.assertFalse(entries["2026-10-11-one"]["premise_dead"])
            self.assertFalse(entries["2026-10-11-two"]["premise_dead"])
            PR.kill_premise(Path(tmp) / "d", trunk, "2026-10-11-one")
            n, _ = D.rebuild_index(Path(tmp) / "d")
            entries = {
                e["id"]: e
                for e in D.load_index_entries(Path(tmp) / "d" / "index.jsonl")
            }
            # the killer dossier stays live: it holds the proof of falsity
            self.assertFalse(entries["2026-10-11-one"]["premise_dead"])
            self.assertFalse(entries["2026-10-11-two"]["premise_dead"])
            # a dossier that merely rested on the dead premise stays buried
            self.assertTrue(entries["2026-10-11-three"]["premise_dead"])

    def test_kill_rejects_dossier_shaped_by_with_no_match(self):
        # a --by that looks like a dossier id must name a real dossier:
        # catches truncated/pasted ids instead of storing them silently
        with tempfile.TemporaryDirectory() as tmp:
            pid = PR.add_premise(tmp, "x", created="2026-10-11")
            with self.assertRaises(ValueError):
                PR.kill_premise(tmp, pid, "2026-10-11-no-such-dossier")
            data = PR.load_registry(tmp)
            self.assertEqual(data["premises"][pid]["status"], "open")

    def test_kill_accepts_matching_dossier_id_and_plain_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = PR.add_premise(tmp + "/d", "x", created="2026-10-11")
            p2 = PR.add_premise(tmp + "/d", "y", created="2026-10-11")
            write_dossier(tmp, "d", "one.md", dict(FILLED), "2026-10-11-one")
            res = PR.kill_premise(Path(tmp) / "d", p1, "2026-10-11-one")
            self.assertEqual(res["killed"], [p1])
            res = PR.kill_premise(Path(tmp) / "d", p2, "lab meeting note")
            self.assertEqual(res["killed"], [p2])

    def test_killer_exemption_needs_dossier_id(self):
        # free-text killer: no dossier matches, so nothing is exempt
        with tempfile.TemporaryDirectory() as tmp:
            trunk = PR.add_premise(tmp + "/d", "trunk holds",
                                   created="2026-10-11")
            s1 = dict(FILLED)
            s1["premises"] = f"- {trunk}"
            write_dossier(tmp, "d", "one.md", s1, "2026-10-11-one")
            PR.kill_premise(Path(tmp) / "d", trunk, "a hand-written note")
            n, _ = D.rebuild_index(Path(tmp) / "d")
            entries = {
                e["id"]: e
                for e in D.load_index_entries(Path(tmp) / "d" / "index.jsonl")
            }
            self.assertTrue(entries["2026-10-11-one"]["premise_dead"])

    def test_killer_exemption_covers_inherited_kills(self):
        # dossier kills the trunk; it lists the grandchild branch: exempt
        # via the "inherited from" marker naming the trunk it killed
        with tempfile.TemporaryDirectory() as tmp:
            trunk = PR.add_premise(tmp + "/d", "trunk holds",
                                   created="2026-10-11")
            mid = PR.add_premise(tmp + "/d", "mid holds",
                                 depends_on=[trunk], created="2026-10-11")
            leaf = PR.add_premise(tmp + "/d", "leaf holds",
                                  depends_on=[mid], created="2026-10-11")
            s1 = dict(FILLED)
            s1["premises"] = f"- {leaf}"
            write_dossier(tmp, "d", "one.md", s1, "2026-10-11-one")
            s2 = dict(FILLED)
            s2["premises"] = f"- {leaf}"
            write_dossier(tmp, "d", "two.md", s2, "2026-10-11-two")
            PR.kill_premise(Path(tmp) / "d", trunk, "2026-10-11-one")
            n, _ = D.rebuild_index(Path(tmp) / "d")
            entries = {
                e["id"]: e
                for e in D.load_index_entries(Path(tmp) / "d" / "index.jsonl")
            }
            self.assertFalse(entries["2026-10-11-one"]["premise_dead"])
            self.assertTrue(entries["2026-10-11-two"]["premise_dead"])

    def test_index_warns_on_unknown_premise(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = dict(FILLED)
            s["premises"] = "- P-20261011-999"
            write_dossier(tmp, "d", "d.md", s, "2026-10-11-unk")
            import io
            from contextlib import redirect_stderr
            buf = io.StringIO()
            with redirect_stderr(buf):
                D.rebuild_index(Path(tmp) / "d")
            self.assertIn("unknown premise", buf.getvalue())
            entries = D.load_index_entries(Path(tmp) / "d" / "index.jsonl")
            # unknown premise treated as live
            self.assertFalse(entries[0]["premise_dead"])


class RecallDeadRouteTest(unittest.TestCase):
    def _bank_with_dead(self, tmp):
        trunk = PR.add_premise(tmp + "/d", "trunk holds",
                               created="2026-10-11")
        s = dict(FILLED)
        s["failure signature"] = "Name: partition-search. If you see X, stop."
        s["premises"] = f"- {trunk}"
        write_dossier(tmp, "d", "dead.md", s, "2026-10-11-dead")
        write_dossier(tmp, "d", "live.md", dict(FILLED), "2026-10-11-live")
        PR.kill_premise(Path(tmp) / "d", trunk, "field-test-note")
        D.rebuild_index(Path(tmp) / "d")

    def test_recall_excludes_dead_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank_with_dead(tmp)
            r = garm("recall", "--task", "partition search", "--dir", "d",
                     # v0.2.11: the live dossier scores 0.00 on this
                     # query, so the default threshold would hide it;
                     # this test is about dead-route exclusion.
                     "--min-score", "0", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("dead routes (premise killed), skipped: 1",
                          r.stdout)
            self.assertIn("2026-10-11-dead", r.stdout)  # in the dead block
            # the dead dossier must not appear in the ranked lines
            ranked = [l for l in r.stdout.splitlines()
                      if l.strip() and l.strip()[0].isdigit()]
            self.assertTrue(all("2026-10-11-dead" not in l for l in ranked))
            self.assertTrue(any("2026-10-11-live" in l for l in ranked))

    def test_recall_include_dead_marks(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._bank_with_dead(tmp)
            r = garm("recall", "--task", "partition search", "--dir", "d",
                     "--include-dead", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("[premise-dead]", r.stdout)

    def test_recall_includes_killer_dossier(self):
        # the dossier that killed the premise stays in default recall:
        # it holds the proof of falsity, not just a dead approach
        with tempfile.TemporaryDirectory() as tmp:
            trunk = PR.add_premise(tmp + "/d", "trunk holds",
                                   created="2026-10-11")
            s = dict(FILLED)
            s["failure signature"] = "Name: partition-search. If you see X, stop."
            s["premises"] = f"- {trunk}"
            write_dossier(tmp, "d", "killer.md", s, "2026-10-11-killer")
            write_dossier(tmp, "d", "live.md", dict(FILLED), "2026-10-11-live")
            PR.kill_premise(Path(tmp) / "d", trunk, "2026-10-11-killer")
            D.rebuild_index(Path(tmp) / "d")
            r = garm("recall", "--task", "partition search", "--dir", "d",
                     cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            ranked = [l for l in r.stdout.splitlines()
                      if l.strip() and l.strip()[0].isdigit()]
            self.assertTrue(any("2026-10-11-killer" in l for l in ranked))
            self.assertNotIn("dead routes", r.stdout)

    def test_cli_premise_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("premise", "add", "--statement", "trunk holds",
                     "--dir", "d", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            m = re.search(r"P-\d{8}-\d{3}", r.stdout)
            self.assertIsNotNone(m, r.stdout)
            pid = m.group(0)
            r = garm("premise", "list", "--dir", "d", cwd=tmp)
            self.assertIn("trunk holds", r.stdout)
            r = garm("premise", "kill", pid, "--by", "d-x",
                     "--dir", "d", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(f"killed: {pid}", r.stdout)
            r = garm("premise", "list", "--dir", "d", cwd=tmp)
            self.assertIn("KILLED", r.stdout)


class RegistryImportExportTest(unittest.TestCase):
    def test_export_copies_registry_and_import_merges(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            pid = PR.add_premise(src, "shared trunk", created="2026-10-11")
            s = dict(FILLED)
            s["premises"] = f"- {pid}"
            write_dossier(tmp, "src", "d.md", s, "2026-10-11-imp")
            out = Path(tmp) / "exp"
            res = D.export_bank(src, out)
            self.assertIn("premises.json", res["copied"])
            dest = Path(tmp) / "dest"
            res2 = D.import_dossiers(out, dest)
            self.assertIn(pid, res2["premises"]["added"])
            # re-import is a no-op for the registry
            res3 = D.import_dossiers(out, dest)
            self.assertEqual(res3["premises"]["added"], [])
            self.assertTrue(
                any(pid == i for i, _ in res3["premises"]["skipped"]))

    def test_import_collision_keeps_local(self):
        # v0.2.10: a collision with a different statement renames the
        # incoming premise (<pid>--from-<agent>) instead of dropping it.
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dest = Path(tmp) / "dest"
            PR.add_premise(src, "foreign claim", created="2026-10-11")
            PR.add_premise(dest, "local claim", created="2026-10-11")
            res = D.import_dossiers(src, dest)
            renamed = res["premises"]["renamed"]
            self.assertIn("P-20261011-001", renamed)
            new_pid = renamed["P-20261011-001"]
            self.assertTrue(new_pid.startswith("P-20261011-001--from-"))
            self.assertIn(new_pid, res["premises"]["added"])
            # local statement untouched
            reg = PR.load_registry(dest)["premises"]
            self.assertEqual(reg["P-20261011-001"]["statement"],
                             "local claim")
            # renamed premise carries the foreign statement
            self.assertEqual(reg[new_pid]["statement"], "foreign claim")


class PremiseEvidenceTest(unittest.TestCase):
    def test_kill_records_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid = PR.add_premise(tmp, "big route holds", created="2026-10-11")
            res = PR.kill_premise(tmp, pid, "dossier-x", evidence="proof")
            self.assertEqual(res["killed"], [pid])
            entry = PR.load_registry(tmp)["premises"][pid]
            self.assertEqual(entry["evidence"], "proof")
            rows = PR.list_premises(tmp)
            self.assertEqual(rows[0]["evidence"], "proof")

    def test_kill_rejects_bad_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid = PR.add_premise(tmp, "big route holds", created="2026-10-11")
            with self.assertRaises(ValueError):
                PR.kill_premise(tmp, pid, "dossier-x", evidence="vibes")

    def test_kill_without_evidence_leaves_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid = PR.add_premise(tmp, "big route holds", created="2026-10-11")
            PR.kill_premise(tmp, pid, "dossier-x")
            entry = PR.load_registry(tmp)["premises"][pid]
            self.assertIsNone(entry.get("evidence"))

    def test_evidence_inherited_by_descendants(self):
        with tempfile.TemporaryDirectory() as tmp:
            big = PR.add_premise(tmp, "big route", created="2026-10-11")
            small = PR.add_premise(tmp, "small route", depends_on=[big],
                                  created="2026-10-11")
            PR.kill_premise(tmp, big, "dossier-x", evidence="outside-work")
            data = PR.load_registry(tmp)
            self.assertEqual(data["premises"][small]["evidence"],
                             "outside-work")
            self.assertIn("inherited", data["premises"][small]["killed_by"])

    def test_merge_carries_evidence_and_rejects_bad(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            pid = PR.add_premise(src, "shared claim", created="2026-10-11")
            PR.kill_premise(src, pid, "dossier-x", evidence="our-tests")
            res = PR.merge_registry(dest, PR.load_registry(src))
            self.assertIn(pid, res["added"])
            self.assertEqual(
                PR.load_registry(dest)["premises"][pid]["evidence"],
                "our-tests")
            # malformed evidence value is skipped, not imported
            bad = {"premises": {"P-20261011-009": {
                "statement": "bad", "depends_on": [], "status": "killed",
                "killed_by": "x", "evidence": "vibes", "created": "2026-10-11"}}}
            res2 = PR.merge_registry(dest, bad)
            self.assertEqual(res2["added"], [])
            self.assertTrue(any("evidence" in r for _, r in res2["skipped"]))

    def test_cli_kill_evidence_flag_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("premise", "add", "--statement", "big route holds",
                     "--dir", "d", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            m = re.search(r"P-\d{8}-\d{3}", r.stdout)
            self.assertIsNotNone(m, r.stdout)
            pid = m.group(0)
            r = garm("premise", "kill", pid, "--by", "d-x",
                     "--evidence", "outside-work", "--dir", "d", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("[evidence: outside-work]", r.stdout)
            r = garm("premise", "list", "--dir", "d", cwd=tmp)
            self.assertIn("[evidence: outside-work]", r.stdout)

    def test_cli_rejects_bad_evidence_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("premise", "add", "--statement", "big route holds",
                     "--dir", "d", cwd=tmp)
            m = re.search(r"P-\d{8}-\d{3}", r.stdout)
            pid = m.group(0)
            r = garm("premise", "kill", pid, "--by", "d-x",
                     "--evidence", "vibes", "--dir", "d", cwd=tmp)
            self.assertNotEqual(r.returncode, 0)

    def test_help_uses_plain_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = garm("premise", "kill", "--help", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("trunk", r.stdout.lower())
            self.assertIn("big route", r.stdout.lower())


if __name__ == "__main__":
    unittest.main()
