"""Opt-in semantic retrieval lane (Tier 2, v0.2.9).

BM25 matches words. This lane matches *meaning*: a small embedding model
turns text into vectors, and cosine similarity finds dossiers that mean
the same thing with different words ("reciprocals" vs "unit fractions"
— the paraphrase the 2026-10-14 transfer test proved BM25 can never
match).

Design rules (the whole reason this ships as Tier 2, not v1):
  * Opt-in only. ``garm recall`` behaves exactly as before unless
    ``--semantic`` is passed (or the MCP ``semantic`` param, or
    ``GARM_SEMANTIC=1`` for the hook). The stdlib-only default path is
    untouched — this module is imported nowhere unless the flag is set.
  * No silent fallback. Flag set but fastembed missing -> hard error
    naming the install command. Model not warmed -> hard error naming
    ``garm semantic warmup``. Garm never pretends to be semantic.
  * Never downloads mid-turn. The model is fetched once by the explicit
    ``garm semantic warmup`` command and cached; recall only reads the
    cache. A hook blocking on a model download would be a real failure
    mode — this design forbids it.
  * Inspectable. The result keeps the semantic subscore next to
    the BM25 subscores, and recall marks hits the meaning lane ranked
    above the BM25 lane with ``[semantic]``.

Dependency: ``fastembed`` (Qdrant, Apache-2.0, ONNX Runtime — no
PyTorch, no GPU). Install with ``pip install garm[semantic]``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

MODEL_NAME = "BAAI/bge-small-en-v1.5"
CACHE_FILENAME = "embeddings.json"

# bge models encode queries and passages asymmetrically; the prefixes
# preserve retrieval direction (a query is not a passage).
_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "


class SemanticError(RuntimeError):
    """The semantic lane was requested but cannot run. The message always
    tells the user the exact command that fixes it."""


def _import_fastembed():
    try:
        from fastembed import TextEmbedding
    except ImportError:
        raise SemanticError(
            "semantic retrieval needs the fastembed package, which is not "
            "installed. Install it with: pip install garm[semantic] "
            "(or: pip install fastembed)"
        )
    return TextEmbedding


def _cache_dir() -> Path:
    """Durable cache dir for the model files.

    fastembed >= 0.9 defaults to ``tempfile/fastembed_cache`` — ephemeral,
    gone on reboot. We pin it under ``~/.cache/fastembed`` (via
    :func:`_ensure_cache_env`) unless the user set ``FASTEMBED_CACHE_PATH``
    themselves, which we always respect.
    """
    custom = os.environ.get("FASTEMBED_CACHE_PATH")
    if custom:
        return Path(custom)
    return Path.home() / ".cache" / "fastembed"


def _ensure_cache_env() -> None:
    """Point fastembed at the durable cache dir. Must run before any
    ``TextEmbedding()`` construction (fastembed reads the env var then).
    setdefault: an explicit user choice always wins."""
    os.environ.setdefault("FASTEMBED_CACHE_PATH", str(_cache_dir()))


def _model_cache_subdir() -> str:
    """Exact on-disk folder for MODEL_NAME inside the cache dir, e.g.
    ``models--Qdrant--bge-small-en-v1.5-onnx-Q``.

    Resolved from fastembed's own model registry (model name -> source
    repo), not hardcoded: if a fastembed upgrade remaps the source repo,
    we look in the right place instead of re-downloading blindly or —
    worse — false-positive on a stale folder.
    """
    TextEmbedding = _import_fastembed()
    source = MODEL_NAME
    try:
        models = TextEmbedding.list_supported_models()
    except Exception:
        models = []
    for m in models or []:
        name = m.get("model") if isinstance(m, dict) else getattr(
            m, "model", None)
        if name == MODEL_NAME:
            sources = m.get("sources") if isinstance(m, dict) else getattr(
                m, "sources", None)
            source = (sources or {}).get("hf") or MODEL_NAME
            break
    return "models--" + source.replace("/", "--")


def model_is_cached() -> bool:
    """True if the model files are already on disk AND complete. Never
    downloads.

    Checks fastembed's exact cache directory for this model (resolved
    via :func:`_model_cache_subdir`, case-insensitive for legacy
    layouts) and validates every file's size against fastembed's own
    ``files_metadata.json`` — the same check fastembed runs before
    deciding to re-download. A partial download (or a dangling symlink,
    which is how HF-hub cache entries look when their blob is missing)
    therefore reads as "not cached", never as a green light. A
    *different* cached model can never false-positive either.
    """
    base = _cache_dir()
    if not base.is_dir():
        return False
    want = _model_cache_subdir().lower()
    for child in base.iterdir():
        if not (child.is_dir() and child.name.lower() == want):
            continue
        if _cache_complete(child):
            return True
    return False


def _cache_complete(model_dir: Path) -> bool:
    """Every file fastembed expects is present at the expected size.
    ``stat()`` follows the snapshots->blobs symlinks, so a dangling link
    (missing blob) fails the check."""
    meta_path = model_dir / "files_metadata.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _cache_fallback_check(model_dir)
    if not isinstance(meta, dict) or not meta:
        return False
    for rel, info in meta.items():
        try:
            size = (model_dir / rel).stat().st_size
        except OSError:
            return False
        if size != info.get("size"):
            return False
    return True


def _cache_fallback_check(model_dir: Path) -> bool:
    """No metadata to validate against (older layout): accept only a
    real, substantial model file. Heuristic, documented as such — a
    79-byte stub must never pass."""
    for p in model_dir.rglob("*.onnx"):
        try:
            if p.stat().st_size > 1_000_000:
                return True
        except OSError:
            continue
    return False


def warmup() -> str:
    """Download (first run) and load the embedding model. Explicit only —
    never called from the recall path."""
    _ensure_cache_env()
    TextEmbedding = _import_fastembed()
    model = TextEmbedding(MODEL_NAME)  # downloads on first run
    dim = len(list(model.embed(["probe"]))[0])
    return (f"semantic model ready: {MODEL_NAME} "
            f"({dim}-dim), cached under {_cache_dir()}")


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity in pure Python. fastembed returns normalized
    vectors, so this is ~the dot product; we normalize anyway."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def _content_hash(sig_text: str, task_text: str, body_text: str = "") -> str:
    return hashlib.sha1(
        f"{MODEL_NAME}\0{sig_text}\0{task_text}\0{body_text}".encode("utf-8")
    ).hexdigest()


class SemanticIndex:
    """Embedding cache + scorer for one dossier bank directory.

    Vectors live in ``<bank>/.garm/embeddings.json``, keyed by dossier
    id, and are recomputed when the dossier text changes (hash
    mismatch). The model itself is loaded lazily on first use — and
    only after :meth:`ensure_ready` has confirmed it is warmed.
    """

    def __init__(self, bank_dir: str | Path) -> None:
        self.bank_dir = Path(bank_dir)
        self._model = None
        self._cache_path = self.bank_dir / ".garm" / CACHE_FILENAME
        self._cache: dict = {}
        self._dirty = False

    # -- readiness ----------------------------------------------------
    def ensure_ready(self) -> None:
        """Raise SemanticError (with the fixing command) unless the lane
        can actually run right now. Never downloads."""
        _import_fastembed()  # raises with install command if missing
        if not model_is_cached():
            raise SemanticError(
                "semantic model is not downloaded yet. "
                "Run once: garm semantic warmup"
            )

    # -- model ---------------------------------------------------------
    def _get_model(self):
        if self._model is None:
            _ensure_cache_env()
            TextEmbedding = _import_fastembed()
            # ensure_ready() ran first, so this must not download — and
            # HF_HUB_OFFLINE=1 makes that a hard guarantee rather than
            # an assumption: any cache problem raises instead of hitting
            # the network mid-turn. (Warmup is the only path that may
            # download, and it never sets this flag.)
            prev = os.environ.get("HF_HUB_OFFLINE")
            os.environ["HF_HUB_OFFLINE"] = "1"
            try:
                self._model = TextEmbedding(MODEL_NAME)
            except Exception as exc:
                raise SemanticError(
                    "could not load the cached semantic model "
                    f"({exc}); re-run: garm semantic warmup"
                ) from exc
            finally:
                if prev is None:
                    del os.environ["HF_HUB_OFFLINE"]
                else:
                    os.environ["HF_HUB_OFFLINE"] = prev
        return self._model

    # -- cache ----------------------------------------------------------
    def _load_cache(self) -> None:
        if self._cache_path.is_file():
            try:
                self._cache = json.loads(
                    self._cache_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                self._cache = {}
        if not isinstance(self._cache, dict):
            self._cache = {}

    def _save_cache(self) -> None:
        if not self._dirty:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps(self._cache, indent=1), encoding="utf-8")
        self._dirty = False

    def _vectors_for(self, dossier_id: str, sig_text: str,
                     task_text: str, body_text: str = ""
                     ) -> tuple[list[float], list[float], list[float]]:
        """(sig_vector, task_vector, body_vector), from cache or freshly
        embedded. v0.2.10 added the body vector — the body sections are
        now indexed (see build_index_entry), so the meaning lane sees
        them too."""
        if not self._cache and not self._dirty:
            self._load_cache()
        want = _content_hash(sig_text, task_text, body_text)
        hit = self._cache.get(dossier_id)
        if (isinstance(hit, dict) and hit.get("hash") == want
                and isinstance(hit.get("sig"), list)
                and isinstance(hit.get("task"), list)
                and isinstance(hit.get("body"), list)):
            return hit["sig"], hit["task"], hit["body"]
        model = self._get_model()
        vecs = list(model.embed([
            _PASSAGE_PREFIX + sig_text,
            _PASSAGE_PREFIX + task_text,
            _PASSAGE_PREFIX + body_text,
        ]))
        sig_v, task_v, body_v = [list(map(float, v)) for v in vecs]
        self._cache[dossier_id] = {
            "model": MODEL_NAME, "hash": want,
            "sig": sig_v, "task": task_v, "body": body_v,
        }
        self._dirty = True
        return sig_v, task_v, body_v

    # -- scoring ---------------------------------------------------------
    def score_entries(self, query_text: str,
                      entries: list[dict]) -> dict[str, float]:
        """Semantic subscore per dossier id, shaped like the BM25 total:
        signature cosine counts double, task cosine single. Range
        [-3, 3]; higher means closer in meaning."""
        if not entries:
            return {}
        model = self._get_model()
        qv = list(map(float, list(
            model.embed([_QUERY_PREFIX + query_text]))[0]))
        out: dict[str, float] = {}
        for e in entries:
            sig_v, task_v, body_v = self._vectors_for(
                e["id"], e.get("signature") or "", e.get("task") or "",
                e.get("body") or "")
            out[e["id"]] = (2 * cosine(qv, sig_v) + cosine(qv, task_v)
                            + cosine(qv, body_v))
        self._save_cache()
        return out


def rank_ids(scores: dict[str, float]) -> dict[str, int]:
    """1-based ranks from a score dict. Ties break by id: deterministic,
    so the ranking is reproducible."""
    ordered = sorted(scores, key=lambda i: (-scores[i], i))
    return {doc_id: n + 1 for n, doc_id in enumerate(ordered)}
