import json
import math
import subprocess
import sys
import uuid
from pathlib import Path

import joblib

from ml.dataset import build_dataset
from ml.evaluate import evaluate_model
from ml.predict import predict_with_model
from ml.train import train_models


REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "tests" / "fixtures" / "runtime_ml_tests"


def _new_base(tag: str) -> Path:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    base = RUNTIME / f"{tag}_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=False)
    return base


def _prepare_model(tag: str, seed: int = 1) -> Path:
    base = _new_base(tag)
    dataset_dir = base / "dataset"
    model_dir = base / "model"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=seed)
    train_models(dataset_dir, model_dir, seed=seed)
    return model_dir


def _sample_row() -> dict[str, float | str]:
    return {
        "code": "sec-ded-64",
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.04,
        "scrub_s": 10.0,
        "latency_ns": 1.0,
        "area_logic_mm2": 1.0,
        "area_macro_mm2": 343.5,
    }


def test_ml_training_deterministic_seed():
    model_a = _prepare_model("det_a", seed=1)
    model_b = _prepare_model("det_b", seed=1)

    metrics_a = json.loads((model_a / "metrics.json").read_text(encoding="utf-8"))
    metrics_b = json.loads((model_b / "metrics.json").read_text(encoding="utf-8"))
    thresholds_a = json.loads((model_a / "thresholds.json").read_text(encoding="utf-8"))
    thresholds_b = json.loads((model_b / "thresholds.json").read_text(encoding="utf-8"))

    assert metrics_a == metrics_b
    assert thresholds_a == thresholds_b

    pred_a = predict_with_model(model_a, _sample_row())
    pred_b = predict_with_model(model_b, _sample_row())

    assert pred_a["ml_recommendation"] == pred_b["ml_recommendation"]
    assert pred_a["confidence"] == pred_b["confidence"]
    assert pred_a["predictions"] == pred_b["predictions"]


def test_ml_train_to_predict_smoke():
    model_dir = _prepare_model("smoke", seed=7)
    pred = predict_with_model(model_dir, _sample_row())

    assert isinstance(pred["ml_recommendation"], str)
    assert 0.0 <= float(pred["confidence"]) <= 1.0
    for key in ("FIT", "carbon_kg", "energy_kWh"):
        assert key in pred["predictions"]
        assert math.isfinite(float(pred["predictions"][key]))


def test_selector_ood_fallback():
    model_dir = _prepare_model("ood", seed=1)
    cmd = [
        sys.executable,
        str(REPO / "ecc_selector.py"),
        "--ml-model",
        str(model_dir),
        "--node",
        "14",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--capacity-gib",
        "1000",
        "--ci",
        "0.55",
        "--bitcell-um2",
        "0.04",
        "--json",
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=REPO)
    data = json.loads(res.stdout)

    assert data["fallback_used"] is True
    assert "OOD" in str(data["fallback_reason"])
    assert data["final_decision"] == data["baseline_recommendation"]


def test_ml_cli_build_and_train_smoke():
    base = _new_base("cli_smoke")
    dataset_dir = base / "dataset"
    model_dir = base / "model"

    cmd_build = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "build-dataset",
        "--from",
        str(REPO / "reports" / "examples"),
        "--out",
        str(dataset_dir),
        "--seed",
        "1",
    ]
    cmd_train = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "train",
        "--dataset",
        str(dataset_dir),
        "--model-out",
        str(model_dir),
        "--seed",
        "1",
    ]

    subprocess.run(cmd_build, check=True, capture_output=True, text=True, cwd=REPO)
    subprocess.run(cmd_train, check=True, capture_output=True, text=True, cwd=REPO)

    assert (dataset_dir / "dataset.csv").is_file()
    assert (dataset_dir / "dataset_schema.json").is_file()
    assert (dataset_dir / "dataset_manifest.json").is_file()
    assert (model_dir / "model.joblib").is_file()
    assert (model_dir / "metrics.json").is_file()
    assert (model_dir / "features.json").is_file()
    assert (model_dir / "thresholds.json").is_file()
    assert (model_dir / "model_card.md").is_file()


