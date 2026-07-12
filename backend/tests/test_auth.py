"""Tests for the real, backend-enforced auth layer: login issues a JWT,
protected routes reject anonymous/wrong-role callers, and the admin seed
endpoints accept either the bootstrap token or a logged-in admin's JWT."""
from datetime import date

from fastapi.testclient import TestClient

from app.db.models import Claim, Escalation
from app.main import app

client = TestClient(app)


def _login(username: str, password: str):
    return client.post("/auth/login", json={"username": username, "password": password})


def test_login_succeeds_with_correct_credentials(demo_users):
    cred = demo_users["adjuster"]
    res = _login(cred["username"], cred["password"])
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "adjuster"
    assert body["username"] == cred["username"]
    assert body["access_token"]


def test_login_fails_with_wrong_password(demo_users):
    cred = demo_users["adjuster"]
    res = _login(cred["username"], "not-the-password")
    assert res.status_code == 401


def test_login_fails_for_unknown_username(demo_users):
    res = _login("does-not-exist", "whatever")
    assert res.status_code == 401


def test_me_returns_identity_for_a_valid_token(demo_users):
    cred = demo_users["admin"]
    token = _login(cred["username"], cred["password"]).json()["access_token"]
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == {"username": cred["username"], "role": "admin"}


def test_me_rejects_missing_token():
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_rejects_garbage_token():
    res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert res.status_code == 401


def _make_pending_escalation(db, claim_id: str) -> int:
    db.add(Claim(claim_id=claim_id, patient_id="PAT-AUTH", plan_type="Basic",
                  treatment_date=date(2026, 1, 15), billed_amount=100.0))
    escalation = Escalation(claim_id=claim_id, status="pending")
    db.add(escalation)
    db.commit()
    db.refresh(escalation)
    return escalation.escalation_id


def test_resolve_escalation_rejects_anonymous_caller(demo_users, clean_db):
    escalation_id = _make_pending_escalation(clean_db, "CLM-AUTH-1")
    res = client.post(f"/escalations/{escalation_id}/resolve", json={"adjuster_decision": "approve"})
    assert res.status_code == 401


def test_resolve_escalation_succeeds_for_logged_in_adjuster_and_records_resolver(demo_users, clean_db):
    escalation_id = _make_pending_escalation(clean_db, "CLM-AUTH-2")
    cred = demo_users["adjuster"]
    token = _login(cred["username"], cred["password"]).json()["access_token"]

    res = client.post(
        f"/escalations/{escalation_id}/resolve",
        json={"adjuster_decision": "approve", "adjuster_notes": "looks fine"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "resolved"
    assert body["resolved_by"] == cred["username"]


def test_admin_seed_endpoint_accepts_a_logged_in_admin_without_the_token(demo_users):
    cred = demo_users["admin"]
    token = _login(cred["username"], cred["password"]).json()["access_token"]
    res = client.post("/admin/seed/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_admin_seed_endpoint_rejects_a_logged_in_adjuster_without_the_token(demo_users):
    cred = demo_users["adjuster"]
    token = _login(cred["username"], cred["password"]).json()["access_token"]
    res = client.post("/admin/seed/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
