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
    curl -X POST https://<backend>/admin/seed/batch    -H "X-Admin-Token: <token>"

Run them in that order; each is safe to retry on its own if it fails.
"""
from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings

router = APIRouter(tags=["admin"])


def _check_token(x_admin_token: str) -> None:
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
async def seed_dataset(x_admin_token: str = Header(default="")):
    _check_token(x_admin_token)
    from scripts import generate_dataset

    return _run("generate_dataset", generate_dataset.main)


@router.post("/admin/seed/database")
async def seed_database(x_admin_token: str = Header(default="")):
    _check_token(x_admin_token)
    from scripts import seed_db

    return _run("seed_db", seed_db.main)


@router.post("/admin/seed/policies")
async def seed_policies(x_admin_token: str = Header(default="")):
    _check_token(x_admin_token)
    from scripts import ingest_policies

    return _run("ingest_policies", ingest_policies.main)


@router.post("/admin/seed/model")
async def seed_model(x_admin_token: str = Header(default="")):
    _check_token(x_admin_token)
    from scripts import train_fraud_model

    return _run("train_fraud_model", train_fraud_model.main)


@router.post("/admin/seed/batch")
async def seed_batch(x_admin_token: str = Header(default="")):
    _check_token(x_admin_token)
    from scripts import run_pipeline_batch

    return _run("run_pipeline_batch", run_pipeline_batch.main)
