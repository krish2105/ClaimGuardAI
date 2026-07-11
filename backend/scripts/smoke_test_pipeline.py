"""Phase 5 smoke test: run the LangGraph pipeline end-to-end on 5 sample
claims drawn from claims.csv and print the full agent_trace for each."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.document_generator import render_claim_document  # noqa: E402
from app.services.pipeline_service import run_pipeline  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    claims = pd.read_csv(DATA_DIR / "claims.csv")
    sample = pd.concat([
        claims[claims["fraud_label"] == False].head(3),  # noqa: E712
        claims[claims["fraud_label"] == True].head(2),
    ])

    for _, row in sample.iterrows():
        doc_text = render_claim_document(
            patient_id=row["patient_id"],
            provider_id=row["provider_id"],
            plan_type=row["plan_type"],
            treatment_date=row["claim_date"],
            icd10_codes=row["icd10_codes"],
            cpt_codes=row["cpt_codes"],
            billed_amount=row["billed_amount"],
        )
        print("=" * 80)
        print(f"Claim {row['claim_id']}  (ground-truth fraud_label={row['fraud_label']})")
        print("=" * 80)
        state = run_pipeline(row["claim_id"], doc_text)
        for step in state.agent_trace:
            print(f"  [{step.agent:15s}] {step.summary}  ({step.duration_ms:.0f} ms)")
        print(f"  --> FINAL DECISION: {state.final_decision}  "
              f"(fraud_score={state.fraud_score}, recommendation={state.decision_recommendation})")
        print()


if __name__ == "__main__":
    main()
