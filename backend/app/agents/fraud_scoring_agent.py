"""Agent 3 — Fraud Scoring Agent.

Deterministic ML step (no LLM call): runs the trained XGBoost model and
attaches SHAP feature attributions, per ARCHITECTURE.md Section 4.4.
"""
import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import xgboost as xgb

from app.agents.state import ClaimState, FeatureContribution
from app.config import get_settings
from app.db.models import Claim, Provider
from app.db.session import SessionLocal
from app.services.fraud_features import build_feature_dict, feature_dict_to_vector


@lru_cache
def _load_model_and_meta():
    settings = get_settings()
    booster = xgb.Booster()
    booster.load_model(settings.fraud_model_path)
    meta = json.loads(Path(settings.fraud_model_meta_path).read_text())
    return booster, meta


def _lookup_context(provider_id: str, patient_id: str, treatment_date) -> dict:
    db = SessionLocal()
    try:
        provider = db.get(Provider, provider_id)
        flagged_history = provider.flagged_history_count if provider else 0

        window_30 = treatment_date.toordinal()
        provider_claims = (
            db.query(Claim)
            .filter(Claim.provider_id == provider_id, Claim.treatment_date <= treatment_date)
            .all()
        )
        patient_claims = (
            db.query(Claim)
            .filter(Claim.patient_id == patient_id, Claim.treatment_date <= treatment_date)
            .all()
        )

        freq_30d = sum(
            1 for c in provider_claims if 0 <= (treatment_date - c.treatment_date).days <= 30
        )
        freq_90d_patient = sum(
            1 for c in patient_claims if 0 <= (treatment_date - c.treatment_date).days <= 90
        )
        prior_dates = [c.treatment_date for c in provider_claims if c.treatment_date < treatment_date]
        days_since_last = (treatment_date - max(prior_dates)).days if prior_dates else None

        return {
            "provider_flagged_history_count": int(flagged_history or 0),
            "provider_claim_frequency_30d": freq_30d,
            "patient_claim_frequency_90d": freq_90d_patient,
            "days_since_last_claim_same_provider": days_since_last,
        }
    finally:
        db.close()


def fraud_scoring_node(state: ClaimState) -> ClaimState:
    t0 = time.time()
    booster, meta = _load_model_and_meta()
    cpt_stats = meta["cpt_stats"]

    cpt_code = state.cpt_codes[0] if state.cpt_codes else ""
    context = _lookup_context(state.provider_id, state.patient_id, state.treatment_date)

    feat = build_feature_dict(
        billed_amount=state.billed_amount or 0.0,
        cpt_code=cpt_code,
        treatment_date=state.treatment_date,
        provider_claim_frequency_30d=context["provider_claim_frequency_30d"],
        patient_claim_frequency_90d=context["patient_claim_frequency_90d"],
        days_since_last_claim_same_provider=context["days_since_last_claim_same_provider"],
        provider_flagged_history_count=context["provider_flagged_history_count"],
        coding_flags_count=len(state.coding_flags),
        plan_type=state.plan_type,
        cpt_stats=cpt_stats,
    )
    vector = feature_dict_to_vector(feat)
    dmatrix = xgb.DMatrix(np.array([vector]), feature_names=meta["feature_names"])

    proba = float(booster.predict(dmatrix)[0])
    state.fraud_score = round(proba * 100, 1)

    # SHAP-style contributions via XGBoost's native pred_contribs (exact,
    # no extra dependency at inference time).
    contribs = booster.predict(dmatrix, pred_contribs=True)[0]  # last entry is bias term
    feature_contribs = list(zip(meta["feature_names"], vector, contribs[:-1]))
    feature_contribs.sort(key=lambda x: abs(x[2]), reverse=True)

    state.fraud_top_features = [
        FeatureContribution(feature=name, value=float(value), contribution=float(contrib))
        for name, value, contrib in feature_contribs[:3]
    ]

    duration_ms = (time.time() - t0) * 1000
    top_feats_summary = ", ".join(f"{f.feature}={f.contribution:+.2f}" for f in state.fraud_top_features)
    state.log(
        "fraud_scoring",
        f"Fraud score {state.fraud_score}/100. Top contributors: {top_feats_summary}",
        detail={"features": feat, "fraud_score": state.fraud_score},
        duration_ms=duration_ms,
    )
    return state
