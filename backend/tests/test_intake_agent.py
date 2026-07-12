from datetime import date

from app.agents.intake_agent import intake_agent_node
from app.agents.state import ClaimState
from app.services.document_generator import render_claim_document


def _good_document():
    return render_claim_document(
        patient_id="PAT-0001",
        provider_id="PRV-001",
        plan_type="Basic",
        treatment_date="2026-01-15",
        icd10_codes=["I10"],
        cpt_codes=["93000"],
        billed_amount=220.0,
    )


def test_intake_extracts_all_fields_from_well_formed_document():
    state = ClaimState(claim_id="CLM-T1", raw_document_text=_good_document())
    result = intake_agent_node(state)

    assert result.patient_id == "PAT-0001"
    assert result.provider_id == "PRV-001"
    assert result.plan_type == "Basic"
    assert result.icd10_codes == ["I10"]
    assert result.cpt_codes == ["93000"]
    assert result.billed_amount == 220.0
    assert result.treatment_date == date(2026, 1, 15)
    assert result.error is None
    assert result.agent_trace[-1].agent == "intake"
    assert result.agent_trace[-1].status == "completed"


def test_intake_escalates_on_missing_fields():
    broken_doc = "Some illegible garbage that matches no expected label at all."
    state = ClaimState(claim_id="CLM-T2", raw_document_text=broken_doc)
    result = intake_agent_node(state)

    assert result.error is not None
    assert result.final_decision == "escalated"
    assert result.escalation_reason == "intake_extraction_failed"
    assert result.agent_trace[-1].status == "failed"


def test_intake_rejects_invalid_plan_type():
    doc = _good_document().replace("Plan Type: Basic", "Plan Type: Bronze")
    state = ClaimState(claim_id="CLM-T3", raw_document_text=doc)
    result = intake_agent_node(state)

    # "Bronze" isn't a valid plan type, so it's treated as missing -> escalate
    assert result.final_decision == "escalated"
