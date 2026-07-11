"""Feature engineering shared by the XGBoost training script and the
runtime Fraud Scoring Agent node, so both compute identical features.

Feature set (Section 4.4 of ARCHITECTURE.md):
  billed_amount_zscore, provider_claim_frequency_30d,
  patient_claim_frequency_90d, days_since_last_claim_same_provider,
  is_weekend_treatment_date, provider_flagged_history_count,
  coding_flags_count, plan_type_encoded
"""
from __future__ import annotations

from datetime import date, timedelta

FEATURE_NAMES = [
    "billed_amount_zscore",
    "provider_claim_frequency_30d",
    "patient_claim_frequency_90d",
    "days_since_last_claim_same_provider",
    "is_weekend_treatment_date",
    "provider_flagged_history_count",
    "coding_flags_count",
    "plan_type_encoded",
]

PLAN_TYPE_ENCODING = {"Basic": 0, "Enhanced": 1, "Thiqa": 2, "Comprehensive": 3}
DEFAULT_DAYS_SINCE_LAST_CLAIM = 365  # sentinel for "no prior claim on record"


def cpt_zscore(billed_amount: float, cpt_stats: dict, cpt_code: str) -> float:
    stats = cpt_stats.get(cpt_code)
    if not stats or stats["std"] <= 0:
        return 0.0
    return (billed_amount - stats["mean"]) / stats["std"]


def is_weekend(d: date) -> int:
    # UAE's official weekend is Saturday-Sunday.
    return int(d.weekday() in (5, 6))


def build_feature_dict(
    *,
    billed_amount: float,
    cpt_code: str,
    treatment_date: date,
    provider_claim_frequency_30d: int,
    patient_claim_frequency_90d: int,
    days_since_last_claim_same_provider: int | None,
    provider_flagged_history_count: int,
    coding_flags_count: int,
    plan_type: str,
    cpt_stats: dict,
) -> dict:
    return {
        "billed_amount_zscore": cpt_zscore(billed_amount, cpt_stats, cpt_code),
        "provider_claim_frequency_30d": provider_claim_frequency_30d,
        "patient_claim_frequency_90d": patient_claim_frequency_90d,
        "days_since_last_claim_same_provider": (
            days_since_last_claim_same_provider
            if days_since_last_claim_same_provider is not None
            else DEFAULT_DAYS_SINCE_LAST_CLAIM
        ),
        "is_weekend_treatment_date": is_weekend(treatment_date),
        "provider_flagged_history_count": provider_flagged_history_count,
        "coding_flags_count": coding_flags_count,
        "plan_type_encoded": PLAN_TYPE_ENCODING.get(plan_type, 0),
    }


def feature_dict_to_vector(feat: dict) -> list[float]:
    return [float(feat[name]) for name in FEATURE_NAMES]


def compute_cpt_stats(claims_df) -> dict:
    """cpt_code -> {mean, std} of billed_amount, from historical claims."""
    stats = {}
    for cpt_code, group in claims_df.groupby("cpt_codes"):
        mean = float(group["billed_amount"].mean())
        std = float(group["billed_amount"].std() or 0.0)
        stats[cpt_code] = {"mean": mean, "std": std if std > 0 else max(mean * 0.25, 1.0)}
    return stats


def coding_flags_count_for_row(icd10_code: str, cpt_code: str, billed_amount: float, cpt_stats: dict) -> int:
    """Approximates what the Coding Agent would flag, for historical training
    rows that have no recorded agent trace."""
    from app.reference_data import is_clinically_coherent

    count = 0
    if not is_clinically_coherent(icd10_code, cpt_code):
        count += 1
    stats = cpt_stats.get(cpt_code)
    if stats and stats["std"] > 0:
        z = (billed_amount - stats["mean"]) / stats["std"]
        if z > 2.5:
            count += 1
    return count


def days_between(later: date, earlier: date) -> int:
    return (later - earlier).days
