from app.agents.decision_router import decision_router_node
from app.agents.state import ClaimState


def _state(**overrides):
    base = dict(
        claim_id="CLM-D1",
        raw_document_text="",
        coding_flags=[],
        fraud_score=10.0,
        decision_recommendation="approve",
    )
    base.update(overrides)
    return ClaimState(**base)


def test_high_fraud_score_always_escalates_even_if_rag_approves():
    state = _state(fraud_score=90.0, decision_recommendation="approve")
    result = decision_router_node(state)
    assert result.final_decision == "escalated"
    assert "fraud score" in result.escalation_reason


def test_rag_escalate_recommendation_propagates():
    state = _state(fraud_score=5.0, decision_recommendation="escalate")
    result = decision_router_node(state)
    assert result.final_decision == "escalated"
    assert "Policy RAG" in result.escalation_reason


def test_diagnosis_procedure_mismatch_always_escalates():
    state = _state(fraud_score=5.0, decision_recommendation="approve", coding_flags=["diagnosis_procedure_mismatch"])
    result = decision_router_node(state)
    assert result.final_decision == "escalated"
    assert "Coding Agent" in result.escalation_reason


def test_low_fraud_and_approve_auto_approves():
    state = _state(fraud_score=20.0, decision_recommendation="approve")
    result = decision_router_node(state)
    assert result.final_decision == "auto_approved"


def test_moderate_fraud_with_approve_falls_through_to_auto_denied():
    # approve recommendation but fraud score isn't low enough to auto-approve,
    # and not high enough to escalate -> conservative default is auto_denied
    state = _state(fraud_score=60.0, decision_recommendation="approve")
    result = decision_router_node(state)
    assert result.final_decision == "auto_denied"


def test_deny_recommendation_results_in_auto_denied():
    state = _state(fraud_score=10.0, decision_recommendation="deny")
    result = decision_router_node(state)
    assert result.final_decision == "auto_denied"


def test_boundary_fraud_score_exactly_at_threshold_does_not_escalate():
    # threshold is "> 75", so exactly 75.0 should NOT trigger the fraud escalation
    state = _state(fraud_score=75.0, decision_recommendation="deny")
    result = decision_router_node(state)
    assert result.final_decision == "auto_denied"


def test_trace_is_appended():
    state = _state()
    result = decision_router_node(state)
    assert result.agent_trace[-1].agent == "decision_router"
