from app.reference_data import (
    CPT_CODES,
    ICD10_CODES,
    cpt_cost_band,
    cpt_requires_prior_auth,
    is_clinically_coherent,
)


def test_coherent_pair_same_category():
    assert is_clinically_coherent("I10", "93000")  # hypertension + ECG, both cardiology


def test_incoherent_pair_different_category():
    assert not is_clinically_coherent("M54.5", "87880")  # low back pain + strep test


def test_general_and_emergency_cpt_always_coherent():
    # general/emergency CPT categories are cross-compatible with any diagnosis
    some_icd = next(iter(ICD10_CODES))
    general_cpt = next(c for c, m in CPT_CODES.items() if m["category"] == "general")
    assert is_clinically_coherent(some_icd, general_cpt)


def test_unknown_codes_are_not_coherent():
    assert not is_clinically_coherent("NOT-A-CODE", "93000")
    assert not is_clinically_coherent("I10", "NOT-A-CODE")


def test_cost_band_lookup():
    band = cpt_cost_band("93000")
    assert band is not None
    lo, hi = band
    assert lo < hi


def test_cost_band_unknown_code():
    assert cpt_cost_band("NOT-A-CODE") is None


def test_prior_auth_flags_match_reference_table():
    for code, meta in CPT_CODES.items():
        assert cpt_requires_prior_auth(code) == meta["prior_auth"]
