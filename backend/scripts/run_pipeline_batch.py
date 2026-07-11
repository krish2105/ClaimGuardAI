"""Runs every seeded claim through the LangGraph pipeline and persists a
Decision (and Escalation, where applicable) for each — so the Claims Queue,
Escalation Queue, and Analytics pages have full, realistic seed data out of
the box, without requiring the user to submit 400 claims by hand first."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.document_generator import render_claim_document  # noqa: E402
from app.services.pipeline_service import run_pipeline  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    claims = pd.read_csv(DATA_DIR / "claims.csv")
    n = len(claims)
    counts = {"auto_approved": 0, "auto_denied": 0, "escalated": 0}

    for i, row in claims.iterrows():
        doc_text = render_claim_document(
            patient_id=row["patient_id"],
            provider_id=row["provider_id"],
            plan_type=row["plan_type"],
            treatment_date=row["claim_date"],
            icd10_codes=row["icd10_codes"],
            cpt_codes=row["cpt_codes"],
            billed_amount=row["billed_amount"],
        )
        state = run_pipeline(row["claim_id"], doc_text)
        counts[state.final_decision] = counts.get(state.final_decision, 0) + 1
        if (i + 1) % 25 == 0 or (i + 1) == n:
            print(f"[{i + 1}/{n}] processed. running totals: {counts}")

    print("\n=== Batch complete ===")
    for k, v in counts.items():
        print(f"  {k}: {v} ({v / n:.1%})")


if __name__ == "__main__":
    main()
