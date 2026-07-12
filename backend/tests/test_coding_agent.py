from datetime import date

from app.agents.coding_agent import coding_agent_node
from app.agents.state import ClaimState


def _state(icd10, cpt, billed, claim_id="CLM-C1"):
    return ClaimState(
        claim_id=claim_id,
        raw_document_text="",
        patient_id="PAT-0001",
        provider_id="PRV-001",
        icd10_codes=icd10,
        cpt_codes=cpt,
        billed_amount=billed,
        treatment_date=date(2026, 1, 15),
        plan_type="Basic",
    )


def test_coherent_normal_claim_has_no_flags():
    state = _state(["I10"], ["93000"], 220.0)
    result = coding_agent_node(state)
    assert result.coding_flags == []
    assert result.coding_confidence is not None
    assert result.agent_trace[-1].agent == "coding"


def test_diagnosis_procedure_mismatch_is_flagged():
    state = _state(["M54.5"], ["87880"], 69.73)  # back pain + pediatric strep test
    result = coding_agent_node(state)
    assert "diagnosis_procedure_mismatch" in result.coding_flags


def test_amount_outlier_is_flagged():
    # 93000 (ECG) typical band is 150-300 AED; 5000 is a huge outlier
    state = _state(["I10"], ["93000"], 5000.0)
    result = coding_agent_node(state)
    assert "amount_outlier" in result.coding_flags
