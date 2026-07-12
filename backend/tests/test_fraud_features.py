from datetime import date

from app.services.fraud_features import (
    FEATURE_NAMES,
    PLAN_TYPE_ENCODING,
    build_feature_dict,
    coding_flags_count_for_row,
    cpt_zscore,
    feature_dict_to_vector,
    is_weekend,
)

CPT_STATS = {"93000": {"mean": 200.0, "std": 50.0}}


def test_cpt_zscore_positive_for_above_average_billing():
    z = cpt_zscore(300.0, CPT_STATS, "93000")
    assert z == 2.0


def test_cpt_zscore_zero_when_no_stats():
    assert cpt_zscore(999.0, CPT_STATS, "UNKNOWN") == 0.0


def test_cpt_zscore_zero_when_std_is_zero():
    stats = {"X": {"mean": 100.0, "std": 0.0}}
    assert cpt_zscore(500.0, stats, "X") == 0.0


def test_is_weekend_saturday_sunday():
    assert is_weekend(date(2026, 7, 11)) == 1  # Saturday
    assert is_weekend(date(2026, 7, 12)) == 1  # Sunday
    assert is_weekend(date(2026, 7, 13)) == 0  # Monday


def test_build_feature_dict_has_all_expected_keys():
    feat = build_feature_dict(
        billed_amount=250.0,
        cpt_code="93000",
        treatment_date=date(2026, 7, 13),
        provider_claim_frequency_30d=3,
        patient_claim_frequency_90d=1,
        days_since_last_claim_same_provider=10,
        provider_flagged_history_count=0,
        coding_flags_count=0,
        plan_type="Basic",
        cpt_stats=CPT_STATS,
    )
    assert set(feat.keys()) == set(FEATURE_NAMES)
    assert feat["plan_type_encoded"] == PLAN_TYPE_ENCODING["Basic"]
    assert feat["is_weekend_treatment_date"] == 0


def test_build_feature_dict_defaults_days_since_last_claim_when_none():
    feat = build_feature_dict(
        billed_amount=100.0,
        cpt_code="93000",
        treatment_date=date(2026, 1, 1),
        provider_claim_frequency_30d=0,
        patient_claim_frequency_90d=0,
        days_since_last_claim_same_provider=None,
        provider_flagged_history_count=0,
        coding_flags_count=0,
        plan_type="Enhanced",
        cpt_stats=CPT_STATS,
    )
    assert feat["days_since_last_claim_same_provider"] == 365


def test_feature_dict_to_vector_matches_order():
    feat = {name: float(i) for i, name in enumerate(FEATURE_NAMES)}
    vector = feature_dict_to_vector(feat)
    assert vector == [float(i) for i in range(len(FEATURE_NAMES))]


def test_coding_flags_count_flags_mismatch():
    # M54.5 (orthopedic) + 87880 (pediatric rapid strep) is not coherent
    count = coding_flags_count_for_row("M54.5", "87880", 69.73, {})
    assert count >= 1


def test_coding_flags_count_flags_amount_outlier():
    stats = {"93000": {"mean": 200.0, "std": 10.0}}
    # coherent pair, but billed amount is a huge outlier (z > 2.5)
    count = coding_flags_count_for_row("I10", "93000", 500.0, stats)
    assert count >= 1


def test_coding_flags_count_zero_for_normal_claim():
    stats = {"93000": {"mean": 200.0, "std": 50.0}}
    count = coding_flags_count_for_row("I10", "93000", 210.0, stats)
    assert count == 0
