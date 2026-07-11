"""Qdrant client factory.

Uses an embedded on-disk Qdrant instance (no server process required) unless
QDRANT_URL is set, in which case it connects to a real Qdrant server — the
Docker Compose service, or a managed cluster such as Qdrant Cloud (pass
QDRANT_API_KEY too, if the cluster requires one). This lets the whole
project run with zero external services for local development/demo, while
still matching the "self-hosted Qdrant" architecture decision for a full
deployment.
"""
from functools import lru_cache

from qdrant_client import QdrantClient

from app.config import get_settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    return QdrantClient(path=settings.qdrant_local_path)
