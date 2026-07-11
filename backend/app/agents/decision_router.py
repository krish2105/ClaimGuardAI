"""Agent 5 — Decision Router (deterministic, not an LLM call).

A high fraud score always earns a human look, by design — a conservative
default for a regulated domain, per ARCHITECTURE.md Sections 4.6 and 15 (Q5).
"""
import time

from app.agents.state import ClaimState

FRAUD_ESCALATION_THRESHOLD = 75.0
FRAUD_AUTO_APPROVE_CEILING = 40.0


def _build_escalation_reason(state: ClaimState) -> str:
    reasons = []
    if state.fraud_score is not None and state.fraud_score > FRAUD_ESCALATION_THRESHOLD:
        reasons.append(f"fraud score {state.fraud_score}/100 exceeds the {FRAUD_ESCALATION_THRESHOLD} threshold")
    if state.decision_recommendation == "escalate":
        reasons.append("Policy RAG Agent recommended escalation")
    if "diagnosis_procedure_mismatch" in state.coding_flags:
        reasons.append("Coding Agent flagged a diagnosis-procedure mismatch")
    return "; ".join(reasons) or "escalation criteria met"


def decision_router_node(state: ClaimState) -> ClaimState:
    t0 = time.time()

    high_fraud = state.fraud_score is not None and state.fraud_score > FRAUD_ESCALATION_THRESHOLD
    rag_escalate = state.decision_recommendation == "escalate"
    coding_mismatch = "diagnosis_procedure_mismatch" in state.coding_flags

    if high_fraud or rag_escalate or coding_mismatch:
        state.final_decision = "escalated"
        state.escalation_reason = _build_escalation_reason(state)
    elif state.decision_recommendation == "approve" and (
        state.fraud_score is not None and state.fraud_score < FRAUD_AUTO_APPROVE_CEILING
    ):
        state.final_decision = "auto_approved"
    else:
        state.final_decision = "auto_denied"

    duration_ms = (time.time() - t0) * 1000
    state.log(
        "decision_router",
        f"Final decision: {state.final_decision}"
        + (f" ({state.escalation_reason})" if state.escalation_reason else ""),
        detail={
            "fraud_score": state.fraud_score,
            "decision_recommendation": state.decision_recommendation,
            "coding_flags": state.coding_flags,
        },
        duration_ms=duration_ms,
    )
    return state
