"""Renders a semi-structured claim intake document (the kind of text you'd
get back from OCR on a claim form / fax) from either a claims.csv row or a
free-form submission. This is the "raw_document_text" the Intake Agent
parses — it stands in for `parse_pdf_tool` in ARCHITECTURE.md Section 4.2
for the synthetic-data demo."""
from datetime import date


def render_claim_document(
    *,
    patient_id: str,
    provider_id: str,
    plan_type: str,
    treatment_date: str | date,
    icd10_codes: list[str] | str,
    cpt_codes: list[str] | str,
    billed_amount: float,
    notes: str = "",
) -> str:
    icd_str = ", ".join(icd10_codes) if isinstance(icd10_codes, list) else icd10_codes
    cpt_str = ", ".join(cpt_codes) if isinstance(cpt_codes, list) else cpt_codes
    treatment_date_str = treatment_date if isinstance(treatment_date, str) else treatment_date.isoformat()

    return f"""CLAIMGUARD AI — CLAIM SUBMISSION FORM (SYNTHETIC / DEMO DATA)
================================================================
Patient ID: {patient_id}
Provider ID: {provider_id}
Plan Type: {plan_type}
Treatment Date: {treatment_date_str}
Diagnosis (ICD-10): {icd_str}
Procedure (CPT): {cpt_str}
Billed Amount: AED {billed_amount:,.2f}
Notes: {notes or "Patient presented for evaluation and treatment consistent with the diagnosis above."}
================================================================
""".strip()
