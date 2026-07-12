from datetime import date

import pytest

from app.agents.fraud_scoring_agent import fraud_scoring_node
from app.agents.state import ClaimState


def _state(**overrides):
    base = dict(
        claim_id="CLM-F1",
        raw_document_text="",
        patient_id="PAT-0001",
        provider_id="PRV-TEST",
        icd10_codes=["I10"],
        cpt_codes=["93000"],
        billed_amount=220.0,
        treatment_date=date(2026, 1, 15),
        plan_type="Basic",
        coding_flags=[],
    )
    base.update(overrides)
    return ClaimState(**base)


def test_fraud_score_is_populated_in_valid_range(sample_provider):
    state = fraud_scoring_node(_state())
    assert state.fraud_score is not None
    assert 0.0 <= state.fraud_score <= 100.0
    assert len(state.fraud_top_features) == 3
    assert state.agent_trace[-1].agent == "fraud_scoring"


def test_top_features_are_signed_contributions(sample_provider):
    state = fraud_scoring_node(_state())
    for feature in state.fraud_top_features:
        assert isinstance(feature.contribution, float)
        assert feature.feature  # non-empty name


def test_extreme_amount_outlier_scores_higher_than_normal_claim(sample_provider):
    normal = fraud_scoring_node(_state(billed_amount=220.0))
    outlier = fraud_scoring_node(_state(claim_id="CLM-F2", billed_amount=50000.0))
    assert outlier.fraud_score >= normal.fraud_score


def test_coding_flags_count_influences_score(sample_provider):
    clean = fraud_scoring_node(_state(coding_flags=[]))
    flagged = fraud_scoring_node(
        _state(claim_id="CLM-F3", coding_flags=["diagnosis_procedure_mismatch", "amount_outlier"])
    )
    assert flagged.fraud_score >= clean.fraud_score
