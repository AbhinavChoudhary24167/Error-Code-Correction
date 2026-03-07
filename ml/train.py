"""Training pipeline for optional ECC ML models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .features import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMNS,
    resolve_dataset_feature_spec,
)
from .model_registry import save_model_bundle
from .predict import _ood_score


def _as_float_dict(series: pd.Series) -> dict[str, float]:
    return {str(k): float(v) for k, v in series.items()}


def _fit_classifier(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    *,
    seed: int,
    model_type: str,
    categorical_features: list[str],
    numeric_features: list[str],
) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ("num", "passthrough", numeric_features),
        ]
    )

    if y_train.nunique() < 2:
        model = DummyClassifier(strategy="most_frequent")
    else:
        if model_type == "linear":
            model = LogisticRegression(max_iter=1000, random_state=seed)
        elif model_type == "gbdt":
            model = RandomForestClassifier(n_estimators=400, random_state=seed, class_weight="balanced")
        else:
            model = RandomForestClassifier(
                n_estimators=200,
                random_state=seed,
                class_weight="balanced",
            )

    pipe = Pipeline([("preprocess", preprocess), ("model", model)])
    pipe.fit(X_train, y_train)
    return pipe


def _fit_regressor(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    *,
    seed: int,
    model_type: str,
    categorical_features: list[str],
    numeric_features: list[str],
) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ("num", "passthrough", numeric_features),
        ]
    )

    if y_train.nunique() < 2:
        model = DummyRegressor(strategy="mean")
    else:
        if model_type == "linear":
            model = Ridge(random_state=seed)
        elif model_type == "gbdt":
            model = RandomForestRegressor(n_estimators=400, random_state=seed)
        else:
            model = RandomForestRegressor(n_estimators=200, random_state=seed)

    pipe = Pipeline([("preprocess", preprocess), ("model", model)])
    pipe.fit(X_train, y_train)
    return pipe


def _bounded_quantile(values: np.ndarray, q: float) -> float:
    if values.size == 0:
        return 0.0
    q = min(max(float(q), 0.0), 1.0)
    return float(np.quantile(values, q))


def _expected_calibration_error(
    y_true: np.ndarray,
    y_pred_idx: np.ndarray,
    confidences: np.ndarray,
    bins: int = 10,
) -> float:
    if y_true.size == 0:
        return 0.0
    ece = 0.0
    n = float(y_true.size)
    edges = np.linspace(0.0, 1.0, bins + 1)
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        if i == bins - 1:
            mask = (confidences >= lo) & (confidences <= hi)
        else:
            mask = (confidences >= lo) & (confidences < hi)
        count = int(mask.sum())
        if count == 0:
            continue
        acc = float((y_true[mask] == y_pred_idx[mask]).mean())
        conf = float(confidences[mask].mean())
        ece += abs(acc - conf) * (count / n)
    return float(ece)


def _multiclass_brier(probs: np.ndarray, y_true_idx: np.ndarray) -> float:
    if probs.size == 0:
        return 0.0
    one_hot = np.zeros_like(probs)
    for i, idx in enumerate(y_true_idx):
        if 0 <= idx < probs.shape[1]:
            one_hot[i, idx] = 1.0
    return float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))


def _conformal_probability_floor(
    probs: np.ndarray,
    y_true_idx: np.ndarray,
    alpha: float,
) -> tuple[float, float]:
    """Return (probability floor, observed coverage) for split-conformal sets."""

    if probs.size == 0 or y_true_idx.size == 0:
        # Degenerate calibration set: fallback to singleton top-1 sets.
        return 1.0, 1.0

    n = y_true_idx.size
    true_probs = np.asarray([probs[i, idx] for i, idx in enumerate(y_true_idx)], dtype=float)
    nonconformity = 1.0 - true_probs

    # Conservative split-conformal quantile index.
    q_level = min(1.0, max(0.0, np.ceil((n + 1) * (1.0 - alpha)) / n))
    qhat = _bounded_quantile(nonconformity, q_level)
    prob_floor = float(min(max(1.0 - qhat, 0.0), 1.0))

    coverage_flags: list[bool] = []
    for i, idx in enumerate(y_true_idx):
        pred_set = np.where(probs[i] >= prob_floor)[0]
        if pred_set.size == 0:
            pred_set = np.asarray([int(np.argmax(probs[i]))])
        coverage_flags.append(int(idx) in set(int(x) for x in pred_set.tolist()))
    observed_coverage = float(np.mean(coverage_flags)) if coverage_flags else 1.0
    return prob_floor, observed_coverage


def _calibrate_ood(
    *,
    bundle_stub: dict[str, Any],
    X_train: pd.DataFrame,
    numeric_features: list[str],
    method: str,
    quantile: float,
    seed: int,
) -> tuple[dict[str, Any], float]:
    method_norm = str(method).strip().lower()
    ood_payload: dict[str, Any] = {"method": method_norm}

    if not numeric_features:
        return ood_payload, 0.0

    X_num = X_train[numeric_features].to_numpy(dtype=float)
    scores: list[float] = []

    if method_norm == "iforest":
        iforest = IsolationForest(random_state=seed, contamination="auto")
        iforest.fit(X_num)
        ood_payload["iforest_model"] = iforest
        scores = (-iforest.score_samples(X_num)).tolist()
    elif method_norm == "mahalanobis":
        mean = X_num.mean(axis=0)
        cov = np.cov(X_num, rowvar=False)
        if cov.ndim == 0:
            cov = np.asarray([[float(cov)]], dtype=float)
        reg = 1e-6
        cov_reg = cov + np.eye(cov.shape[0]) * reg
        inv_cov = np.linalg.pinv(cov_reg)
        ood_payload["mahalanobis_mean"] = mean.tolist()
        ood_payload["mahalanobis_inv_cov"] = inv_cov.tolist()

        for row in X_num:
            diff = row - mean
            dist = float(np.sqrt(max(0.0, float(diff @ inv_cov @ diff.T))))
            scores.append(dist)
    else:
        ood_payload["method"] = "zscore"
        for _, row in X_train.iterrows():
            feature_row = {k: row[k] for k in numeric_features}
            score, _ = _ood_score(
                bundle_stub,
                feature_row,
                method="zscore",
                numeric_features=numeric_features,
            )
            scores.append(float(score))

    ood_threshold = _bounded_quantile(np.asarray(scores, dtype=float), quantile)
    return ood_payload, float(ood_threshold)


def train_models(
    dataset_dir: Path,
    model_out: Path,
    seed: int = 1,
    *,
    model_type: str = "rf",
    calibrate_confidence: str = "none",
    confidence_target_metric: str = "accuracy",
    ood_method: str = "zscore",
    ood_quantile: float = 0.995,
    conformal_alpha: float = 0.1,
) -> dict[str, Path]:
    """Train classifier/regressors and persist model artifacts."""

    dataset_dir = dataset_dir.resolve()
    model_out = model_out.resolve()
    model_out.mkdir(parents=True, exist_ok=True)

    dataset_path = dataset_dir / "dataset.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

    df = pd.read_csv(dataset_path)
    feature_spec = resolve_dataset_feature_spec(dataset_dir, dataframe_columns=df.columns)
    categorical_features = list(feature_spec.get("categorical", CATEGORICAL_FEATURES))
    numeric_features = list(feature_spec.get("numeric", NUMERIC_FEATURES))

    required = set(categorical_features + numeric_features + TARGET_COLUMNS)
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset missing columns: {missing}")

    X = df[categorical_features + numeric_features].copy()
    y_cls = df["label_code"].astype(str)
    y_fit = df["fit_true"].astype(float)
    y_carbon = df["carbon_true"].astype(float)
    y_energy = df["energy_true"].astype(float)

    if len(df) < 4:
        X_train = X_test = X
        y_cls_train = y_cls_test = y_cls
        y_fit_train = y_fit_test = y_fit
        y_carbon_train = y_carbon_test = y_carbon
        y_energy_train = y_energy_test = y_energy
    else:
        idx_train, idx_test = train_test_split(
            df.index,
            test_size=0.25,
            random_state=seed,
            shuffle=True,
        )
        X_train = X.loc[idx_train]
        X_test = X.loc[idx_test]
        y_cls_train, y_cls_test = y_cls.loc[idx_train], y_cls.loc[idx_test]
        y_fit_train, y_fit_test = y_fit.loc[idx_train], y_fit.loc[idx_test]
        y_carbon_train, y_carbon_test = y_carbon.loc[idx_train], y_carbon.loc[idx_test]
        y_energy_train, y_energy_test = y_energy.loc[idx_train], y_energy.loc[idx_test]

    clf = _fit_classifier(
        X_train,
        y_cls_train,
        seed=seed,
        model_type=model_type,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
    )
    if calibrate_confidence in {"isotonic", "platt"} and y_cls_train.nunique() > 1 and len(X_train) >= 10:
        method = "isotonic" if calibrate_confidence == "isotonic" else "sigmoid"
        clf = CalibratedClassifierCV(clf, cv=3, method=method)
        clf.fit(X_train, y_cls_train)

    reg_fit = _fit_regressor(
        X_train,
        y_fit_train,
        seed=seed,
        model_type=model_type,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
    )
    reg_carbon = _fit_regressor(
        X_train,
        y_carbon_train,
        seed=seed,
        model_type=model_type,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
    )
    reg_energy = _fit_regressor(
        X_train,
        y_energy_train,
        seed=seed,
        model_type=model_type,
        categorical_features=categorical_features,
        numeric_features=numeric_features,
    )

    pred_cls = clf.predict(X_test)
    pred_fit = reg_fit.predict(X_test)
    pred_carbon = reg_carbon.predict(X_test)
    pred_energy = reg_energy.predict(X_test)

    acc = float(accuracy_score(y_cls_test, pred_cls)) if len(y_cls_test) else 1.0
    fit_mae = float(mean_absolute_error(y_fit_test, pred_fit)) if len(y_fit_test) else 0.0
    carbon_mae = float(mean_absolute_error(y_carbon_test, pred_carbon)) if len(y_carbon_test) else 0.0
    energy_mae = float(mean_absolute_error(y_energy_test, pred_energy)) if len(y_energy_test) else 0.0

    fit_r2 = float(r2_score(y_fit_test, pred_fit)) if len(y_fit_test) > 1 else 1.0
    carbon_r2 = float(r2_score(y_carbon_test, pred_carbon)) if len(y_carbon_test) > 1 else 1.0
    energy_r2 = float(r2_score(y_energy_test, pred_energy)) if len(y_energy_test) > 1 else 1.0

    if numeric_features:
        means = _as_float_dict(X_train[numeric_features].mean())
        stds = _as_float_dict(X_train[numeric_features].std(ddof=0).replace(0, 1.0))
    else:
        means = {}
        stds = {}

    confidence_threshold = 0.6
    if acc < 0.5:
        confidence_threshold = 0.75

    classes = np.asarray(clf.classes_)
    probs_test = clf.predict_proba(X_test) if len(X_test) else np.zeros((0, len(classes)))
    class_index = {str(c): i for i, c in enumerate(classes.tolist())}
    y_test_idx = np.asarray([class_index[str(v)] for v in y_cls_test.tolist()], dtype=int) if len(y_cls_test) else np.zeros((0,), dtype=int)
    y_pred_idx = np.asarray([class_index.get(str(v), -1) for v in pred_cls.tolist()], dtype=int) if len(pred_cls) else np.zeros((0,), dtype=int)
    confidences = probs_test.max(axis=1) if probs_test.size else np.zeros((0,), dtype=float)

    ece = _expected_calibration_error(y_test_idx, y_pred_idx, confidences, bins=10)
    brier = _multiclass_brier(probs_test, y_test_idx)

    prob_floor, pred_set_coverage = _conformal_probability_floor(
        probs_test,
        y_test_idx,
        alpha=float(conformal_alpha),
    )

    if confidences.size:
        mask = confidences >= confidence_threshold
        if mask.any():
            covered = []
            for i in np.where(mask)[0].tolist():
                pred_set = np.where(probs_test[i] >= prob_floor)[0]
                if pred_set.size == 0:
                    pred_set = np.asarray([int(np.argmax(probs_test[i]))])
                covered.append(int(y_test_idx[i]) in set(int(x) for x in pred_set.tolist()))
            coverage_at_conf = float(np.mean(covered)) if covered else 1.0
        else:
            # No samples meet confidence minimum; treat as neutral fully-covered edge case.
            coverage_at_conf = 1.0
    else:
        coverage_at_conf = 1.0

    bundle_stub = {
        "train_stats": {
            "means": means,
            "stds": stds,
        }
    }
    ood_payload, ood_threshold = _calibrate_ood(
        bundle_stub=bundle_stub,
        X_train=X_train,
        numeric_features=numeric_features,
        method=ood_method,
        quantile=float(ood_quantile),
        seed=seed,
    )

    thresholds = {
        "confidence_min": float(confidence_threshold),
        "ood_max_abs_z": float(ood_threshold),
        "ood_method": str(ood_payload.get("method", "zscore")),
        "ood_threshold": float(ood_threshold),
        "conformal_alpha": float(conformal_alpha),
        "prediction_set_min_coverage": float(pred_set_coverage),
        "ml_policy": "carbon_min",
        # Internal helper key used during prediction set construction.
        "conformal_prob_min": float(prob_floor),
    }

    uncertainty = {
        "calibration_method": (
            f"{calibrate_confidence}+split_conformal"
            if calibrate_confidence != "none"
            else "split_conformal"
        ),
        "ece": float(ece),
        "brier_score": float(brier),
        "coverage_at_confidence_min": float(coverage_at_conf),
    }

    base_clf = clf.calibrated_classifiers_[0].estimator if isinstance(clf, CalibratedClassifierCV) else clf
    transformed_features = list(base_clf.named_steps["preprocess"].get_feature_names_out())

    bundle: dict[str, Any] = {
        "version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": int(seed),
        "model_type": model_type,
        "calibrate_confidence": calibrate_confidence,
        "confidence_target_metric": confidence_target_metric,
        "features": {
            "categorical": categorical_features,
            "numeric": numeric_features,
            "enabled_optional": list(feature_spec.get("enabled_features", [])),
            "feature_pack": str(feature_spec.get("feature_pack", "core")),
            "transformed": transformed_features,
        },
        "classifier": clf,
        "regressors": {
            "fit": reg_fit,
            "carbon": reg_carbon,
            "energy": reg_energy,
        },
        "train_stats": {
            "means": means,
            "stds": stds,
            "train_size": int(len(X_train)),
            "test_size": int(len(X_test)),
        },
        "thresholds": thresholds,
        "ood": ood_payload,
    }

    model_path = save_model_bundle(bundle, model_out)

    metrics = {
        "classifier": {
            "accuracy": acc,
            "target_metric": confidence_target_metric,
        },
        "regression": {
            "fit": {"mae": fit_mae, "r2": fit_r2},
            "carbon": {"mae": carbon_mae, "r2": carbon_r2},
            "energy": {"mae": energy_mae, "r2": energy_r2},
        },
    }

    metrics_path = model_out / "metrics.json"
    features_path = model_out / "features.json"
    thresholds_path = model_out / "thresholds.json"
    uncertainty_path = model_out / "uncertainty.json"
    model_card_path = model_out / "model_card.md"

    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    features_path.write_text(json.dumps(bundle["features"], indent=2), encoding="utf-8")
    thresholds_path.write_text(json.dumps(thresholds, indent=2), encoding="utf-8")
    uncertainty_path.write_text(json.dumps(uncertainty, indent=2), encoding="utf-8")

    model_card = "\n".join(
        [
            "# ECC ML Model Card",
            "",
            "- Type: advisory-only selector and metric predictor",
            f"- Seed: {seed}",
            f"- Training rows: {len(X_train)}",
            f"- Test rows: {len(X_test)}",
            f"- Classifier accuracy: {acc:.4f}",
            f"- FIT MAE: {fit_mae:.6g}",
            f"- Carbon MAE: {carbon_mae:.6g}",
            f"- Energy MAE: {energy_mae:.6g}",
            f"- OOD method: {thresholds['ood_method']}",
            f"- OOD threshold: {thresholds['ood_threshold']:.6g}",
            f"- Conformal alpha: {thresholds['conformal_alpha']}",
            "",
            "## Safety",
            "",
            "Hard constraints are enforced by the baseline selector first.",
            "ML output is advisory and should fallback on low confidence or OOD.",
        ]
    )
    model_card_path.write_text(model_card + "\n", encoding="utf-8")

    return {
        "model": model_path,
        "metrics": metrics_path,
        "features": features_path,
        "thresholds": thresholds_path,
        "uncertainty": uncertainty_path,
        "model_card": model_card_path,
    }
