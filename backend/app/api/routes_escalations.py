from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, aliased

from app.api.schemas import EscalationItem, EscalationResolveRequest
from app.auth import require_role
from app.db.models import Claim, Decision, Escalation, User
from app.db.session import get_db
from app.rate_limit import limiter

router = APIRouter(tags=["escalations"])


def _latest_decision_subquery(db: Session):
    return (
        db.query(Decision.claim_id, func.max(Decision.decision_id).label("latest_decision_id"))
        .group_by(Decision.claim_id)
        .subquery()
    )


@router.get("/escalations", response_model=list[EscalationItem])
def list_escalations(status: str = "pending", db: Session = Depends(get_db)):
    latest_decision_ids = _latest_decision_subquery(db)
    LatestDecision = aliased(Decision)

    query = (
        db.query(Escalation, Claim, LatestDecision)
        .join(Claim, Claim.claim_id == Escalation.claim_id)
        .outerjoin(latest_decision_ids, latest_decision_ids.c.claim_id == Escalation.claim_id)
        .outerjoin(LatestDecision, LatestDecision.decision_id == latest_decision_ids.c.latest_decision_id)
        .order_by(desc(Escalation.created_at))
    )
    if status and status != "all":
        query = query.filter(Escalation.status == status)

    results = []
    for escalation, claim, decision in query.all():
        results.append(EscalationItem(
            escalation_id=escalation.escalation_id,
            claim_id=escalation.claim_id,
            status=escalation.status,
            adjuster_decision=escalation.adjuster_decision,
            adjuster_notes=escalation.adjuster_notes,
            resolved_by=escalation.resolved_by,
            created_at=escalation.created_at,
            resolved_at=escalation.resolved_at,
            fraud_score=float(decision.fraud_score) if decision and decision.fraud_score is not None else None,
            escalation_reason=decision.escalation_reason if decision else None,
            plan_type=claim.plan_type,
            billed_amount=float(claim.billed_amount) if claim.billed_amount is not None else None,
        ))
    return results


@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationItem)
@limiter.limit("30/minute")
def resolve_escalation(
    request: Request,
    escalation_id: int,
    payload: EscalationResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("adjuster", "admin")),
):
    escalation = db.get(Escalation, escalation_id)
    if not escalation:
        raise HTTPException(404, f"Escalation {escalation_id} not found")

    escalation.status = "resolved"
    escalation.adjuster_decision = payload.adjuster_decision
    escalation.adjuster_notes = payload.adjuster_notes
    escalation.resolved_by = user.username
    escalation.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(escalation)

    claim = db.get(Claim, escalation.claim_id)
    decision = (
        db.query(Decision)
        .filter(Decision.claim_id == escalation.claim_id)
        .order_by(desc(Decision.decision_id))
        .first()
    )

    return EscalationItem(
        escalation_id=escalation.escalation_id,
        claim_id=escalation.claim_id,
        status=escalation.status,
        adjuster_decision=escalation.adjuster_decision,
        adjuster_notes=escalation.adjuster_notes,
        resolved_by=escalation.resolved_by,
        created_at=escalation.created_at,
        resolved_at=escalation.resolved_at,
        fraud_score=float(decision.fraud_score) if decision and decision.fraud_score is not None else None,
        escalation_reason=decision.escalation_reason if decision else None,
        plan_type=claim.plan_type if claim else None,
        billed_amount=float(claim.billed_amount) if claim and claim.billed_amount is not None else None,
    )
