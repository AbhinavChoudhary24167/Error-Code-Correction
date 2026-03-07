import json
import shutil
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.dataset import build_dataset
from ml.drift import _psi_1d

from tests.python.test_ml_integration import REPO, _new_base, _prepare_model


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)


def test_ml_report_card_includes_expected_sections_with_evaluation():
    model_dir = _prepare_model("phase4_report", seed=17, model_type="linear")
    base = _new_base("phase4_report_eval")
    dataset_dir = base / "dataset"
    eval_dir = base / "eval"
    report_path = base / "report_card.md"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=17)

    eval_cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "evaluate",
        "--dataset",
        str(dataset_dir),
        "--model",
        str(model_dir),
        "--out",
        str(eval_dir),
    ]
    eval_res = _run(eval_cmd)
    assert eval_res.returncode == 0, eval_res.stderr

    shutil.copy2(eval_dir / "evaluation.json", model_dir / "evaluation.json")

    report_cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "report-card",
        "--model",
        str(model_dir),
        "--out",
        str(report_path),
    ]
    report_res = _run(report_cmd)
    assert report_res.returncode == 0, report_res.stderr
    assert report_path.is_file()

    contents = report_path.read_text(encoding="utf-8")
    for heading in ("## Training Metrics", "## Thresholds", "## Uncertainty", "## Evaluation"):
        assert heading in contents

    metrics = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
    thresholds = json.loads((model_dir / "thresholds.json").read_text(encoding="utf-8"))
    uncertainty = json.loads((model_dir / "uncertainty.json").read_text(encoding="utf-8"))
    evaluation = json.loads((model_dir / "evaluation.json").read_text(encoding="utf-8"))

    for key in sorted(metrics):
        assert f"- `{key}`:" in contents
    for key in sorted(thresholds):
        assert f"- `{key}`:" in contents
    for key in sorted(uncertainty):
        assert f"- `{key}`:" in contents
    for key in sorted(evaluation):
        assert f"- `{key}`:" in contents


def test_ml_report_card_fallback_when_evaluation_missing():
    model_dir = _prepare_model("phase4_report_noeval", seed=23, model_type="linear")
    base = _new_base("phase4_report_noeval")
    report_path = base / "report_card.md"

    eval_artifact = model_dir / "evaluation.json"
    if eval_artifact.exists():
        eval_artifact.unlink()

    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "report-card",
        "--model",
        str(model_dir),
        "--out",
        str(report_path),
    ]
    res = _run(cmd)
    assert res.returncode == 0, res.stderr

    contents = report_path.read_text(encoding="utf-8")
    assert "## Evaluation" in contents
    assert "- `status`: evaluation.json not found in model directory" in contents


def test_ml_check_drift_schema_and_deterministic_values():
    model_dir = _prepare_model("phase4_drift", seed=31, model_type="linear")
    base = _new_base("phase4_drift")
    dataset_dir = base / "new_dataset"
    drift_path = base / "drift.json"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=31)

    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "check-drift",
        "--model",
        str(model_dir),
        "--new-data",
        str(dataset_dir),
        "--out",
        str(drift_path),
    ]
    res = _run(cmd)
    assert res.returncode == 0, res.stderr

    drift = json.loads(drift_path.read_text(encoding="utf-8"))

    assert set(drift.keys()) == {
        "population_stability_index",
        "ood_rate_delta",
        "confidence_shift",
        "summary",
        "status",
    }
    assert set(drift["status"].keys()) == {"drift_detected", "severity"}

    assert drift["ood_rate_delta"] == 0.0
    assert drift["confidence_shift"] > 0.0

    df = pd.read_csv(dataset_dir / "dataset.csv")
    bundle = joblib.load(model_dir / "model.joblib")
    numeric_features = [
        "node",
        "vdd",
        "temp",
        "capacity_gib",
        "ci",
        "bitcell_um2",
        "scrub_s",
        "latency_ns",
        "area_logic_mm2",
        "area_macro_mm2",
    ]
    expected_psi: dict[str, float] = {}
    n = max(len(df), 64)
    means = bundle.get("train_stats", {}).get("means", {})
    stds = bundle.get("train_stats", {}).get("stds", {})
    for feat in numeric_features:
        mean = float(means.get(feat, 0.0))
        std = float(stds.get(feat, 1.0))
        if not np.isfinite(std) or std <= 0:
            std = 1.0
        ref = np.linspace(mean - 1.5 * std, mean + 1.5 * std, n)
        expected_psi[feat] = float(_psi_1d(ref, df[feat].to_numpy(dtype=float)))

    assert drift["population_stability_index"] == expected_psi


def test_ml_check_drift_fail_on_drift_exit_code():
    model_dir = _prepare_model("phase4_drift_fail", seed=41, model_type="linear")
    base = _new_base("phase4_drift_fail")
    dataset_dir = base / "new_dataset"

    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=41)
    dataset_path = dataset_dir / "dataset.csv"
    rows = dataset_path.read_text(encoding="utf-8").splitlines()
    header = rows[0].split(",")
    vdd_idx = header.index("vdd")
    temp_idx = header.index("temp")

    shifted = [rows[0]]
    for line in rows[1:]:
        cols = line.split(",")
        cols[vdd_idx] = "4.0"
        cols[temp_idx] = "180.0"
        shifted.append(",".join(cols))
    dataset_path.write_text("\n".join(shifted) + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "ml",
        "check-drift",
        "--model",
        str(model_dir),
        "--new-data",
        str(dataset_dir),
        "--fail-on-drift",
    ]
    res = _run(cmd)

    assert res.returncode == 2
    drift = json.loads((REPO / "drift.json").read_text(encoding="utf-8"))
    assert drift["status"]["drift_detected"] is True
