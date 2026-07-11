"""Generate the synthetic ClaimGuard AI dataset.

Produces backend/data/providers.csv (~40 rows) and backend/data/claims.csv
(~400 rows) spanning 12 months, with three fraud archetypes programmatically
injected at roughly an 8% rate:

  1. amount_inflation      - billed_amount is 3-5x the CPT code's normal band
  2. phantom_billing       - same provider+patient bill multiple same-day
                             claims for clinically incompatible procedures
  3. diagnosis_mismatch    - the CPT procedure does not clinically match the
                             ICD-10 diagnosis on the claim

`fraud_label` is ground truth used ONLY for model training/evaluation. The
agent pipeline never sees this column.

Ethics note: every value here is synthetically generated. No real patient,
provider or claims data is used anywhere in this project (UAE PDPL-aligned).
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.reference_data import CPT_CODES, ICD10_CODES, CROSS_COMPATIBLE_CPT_CATEGORIES  # noqa: E402

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

OUT_DIR = Path(__file__).resolve().parents[1] / "data"
N_PROVIDERS = 40
N_CLAIMS = 400
FRAUD_RATE = 0.08
PLAN_TYPES = ["Basic", "Enhanced", "Thiqa", "Comprehensive"]
PLAN_WEIGHTS = [0.35, 0.30, 0.20, 0.15]
SPECIALTIES = [
    "General Practice", "Cardiology", "Endocrinology", "Orthopedics",
    "Obstetrics & Gynecology", "Pediatrics", "Dermatology", "Gastroenterology",
    "Psychiatry", "Oncology", "Emergency Medicine", "Dental", "Ophthalmology",
]

CATEGORY_TO_ICD = {}
for code, meta in ICD10_CODES.items():
    CATEGORY_TO_ICD.setdefault(meta["category"], []).append(code)

CATEGORY_TO_CPT = {}
for code, meta in CPT_CODES.items():
    CATEGORY_TO_CPT.setdefault(meta["category"], []).append(code)

ALL_ICD = list(ICD10_CODES.keys())
ALL_CPT = list(CPT_CODES.keys())


def gen_providers(n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "provider_id": f"PRV-{i:03d}",
            "specialty": random.choice(SPECIALTIES),
            "claim_volume_30d_avg": np.random.randint(5, 120),
            "flagged_history_count": np.random.choice([0, 0, 0, 0, 1, 1, 2, 3], p=None) if False else int(np.random.poisson(0.4)),
        })
    return pd.DataFrame(rows)


def random_treatment_date() -> date:
    start = date(2025, 7, 1)
    offset = np.random.randint(0, 365)
    return start + timedelta(days=int(offset))


def coherent_code_pair() -> tuple[str, str]:
    category = random.choice(list(CATEGORY_TO_ICD.keys()))
    icd = random.choice(CATEGORY_TO_ICD[category])
    candidate_cpts = CATEGORY_TO_CPT.get(category, []) + [
        c for c, m in CPT_CODES.items() if m["category"] in CROSS_COMPATIBLE_CPT_CATEGORIES
    ]
    cpt = random.choice(candidate_cpts)
    return icd, cpt


def mismatched_code_pair() -> tuple[str, str]:
    icd = random.choice(ALL_ICD)
    icd_cat = ICD10_CODES[icd]["category"]
    non_coherent_cpts = [
        c for c, m in CPT_CODES.items()
        if m["category"] != icd_cat and m["category"] not in CROSS_COMPATIBLE_CPT_CATEGORIES
    ]
    cpt = random.choice(non_coherent_cpts)
    return icd, cpt


def normal_billed_amount(cpt_code: str) -> float:
    lo, hi = CPT_CODES[cpt_code]["cost_band_aed"]
    return round(np.random.uniform(lo, hi), 2)


def inflated_billed_amount(cpt_code: str) -> float:
    lo, hi = CPT_CODES[cpt_code]["cost_band_aed"]
    multiplier = np.random.uniform(3.0, 5.0)
    return round(hi * multiplier, 2)


def gen_claims(providers: pd.DataFrame) -> pd.DataFrame:
    provider_ids = providers["provider_id"].tolist()
    n_fraud_target = int(round(N_CLAIMS * FRAUD_RATE))
    n_per_archetype = n_fraud_target // 3
    archetypes = (
        ["amount_inflation"] * n_per_archetype
        + ["phantom_billing"] * n_per_archetype
        + ["diagnosis_mismatch"] * (n_fraud_target - 2 * n_per_archetype)
    )
    random.shuffle(archetypes)

    rows = []
    claim_counter = 1
    patient_pool = [f"PAT-{i:04d}" for i in range(1, 251)]

    fraud_slots = set(np.random.choice(range(N_CLAIMS), size=len(archetypes), replace=False))
    archetype_by_slot = dict(zip(sorted(fraud_slots), archetypes))

    slot = 0
    while len(rows) < N_CLAIMS and slot < N_CLAIMS:
        archetype = archetype_by_slot.get(slot)
        provider_id = random.choice(provider_ids)
        patient_id = random.choice(patient_pool)
        plan_type = np.random.choice(PLAN_TYPES, p=PLAN_WEIGHTS)
        treatment_dt = random_treatment_date()

        if archetype == "diagnosis_mismatch":
            icd, cpt = mismatched_code_pair()
            billed = normal_billed_amount(cpt)
            fraud_label = True
        elif archetype == "amount_inflation":
            icd, cpt = coherent_code_pair()
            billed = inflated_billed_amount(cpt)
            fraud_label = True
        else:
            icd, cpt = coherent_code_pair()
            billed = normal_billed_amount(cpt)
            fraud_label = False

        prior_auth_required = bool(CPT_CODES[cpt]["prior_auth"])
        prior_auth_obtained = (
            (np.random.rand() < 0.85) if prior_auth_required else True
        )

        claim_id = f"CLM-{claim_counter:05d}"
        claim_counter += 1
        rows.append({
            "claim_id": claim_id,
            "patient_id": patient_id,
            "provider_id": provider_id,
            "icd10_codes": icd,
            "cpt_codes": cpt,
            "billed_amount": billed,
            "approved_amount": round(billed * np.random.uniform(0.6, 1.0), 2) if not fraud_label else round(billed * np.random.uniform(0.0, 0.4), 2),
            "claim_date": treatment_dt.isoformat(),
            "plan_type": plan_type,
            "prior_auth_required": prior_auth_required,
            "prior_auth_obtained": prior_auth_obtained,
            "fraud_label": fraud_label,
        })
        slot += 1

        # Phantom billing archetype: emit 2-3 extra same-day, same
        # provider+patient claims for incompatible procedure categories.
        if archetype == "phantom_billing":
            n_extra = np.random.randint(2, 4)
            used_categories = {CPT_CODES[cpt]["category"]}
            for _ in range(n_extra):
                if len(rows) >= N_CLAIMS:
                    break
                other_categories = [c for c in CATEGORY_TO_CPT if c not in used_categories]
                if not other_categories:
                    break
                cat = random.choice(other_categories)
                used_categories.add(cat)
                extra_cpt = random.choice(CATEGORY_TO_CPT[cat])
                extra_icd = random.choice(CATEGORY_TO_ICD.get(cat, ALL_ICD))
                extra_billed = normal_billed_amount(extra_cpt)
                extra_claim_id = f"CLM-{claim_counter:05d}"
                claim_counter += 1
                rows.append({
                    "claim_id": extra_claim_id,
                    "patient_id": patient_id,
                    "provider_id": provider_id,
                    "icd10_codes": extra_icd,
                    "cpt_codes": extra_cpt,
                    "billed_amount": extra_billed,
                    "approved_amount": round(extra_billed * np.random.uniform(0.0, 0.4), 2),
                    "claim_date": treatment_dt.isoformat(),
                    "plan_type": plan_type,
                    "prior_auth_required": bool(CPT_CODES[extra_cpt]["prior_auth"]),
                    "prior_auth_obtained": True,
                    "fraud_label": True,
                })
                slot += 1

    df = pd.DataFrame(rows[:N_CLAIMS])
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    providers = gen_providers(N_PROVIDERS)
    claims = gen_claims(providers)

    providers.to_csv(OUT_DIR / "providers.csv", index=False)
    claims.to_csv(OUT_DIR / "claims.csv", index=False)

    fraud_count = int(claims["fraud_label"].sum())
    print(f"providers.csv: {len(providers)} rows -> {OUT_DIR / 'providers.csv'}")
    print(f"claims.csv:    {len(claims)} rows -> {OUT_DIR / 'claims.csv'}")
    print(f"fraud_label=True rows: {fraud_count} ({fraud_count / len(claims):.1%})")


if __name__ == "__main__":
    main()
