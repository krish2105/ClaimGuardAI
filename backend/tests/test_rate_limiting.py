"""The admin seed endpoints and /claims/submit are the most expensive routes
in the API (they shell out to model training / the full LLM pipeline), so
they carry a tighter per-IP rate limit than the app-wide default. This test
locks in that the limit actually rejects requests once exceeded."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_admin_seed_endpoint_is_rate_limited_after_five_calls_per_minute():
    statuses = [
        client.post("/admin/seed/dataset", headers={"X-Admin-Token": "wrong"}).status_code
        for _ in range(7)
    ]
    assert statuses[:5] == [403] * 5
    assert statuses[5:] == [429, 429]


def test_claims_submit_is_rate_limited_after_ten_calls_per_minute():
    statuses = [
        client.post("/claims/submit", json={"raw_document_text": "test"}).status_code
        for _ in range(12)
    ]
    assert statuses[:10] == [200] * 10
    assert statuses[10:] == [429, 429]
