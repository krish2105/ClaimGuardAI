"""Test configuration. Sets env vars BEFORE any `app.*` module is imported
(conftest.py is always collected first by pytest), so every module that
reads settings at import time — notably app/db/session.py, which builds
the SQLAlchemy engine as soon as it's imported — picks up the test values."""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Fresh-per-session temp dirs rather than a fixed path under tests/: reusing a
# fixed path let stale local Qdrant/embedder storage from a previous run
# collide with the current run's schema and fail with a confusing pydantic
# validation error, so each test session gets an isolated throwaway dir.
_TEST_STATE_DIR = Path(tempfile.mkdtemp(prefix="claimguard_test_"))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://claimguard:claimguard@localhost:5432/claimguard_test",
)
os.environ.setdefault("QDRANT_URL", "")
os.environ.setdefault("QDRANT_LOCAL_PATH", str(_TEST_STATE_DIR / "qdrant"))
os.environ.setdefault("QDRANT_COLLECTION", "claimguard_policies_test")
os.environ.setdefault("ANTHROPIC_API_KEY", "")  # force mock mode — deterministic, no network
os.environ.setdefault("ADMIN_SEED_TOKEN", "test-admin-token")
os.environ.setdefault("FORCE_TFIDF_EMBEDDINGS", "true")  # fast + deterministic, no HF download
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3100")

# Tests re-fit the TF-IDF embedder on a tiny synthetic corpus; without this
# override that fit would overwrite the real backend/models/ artifacts.
os.environ.setdefault("EMBEDDING_CONFIG_PATH", str(_TEST_STATE_DIR / "embedding_config.json"))
os.environ.setdefault("TFIDF_EMBEDDER_PATH", str(_TEST_STATE_DIR / "tfidf_embedder.joblib"))

import pytest  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.models import Claim, Provider, User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    """Create a clean schema once for the whole test session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def clean_db(db_session):
    """Truncate all tables before a test that needs a known-empty DB."""
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
    yield db_session


@pytest.fixture()
def sample_provider(clean_db):
    provider = Provider(
        provider_id="PRV-TEST",
        specialty="General Practice",
        claim_volume_30d_avg=10,
        flagged_history_count=0,
    )
    clean_db.add(provider)
    clean_db.commit()
    return provider


@pytest.fixture()
def settings():
    return get_settings()


@pytest.fixture()
def demo_users(clean_db):
    """A known adjuster + admin account with plaintext passwords available
    for login-flow tests, and their ORM rows for tests that just need a
    logged-in-as identity without going through /auth/login."""
    creds = {
        "adjuster": {"username": "test-adjuster", "password": "adjuster-pass"},
        "admin": {"username": "test-admin", "password": "admin-pass"},
    }
    for role, cred in creds.items():
        user = User(username=cred["username"], password_hash=hash_password(cred["password"]), role=role)
        clean_db.add(user)
    clean_db.commit()
    return creds
