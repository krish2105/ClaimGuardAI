"""Agent 2 — Coding Agent.

Validates that ICD-10/CPT code pairs on a claim are clinically coherent and
checks for upcoding/unbundling patterns, per ARCHITECTURE.md Section 4.3.
"""
import time

from app.agents.llm_client import get_llm_client
from app.agents.state import ClaimState
from app.config import get_settings
from app.reference_data import CPT_CODES, ICD10_CODES, is_clinically_coherent
from app.db.session import SessionLocal
from app.db.models import Claim

SYSTEM_PROMPT = """You are the Coding Agent for ClaimGuard AI. Given a claim's ICD-10 diagnosis codes and
CPT procedure codes, determine:
1. Are the diagnosis and procedure codes clinically coherent together?
2. Does the billed amount look consistent with the procedure code's typical cost band
   (reference: {cpt_cost_bands})?
3. Is there evidence of unbundling (billing separately for procedures normally billed
   as one bundled code)?

Return JSON:
{
  "coding_flags": [string],       // e.g. ["diagnosis_procedure_mismatch", "amount_outlier"]
  "coding_confidence": number     // 0.0-1.0, your confidence in this assessment
}

CLAIM: {claim_json}
REFERENCE CODE PAIRS: {valid_pairs_sample}
"""


def _cost_band_context(cpt_codes: list[str]) -> dict:
    return {c: CPT_CODES[c]["cost_band_aed"] for c in cpt_codes if c in CPT_CODES}


def _check_same_day_unrelated_claims(state: ClaimState) -> bool:
    """Looks for other claims from the same provider+patient on the same
    treatment date spanning clinically unrelated categories — the phantom
    billing / unbundling signal defined in fraud_waste_abuse_definitions.md
    (Clause CG-FWA-002/003)."""
    if not (state.provider_id and state.patient_id and state.treatment_date):
        return False
    db = SessionLocal()
    try:
        same_day = (
            db.query(Claim)
            .filter(
                Claim.provider_id == state.provider_id,
                Claim.patient_id == state.patient_id,
                Claim.treatment_date == state.treatment_date,
                Claim.claim_id != state.claim_id,
            )
            .all()
        )
    finally:
        db.close()

    if not same_day:
        return False

    this_categories = {ICD10_CODES[c]["category"] for c in state.icd10_codes if c in ICD10_CODES}
    for other in same_day:
        other_categories = {ICD10_CODES.get(c, {}).get("category") for c in (other.icd10_codes or [])}
        if other_categories and not (other_categories & this_categories):
            return True
    return False


def _mock_assess(state: ClaimState) -> dict:
    flags: list[str] = []

    coherent_pairs = 0
    total_pairs = 0
    for icd in state.icd10_codes:
        for cpt in state.cpt_codes:
            total_pairs += 1
            if is_clinically_coherent(icd, cpt):
                coherent_pairs += 1
    if total_pairs and coherent_pairs == 0:
        flags.append("diagnosis_procedure_mismatch")

    amount_outlier = False
    if state.billed_amount is not None:
        for cpt in state.cpt_codes:
            band = CPT_CODES.get(cpt, {}).get("cost_band_aed")
            if band and state.billed_amount > band[1] * 2.0:
                amount_outlier = True
    if amount_outlier:
        flags.append("amount_outlier")

    if _check_same_day_unrelated_claims(state):
        flags.append("possible_unbundling_or_phantom_billing")

    confidence = 0.9 if flags else 0.95
    return {"coding_flags": flags, "coding_confidence": confidence}


def coding_agent_node(state: ClaimState) -> ClaimState:
    t0 = time.time()
    settings = get_settings()
    client = get_llm_client()

    claim_json = {
        "icd10_codes": state.icd10_codes,
        "cpt_codes": state.cpt_codes,
        "billed_amount": state.billed_amount,
        "plan_type": state.plan_type,
    }
    result = client.call_json(
        system=SYSTEM_PROMPT,
        user=(
            f"CLAIM: {claim_json}\n"
            f"REFERENCE CODE PAIRS: {[(c, ICD10_CODES[c]['category']) for c in state.icd10_codes if c in ICD10_CODES]}\n"
            f"CPT COST BANDS: {_cost_band_context(state.cpt_codes)}"
        ),
        model=settings.claude_model_reasoning,
        mock_fn=lambda: _mock_assess(state),
    )

    state.coding_flags = result.get("coding_flags", [])
    state.coding_confidence = result.get("coding_confidence")

    duration_ms = (time.time() - t0) * 1000
    summary = (
        f"Flags: {state.coding_flags}" if state.coding_flags else "No coding integrity issues found"
    )
    state.log("coding", summary, detail=result, duration_ms=duration_ms)
    return state
