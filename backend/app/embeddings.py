"""Embedding backend for the Policy RAG index.

Preferred backend: sentence-transformers/all-MiniLM-L6-v2 (local, free, no
per-call cost). Some sandboxed/offline environments cannot reach the
Hugging Face Hub to download model weights on first run, so this module
transparently falls back to a deterministic TF-IDF + SVD embedding fit on
the policy corpus itself. The active backend is recorded in
`backend/models/embedding_config.json` so ingestion and query-time encoding
always agree on which one is in use.

To force the production embedding model once network access to Hugging Face
is available, delete `backend/models/embedding_config.json` and re-run
`scripts/ingest_policies.py` — it will retry sentence-transformers first.
"""
import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

_MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
# Overridable so tests can fit/save a throwaway embedder without clobbering
# the real dev/prod model artifacts checked into backend/models/.
CONFIG_PATH = Path(os.getenv("EMBEDDING_CONFIG_PATH", str(_MODELS_DIR / "embedding_config.json")))
TFIDF_PATH = Path(os.getenv("TFIDF_EMBEDDER_PATH", str(_MODELS_DIR / "tfidf_embedder.joblib")))
EMBED_DIM_TFIDF = 256

# Hard override to skip sentence-transformers/torch entirely (~300-500MB just
# to import), for memory-constrained hosts like a Render free-tier instance
# (512MB total). Set FORCE_TFIDF_EMBEDDINGS=true to guarantee the lightweight
# path is used instead of risking an OOM kill mid-request.
FORCE_TFIDF = os.getenv("FORCE_TFIDF_EMBEDDINGS", "").strip().lower() in {"1", "true", "yes"}


def _read_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _write_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


@lru_cache
def _try_sentence_transformer():
    if FORCE_TFIDF:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return model
    except Exception:
        return None


class _TfidfEmbedder:
    """Deterministic offline embedder: TF-IDF -> TruncatedSVD -> L2-normalize."""

    def __init__(self):
        self.vectorizer = None
        self.svd = None

    def fit(self, texts: list[str]) -> np.ndarray:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), max_features=4000, stop_words="english"
        )
        tfidf = self.vectorizer.fit_transform(texts)
        n_components = min(EMBED_DIM_TFIDF, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
        n_components = max(n_components, 2)
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        vecs = self.svd.fit_transform(tfidf)
        return self._normalize(vecs)

    def transform(self, texts: list[str]) -> np.ndarray:
        tfidf = self.vectorizer.transform(texts)
        vecs = self.svd.transform(tfidf)
        return self._normalize(vecs)

    @staticmethod
    def _normalize(vecs: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms

    def save(self, path: Path) -> None:
        joblib.dump({"vectorizer": self.vectorizer, "svd": self.svd}, path)

    @classmethod
    def load(cls, path: Path) -> "_TfidfEmbedder":
        obj = cls()
        data = joblib.load(path)
        obj.vectorizer = data["vectorizer"]
        obj.svd = data["svd"]
        return obj


@lru_cache
def _load_tfidf_embedder() -> _TfidfEmbedder:
    return _TfidfEmbedder.load(TFIDF_PATH)


def embed_texts(texts: list[str], fit: bool = False) -> list[list[float]]:
    """Embed a batch of texts. Pass fit=True only from the ingestion script,
    when (re)building the index from the full corpus."""
    cfg = _read_config()

    # Once the index has been built with the TF-IDF fallback, keep using it
    # for query-time encoding too (a real ST model would produce vectors in
    # a different, incompatible space).
    if not fit and cfg.get("backend") == "tfidf-svd":
        embedder = _load_tfidf_embedder()
        return embedder.transform(texts).tolist()

    st_model = _try_sentence_transformer()
    if st_model is not None:
        if fit:
            _write_config({"backend": "sentence-transformers", "dim": 384})
        vecs = st_model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs).tolist()

    # Offline fallback
    if fit:
        embedder = _TfidfEmbedder()
        vecs = embedder.fit(texts)
        embedder.save(TFIDF_PATH)
        _write_config({"backend": "tfidf-svd", "dim": int(vecs.shape[1])})
        _load_tfidf_embedder.cache_clear()
        return vecs.tolist()

    if not TFIDF_PATH.exists():
        raise RuntimeError(
            "No embedding backend is ready yet. Run scripts/ingest_policies.py first."
        )
    embedder = _load_tfidf_embedder()
    return embedder.transform(texts).tolist()


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def embedding_backend_name() -> str:
    st_model = _try_sentence_transformer()
    if st_model is not None:
        return "sentence-transformers/all-MiniLM-L6-v2"
    return _read_config().get("backend", "unconfigured")
