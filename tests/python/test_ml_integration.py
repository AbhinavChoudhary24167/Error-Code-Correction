import json
import math
import subprocess
import sys
import uuid
from pathlib import Path

import joblib

from ml.dataset import build_dataset
from ml.evaluate import evaluate_model
from ml.predict import predict_with_model, resolve_thresholds
from ml.train import train_models


REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "tests" / "fixtures" / "runtime_ml_tests"


def _new_base(tag: str) -> Path:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    base = RUNTIME / f"{tag}_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=False)
    return base


def _prepare_model(tag: str, seed: int = 1, **train_kwargs) -> Path:
    base = _new_base(tag)
    dataset_dir = base / "dataset"
    model_dir = base / "model"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=seed)
    train_models(dataset_dir, model_dir, seed=seed, **train_kwargs)
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
    assert (model_dir / "uncertainty.json").is_file()
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


def test_thresholds_schema_and_uncertainty_artifact():
    model_dir = _prepare_model("schema", seed=3, ood_method="mahalanobis", ood_quantile=0.99, conformal_alpha=0.2)
    thresholds = json.loads((model_dir / "thresholds.json").read_text(encoding="utf-8"))
    for key in (
        "confidence_min",
        "ood_max_abs_z",
        "ood_method",
        "ood_threshold",
        "conformal_alpha",
        "prediction_set_min_coverage",
    ):
        assert key in thresholds

    uncertainty = json.loads((model_dir / "uncertainty.json").read_text(encoding="utf-8"))
    for key in ("calibration_method", "ece", "brier_score", "coverage_at_confidence_min"):
        assert key in uncertainty
    assert isinstance(uncertainty["ece"], float)
    assert isinstance(uncertainty["brier_score"], float)
    assert isinstance(uncertainty["coverage_at_confidence_min"], float)


def test_ood_method_selection_and_threshold_numeric():
    for method in ("zscore", "mahalanobis", "iforest"):
        model_dir = _prepare_model(f"ood_{method}", seed=9, ood_method=method)
        thresholds = json.loads((model_dir / "thresholds.json").read_text(encoding="utf-8"))
        assert thresholds["ood_method"] == method
        assert isinstance(float(thresholds["ood_threshold"]), float)


def test_backward_compatible_threshold_loading_from_legacy_file():
    model_dir = _prepare_model("legacy_thresholds", seed=2)

    bundle = joblib.load(model_dir / "model.joblib")
    bundle["thresholds"] = {
        "confidence_min": 0.61,
        "ood_max_abs_z": 3.2,
    }
    joblib.dump(bundle, model_dir / "model.joblib")

    legacy_thresholds = {
        "confidence_min": 0.61,
        "ood_max_abs_z": 3.2,
    }
    (model_dir / "thresholds.json").write_text(json.dumps(legacy_thresholds, indent=2), encoding="utf-8")

    pred = predict_with_model(model_dir, _sample_row())
    resolved = resolve_thresholds(legacy_thresholds, model_dir=model_dir)
    assert pred["ood_method"] == "zscore"
    assert pred["ood_threshold"] == resolved["ood_threshold"] == 3.2


def test_ml_cli_train_rejects_invalid_quantile():
    base = _new_base("invalid_quantile")
    dataset_dir = base / "dataset"
    model_dir = base / "model"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=1)
    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "train",
        "--dataset",
        str(dataset_dir),
        "--model-out",
        str(model_dir),
        "--ood-quantile",
        "1.2",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert res.returncode != 0
    assert "Expected a float in (0,1)" in (res.stderr + res.stdout)


def test_selector_overrides_and_ml_debug_json_only():
    model_dir = _prepare_model("selector_debug", seed=4)
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
        "8",
        "--ci",
        "0.55",
        "--bitcell-um2",
        "0.04",
        "--ml-confidence-min",
        "0.99",
        "--ml-ood-max",
        "0.1",
        "--ml-policy",
        "utility_balanced",
        "--ml-debug",
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=REPO)
    data = json.loads(res.stdout)

    assert data["selected_policy"] == "utility_balanced"
    assert "confidence_score" in data
    assert "confidence_threshold" in data
    assert "ood_method" in data
    assert "ood_score" in data
    assert "ood_threshold" in data
    assert "in_distribution" in data
    assert "prediction_set" in data
    assert "eligible_candidates" in data
    assert "rejected_candidates" in data
