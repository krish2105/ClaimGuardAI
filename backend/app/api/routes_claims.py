import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, aliased

from app.api.schemas import (
    ClaimDetail,
    ClaimListItem,
    ClaimListResponse,
    ClaimSubmitRequest,
    ClaimSubmitResponse,
    DecisionTraceResponse,
    TraceStep,
)
from app.db.models import Claim, Decision
from app.db.session import get_db
from app.rate_limit import limiter
from app.services.document_generator import render_claim_document
from app.services.pipeline_stream import run_and_broadcast

router = APIRouter(tags=["claims"])


def _new_claim_id() -> str:
    return f"CLM-U{uuid.uuid4().hex[:8].upper()}"


def _latest_decision(db: Session, claim_id: str) -> Decision | None:
    return (
        db.query(Decision)
        .filter(Decision.claim_id == claim_id)
        .order_by(desc(Decision.decision_id))
        .first()
    )


@router.post("/claims/submit", response_model=ClaimSubmitResponse)
@limiter.limit("10/minute")
async def submit_claim(request: Request, payload: ClaimSubmitRequest, background_tasks: BackgroundTasks):
    claim_id = _new_claim_id()

    if payload.raw_document_text:
        doc_text = payload.raw_document_text
    else:
        missing = [
            f for f in ("patient_id", "provider_id", "plan_type", "treatment_date",
                        "icd10_codes", "cpt_codes", "billed_amount")
            if getattr(payload, f) in (None, [], "")
        ]
        if missing:
            raise HTTPException(400, f"Missing required fields to build a claim document: {missing}")
        doc_text = render_claim_document(
            patient_id=payload.patient_id,
            provider_id=payload.provider_id,
            plan_type=payload.plan_type,
            treatment_date=payload.treatment_date,
            icd10_codes=payload.icd10_codes,
            cpt_codes=payload.cpt_codes,
            billed_amount=payload.billed_amount,
            notes=payload.notes or "",
        )

    asyncio.create_task(run_and_broadcast(claim_id, doc_text))

    return ClaimSubmitResponse(claim_id=claim_id, ws_url=f"/ws/claims/{claim_id}/stream")


@router.get("/claims", response_model=ClaimListResponse)
def list_claims(
    status: str | None = None,
    plan_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    # A claim can be re-processed (e.g. re-submitted for a demo), leaving
    # multiple Decision rows — always join only the most recent one so a
    # claim never appears more than once in the queue.
    latest_decision_ids = (
        db.query(
            Decision.claim_id,
            func.max(Decision.decision_id).label("latest_decision_id"),
        )
        .group_by(Decision.claim_id)
        .subquery()
    )
    LatestDecision = aliased(Decision)

    query = (
        db.query(Claim, LatestDecision)
        .outerjoin(latest_decision_ids, latest_decision_ids.c.claim_id == Claim.claim_id)
        .outerjoin(LatestDecision, LatestDecision.decision_id == latest_decision_ids.c.latest_decision_id)
        .order_by(desc(Claim.created_at))
    )
    if plan_type:
        query = query.filter(Claim.plan_type == plan_type)
    if status:
        query = query.filter(LatestDecision.final_decision == status)

    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    items = [
        ClaimListItem(
            claim_id=claim.claim_id,
            patient_id=claim.patient_id,
            provider_id=claim.provider_id,
            plan_type=claim.plan_type,
            billed_amount=float(claim.billed_amount) if claim.billed_amount is not None else None,
            treatment_date=claim.treatment_date,
            fraud_score=float(decision.fraud_score) if decision and decision.fraud_score is not None else None,
            coding_flags=(decision.coding_flags if decision else []) or [],
            decision_recommendation=decision.decision_recommendation if decision else None,
            final_decision=decision.final_decision if decision else None,
            created_at=claim.created_at,
        )
        for claim, decision in rows
    ]
    return ClaimListResponse(total=total, items=items)


@router.get("/claims/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: str, db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")
    decision = _latest_decision(db, claim_id)

    return ClaimDetail(
        claim_id=claim.claim_id,
        patient_id=claim.patient_id,
        provider_id=claim.provider_id,
        plan_type=claim.plan_type,
        billed_amount=float(claim.billed_amount) if claim.billed_amount is not None else None,
        treatment_date=claim.treatment_date,
        icd10_codes=claim.icd10_codes or [],
        cpt_codes=claim.cpt_codes or [],
        approved_amount=float(claim.approved_amount) if claim.approved_amount is not None else None,
        prior_auth_required=claim.prior_auth_required,
        prior_auth_obtained=claim.prior_auth_obtained,
        fraud_score=float(decision.fraud_score) if decision and decision.fraud_score is not None else None,
        coding_flags=(decision.coding_flags if decision else []) or [],
        decision_recommendation=decision.decision_recommendation if decision else None,
        final_decision=decision.final_decision if decision else None,
        fraud_top_features=(decision.fraud_top_features if decision else []) or [],
        retrieved_clauses=(decision.retrieved_clauses if decision else []) or [],
        decision_rationale=decision.decision_rationale if decision else None,
        escalation_reason=decision.escalation_reason if decision else None,
        created_at=claim.created_at,
    )


@router.get("/claims/{claim_id}/decision-trace", response_model=DecisionTraceResponse)
def get_decision_trace(claim_id: str, db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")
    decision = _latest_decision(db, claim_id)
    if not decision:
        return DecisionTraceResponse(claim_id=claim_id, final_decision=None, agent_trace=[])

    return DecisionTraceResponse(
        claim_id=claim_id,
        final_decision=decision.final_decision,
        agent_trace=[TraceStep(**step) for step in (decision.agent_trace or [])],
    )
