"""Prediction utilities for optional ECC ML layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Any

import numpy as np
import pandas as pd

from .features import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    resolve_model_feature_spec,
    row_to_feature_dict,
)
from .model_registry import load_model_bundle as _load_model_bundle


DEFAULT_THRESHOLDS: dict[str, float | str] = {
    "confidence_min": 0.6,
    "ood_max_abs_z": 4.0,
    "ood_method": "zscore",
    "ood_threshold": 4.0,
    "conformal_alpha": 0.1,
    "prediction_set_min_coverage": 0.0,
    "ml_policy": "carbon_min",
    # Internal helper for prediction-set construction.
    "conformal_prob_min": 0.5,
}

_ALLOWED_OOD_METHODS = {"zscore", "mahalanobis", "iforest"}
_ALLOWED_POLICIES = {"carbon_min", "fit_min", "energy_min", "utility_balanced"}


def load_model_bundle(model_dir: Path) -> dict:
    return _load_model_bundle(model_dir)


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _load_thresholds_file(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "thresholds.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_thresholds(
    raw_thresholds: Mapping[str, object] | None,
    *,
    model_dir: Path | None = None,
    confidence_min_override: float | None = None,
    ood_threshold_override: float | None = None,
    policy_override: str | None = None,
) -> dict[str, float | str]:
    """Resolve thresholds with backward-compatible defaults and overrides."""

    merged: dict[str, object] = {}
    merged.update(raw_thresholds or {})
    if model_dir is not None:
        # File values are treated as operator-facing artifact defaults.
        merged.update(_load_thresholds_file(model_dir))

    resolved: dict[str, float | str] = dict(DEFAULT_THRESHOLDS)
    resolved["confidence_min"] = _safe_float(merged.get("confidence_min"), 0.6)

    method = str(merged.get("ood_method", "zscore")).strip().lower()
    if method not in _ALLOWED_OOD_METHODS:
        method = "zscore"
    resolved["ood_method"] = method

    legacy_ood = _safe_float(merged.get("ood_max_abs_z"), 4.0)
    resolved_ood = _safe_float(merged.get("ood_threshold"), legacy_ood)
    resolved["ood_threshold"] = resolved_ood
    # Preserve legacy key semantics as alias for compatibility with old code.
    resolved["ood_max_abs_z"] = resolved_ood

    resolved["conformal_alpha"] = _safe_float(merged.get("conformal_alpha"), 0.1)
    resolved["prediction_set_min_coverage"] = _safe_float(
        merged.get("prediction_set_min_coverage"), 0.0
    )
    resolved["conformal_prob_min"] = _safe_float(merged.get("conformal_prob_min"), 0.5)

    policy = str(merged.get("ml_policy", "carbon_min")).strip().lower()
    if policy not in _ALLOWED_POLICIES:
        policy = "carbon_min"
    resolved["ml_policy"] = policy

    if confidence_min_override is not None:
        resolved["confidence_min"] = float(confidence_min_override)
    if ood_threshold_override is not None:
        resolved["ood_threshold"] = float(ood_threshold_override)
        resolved["ood_max_abs_z"] = float(ood_threshold_override)
    if policy_override is not None:
        override_policy = str(policy_override).strip().lower()
        if override_policy in _ALLOWED_POLICIES:
            resolved["ml_policy"] = override_policy

    return resolved


def _zscore_map(
    bundle: dict,
    feature_row: dict[str, float | str],
    *,
    numeric_features: list[str],
) -> dict[str, float]:
    means = bundle.get("train_stats", {}).get("means", {})
    stds = bundle.get("train_stats", {}).get("stds", {})
    z_map: dict[str, float] = {}
    for key in numeric_features:
        mean = float(means.get(key, 0.0))
        std = float(stds.get(key, 1.0))
        if std <= 0:
            std = 1.0
        val = float(feature_row.get(key, 0.0))
        z_map[key] = abs((val - mean) / std)
    return z_map


def _numeric_vector(feature_row: Mapping[str, float | str], *, numeric_features: list[str]) -> np.ndarray:
    return np.asarray([float(feature_row.get(k, 0.0)) for k in numeric_features], dtype=float)


def _ood_score(
    bundle: dict,
    feature_row: dict[str, float | str],
    *,
    method: str,
    numeric_features: list[str] | None = None,
) -> tuple[float, dict[str, float]]:
    """Compute OOD score where larger means more out-of-distribution."""

    if numeric_features is None:
        numeric_features = list(resolve_model_feature_spec(bundle).get("numeric", NUMERIC_FEATURES))

    method_norm = str(method).strip().lower()
    if method_norm == "zscore":
        z_map = _zscore_map(bundle, feature_row, numeric_features=numeric_features)
        return (max(z_map.values()) if z_map else 0.0), z_map

    ood = bundle.get("ood", {}) if isinstance(bundle.get("ood"), dict) else {}
    vec = _numeric_vector(feature_row, numeric_features=numeric_features)

    if method_norm == "mahalanobis":
        mean = np.asarray(ood.get("mahalanobis_mean", []), dtype=float)
        inv_cov = np.asarray(ood.get("mahalanobis_inv_cov", []), dtype=float)
        if mean.shape != vec.shape or inv_cov.shape != (len(vec), len(vec)):
            z_map = _zscore_map(bundle, feature_row, numeric_features=numeric_features)
            return (max(z_map.values()) if z_map else 0.0), z_map
        diff = vec - mean
        dist = float(np.sqrt(max(0.0, float(diff @ inv_cov @ diff.T))))
        return dist, {"mahalanobis": dist}

    if method_norm == "iforest":
        model = ood.get("iforest_model")
        if model is None:
            z_map = _zscore_map(bundle, feature_row, numeric_features=numeric_features)
            return (max(z_map.values()) if z_map else 0.0), z_map
        score = float(-model.score_samples(np.asarray([vec]))[0])
        return score, {"iforest_anomaly": score}

    z_map = _zscore_map(bundle, feature_row, numeric_features=numeric_features)
    return (max(z_map.values()) if z_map else 0.0), z_map


def _prediction_set(classes: np.ndarray, probs: np.ndarray, prob_min: float) -> list[str]:
    labels = [str(classes[i]) for i, p in enumerate(probs) if float(p) >= float(prob_min)]
    if not labels:
        best_idx = int(np.argmax(probs))
        labels = [str(classes[best_idx])]
    return labels


def predict_with_model(
    model_dir: Path,
    row: Mapping[str, object],
    scenario_defaults: Mapping[str, float] | None = None,
    *,
    confidence_min_override: float | None = None,
    ood_threshold_override: float | None = None,
    policy_override: str | None = None,
) -> dict[str, object]:
    """Predict recommended code and reliability/energy/carbon metrics."""

    bundle = load_model_bundle(model_dir)
    feature_spec = resolve_model_feature_spec(bundle)
    categorical_features = list(feature_spec.get("categorical", CATEGORICAL_FEATURES))
    numeric_features = list(feature_spec.get("numeric", NUMERIC_FEATURES))

    feature_row = row_to_feature_dict(
        row,
        scenario_defaults=scenario_defaults,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
    )
    X = pd.DataFrame([{k: feature_row[k] for k in categorical_features + numeric_features}])

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

    thresholds = resolve_thresholds(
        bundle.get("thresholds", {}),
        model_dir=model_dir,
        confidence_min_override=confidence_min_override,
        ood_threshold_override=ood_threshold_override,
        policy_override=policy_override,
    )

    ood_method = str(thresholds["ood_method"])
    ood_score, ood_detail = _ood_score(
        bundle,
        feature_row,
        method=ood_method,
        numeric_features=numeric_features,
    )
    confidence_min = float(thresholds["confidence_min"])
    ood_threshold = float(thresholds["ood_threshold"])
    prediction_set = _prediction_set(classes, probs, float(thresholds["conformal_prob_min"]))

    ood = ood_score > ood_threshold
    low_confidence = confidence < confidence_min

    fallback_reason = None
    if ood:
        fallback_reason = (
            f"OOD {ood_method} score={ood_score:.3f} > {ood_threshold:.3f}"
        )
    elif low_confidence:
        fallback_reason = f"confidence {confidence:.3f} < {confidence_min:.3f}"

    return {
        "ml_recommendation": ml_code,
        "confidence": confidence,
        "confidence_threshold": confidence_min,
        "predictions": {
            "FIT": pred_fit,
            "carbon_kg": pred_carbon,
            "energy_kWh": pred_energy,
        },
        "ood": ood,
        "ood_method": ood_method,
        "ood_score": ood_score,
        "ood_threshold": ood_threshold,
        # Legacy compatibility fields.
        "ood_max_abs_z": ood_score,
        "ood_feature_z": ood_detail,
        "low_confidence": low_confidence,
        "fallback_reason": fallback_reason,
        "features": feature_row,
        "in_distribution": not ood,
        "prediction_set": prediction_set,
        "selected_policy": str(thresholds["ml_policy"]),
        "thresholds_used": thresholds,
    }


__all__ = ["load_model_bundle", "predict_with_model", "resolve_thresholds", "_ood_score"]
