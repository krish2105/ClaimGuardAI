from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.api.schemas import CodingFlagCount, FraudTrendPoint, FraudTrendsResponse
from app.db.models import Claim, Decision
from app.db.session import get_db

router = APIRouter(tags=["analytics"])


@router.get("/analytics/fraud-trends", response_model=FraudTrendsResponse)
def fraud_trends(db: Session = Depends(get_db)):
    # Only the most recent Decision per claim counts — a claim reprocessed
    # for a demo shouldn't be double-counted in the trend/flag aggregates.
    latest_decision_ids = (
        db.query(Decision.claim_id, func.max(Decision.decision_id).label("latest_decision_id"))
        .group_by(Decision.claim_id)
        .subquery()
    )
    LatestDecision = aliased(Decision)

    rows = (
        db.query(Claim, LatestDecision)
        .join(latest_decision_ids, latest_decision_ids.c.claim_id == Claim.claim_id)
        .join(LatestDecision, LatestDecision.decision_id == latest_decision_ids.c.latest_decision_id)
        .all()
    )

    monthly = defaultdict(lambda: {"total": 0, "escalated": 0, "auto_approved": 0, "auto_denied": 0, "fraud_scores": []})
    coding_flag_counter: Counter = Counter()
    plan_type_counter: Counter = Counter()
    total_escalated = 0

    for claim, decision in rows:
        period = claim.treatment_date.strftime("%Y-%m") if claim.treatment_date else "unknown"
        bucket = monthly[period]
        bucket["total"] += 1
        if decision.final_decision == "escalated":
            bucket["escalated"] += 1
            total_escalated += 1
        elif decision.final_decision == "auto_approved":
            bucket["auto_approved"] += 1
        elif decision.final_decision == "auto_denied":
            bucket["auto_denied"] += 1
        if decision.fraud_score is not None:
            bucket["fraud_scores"].append(float(decision.fraud_score))

        for flag in decision.coding_flags or []:
            coding_flag_counter[flag] += 1
        plan_type_counter[claim.plan_type] += 1

    trend = [
        FraudTrendPoint(
            period=period,
            total_claims=b["total"],
            escalated=b["escalated"],
            auto_approved=b["auto_approved"],
            auto_denied=b["auto_denied"],
            avg_fraud_score=round(sum(b["fraud_scores"]) / len(b["fraud_scores"]), 1) if b["fraud_scores"] else 0.0,
        )
        for period, b in sorted(monthly.items())
    ]

    total = len(rows)
    return FraudTrendsResponse(
        trend=trend,
        coding_flag_frequency=[
            CodingFlagCount(flag=flag, count=count)
            for flag, count in coding_flag_counter.most_common()
        ],
        escalation_rate=round(total_escalated / total, 4) if total else 0.0,
        total_claims_processed=total,
        plan_type_breakdown=dict(plan_type_counter),
    )
