"""Training pipeline for optional ECC ML models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET_COLUMNS
from .model_registry import save_model_bundle


def _as_float_dict(series: pd.Series) -> dict[str, float]:
    return {str(k): float(v) for k, v in series.items()}


def _fit_classifier(X_train: pd.DataFrame, y_train: pd.Series, seed: int, model_type: str) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )

    if y_train.nunique() < 2:
        model = DummyClassifier(strategy="most_frequent")
    else:
        if model_type == "linear":
            model = LogisticRegression(max_iter=1000, random_state=seed)
        elif model_type == "gbdt":
            model = GradientBoostingClassifier(random_state=seed)
        else:
            model = RandomForestClassifier(
                n_estimators=200,
                random_state=seed,
                class_weight="balanced",
            )

    pipe = Pipeline([("preprocess", preprocess), ("model", model)])
    pipe.fit(X_train, y_train)
    return pipe


def _fit_regressor(X_train: pd.DataFrame, y_train: pd.Series, seed: int, model_type: str) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )

    if y_train.nunique() < 2:
        model = DummyRegressor(strategy="mean")
    else:
        if model_type == "linear":
            model = Ridge(random_state=seed)
        elif model_type == "gbdt":
            model = GradientBoostingRegressor(random_state=seed)
        else:
            model = RandomForestRegressor(n_estimators=200, random_state=seed)

    pipe = Pipeline([("preprocess", preprocess), ("model", model)])
    pipe.fit(X_train, y_train)
    return pipe


def train_models(
    dataset_dir: Path,
    model_out: Path,
    seed: int = 1,
    *,
    model_type: str = "rf",
    calibrate_confidence: str = "none",
    confidence_target_metric: str = "accuracy",
) -> dict[str, Path]:
    """Train classifier/regressors and persist model artifacts."""

    dataset_dir = dataset_dir.resolve()
    model_out = model_out.resolve()
    model_out.mkdir(parents=True, exist_ok=True)

    dataset_path = dataset_dir / "dataset.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

    df = pd.read_csv(dataset_path)
    required = set(CATEGORICAL_FEATURES + NUMERIC_FEATURES + TARGET_COLUMNS)
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset missing columns: {missing}")

    X = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES].copy()
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

    clf = _fit_classifier(X_train, y_cls_train, seed=seed, model_type=model_type)
    if calibrate_confidence in {"isotonic", "platt"} and y_cls_train.nunique() > 1 and len(X_train) >= 10:
        method = "isotonic" if calibrate_confidence == "isotonic" else "sigmoid"
        clf = CalibratedClassifierCV(clf, cv=3, method=method)
        clf.fit(X_train, y_cls_train)

    reg_fit = _fit_regressor(X_train, y_fit_train, seed=seed, model_type=model_type)
    reg_carbon = _fit_regressor(X_train, y_carbon_train, seed=seed, model_type=model_type)
    reg_energy = _fit_regressor(X_train, y_energy_train, seed=seed, model_type=model_type)

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

    means = _as_float_dict(X_train[NUMERIC_FEATURES].mean())
    stds = _as_float_dict(X_train[NUMERIC_FEATURES].std(ddof=0).replace(0, 1.0))

    confidence_threshold = 0.6
    if acc < 0.5:
        confidence_threshold = 0.75

    thresholds = {
        "confidence_min": confidence_threshold,
        "ood_max_abs_z": 4.0,
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
            "categorical": CATEGORICAL_FEATURES,
            "numeric": NUMERIC_FEATURES,
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
    model_card_path = model_out / "model_card.md"

    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    features_path.write_text(json.dumps(bundle["features"], indent=2), encoding="utf-8")
    thresholds_path.write_text(json.dumps(thresholds, indent=2), encoding="utf-8")

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
        "model_card": model_card_path,
    }
