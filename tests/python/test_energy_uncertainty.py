import json
import subprocess
import sys
from pathlib import Path

import energy_model


REPO = Path(__file__).resolve().parents[2]


def test_uncertainty_loader_is_deterministic():
    path = REPO / "tech_calib_uncertainty.json"
    first = energy_model.load_calibration_uncertainty(path)
    second = energy_model.load_calibration_uncertainty(path)
    assert first == second
    assert first[28][0.8]["gates"]["xor"]["n"] == 64


def test_confidence_is_stable_and_bounded():
    path = REPO / "tech_calib_uncertainty.json"
    a = energy_model.operation_confidence(
        "sec-ded", 28, 0.8, uncertainty_path=path, max_relative_stddev=0.25
    )
    b = energy_model.operation_confidence(
        "sec-ded", 28, 0.8, uncertainty_path=path, max_relative_stddev=0.25
    )
    assert a == b
    assert 0.0 <= a["confidence_score"] <= 1.0
    assert a["relative_stddev"] <= a["confidence_threshold"]


def test_energy_report_adds_confidence_only_when_requested():
    path = REPO / "tech_calib_uncertainty.json"
    baseline = energy_model.energy_report("sec-ded", 28, 0.8, 75, 1000, 1)
    with_conf = energy_model.energy_report(
        "sec-ded", 28, 0.8, 75, 1000, 1, uncertainty_path=path, include_confidence=True
    )
    assert "confidence" not in baseline
    assert "confidence" in with_conf


def test_cli_strict_validation_rejects_missing_uncertainty():
    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "energy",
        "--code",
        "sec-ded",
        "--node",
        "28",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--ops",
        "1e6",
        "--lifetime-h",
        "1000",
        "--strict-validation",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert res.returncode != 0
    assert "Strict validation requires uncertainty metadata path" in res.stderr


def test_cli_strict_validation_rejects_too_wide_uncertainty(tmp_path: Path):
    payload = json.loads((REPO / "tech_calib_uncertainty.json").read_text(encoding="utf-8"))
    payload["28"]["0.8"]["gates"]["xor"]["stddev"] = payload["28"]["0.8"]["gates"]["xor"]["mean"]
    wide = tmp_path / "wide_uncertainty.json"
    wide.write_text(json.dumps(payload), encoding="utf-8")

    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "energy",
        "--code",
        "sec-ded",
        "--node",
        "28",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--ops",
        "1e6",
        "--lifetime-h",
        "1000",
        "--strict-validation",
        "--uncertainty-path",
        str(wide),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert res.returncode != 0
    assert "Uncertainty too wide for strict validation" in res.stderr
