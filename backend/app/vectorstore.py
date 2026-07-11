"""Qdrant client factory.

Uses an embedded on-disk Qdrant instance (no server process required) unless
QDRANT_URL is set, in which case it connects to a real Qdrant server (e.g.
the Docker Compose service). This lets the whole project run with zero
external services for local development/demo, while still matching the
"self-hosted Qdrant" architecture decision for a full Docker deployment.
"""
from functools import lru_cache

from qdrant_client import QdrantClient

from app.config import get_settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)
    return QdrantClient(path=settings.qdrant_local_path)
