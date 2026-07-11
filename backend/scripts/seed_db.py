"""Create the schema (if needed) and load claims.csv / providers.csv into Postgres."""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.models import Claim, Provider  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes"}


def main() -> None:
    Base.metadata.create_all(bind=engine)

    providers_df = pd.read_csv(DATA_DIR / "providers.csv")
    claims_df = pd.read_csv(DATA_DIR / "claims.csv")

    db = SessionLocal()
    try:
        db.query(Claim).delete()
        db.query(Provider).delete()
        db.commit()

        for _, row in providers_df.iterrows():
            db.add(Provider(
                provider_id=row["provider_id"],
                specialty=row["specialty"],
                claim_volume_30d_avg=int(row["claim_volume_30d_avg"]),
                flagged_history_count=int(row["flagged_history_count"]),
            ))
        db.commit()

        for _, row in claims_df.iterrows():
            db.add(Claim(
                claim_id=row["claim_id"],
                patient_id=row["patient_id"],
                provider_id=row["provider_id"],
                icd10_codes=[c.strip() for c in str(row["icd10_codes"]).split(",")],
                cpt_codes=[c.strip() for c in str(row["cpt_codes"]).split(",")],
                billed_amount=float(row["billed_amount"]),
                approved_amount=float(row["approved_amount"]),
                treatment_date=datetime.strptime(row["claim_date"], "%Y-%m-%d").date(),
                plan_type=row["plan_type"],
                prior_auth_required=to_bool(row["prior_auth_required"]),
                prior_auth_obtained=to_bool(row["prior_auth_obtained"]),
                fraud_label=to_bool(row["fraud_label"]),
            ))
        db.commit()

        print(f"Seeded {len(providers_df)} providers and {len(claims_df)} claims.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