def test_ml_build_dataset_policy_manifest_fields():
    base = _new_base("policy_manifest")
    dataset_dir = base / "dataset"

    build_dataset(
        REPO / "reports" / "examples",
        dataset_dir,
        seed=2,
        label_policy="utility_balanced",
        utility_alpha_fit=2.0,
        utility_beta_carbon=1.0,
        utility_gamma_energy=0.5,
        split_strategy="scenario_hash",
    )
    manifest = json.loads((dataset_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["label_policy"] == "utility_balanced"
    assert manifest["utility_weights"] == {
        "alpha_fit": 2.0,
        "beta_carbon": 1.0,
        "gamma_energy": 0.5,
    }
    assert manifest["split_strategy"] == "scenario_hash"
    assert manifest["feature_version"] == 1


def test_ml_evaluate_smoke():
    base = _new_base("eval_smoke")
    dataset_dir = base / "dataset"
    model_dir = base / "model"
    eval_dir = base / "eval"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=5, label_policy="fit_min")
    train_models(dataset_dir, model_dir, seed=5, model_type="linear")
    artifacts = evaluate_model(dataset_dir, model_dir, eval_dir, policy="fit_min")

    out = json.loads((artifacts["evaluation"]).read_text(encoding="utf-8"))
    assert out["summary"]["policy"] == "fit_min"
    assert "classification" in out
    assert "regression" in out
    assert "fallback_breakdown" in out


def test_ml_train_gbdt_uses_boosted_estimators():
    base = _new_base("gbdt_models")
    dataset_dir = base / "dataset"
    model_dir = base / "model"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    import pandas as pd

    rows = []
    for idx in range(8):
        rows.append(
            {
                "code": "sec-ded-64" if idx % 2 == 0 else "taec-64",
                "node": 14,
                "vdd": 0.8,
                "temp": 75.0,
                "capacity_gib": 8.0,
                "ci": 0.55,
                "bitcell_um2": 0.04,
                "scrub_s": 10.0,
                "latency_ns": 1.0 + 0.1 * idx,
                "area_logic_mm2": 1.0 + 0.05 * idx,
                "area_macro_mm2": 343.5,
                "fit_true": 100.0 + idx,
                "carbon_true": 50.0 + 0.2 * idx,
                "energy_true": 10.0 + 0.3 * idx,
                "label_code": "sec-ded-64" if idx % 2 == 0 else "taec-64",
                "scenario_hash": f"s{idx}",
                "source_kind": "unit",
                "source_file": "unit.csv",
            }
        )

    pd.DataFrame(rows).to_csv(dataset_dir / "dataset.csv", index=False)

    train_models(dataset_dir, model_dir, seed=3, model_type="gbdt")

    bundle = joblib.load(model_dir / "model.joblib")
    clf_model = bundle["classifier"].named_steps["model"]
    reg_fit_model = bundle["regressors"]["fit"].named_steps["model"]
    reg_carbon_model = bundle["regressors"]["carbon"].named_steps["model"]
    reg_energy_model = bundle["regressors"]["energy"].named_steps["model"]

    assert clf_model.__class__.__name__ == "GradientBoostingClassifier"
    assert reg_fit_model.__class__.__name__ == "GradientBoostingRegressor"
    assert reg_carbon_model.__class__.__name__ == "GradientBoostingRegressor"
    assert reg_energy_model.__class__.__name__ == "GradientBoostingRegressor"


def test_ml_evaluate_defaults_policy_from_manifest():
    base = _new_base("eval_manifest_policy")
    dataset_dir = base / "dataset"
    model_dir = base / "model"
    eval_dir = base / "eval"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=11, label_policy="fit_min")
    train_models(dataset_dir, model_dir, seed=11)
    artifacts = evaluate_model(dataset_dir, model_dir, eval_dir)

    out = json.loads(artifacts["evaluation"].read_text(encoding="utf-8"))
    assert out["summary"]["policy"] == "fit_min"


def test_ml_evaluate_fallback_rate_counts_unique_rows():
    base = _new_base("eval_fallback_unique")
    dataset_dir = base / "dataset"
    model_dir = base / "model"
    eval_dir = base / "eval"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=13)
    train_models(dataset_dir, model_dir, seed=13)

    model_path = model_dir / "model.joblib"
    bundle = joblib.load(model_path)
    bundle["thresholds"]["confidence_min"] = 1.1
    bundle["thresholds"]["ood_max_abs_z"] = -1.0
    joblib.dump(bundle, model_path)

    artifacts = evaluate_model(dataset_dir, model_dir, eval_dir)
    out = json.loads(artifacts["evaluation"].read_text(encoding="utf-8"))
    assert out["summary"]["fallback_rate"] <= 1.0
    assert out["summary"]["fallback_rate"] == 1.0
