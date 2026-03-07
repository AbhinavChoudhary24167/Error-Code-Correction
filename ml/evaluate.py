"""Evaluation helpers for optional ECC ML models."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error

from .features import row_to_feature_dict, resolve_model_feature_spec
from .model_registry import load_model_bundle
from .predict import _ood_score, resolve_thresholds


TARGET_TO_PRED = {
    "fit_true": "fit",
    "carbon_true": "carbon",
    "energy_true": "energy",
}


def _safe_mape(y_true: pd.Series, y_pred: pd.Series) -> float:
    eps = 1e-12
    denom = y_true.abs() > eps
    if int(denom.sum()) == 0:
        return 0.0
    pct = ((y_true[denom] - y_pred[denom]).abs() / y_true[denom].abs()) * 100.0
    return float(pct.mean())


def _safe_rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    if len(y_true) == 0:
        return 0.0
    sq = ((y_true - y_pred) ** 2).mean()
    return float(math.sqrt(float(sq)))


def _calc_target_metrics(df: pd.DataFrame, target: str, pred_col: str) -> dict[str, float]:
    y_true = df[target].astype(float)
    y_pred = df[pred_col].astype(float)
    err = y_pred - y_true
    mae = float(mean_absolute_error(y_true, y_pred)) if len(df) else 0.0
    return {
        "mae": mae,
        "mape_pct": _safe_mape(y_true, y_pred),
        "rmse": _safe_rmse(y_true, y_pred),
        "mean_error": float(err.mean()) if len(df) else 0.0,
        "mean_percentage_error_pct": float((((err) / y_true.replace(0.0, pd.NA)).dropna() * 100.0).mean()) if len(df) else 0.0,
    }


def _worst_bin_metrics(df: pd.DataFrame, *, target: str, pred_col: str) -> dict[str, dict[str, object]]:
    if len(df) == 0:
        return {
            "node": {"bin": None, "mae": 0.0, "rows": 0},
            "vdd": {"bin": None, "mae": 0.0, "rows": 0},
            "temp": {"bin": None, "mae": 0.0, "rows": 0},
            "gate": {"bin": None, "mae": 0.0, "rows": 0},
        }

    def worst_for(col: str) -> dict[str, object]:
        grouped = []
        for bin_value, g in df.groupby(col):
            mae = float(mean_absolute_error(g[target].astype(float), g[pred_col].astype(float)))
            grouped.append((mae, str(bin_value), int(len(g))))
        grouped.sort(reverse=True)
        top = grouped[0]
        return {"bin": top[1], "mae": top[0], "rows": top[2]}

    return {
        "node": worst_for("node"),
        "vdd": worst_for("vdd"),
        "temp": worst_for("temp"),
        "gate": worst_for("code"),
    }


def _select_eval_rows(df: pd.DataFrame, dataset_dir: Path, split: str) -> pd.DataFrame:
    if split == "all":
        return df.copy()

    split_path = dataset_dir / "dataset_splits.json"
    if not split_path.is_file():
        raise FileNotFoundError(
            f"Missing split file: {split_path}. Run `eccsim.py ml split-dataset --dataset {dataset_dir}` first."
        )
    payload = json.loads(split_path.read_text(encoding="utf-8"))
    rows = payload.get("rows", {}).get(split)
    if not isinstance(rows, list):
        raise ValueError(f"Split {split!r} not found in {split_path}")
    return df.iloc[rows].reset_index(drop=True)


def _evaluate_thresholds(holdout: dict[str, object], thresholds: dict[str, object]) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    for target_key, target_thresholds in thresholds.get("overall", {}).items():
        observed = holdout["overall"].get(target_key, {})
        for metric_key, limit in target_thresholds.items():
            val = float(observed.get(metric_key, 0.0))
            lim = float(limit)
            checks.append(
                {
                    "metric": f"overall.{target_key}.{metric_key}",
                    "value": val,
                    "limit": lim,
                    "pass": val <= lim,
                }
            )

    bias_limit = thresholds.get("bias", {}).get("max_abs_mean_error")
    if bias_limit is not None:
        lim = float(bias_limit)
        for target_key, observed in holdout["bias"].items():
            val = abs(float(observed.get("mean_error", 0.0)))
            checks.append(
                {
                    "metric": f"bias.{target_key}.abs_mean_error",
                    "value": val,
                    "limit": lim,
                    "pass": val <= lim,
                }
            )

    worst_fit_limit = thresholds.get("worst_bin", {}).get("max_fit_mae")
    if worst_fit_limit is not None:
        lim = float(worst_fit_limit)
        for axis, observed in holdout["worst_bin_error"].items():
            val = float(observed.get("mae", 0.0))
            checks.append(
                {
                    "metric": f"worst_bin_error.{axis}.mae",
                    "value": val,
                    "limit": lim,
                    "pass": val <= lim,
                }
            )

    return {
        "pass": bool(all(bool(c["pass"]) for c in checks)),
        "checks": checks,
    }


def evaluate_model(
    dataset_dir: Path,
    model_dir: Path,
    out_dir: Path,
    *,
    policy: str | None = None,
    ood_threshold: float | None = None,
    split: str = "all",
    signoff_thresholds: Path | None = None,
    strict_signoff: bool = False,
) -> dict[str, Path]:
    dataset_path = dataset_dir / "dataset.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    full_df = pd.read_csv(dataset_path)
    df = _select_eval_rows(full_df, dataset_dir, split)
    y = df["label_code"].astype(str)

    bundle = load_model_bundle(model_dir)
    feature_spec = resolve_model_feature_spec(bundle)
    categorical_features = list(feature_spec.get("categorical", ["code"]))
    numeric_features = list(feature_spec.get("numeric", []))

    feature_rows = [
        row_to_feature_dict(
            row.to_dict(),
            categorical_features=categorical_features,
            numeric_features=numeric_features,
        )
        for _, row in df.iterrows()
    ]
    X = pd.DataFrame(feature_rows, columns=categorical_features + numeric_features)

    clf = bundle["classifier"]
    reg_fit = bundle["regressors"]["fit"]
    reg_carbon = bundle["regressors"]["carbon"]
    reg_energy = bundle["regressors"]["energy"]

    if len(df):
        y_pred = clf.predict(X)
        fit_pred = reg_fit.predict(X)
        carbon_pred = reg_carbon.predict(X)
        energy_pred = reg_energy.predict(X)
        probs = clf.predict_proba(X)
        confidences = [float(row.max()) for row in probs]
    else:
        y_pred = []
        fit_pred = []
        carbon_pred = []
        energy_pred = []
        confidences = []

    resolved = resolve_thresholds(
        bundle.get("thresholds", {}),
        model_dir=model_dir,
        ood_threshold_override=ood_threshold,
        policy_override=policy,
    )
    confidence_min = float(resolved["confidence_min"])
    ood_method = str(resolved["ood_method"])
    ood_max = float(resolved["ood_threshold"])

    ood_count = 0
    low_conf_count = 0
    for feature_row in feature_rows:
        score, _ = _ood_score(
            bundle,
            feature_row,
            method=ood_method,
            numeric_features=numeric_features,
        )
        if score > ood_max:
            ood_count += 1
    for conf in confidences:
        if conf < confidence_min:
            low_conf_count += 1

    evaluation = {
        "summary": {
            "rows": int(len(df)),
            "policy": str(resolved["ml_policy"]),
            "split": str(split),
            "fallback_rate": float((ood_count + low_conf_count) / max(len(df), 1)),
            "ood_rate": float(ood_count / max(len(df), 1)),
            "ood_method": ood_method,
            "ood_threshold": ood_max,
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

    df_metrics = df.copy()
    df_metrics["fit_pred"] = fit_pred
    df_metrics["carbon_pred"] = carbon_pred
    df_metrics["energy_pred"] = energy_pred

    holdout_report = {
        "overall": {
            key: _calc_target_metrics(df_metrics, key, f"{pred}_pred") for key, pred in TARGET_TO_PRED.items()
        },
        "worst_bin_error": _worst_bin_metrics(df_metrics, target="fit_true", pred_col="fit_pred"),
        "bias": {
            key: {
                "mean_error": vals["mean_error"],
                "mean_percentage_error_pct": vals["mean_percentage_error_pct"],
            }
            for key, vals in {
                k: _calc_target_metrics(df_metrics, k, f"{p}_pred") for k, p in TARGET_TO_PRED.items()
            }.items()
        },
    }
    evaluation["holdout_report"] = holdout_report

    threshold_status = None
    if signoff_thresholds is not None:
        thresholds_payload = json.loads(signoff_thresholds.read_text(encoding="utf-8"))
        threshold_status = _evaluate_thresholds(holdout_report, thresholds_payload)
        evaluation["signoff"] = {
            "thresholds_file": str(signoff_thresholds),
            **threshold_status,
        }
        if strict_signoff and not bool(threshold_status["pass"]):
            raise ValueError("Signoff thresholds failed in strict mode")

    out = out_dir / "evaluation.json"
    out.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

    holdout_out = out_dir / "holdout_report.json"
    holdout_out.write_text(json.dumps(holdout_report, indent=2), encoding="utf-8")
    artifacts = {"evaluation": out, "holdout_report": holdout_out}
    if threshold_status is not None:
        signoff_out = out_dir / "signoff_status.json"
        signoff_out.write_text(json.dumps(threshold_status, indent=2), encoding="utf-8")
        artifacts["signoff"] = signoff_out
    return artifacts
