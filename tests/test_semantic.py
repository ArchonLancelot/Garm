"""v0.2.9: Tier 2 opt-in semantic lane.

Covers (all without the real model — fastembed is never imported here):
  RRF fusion math over per-lane ranks (stub backend), boosts folded
  into both lanes, return_ranks shape, default-path scores unchanged
  (sem == 0.0), embedding cache hit/miss/invalidation with a fake
  model, the guarded-import error message (fastembed genuinely hidden),
  warmup gating in ensure_ready, MCP wiring keys, and CLI parser wiring
  for --semantic / semantic warmup.

The real-model gate — the transfer test's paraphrase drill ranking the
P2 autopsy top-3 — is a manual QA step, not a unit test: it needs the
model download and the shipped banks.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from garm import dossier as D  # noqa: E402
from garm import retrieval as RU  # noqa: E402
from garm import semantic as SEM  # noqa: E402

# v0.2.11: a clean checkout has neither optional extra, and tests that
# need the real package must SKIP, not error — a red "FAILED (errors=3)"
# on first checkout is the wrong first impression for this project.
# Availability is probed, never imported for real use here (the
# "fastembed genuinely hidden" guard test still simulates absence).
FASTEMBED_AVAILABLE = importlib.util.find_spec("fastembed") is not None
MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None


def make_bank(tmp, dossiers):
    """dossiers: list of (id, task, signature). Returns bank dir."""
    bank = Path(tmp) / "bank"
    bank.mkdir(parents=True, exist_ok=True)
    for i, (did, task, signature) in enumerate(dossiers):
        sections = {
            "what was tried": f"Tried thing {i}.",
            "root cause": f"Cause {i}.",
            "failure signature": signature,
            "blocking constraint": f"Constraint {i}.",
            "what retrieval would have changed": f"Change {i}.",
            "confidence": "High.",
        }
        text = D.render_template(
            task=task, agent="test-agent", failure_class="reasoning-error",
            id_=did, sections=sections)
        (bank / f"{did}.md").write_text(text, encoding="utf-8")
    return bank


class StubBackend:
    """Fake semantic backend: fixed sem scores, records calls."""

    def __init__(self, scores):
        self._scores = scores
        self.calls = []

    def score_entries(self, query_text, entries):
        self.calls.append(query_text)
        return {e["id"]: self._scores[e["id"]] for e in entries}


class TestSemanticRanking(unittest.TestCase):
    def _entries(self):
        # BM25 ranking for query "alpha": d1 (3 sig hits) > d2 (1) > d3 (0)
        return [
            {"id": "d1", "sig_keywords": ["alpha"] * 3, "keywords": [],
             "signature": "s1", "task": "t1",
             "confirmed_fixes": 0, "confirmed_insights": 0},
            {"id": "d2", "sig_keywords": ["alpha"], "keywords": [],
             "signature": "s2", "task": "t2",
             "confirmed_fixes": 0, "confirmed_insights": 0},
            {"id": "d3", "sig_keywords": [], "keywords": [],
             "signature": "s3", "task": "t3",
             "confirmed_fixes": 0, "confirmed_insights": 0},
        ]

    def test_semantic_lane_leads(self):
        entries = self._entries()
        # lexical alone ranks d1 first
        lex = RU.score_corpus(["alpha"], entries)
        self.assertEqual(
            sorted(lex, key=lambda i: -lex[i][0])[0], "d1")
        # semantic lane disagrees: d2 > d3 > d1. In semantic mode the
        # meaning lane leads (--semantic is an explicit statement that
        # lexical failed for this query), so the order follows the
        # semantic ranks and the BM25 winner does not veto it.
        stub = StubBackend({"d1": -1.0, "d2": 2.9, "d3": 0.5})
        scores, ranks = RU.score_corpus(
            ["alpha"], entries, semantic=stub,
            query_text="alpha query", return_ranks=True)
        order = sorted(scores, key=lambda i: -scores[i][0])
        self.assertEqual(order, ["d2", "d3", "d1"])
        self.assertEqual(ranks["d2"], (2, 1))
        self.assertEqual(ranks["d1"], (1, 3))
        # total is the semantic score plus boosts (interpretable scale)
        self.assertAlmostEqual(scores["d2"][0], 2.9, places=9)
        self.assertAlmostEqual(scores["d3"][0], 0.5, places=9)
        self.assertAlmostEqual(scores["d1"][0], -1.0, places=9)
        # semantic subscore is reported for inspectability
        self.assertAlmostEqual(scores["d2"][4], 2.9)
        # BM25 subscores still reported alongside
        self.assertGreater(scores["d1"][1], scores["d2"][1])

    def test_boosts_fold_into_semantic_lane(self):
        entries = self._entries()
        entries[2]["confirmed_fixes"] = 5  # d3: weakest lexically
        stub = StubBackend({"d1": 0.0, "d2": 0.0, "d3": 0.1})
        scores, ranks = RU.score_corpus(
            ["alpha"], entries, semantic=stub,
            query_text="q", return_ranks=True)
        # +5 in the semantic lane puts d3 first there -> ranked first
        order = sorted(scores, key=lambda i: -scores[i][0])
        self.assertEqual(order[0], "d3")
        self.assertEqual(ranks["d3"][1], 1)  # sem_rank
        self.assertEqual(scores["d3"][5], 5)  # fix boost reported

    def test_default_path_unchanged(self):
        entries = self._entries()
        scores = RU.score_corpus(["alpha"], entries)
        for e in entries:
            total, ss, ts, bs, sem, fix_b, ins_b = scores[e["id"]]
            self.assertEqual(sem, 0.0)
            self.assertAlmostEqual(total, 2 * ss + ts + fix_b + ins_b)
        # and the default call shape is still just the dict
        self.assertIsInstance(scores, dict)

    def test_rank_ids_deterministic(self):
        ranks = SEM.rank_ids({"b": 1.0, "a": 1.0, "c": 0.5})
        self.assertEqual(ranks, {"a": 1, "b": 2, "c": 3})


class FakeModel:
    def __init__(self, dim=4):
        self.dim = dim
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        # deterministic pseudo-vectors from the text
        out = []
        for t in texts:
            h = abs(hash(t))
            out.append([float((h >> (8 * i)) & 0xFF) / 255
                        for i in range(self.dim)])
        return out


class TestSemanticCache(unittest.TestCase):
    def _index(self, tmp):
        idx = SEM.SemanticIndex(Path(tmp) / "bank")
        fake = FakeModel()
        idx._get_model = lambda: fake  # bypass fastembed entirely
        return idx, fake

    def test_cache_hit_avoids_reembed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            idx, fake = self._index(tmp)
            entries = [{"id": "d1", "signature": "sig one",
                        "task": "task one"}]
            idx.score_entries("query text", entries)
            calls_after_first = fake.calls
            self.assertGreater(calls_after_first, 0)
            idx2, fake2 = self._index(tmp)
            # fresh index object, same bank dir -> cache hit on disk
            idx2._get_model = lambda: fake2
            scores = idx2.score_entries("query text", entries)
            self.assertEqual(fake2.calls, 1)  # only the query embedded
            self.assertIn("d1", scores)

    def test_edit_invalidates_cache(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            idx, fake = self._index(tmp)
            entries = [{"id": "d1", "signature": "sig one",
                        "task": "task one"}]
            idx.score_entries("q", entries)
            before = fake.calls
            entries[0]["signature"] = "sig one CHANGED"
            idx.score_entries("q", entries)
            self.assertGreater(fake.calls, before)

    def test_cosine_sanity(self):
        self.assertAlmostEqual(SEM.cosine([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(SEM.cosine([1, 0], [0, 1]), 0.0)
        self.assertEqual(SEM.cosine([0, 0], [1, 1]), 0.0)


class TestGuards(unittest.TestCase):
    def test_missing_fastembed_error_names_install(self):
        # genuinely hide fastembed: None in sys.modules -> ImportError
        sentinel = object()
        old = sys.modules.get("fastembed", sentinel)
        sys.modules["fastembed"] = None
        try:
            with self.assertRaises(SEM.SemanticError) as cm:
                SEM._import_fastembed()
        finally:
            if old is sentinel:
                del sys.modules["fastembed"]
            else:
                sys.modules["fastembed"] = old
        self.assertIn("pip install garm[semantic]", str(cm.exception))

    def test_ensure_ready_blocks_unwarmed_model(self):
        idx = SEM.SemanticIndex("/tmp/definitely-not-a-bank")
        with mock.patch.object(SEM, "_import_fastembed",
                               return_value=object()), \
             mock.patch.object(SEM, "model_is_cached", return_value=False):
            with self.assertRaises(SEM.SemanticError) as cm:
                idx.ensure_ready()
        self.assertIn("garm semantic warmup", str(cm.exception))

    def test_ensure_ready_passes_when_warmed(self):
        idx = SEM.SemanticIndex("/tmp/definitely-not-a-bank")
        with mock.patch.object(SEM, "_import_fastembed",
                               return_value=object()), \
             mock.patch.object(SEM, "model_is_cached", return_value=True):
            idx.ensure_ready()  # must not raise

    @unittest.skipUnless(FASTEMBED_AVAILABLE, "fastembed not installed")
    def test_model_is_cached_exact_dir(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            env = {"FASTEMBED_CACHE_PATH": tmp}
            subdir = SEM._model_cache_subdir()
            with mock.patch.dict("os.environ", env):
                self.assertFalse(SEM.model_is_cached())
                # a DIFFERENT cached model must not false-positive
                other = Path(tmp) / "models--other--model"
                other.mkdir()
                (other / "model.onnx").write_bytes(b"x")
                self.assertFalse(SEM.model_is_cached())
                # the real model dir, but with a size mismatch (partial
                # download) -> still not cached
                mine = Path(tmp) / subdir
                snap = mine / "snapshots" / "rev1"
                snap.mkdir(parents=True)
                blob = mine / "blobs" / "abc123"
                blob.parent.mkdir(parents=True)
                blob.write_bytes(b"too small")
                (snap / "model_optimized.onnx").symlink_to(blob)
                (mine / "files_metadata.json").write_text(json.dumps({
                    "snapshots/rev1/model_optimized.onnx":
                        {"size": 100, "blob_id": "abc123"},
                }))
                self.assertFalse(SEM.model_is_cached())
                # complete file -> cached
                blob.write_bytes(b"x" * 100)
                self.assertTrue(SEM.model_is_cached())


class TestWiring(unittest.TestCase):
    def test_cli_parses_semantic_flag(self):
        from garm import cli
        args = cli.build_parser().parse_args(
            ["recall", "--task", "x", "--semantic"])
        self.assertTrue(args.semantic)
        self.assertEqual(args.func, cli.cmd_recall)

    def test_cli_parses_semantic_warmup(self):
        from garm import cli
        args = cli.build_parser().parse_args(["semantic", "warmup"])
        self.assertEqual(args.func, cli.cmd_semantic_warmup)

    @unittest.skipUnless(MCP_AVAILABLE, "mcp package not installed")
    def test_mcp_recall_semantic_keys(self):
        import tempfile
        from mcp_server import server as S
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [("d1", "flaky checkout flow",
                                    "checkout intermittently fails")])
            fake_idx = mock.Mock()
            fake_idx.score_entries.return_value = {"d1": 1.5}
            fake_idx.ensure_ready.return_value = None
            with mock.patch.object(S.SEM, "SemanticIndex",
                                   return_value=fake_idx):
                out = S.recall_impl(
                    "flaky checkout", top=3, semantic=True,
                    dir=str(bank))
            import json
            rows = json.loads(out)
            self.assertEqual(len(rows), 1)
            self.assertIn("semantic_score", rows[0])
            self.assertIn("semantic_lane_first", rows[0])
            self.assertAlmostEqual(rows[0]["semantic_score"], 1.5)

    @unittest.skipUnless(MCP_AVAILABLE, "mcp package not installed")
    def test_mcp_recall_semantic_guard_propagates(self):
        import tempfile
        from mcp_server import server as S
        with tempfile.TemporaryDirectory() as tmp:
            bank = make_bank(tmp, [("d1", "flaky checkout flow",
                                    "checkout intermittently fails")])
            with mock.patch.object(
                    S.SEM.SemanticIndex, "ensure_ready",
                    side_effect=SEM.SemanticError("need warmup")):
                with self.assertRaises(SEM.SemanticError):
                    S.recall_impl("flaky checkout", semantic=True,
                                  dir=str(bank))


if __name__ == "__main__":
    unittest.main()
