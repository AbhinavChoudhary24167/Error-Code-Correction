import json
import subprocess
import sys
from pathlib import Path

from ml.dataset import build_dataset
from ml.evaluate import evaluate_model
from ml.train import train_models
from ml.splits import create_deterministic_splits

from tests.python.test_ml_integration import REPO, _new_base


def test_deterministic_split_script_reproducible():
    base = _new_base("split_repro")
    dataset_dir = base / "dataset"
    split_a = base / "split_a.json"
    split_b = base / "split_b.json"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=12)
    create_deterministic_splits(dataset_dir, split_a, seed=99)
    create_deterministic_splits(dataset_dir, split_b, seed=99)

    assert json.loads(split_a.read_text(encoding="utf-8")) == json.loads(split_b.read_text(encoding="utf-8"))


def test_holdout_evaluation_outputs_and_signoff_passes():
    base = _new_base("holdout_eval")
    dataset_dir = base / "dataset"
    model_dir = base / "model"
    eval_dir = base / "eval"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=8)
    create_deterministic_splits(dataset_dir, seed=8)
    train_models(dataset_dir, model_dir, seed=8, model_type="linear")

    artifacts = evaluate_model(
        dataset_dir,
        model_dir,
        eval_dir,
        split="holdout",
        signoff_thresholds=REPO / "config" / "signoff_thresholds.json",
        strict_signoff=True,
    )

    evaluation = json.loads(artifacts["evaluation"].read_text(encoding="utf-8"))
    holdout_report = json.loads(artifacts["holdout_report"].read_text(encoding="utf-8"))

    assert evaluation["summary"]["split"] == "holdout"
    assert evaluation["signoff"]["pass"] is True
    assert set(holdout_report.keys()) == {"overall", "worst_bin_error", "bias"}
    assert set(holdout_report["worst_bin_error"].keys()) == {"node", "vdd", "temp", "gate"}


def test_holdout_strict_signoff_fails_when_thresholds_too_low(tmp_path: Path):
    base = _new_base("holdout_fail")
    dataset_dir = base / "dataset"
    model_dir = base / "model"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=13)
    create_deterministic_splits(dataset_dir, seed=13)
    train_models(dataset_dir, model_dir, seed=13, model_type="linear")

    thresholds = {
        "overall": {
            "fit_true": {"mae": -1.0, "mape_pct": -1.0, "rmse": -1.0},
            "carbon_true": {"mae": -1.0, "mape_pct": -1.0, "rmse": -1.0},
            "energy_true": {"mae": -1.0, "mape_pct": -1.0, "rmse": -1.0},
        },
        "worst_bin": {"max_fit_mae": -1.0},
        "bias": {"max_abs_mean_error": -1.0},
    }
    cfg = tmp_path / "strict_fail_thresholds.json"
    cfg.write_text(json.dumps(thresholds, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "evaluate",
        "--dataset",
        str(dataset_dir),
        "--model",
        str(model_dir),
        "--out",
        str(base / "eval"),
        "--split",
        "holdout",
        "--signoff-thresholds",
        str(cfg),
        "--strict-signoff",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert res.returncode != 0
