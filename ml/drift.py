"""Drift checks for optional ECC ML workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, resolve_model_feature_spec
from .predict import _ood_score, load_model_bundle, resolve_thresholds

_EPS = 1e-9


DRIFT_POLICY_THRESHOLDS: dict[str, dict[str, float]] = {
    "psi": {"warn": 0.2, "fail": 0.3},
    "confidence_shift": {"warn": 0.1, "fail": 0.2},
    "ood_rate_delta": {"warn": 0.05, "fail": 0.1},
}


def _psi_1d(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    if ref.size == 0 or cur.size == 0:
        return 0.0

    lo = float(min(np.min(ref), np.min(cur)))
    hi = float(max(np.max(ref), np.max(cur)))
    if not np.isfinite(lo) or not np.isfinite(hi):
        return 0.0
    if hi <= lo:
        return 0.0

    edges = np.linspace(lo, hi, bins + 1)
    ref_hist, _ = np.histogram(ref, bins=edges)
    cur_hist, _ = np.histogram(cur, bins=edges)

    ref_pct = ref_hist / max(float(ref_hist.sum()), 1.0)
    cur_pct = cur_hist / max(float(cur_hist.sum()), 1.0)

    ref_pct = np.clip(ref_pct.astype(float), _EPS, 1.0)
    cur_pct = np.clip(cur_pct.astype(float), _EPS, 1.0)
    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(max(0.0, psi))


def _feature_frame(
    df: pd.DataFrame,
    *,
    categorical_features: list[str],
    numeric_features: list[str],
) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for col in categorical_features:
        if col in df.columns:
            out[col] = df[col].astype(str)
        else:
            out[col] = "unknown"
    for col in numeric_features:
        if col in df.columns:
            out[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
        else:
            out[col] = 0.0
    return out[categorical_features + numeric_features]


def _reference_numeric_distribution(
    bundle: dict[str, Any],
    *,
    numeric_features: list[str],
    reference_rows: int,
) -> dict[str, np.ndarray]:
    means = bundle.get("train_stats", {}).get("means", {})
    stds = bundle.get("train_stats", {}).get("stds", {})
    n = max(int(reference_rows), 64)
    ref: dict[str, np.ndarray] = {}
    for feat in numeric_features:
        mean = float(means.get(feat, 0.0))
        std = float(stds.get(feat, 1.0))
        if not np.isfinite(std) or std <= 0:
            std = 1.0
        ref[feat] = np.linspace(mean - 1.5 * std, mean + 1.5 * std, n)
    return ref


def compute_drift_report(model_dir: Path, new_data_dir: Path) -> dict[str, Any]:
    model_dir = model_dir.resolve()
    new_data_dir = new_data_dir.resolve()

    dataset_path = new_data_dir / "dataset.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

    bundle = load_model_bundle(model_dir)
    thresholds = resolve_thresholds(bundle.get("thresholds", {}), model_dir=model_dir)
    feature_spec = resolve_model_feature_spec(bundle)
    categorical_features = list(feature_spec.get("categorical", CATEGORICAL_FEATURES))
    numeric_features = list(feature_spec.get("numeric", NUMERIC_FEATURES))

    raw_df = pd.read_csv(dataset_path)
    X = _feature_frame(
        raw_df,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
    )

    reference_numeric = _reference_numeric_distribution(
        bundle,
        numeric_features=numeric_features,
        reference_rows=len(X),
    )
    psi_map: dict[str, float] = {}
    for feat in numeric_features:
        psi_map[feat] = float(_psi_1d(reference_numeric[feat], X[feat].to_numpy(dtype=float)))

    ood_method = str(thresholds["ood_method"])
    ood_threshold = float(thresholds["ood_threshold"])
    ood_scores: list[float] = []
    for _, row in X[numeric_features].iterrows():
        feature_row = {k: float(row[k]) for k in numeric_features}
        score, _ = _ood_score(
            bundle,
            feature_row,
            method=ood_method,
            numeric_features=numeric_features,
        )
        ood_scores.append(float(score))
    new_ood_rate = float(np.mean(np.asarray(ood_scores, dtype=float) > ood_threshold)) if ood_scores else 0.0

    reference_ood_rate = float(bundle.get("train_stats", {}).get("reference_ood_rate", 0.0))
    ood_rate_delta = float(new_ood_rate - reference_ood_rate)

    classifier = bundle["classifier"]
    probs = classifier.predict_proba(X)
    new_confidence_mean = float(np.mean(np.max(probs, axis=1))) if len(probs) else 0.0
    reference_confidence_mean = float(
        bundle.get("train_stats", {}).get("reference_confidence_mean", thresholds["confidence_min"])
    )
    confidence_shift = float(new_confidence_mean - reference_confidence_mean)

    max_psi = float(max(psi_map.values()) if psi_map else 0.0)
    mean_psi = float(np.mean(list(psi_map.values())) if psi_map else 0.0)

    psi_warn = float(DRIFT_POLICY_THRESHOLDS["psi"]["warn"])
    psi_crit = float(DRIFT_POLICY_THRESHOLDS["psi"]["fail"])
    ood_warn = float(DRIFT_POLICY_THRESHOLDS["ood_rate_delta"]["warn"])
    ood_crit = float(DRIFT_POLICY_THRESHOLDS["ood_rate_delta"]["fail"])
    conf_warn = float(DRIFT_POLICY_THRESHOLDS["confidence_shift"]["warn"])
    conf_crit = float(DRIFT_POLICY_THRESHOLDS["confidence_shift"]["fail"])

    drift_detected = bool(
        max_psi >= psi_warn or abs(ood_rate_delta) >= ood_warn or abs(confidence_shift) >= conf_warn
    )
    severity = "none"
    if drift_detected:
        severity = "high" if (
            max_psi >= psi_crit or abs(ood_rate_delta) >= ood_crit or abs(confidence_shift) >= conf_crit
        ) else "medium"

    return {
        "population_stability_index": {k: float(v) for k, v in sorted(psi_map.items())},
        "ood_rate_delta": float(ood_rate_delta),
        "confidence_shift": float(confidence_shift),
        "summary": {
            "max_psi": float(max_psi),
            "mean_psi": float(mean_psi),
            "reference_ood_rate": float(reference_ood_rate),
            "new_ood_rate": float(new_ood_rate),
            "reference_confidence_mean": float(reference_confidence_mean),
            "new_confidence_mean": float(new_confidence_mean),
        },
        "status": {
            "drift_detected": drift_detected,
            "severity": severity,
        },
    }


def compute_drift_policy(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    max_psi = float(summary.get("max_psi", 0.0))
    confidence_shift = float(report.get("confidence_shift", 0.0))
    confidence_drop = max(0.0, -confidence_shift)
    ood_rate_delta = abs(float(report.get("ood_rate_delta", 0.0)))

    warn_hits: list[str] = []
    fail_hits: list[str] = []

    if max_psi >= float(DRIFT_POLICY_THRESHOLDS["psi"]["warn"]):
        warn_hits.append("psi")
    if max_psi >= float(DRIFT_POLICY_THRESHOLDS["psi"]["fail"]):
        fail_hits.append("psi")

    if confidence_drop >= float(DRIFT_POLICY_THRESHOLDS["confidence_shift"]["warn"]):
        warn_hits.append("confidence_shift")
    if confidence_drop >= float(DRIFT_POLICY_THRESHOLDS["confidence_shift"]["fail"]):
        fail_hits.append("confidence_shift")

    if ood_rate_delta >= float(DRIFT_POLICY_THRESHOLDS["ood_rate_delta"]["warn"]):
        warn_hits.append("ood_rate_delta")
    if ood_rate_delta >= float(DRIFT_POLICY_THRESHOLDS["ood_rate_delta"]["fail"]):
        fail_hits.append("ood_rate_delta")

    action = "none"
    if fail_hits:
        action = "fail"
    elif warn_hits:
        action = "warn"

    retrain_recommended = bool(action != "none")
    return {
        "policy_version": 1,
        "thresholds": DRIFT_POLICY_THRESHOLDS,
        "actions": {
            "warn_threshold_hit": bool(warn_hits),
            "fail_threshold_hit": bool(fail_hits),
            "retrain_recommended": retrain_recommended,
            "action": action,
        },
        "triggered_metrics": {
            "warn": sorted(set(warn_hits)),
            "fail": sorted(set(fail_hits)),
        },
    }


def check_drift(
    model_dir: Path,
    new_data_dir: Path,
    out_path: Path,
    *,
    policy_out_path: Path | None = None,
) -> dict[str, Any]:
    report = compute_drift_report(model_dir, new_data_dir)
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    artifacts: dict[str, Any] = {
        "drift": out_path,
        "drift_detected": bool(report["status"]["drift_detected"]),
    }
    if policy_out_path is not None:
        policy_payload = compute_drift_policy(report)
        policy_out_path = policy_out_path.resolve()
        policy_out_path.parent.mkdir(parents=True, exist_ok=True)
        policy_out_path.write_text(json.dumps(policy_payload, indent=2, sort_keys=True), encoding="utf-8")
        artifacts["drift_policy"] = policy_out_path
        artifacts["policy_action"] = str(policy_payload["actions"]["action"])
    return artifacts
