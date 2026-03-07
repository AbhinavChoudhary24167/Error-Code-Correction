"""Lifecycle utilities for optional ECC ML workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .features import row_to_feature_dict, resolve_model_feature_spec
from .model_registry import load_model_bundle
from .predict import _ood_score


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report_card(model_dir: Path, out_path: Path | None = None) -> Path:
    model_dir = Path(model_dir)
    card_path = out_path if out_path is not None else (model_dir / "model_card.md")

    metrics = _load_json(model_dir / "metrics.json")
    thresholds = _load_json(model_dir / "thresholds.json")
    uncertainty = _load_json(model_dir / "uncertainty.json")

    evaluation_path = model_dir / "evaluation.json"
    evaluation = _load_json(evaluation_path) if evaluation_path.is_file() else None

    lines = [
        "# ECC ML Report Card",
        "",
        "## Metrics",
        "",
        "```json",
        json.dumps(metrics, indent=2, sort_keys=True),
        "```",
        "",
        "## Thresholds",
        "",
        "```json",
        json.dumps(thresholds, indent=2, sort_keys=True),
        "```",
        "",
        "## Uncertainty",
        "",
        "```json",
        json.dumps(uncertainty, indent=2, sort_keys=True),
        "```",
        "",
        "## Evaluation",
        "",
    ]
    if evaluation is None:
        lines.extend([
            "No evaluation artifact found (`evaluation.json`).",
            "",
            "Run `eccsim.py ml evaluate --dataset <dataset_dir> --model <model_dir> --out <eval_dir>` to generate it.",
        ])
    else:
        lines.extend([
            "```json",
            json.dumps(evaluation, indent=2, sort_keys=True),
            "```",
        ])

    card_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return card_path


def _severity(drift_detected: bool, max_psi: float, ood_rate_delta: float, confidence_shift: float) -> str:
    if not drift_detected:
        return "none"
    if max_psi >= 1.0 or ood_rate_delta >= 0.2 or confidence_shift <= -0.2:
        return "high"
    if max_psi >= 0.5 or ood_rate_delta >= 0.1 or confidence_shift <= -0.1:
        return "medium"
    return "low"


def check_drift(model_dir: Path, new_data_dir: Path, out_path: Path) -> tuple[Path, bool]:
    model_dir = Path(model_dir)
    new_data_dir = Path(new_data_dir)
    out_path = Path(out_path)

    dataset_path = new_data_dir / "dataset.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

    bundle = load_model_bundle(model_dir)
    thresholds = _load_json(model_dir / "thresholds.json")

    feature_spec = resolve_model_feature_spec(bundle)
    categorical_features = list(feature_spec.get("categorical", ["code"]))
    numeric_features = list(feature_spec.get("numeric", []))

    df = pd.read_csv(dataset_path)
    feature_rows = [
        row_to_feature_dict(
            row.to_dict(),
            categorical_features=categorical_features,
            numeric_features=numeric_features,
        )
        for _, row in df.iterrows()
    ]

    baseline_means = bundle.get("train_stats", {}).get("means", {})
    baseline_stds = bundle.get("train_stats", {}).get("stds", {})

    psi: dict[str, float] = {}
    for feature in numeric_features:
        baseline_mean = float(baseline_means.get(feature, 0.0))
        baseline_std = float(baseline_stds.get(feature, 0.0))
        if baseline_std == 0.0:
            baseline_std = 1.0
        new_mean = float(df[feature].astype(float).mean()) if feature in df.columns and len(df) else baseline_mean
        psi[feature] = float(abs(new_mean - baseline_mean) / baseline_std)

    clf = bundle["classifier"]
    X = pd.DataFrame(feature_rows, columns=categorical_features + numeric_features)
    probs = clf.predict_proba(X)
    confidences = [float(row.max()) for row in probs]

    ood_method = str(thresholds.get("ood_method", "zscore"))
    ood_threshold = float(thresholds.get("ood_threshold", thresholds.get("ood_max_abs_z", 3.0)))
    ood_count = 0
    for feature_row in feature_rows:
        score, _ = _ood_score(bundle, feature_row, method=ood_method, numeric_features=numeric_features)
        if score > ood_threshold:
            ood_count += 1

    ood_rate = float(ood_count / max(len(feature_rows), 1))
    confidence_min = float(thresholds.get("confidence_min", 0.5))
    mean_confidence = float(sum(confidences) / max(len(confidences), 1))

    # Baseline is expected near threshold; positive means confidence increase, negative means drop.
    confidence_shift = float(mean_confidence - confidence_min)
    ood_rate_delta = float(ood_rate)
    max_psi = max(psi.values(), default=0.0)
    drift_detected = bool(max_psi > 0.3 or ood_rate_delta > 0.1 or confidence_shift < -0.1)

    payload = {
        "population_stability_index": psi,
        "ood_rate_delta": ood_rate_delta,
        "confidence_shift": confidence_shift,
        "status": {
            "drift_detected": drift_detected,
            "severity": _severity(drift_detected, max_psi, ood_rate_delta, confidence_shift),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path, drift_detected
