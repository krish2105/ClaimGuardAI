"""One-time data bootstrap endpoints for hosts with no shell access (e.g. a
Render/Railway free-tier deployment). Disabled unless ADMIN_SEED_TOKEN is
set — intentionally fails closed rather than defaulting to open, since this
wipes and reloads the claims table.

Split into separate, synchronous steps (rather than one big background job)
specifically because a memory-constrained free-tier instance can get killed
and silently restarted mid-job, which wiped an earlier in-memory-only
progress tracker without a trace. Each call below blocks until that one step
finishes and returns its own success/failure directly, so a crash on one
step doesn't lose track of the ones before it:

    curl -X POST https://<backend>/admin/seed/dataset  -H "X-Admin-Token: <token>"
    curl -X POST https://<backend>/admin/seed/database -H "X-Admin-Token: <token>"
    curl -X POST https://<backend>/admin/seed/policies -H "X-Admin-Token: <token>"
    curl -X POST https://<backend>/admin/seed/model    -H "X-Admin-Token: <token>"
    curl -X POST https://<backend>/admin/seed/users    -H "X-Admin-Token: <token>"
    curl -X POST https://<backend>/admin/seed/batch    -H "X-Admin-Token: <token>"

Run them in that order; each is safe to retry on its own if it fails.

Authorization accepts EITHER the X-Admin-Token header above OR a logged-in
admin's JWT (Authorization: Bearer ...) — the token is what lets you
bootstrap a brand new deployment where no user accounts exist yet (see
seed_users below); once an admin account exists, being logged in as that
admin is sufficient on its own.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.auth import get_current_user_optional
from app.config import get_settings
from app.db.models import User
from app.rate_limit import limiter

router = APIRouter(tags=["admin"])


def _check_token(x_admin_token: str, user: User | None) -> None:
    if user is not None and user.role == "admin":
        return
    settings = get_settings()
    if not settings.admin_seed_token or x_admin_token != settings.admin_seed_token:
        raise HTTPException(403, "Missing or invalid X-Admin-Token")


def _run(step_name: str, fn) -> dict:
    try:
        fn()
        return {"status": "done", "step": step_name}
    except Exception as exc:  # noqa: BLE001 - surface the real error to the caller
        raise HTTPException(500, f"{step_name} failed: {exc}") from exc


@router.post("/admin/seed/dataset")
@limiter.limit("5/minute")
async def seed_dataset(
    request: Request, x_admin_token: str = Header(default=""), user: User | None = Depends(get_current_user_optional)
):
    _check_token(x_admin_token, user)
    from scripts import generate_dataset

    return _run("generate_dataset", generate_dataset.main)


@router.post("/admin/seed/database")
@limiter.limit("5/minute")
async def seed_database(
    request: Request, x_admin_token: str = Header(default=""), user: User | None = Depends(get_current_user_optional)
):
    _check_token(x_admin_token, user)
    from scripts import seed_db

    return _run("seed_db", seed_db.main)


@router.post("/admin/seed/policies")
@limiter.limit("5/minute")
async def seed_policies(
    request: Request, x_admin_token: str = Header(default=""), user: User | None = Depends(get_current_user_optional)
):
    _check_token(x_admin_token, user)
    from scripts import ingest_policies

    return _run("ingest_policies", ingest_policies.main)


@router.post("/admin/seed/model")
@limiter.limit("5/minute")
async def seed_model(
    request: Request, x_admin_token: str = Header(default=""), user: User | None = Depends(get_current_user_optional)
):
    _check_token(x_admin_token, user)
    from scripts import train_fraud_model

    return _run("train_fraud_model", train_fraud_model.main)


@router.post("/admin/seed/users")
@limiter.limit("5/minute")
async def seed_users(
    request: Request, x_admin_token: str = Header(default=""), user: User | None = Depends(get_current_user_optional)
):
    _check_token(x_admin_token, user)
    from scripts import seed_users as seed_users_script

    return _run("seed_users", seed_users_script.main)


@router.post("/admin/seed/batch")
@limiter.limit("5/minute")
async def seed_batch(
    request: Request, x_admin_token: str = Header(default=""), user: User | None = Depends(get_current_user_optional)
):
    _check_token(x_admin_token, user)
    from scripts import run_pipeline_batch

    return _run("run_pipeline_batch", run_pipeline_batch.main)
