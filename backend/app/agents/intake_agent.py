"""Agent 1 — Intake Agent.

Turns a raw claim document into a validated ClaimState. Uses Claude Haiku
for extraction (cost-controlled); falls back to a deterministic label:value
parser when running in mock mode. If required fields cannot be extracted,
the claim is routed straight to escalation per ARCHITECTURE.md Section 4.2.
"""
import re
import time
from datetime import datetime

from app.agents.llm_client import get_llm_client
from app.agents.state import ClaimState
from app.config import get_settings

SYSTEM_PROMPT = """You are the Intake Agent for ClaimGuard AI, a UAE health insurance claims system.
Extract the following fields from the claim document text below. Output ONLY valid JSON
matching this schema — no explanation, no markdown fences:

{
  "patient_id": string,
  "provider_id": string,
  "icd10_codes": [string],
  "cpt_codes": [string],
  "billed_amount": number,
  "treatment_date": "YYYY-MM-DD",
  "plan_type": "Basic" | "Enhanced" | "Thiqa" | "Comprehensive"
}

If a field is missing or illegible in the source text, use null for that field and do not guess.
"""

REQUIRED_FIELDS = [
    "patient_id", "provider_id", "icd10_codes", "cpt_codes",
    "billed_amount", "treatment_date", "plan_type",
]

_LABEL_PATTERNS = {
    "patient_id": r"Patient ID:\s*([A-Za-z0-9\-]+)",
    "provider_id": r"Provider ID:\s*([A-Za-z0-9\-]+)",
    "plan_type": r"Plan Type:\s*([A-Za-z]+)",
    "treatment_date": r"Treatment Date:\s*([0-9\-]+)",
    "icd10_codes": r"Diagnosis \(ICD-10\):\s*([A-Za-z0-9,\.\s]+?)(?:\n|$)",
    "cpt_codes": r"Procedure \(CPT\):\s*([A-Za-z0-9,\s]+?)(?:\n|$)",
    "billed_amount": r"Billed Amount:\s*AED\s*([0-9,\.]+)",
}

_VALID_PLAN_TYPES = {"Basic", "Enhanced", "Thiqa", "Comprehensive"}


def _mock_extract(document_text: str) -> dict:
    def find(key: str):
        m = re.search(_LABEL_PATTERNS[key], document_text)
        return m.group(1).strip() if m else None

    icd_raw = find("icd10_codes")
    cpt_raw = find("cpt_codes")
    billed_raw = find("billed_amount")
    plan_type = find("plan_type")

    return {
        "patient_id": find("patient_id"),
        "provider_id": find("provider_id"),
        "icd10_codes": [c.strip() for c in icd_raw.split(",")] if icd_raw else None,
        "cpt_codes": [c.strip() for c in cpt_raw.split(",")] if cpt_raw else None,
        "billed_amount": float(billed_raw.replace(",", "")) if billed_raw else None,
        "treatment_date": find("treatment_date"),
        "plan_type": plan_type if plan_type in _VALID_PLAN_TYPES else None,
    }


def intake_agent_node(state: ClaimState) -> ClaimState:
    t0 = time.time()
    settings = get_settings()
    client = get_llm_client()

    result = client.call_json(
        system=SYSTEM_PROMPT,
        user=f"CLAIM DOCUMENT TEXT:\n{state.raw_document_text}",
        model=settings.claude_model_extraction,
        mock_fn=lambda: _mock_extract(state.raw_document_text),
    )

    missing = [f for f in REQUIRED_FIELDS if not result.get(f)]
    duration_ms = (time.time() - t0) * 1000

    if missing:
        state.error = f"intake_extraction_failed: missing fields {missing}"
        state.final_decision = "escalated"
        state.escalation_reason = "intake_extraction_failed"
        state.log(
            "intake",
            f"Extraction failed — missing required fields: {missing}",
            detail={"raw_result": result},
            status="failed",
            duration_ms=duration_ms,
        )
        return state

    state.patient_id = result["patient_id"]
    state.provider_id = result["provider_id"]
    state.icd10_codes = result["icd10_codes"]
    state.cpt_codes = result["cpt_codes"]
    state.billed_amount = float(result["billed_amount"])
    state.treatment_date = datetime.strptime(result["treatment_date"], "%Y-%m-%d").date()
    state.plan_type = result["plan_type"]
    state.intake_confidence = 0.99 if client.mock_mode else 0.9

    state.log(
        "intake",
        f"Extracted claim for patient {state.patient_id} at provider {state.provider_id} "
        f"({state.plan_type} plan, AED {state.billed_amount:,.2f})",
        detail=result,
        duration_ms=duration_ms,
    )
    return state
