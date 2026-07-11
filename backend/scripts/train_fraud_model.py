"""Train the XGBoost fraud-scoring model on the synthetic claims dataset.

Builds the Section 4.4 feature set for every historical claim, trains a
binary classifier against the (agent-hidden) `fraud_label` ground truth,
evaluates on a held-out split, and saves:
  - backend/models/fraud_model.json      (XGBoost booster, native format)
  - backend/models/fraud_model_meta.json (feature names, plan encoding,
                                           per-CPT cost stats, eval metrics)
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.fraud_features import (  # noqa: E402
    FEATURE_NAMES,
    build_feature_dict,
    coding_flags_count_for_row,
    compute_cpt_stats,
    days_between,
    feature_dict_to_vector,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def build_training_frame(claims: pd.DataFrame, providers: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    claims = claims.copy()
    claims["claim_date"] = pd.to_datetime(claims["claim_date"]).dt.date
    claims = claims.sort_values("claim_date").reset_index(drop=True)

    cpt_stats = compute_cpt_stats(claims)
    provider_flags = providers.set_index("provider_id")["flagged_history_count"].to_dict()

    rows = []
    provider_history: dict[str, list] = {}
    patient_history: dict[str, list] = {}

    for _, row in claims.iterrows():
        provider_id = row["provider_id"]
        patient_id = row["patient_id"]
        tdate = row["claim_date"]

        prov_dates = provider_history.get(provider_id, [])
        pat_dates = patient_history.get(patient_id, [])

        freq_30d = sum(1 for d in prov_dates if 0 <= days_between(tdate, d) <= 30)
        freq_90d_patient = sum(1 for d in pat_dates if 0 <= days_between(tdate, d) <= 90)
        prior_prov_dates = [d for d in prov_dates if d < tdate]
        days_since_last = days_between(tdate, max(prior_prov_dates)) if prior_prov_dates else None

        coding_flags_count = coding_flags_count_for_row(
            row["icd10_codes"], row["cpt_codes"], row["billed_amount"], cpt_stats
        )

        feat = build_feature_dict(
            billed_amount=row["billed_amount"],
            cpt_code=row["cpt_codes"],
            treatment_date=tdate,
            provider_claim_frequency_30d=freq_30d,
            patient_claim_frequency_90d=freq_90d_patient,
            days_since_last_claim_same_provider=days_since_last,
            provider_flagged_history_count=int(provider_flags.get(provider_id, 0)),
            coding_flags_count=coding_flags_count,
            plan_type=row["plan_type"],
            cpt_stats=cpt_stats,
        )
        feat["fraud_label"] = int(row["fraud_label"])
        rows.append(feat)

        provider_history.setdefault(provider_id, []).append(tdate)
        patient_history.setdefault(patient_id, []).append(tdate)

    return pd.DataFrame(rows), cpt_stats


def main() -> None:
    claims = pd.read_csv(DATA_DIR / "claims.csv")
    providers = pd.read_csv(DATA_DIR / "providers.csv")

    frame, cpt_stats = build_training_frame(claims, providers)
    X = frame[FEATURE_NAMES]
    y = frame["fraud_label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        random_state=42,
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)

    metrics = {
        "auc_roc": float(roc_auc_score(y_test, proba)),
        "accuracy": float(accuracy_score(y_test, preds)),
        "precision": float(precision_score(y_test, preds, zero_division=0)),
        "recall": float(recall_score(y_test, preds, zero_division=0)),
        "f1": float(f1_score(y_test, preds, zero_division=0)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "fraud_rate": float(y.mean()),
        "trained_at": datetime.utcnow().isoformat(),
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.get_booster().save_model(str(MODELS_DIR / "fraud_model.json"))

    meta = {
        "feature_names": FEATURE_NAMES,
        "cpt_stats": cpt_stats,
        "provider_flagged_history": providers.set_index("provider_id")["flagged_history_count"].to_dict(),
        "eval_metrics": metrics,
    }
    (MODELS_DIR / "fraud_model_meta.json").write_text(json.dumps(meta, indent=2))

    print("=== Fraud model training complete ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print(f"\nModel saved to {MODELS_DIR / 'fraud_model.json'}")
    print(f"Metadata saved to {MODELS_DIR / 'fraud_model_meta.json'}")

    if metrics["auc_roc"] < 0.80:
        print("\nWARNING: AUC below the 0.80 target in ARCHITECTURE.md Section 12.")


if __name__ == "__main__":
    main()
