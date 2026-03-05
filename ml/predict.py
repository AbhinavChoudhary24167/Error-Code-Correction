"""Prediction utilities for optional ECC ML layer."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd

from .features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, row_to_feature_dict
from .model_registry import load_model_bundle as _load_model_bundle


def load_model_bundle(model_dir: Path) -> dict:
    return _load_model_bundle(model_dir)


def _ood_score(bundle: dict, feature_row: dict[str, float | str]) -> tuple[float, dict[str, float]]:
    means = bundle.get("train_stats", {}).get("means", {})
    stds = bundle.get("train_stats", {}).get("stds", {})
    z_map: dict[str, float] = {}
    for key in NUMERIC_FEATURES:
        mean = float(means.get(key, 0.0))
        std = float(stds.get(key, 1.0))
        if std <= 0:
            std = 1.0
        val = float(feature_row.get(key, 0.0))
        z_map[key] = abs((val - mean) / std)
    return max(z_map.values()) if z_map else 0.0, z_map


def predict_with_model(
    model_dir: Path,
    row: Mapping[str, object],
    scenario_defaults: Mapping[str, float] | None = None,
) -> dict[str, object]:
    """Predict recommended code and reliability/energy/carbon metrics."""

    bundle = load_model_bundle(model_dir)
    feature_row = row_to_feature_dict(row, scenario_defaults=scenario_defaults)
    X = pd.DataFrame([{k: feature_row[k] for k in CATEGORICAL_FEATURES + NUMERIC_FEATURES}])

    classifier = bundle["classifier"]
    classes = classifier.classes_
    probs = classifier.predict_proba(X)[0]
    best_idx = max(range(len(probs)), key=lambda i: probs[i])
    ml_code = str(classes[best_idx])
    confidence = float(probs[best_idx])

    reg_fit = bundle["regressors"]["fit"]
    reg_carbon = bundle["regressors"]["carbon"]
    reg_energy = bundle["regressors"]["energy"]

    pred_fit = float(reg_fit.predict(X)[0])
    pred_carbon = float(reg_carbon.predict(X)[0])
    pred_energy = float(reg_energy.predict(X)[0])

    max_z, z_map = _ood_score(bundle, feature_row)
    thresholds = bundle.get("thresholds", {})
    confidence_min = float(thresholds.get("confidence_min", 0.6))
    ood_max_abs_z = float(thresholds.get("ood_max_abs_z", 4.0))

    ood = max_z > ood_max_abs_z
    low_confidence = confidence < confidence_min

    fallback_reason = None
    if ood:
        fallback_reason = f"OOD max|z|={max_z:.3f} > {ood_max_abs_z:.3f}"
    elif low_confidence:
        fallback_reason = f"confidence {confidence:.3f} < {confidence_min:.3f}"

    return {
        "ml_recommendation": ml_code,
        "confidence": confidence,
        "predictions": {
            "FIT": pred_fit,
            "carbon_kg": pred_carbon,
            "energy_kWh": pred_energy,
        },
        "ood": ood,
        "ood_max_abs_z": max_z,
        "ood_feature_z": z_map,
        "low_confidence": low_confidence,
        "fallback_reason": fallback_reason,
        "features": feature_row,
    }
