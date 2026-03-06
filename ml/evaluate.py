"""Evaluation helpers for optional ECC ML models."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error

from .features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from .model_registry import load_model_bundle
from .predict import _ood_score


def _resolve_policy(dataset_dir: Path, explicit_policy: str | None) -> str:
    if explicit_policy:
        return explicit_policy
    manifest_path = dataset_dir / "dataset_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            label_policy = manifest.get("label_policy")
            if label_policy:
                return str(label_policy)
        except Exception:
            pass
    return "carbon_min"


def evaluate_model(
    dataset_dir: Path,
    model_dir: Path,
    out_dir: Path,
    *,
    policy: str | None = None,
    ood_threshold: float | None = None,
) -> dict[str, Path]:
    dataset_path = dataset_dir / "dataset.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(dataset_path)
    X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES].copy()
    y = df["label_code"].astype(str)

    bundle = load_model_bundle(model_dir)
    clf = bundle["classifier"]
    reg_fit = bundle["regressors"]["fit"]
    reg_carbon = bundle["regressors"]["carbon"]
    reg_energy = bundle["regressors"]["energy"]

    y_pred = clf.predict(X)
    fit_pred = reg_fit.predict(X)
    carbon_pred = reg_carbon.predict(X)
    energy_pred = reg_energy.predict(X)

    thresholds = bundle.get("thresholds", {})
    confidence_min = float(thresholds.get("confidence_min", 0.6))
    default_ood = float(thresholds.get("ood_max_abs_z", 4.0))
    ood_max = float(default_ood if ood_threshold is None else ood_threshold)

    probs = clf.predict_proba(X)
    confidences = [float(row.max()) for row in probs]

    ood_flags: list[bool] = []
    low_conf_flags: list[bool] = []

    for idx, (_, row) in enumerate(X.iterrows()):
        feature_row = {k: row[k] for k in CATEGORICAL_FEATURES + NUMERIC_FEATURES}
        max_z, _ = _ood_score(bundle, feature_row)
        ood_flags.append(max_z > ood_max)
        low_conf_flags.append(confidences[idx] < confidence_min)

    ood_count = int(sum(1 for flag in ood_flags if flag))
    low_conf_count = int(sum(1 for flag in low_conf_flags if flag))
    fallback_count = int(sum(1 for ood, low in zip(ood_flags, low_conf_flags) if ood or low))

    resolved_policy = _resolve_policy(dataset_dir, policy)

    evaluation = {
        "summary": {
            "rows": int(len(df)),
            "policy": resolved_policy,
            "fallback_rate": float(fallback_count / max(len(df), 1)),
            "ood_rate": float(ood_count / max(len(df), 1)),
        },
        "classification": {
            "accuracy": float(accuracy_score(y, y_pred)) if len(y) else 1.0,
            "f1_macro": float(f1_score(y, y_pred, average="macro")) if len(y) else 1.0,
            "confusion_matrix": confusion_matrix(y, y_pred, labels=sorted(y.unique())).tolist() if len(y) else [],
        },
        "regression": {
            "fit_mae": float(mean_absolute_error(df["fit_true"], fit_pred)) if len(df) else 0.0,
            "carbon_mae": float(mean_absolute_error(df["carbon_true"], carbon_pred)) if len(df) else 0.0,
            "energy_mae": float(mean_absolute_error(df["energy_true"], energy_pred)) if len(df) else 0.0,
        },
        "fallback_breakdown": {
            "ood": int(ood_count),
            "low_confidence": int(low_conf_count),
            "constraints": 0,
        },
    }

    out = out_dir / "evaluation.json"
    out.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    return {"evaluation": out}
