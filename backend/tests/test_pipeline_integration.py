"""End-to-end test of the full 5-agent LangGraph pipeline, exercising real
DB lookups and a real (test-isolated) Qdrant index, in mock LLM mode."""
import pytest

from app.services.document_generator import render_claim_document
from app.services.pipeline_service import run_pipeline


@pytest.fixture(autouse=True)
def _ensure_policy_index(tmp_path_factory):
    """Ingests a tiny synthetic policy corpus into the test-isolated Qdrant
    collection so the Policy RAG Agent has something real to retrieve,
    without depending on whatever the dev environment happens to have
    ingested into its own (different) collection/path."""
    import sys
    from pathlib import Path

    backend_root = Path(__file__).resolve().parents[1]
    policies_dir = tmp_path_factory.mktemp("policies")
    (policies_dir / "basic_plan_benefits.md").write_text(
        "---\n"
        "doc_id: basic_plan_benefits\n"
        "plan_type: Basic\n"
        "category: benefits\n"
        "effective_date: 2026-01-01\n"
        "---\n\n"
        "## Clause CG-BASIC-001: Outpatient Consultation Coverage\n\n"
        "Outpatient physician consultations including ECG (CPT 93000) are "
        "covered at 80% for members on the Basic plan.\n"
    )

    sys.path.insert(0, str(backend_root))
    from scripts.ingest_policies import main as ingest_main

    import scripts.ingest_policies as ingest_module

    original_dir = ingest_module.POLICIES_DIR
    ingest_module.POLICIES_DIR = policies_dir
    try:
        ingest_main()
    finally:
        ingest_module.POLICIES_DIR = original_dir


def test_pipeline_runs_end_to_end_for_a_clean_claim(clean_db):
    doc = render_claim_document(
        patient_id="PAT-0001",
        provider_id="PRV-001",
        plan_type="Basic",
        treatment_date="2026-01-15",
        icd10_codes=["I10"],
        cpt_codes=["93000"],
        billed_amount=220.0,
    )
    state = run_pipeline("CLM-PIPE-1", doc)

    assert state.error is None
    assert state.final_decision in {"auto_approved", "auto_denied", "escalated"}
    assert len(state.agent_trace) == 5
    assert [s.agent for s in state.agent_trace] == [
        "intake", "coding", "fraud_scoring", "policy_rag", "decision_router",
    ]


def test_pipeline_escalates_a_diagnosis_procedure_mismatch(clean_db):
    doc = render_claim_document(
        patient_id="PAT-0002",
        provider_id="PRV-002",
        plan_type="Basic",
        treatment_date="2026-01-15",
        icd10_codes=["M54.5"],
        cpt_codes=["87880"],
        billed_amount=69.73,
    )
    state = run_pipeline("CLM-PIPE-2", doc)

    assert "diagnosis_procedure_mismatch" in state.coding_flags
    assert state.final_decision == "escalated"


def test_pipeline_short_circuits_on_intake_failure(clean_db):
    state = run_pipeline("CLM-PIPE-3", "completely illegible garbage document")
    assert state.final_decision == "escalated"
    assert state.escalation_reason == "intake_extraction_failed"
    # only the intake step should have run before the pipeline short-circuited
    assert [s.agent for s in state.agent_trace] == ["intake"]


def test_pipeline_persists_decision_to_db(clean_db):
    from app.db.models import Decision

    doc = render_claim_document(
        patient_id="PAT-0003",
        provider_id="PRV-003",
        plan_type="Enhanced",
        treatment_date="2026-02-01",
        icd10_codes=["I10"],
        cpt_codes=["93000"],
        billed_amount=250.0,
    )
    run_pipeline("CLM-PIPE-4", doc)

    saved = clean_db.query(Decision).filter(Decision.claim_id == "CLM-PIPE-4").first()
    assert saved is not None
    assert saved.final_decision is not None
    assert saved.agent_trace and len(saved.agent_trace) == 5
