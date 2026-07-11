"""One-time data bootstrap endpoint for hosts with no shell access (e.g. a
Render/Railway free-tier deployment with a private, internal-only Qdrant
service). Disabled unless ADMIN_SEED_TOKEN is set — intentionally fails
closed rather than defaulting to open, since it wipes and reloads the
claims table.

    curl -X POST https://<your-backend>/admin/seed -H "X-Admin-Token: <token>"
    curl https://<your-backend>/admin/seed/status
"""
import asyncio

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings

router = APIRouter(tags=["admin"])

_state: dict = {"status": "idle", "detail": ""}


def _run_seed_sync() -> None:
    global _state
    try:
        # Imported lazily so a normal API request never pays for loading
        # pandas/xgboost/etc. unless this endpoint is actually used.
        from scripts import (
            generate_dataset,
            ingest_policies,
            run_pipeline_batch,
            seed_db,
            train_fraud_model,
        )

        _state = {"status": "running", "detail": "generating synthetic dataset"}
        generate_dataset.main()

        _state["detail"] = "seeding Postgres"
        seed_db.main()

        _state["detail"] = "ingesting policy corpus into Qdrant"
        ingest_policies.main()

        _state["detail"] = "training the XGBoost fraud model"
        train_fraud_model.main()

        _state["detail"] = "running all seeded claims through the pipeline"
        run_pipeline_batch.main()

        _state = {"status": "done", "detail": "seed complete"}
    except Exception as exc:  # noqa: BLE001 - surface any failure via /status
        _state = {"status": "error", "detail": str(exc)}


@router.post("/admin/seed")
async def trigger_seed(x_admin_token: str = Header(default="")):
    settings = get_settings()
    if not settings.admin_seed_token or x_admin_token != settings.admin_seed_token:
        raise HTTPException(403, "Missing or invalid X-Admin-Token")
    if _state["status"] == "running":
        return {"status": "already_running", "detail": _state["detail"]}

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_seed_sync)
    return {"status": "started"}


@router.get("/admin/seed/status")
async def seed_status():
    return _state
