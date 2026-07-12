"""Runs a claim through the compiled LangGraph pipeline and persists the
resulting decision + audit trail to Postgres."""
from app.agents.graph import claim_pipeline
from app.agents.state import ClaimState
from app.db.models import AuditLog, Claim, Decision, Escalation, Provider
from app.db.session import SessionLocal


def run_pipeline(claim_id: str, raw_document_text: str) -> ClaimState:
    initial = ClaimState(claim_id=claim_id, raw_document_text=raw_document_text)
    result = claim_pipeline.invoke(initial)
    state = result if isinstance(result, ClaimState) else ClaimState(**result)
    _persist(state)
    return state


def _upsert_provider(db, state: ClaimState) -> None:
    """A live claim submission can name a provider_id that was never
    seeded (e.g. a genuinely new provider). claims.provider_id has a FK
    to providers, so insert a minimal placeholder row rather than crash
    the whole pipeline persistence step over a missing lookup row."""
    if not state.provider_id or db.get(Provider, state.provider_id) is not None:
        return
    db.add(Provider(
        provider_id=state.provider_id,
        specialty=None,
        claim_volume_30d_avg=0,
        flagged_history_count=0,
    ))
    db.flush()


def _upsert_claim(db, state: ClaimState) -> None:
    """Live claim submissions (unlike the CSV-seeded ones) have no row in
    `claims` yet — create one from the Intake Agent's extracted fields so
    the Decision/Escalation foreign keys resolve."""
    if db.get(Claim, state.claim_id) is not None:
        return
    _upsert_provider(db, state)
    db.add(Claim(
        claim_id=state.claim_id,
        # patient_id is NOT NULL; fall back to a placeholder when Intake
        # failed to extract it, so the failed claim is still auditable.
        patient_id=state.patient_id or "UNKNOWN",
        provider_id=state.provider_id,
        icd10_codes=state.icd10_codes,
        cpt_codes=state.cpt_codes,
        billed_amount=state.billed_amount,
        treatment_date=state.treatment_date,
        plan_type=state.plan_type,
        prior_auth_required=None,
        prior_auth_obtained=None,
        fraud_label=None,
    ))
    db.flush()


def _persist(state: ClaimState) -> None:
    db = SessionLocal()
    try:
        _upsert_claim(db, state)

        decision = Decision(
            claim_id=state.claim_id,
            coding_flags=state.coding_flags,
            fraud_score=state.fraud_score,
            fraud_top_features=[f.model_dump() for f in state.fraud_top_features],
            retrieved_clauses=[c.model_dump() for c in state.retrieved_clauses],
            decision_recommendation=state.decision_recommendation,
            decision_rationale=state.decision_rationale,
            final_decision=state.final_decision,
            escalation_reason=state.escalation_reason,
            agent_trace=[step.model_dump(mode="json") for step in state.agent_trace],
        )
        db.add(decision)

        db.add(AuditLog(
            claim_id=state.claim_id,
            event_type="pipeline_completed",
            event_payload={"final_decision": state.final_decision},
        ))

        if state.final_decision == "escalated":
            existing_pending = (
                db.query(Escalation)
                .filter(Escalation.claim_id == state.claim_id, Escalation.status == "pending")
                .first()
            )
            if existing_pending is None:
                db.add(Escalation(claim_id=state.claim_id, status="pending"))

        db.commit()
    finally:
        db.close()
