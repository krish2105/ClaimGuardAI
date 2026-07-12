"""Tests for the Policy RAG Agent's core differentiator: the citation
guardrail. A recommendation is only trusted if every clause_id it cites was
actually present in the retrieved set — this is the mechanism that stops the
agent from inventing a policy rule, and it's the single most important
behavior in the whole pipeline to have covered by a test."""
from datetime import date
from unittest.mock import patch

from app.agents import policy_rag_agent
from app.agents.state import ClaimState, RetrievedClause


def _state():
    return ClaimState(
        claim_id="CLM-R1",
        raw_document_text="",
        patient_id="PAT-0001",
        provider_id="PRV-001",
        icd10_codes=["I10"],
        cpt_codes=["93000"],
        billed_amount=220.0,
        treatment_date=date(2026, 1, 15),
        plan_type="Basic",
        coding_flags=[],
        fraud_score=10.0,
    )


def _retrieved():
    return [
        RetrievedClause(
            clause_id="CG-BASIC-001",
            text="Sample benefits clause text.",
            source_doc="basic_plan_benefits.md",
            plan_type="Basic",
            category="benefits",
            similarity=0.8,
        )
    ]


def test_valid_citation_is_trusted():
    state = _state()
    with patch.object(policy_rag_agent, "_retrieve", return_value=_retrieved()):
        result = policy_rag_agent.policy_rag_agent_node(state)

    assert result.decision_recommendation == "approve"
    assert result.cited_clause_ids == ["CG-BASIC-001"]
    assert result.retrieved_clauses[0].clause_id == "CG-BASIC-001"


def test_hallucinated_citation_forces_escalation():
    """If the LLM (or mock) cites a clause_id that was never retrieved, the
    guardrail must override it to escalate rather than trust the citation."""
    state = _state()
    fake_llm_result = {
        "decision_recommendation": "approve",
        "decision_rationale": "Per [CG-MADE-UP-999], this is covered.",
        "cited_clause_ids": ["CG-MADE-UP-999"],  # not in the retrieved set
        "confidence": 0.9,
    }

    class _FakeClient:
        mock_mode = True

        def call_json(self, **kwargs):
            return fake_llm_result

    with patch.object(policy_rag_agent, "_retrieve", return_value=_retrieved()), \
         patch.object(policy_rag_agent, "get_llm_client", return_value=_FakeClient()):
        result = policy_rag_agent.policy_rag_agent_node(state)

    assert result.decision_recommendation == "escalate"
    assert result.cited_clause_ids == []
    assert result.rag_confidence == 0.0
    assert "CG-MADE-UP-999" in result.decision_rationale


def test_no_retrieved_clauses_forces_escalation():
    state = _state()
    with patch.object(policy_rag_agent, "_retrieve", return_value=[]):
        result = policy_rag_agent.policy_rag_agent_node(state)

    assert result.decision_recommendation == "escalate"
    assert result.retrieved_clauses == []


def test_weak_similarity_forces_escalation_in_mock_mode():
    weak_clause = RetrievedClause(
        clause_id="CG-WEAK-001",
        text="Barely relevant text.",
        source_doc="somewhere.md",
        plan_type="Basic",
        category="benefits",
        similarity=0.05,  # below MIN_SIMILARITY_FOR_GROUNDING
    )
    state = _state()
    with patch.object(policy_rag_agent, "_retrieve", return_value=[weak_clause]):
        result = policy_rag_agent.policy_rag_agent_node(state)

    assert result.decision_recommendation == "escalate"
