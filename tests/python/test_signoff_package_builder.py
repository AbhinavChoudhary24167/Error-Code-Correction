import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "build_signoff_package.py"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_signoff_package_success(tmp_path: Path):
    envelope = tmp_path / "envelope.md"
    envelope.write_text("# envelope\n", encoding="utf-8")

    provenance = tmp_path / "provenance.json"
    _write_json(provenance, {"sources": ["fixture"]})

    uncertainty = tmp_path / "uncertainty.json"
    _write_json(uncertainty, {"bands": [0.1, 0.2]})

    holdout = tmp_path / "holdout.json"
    _write_json(holdout, {"signoff": {"pass": True}})

    drift = tmp_path / "drift.json"
    _write_json(drift, {"status": {"drift_detected": False, "severity": "none"}})

    compat = tmp_path / "compat.json"
    _write_json(compat, {"pass": True, "failed": 0})

    version = "test-signoff-pass"
    out_root = tmp_path / "out"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--version",
        version,
        "--out-root",
        str(out_root),
        "--calibration-envelope",
        str(envelope),
        "--provenance-manifest",
        str(provenance),
        "--uncertainty-report",
        str(uncertainty),
        "--holdout-metrics",
        str(holdout),
        "--drift-status",
        str(drift),
        "--compatibility-test-results",
        str(compat),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert res.returncode == 0, res.stderr

    out_dir = out_root / version
    assert (out_dir / "summary.md").is_file()
    assert (out_dir / "manifest.json").is_file()


def test_build_signoff_package_fails_threshold_gate(tmp_path: Path):
    envelope = tmp_path / "envelope.md"
    envelope.write_text("# envelope\n", encoding="utf-8")

    provenance = tmp_path / "provenance.json"
    _write_json(provenance, {"sources": ["fixture"]})

    uncertainty = tmp_path / "uncertainty.json"
    _write_json(uncertainty, {"bands": [0.1, 0.2]})

    holdout = tmp_path / "holdout.json"
    _write_json(holdout, {"signoff": {"pass": False}})

    drift = tmp_path / "drift.json"
    _write_json(drift, {"status": {"drift_detected": False, "severity": "none"}})

    compat = tmp_path / "compat.json"
    _write_json(compat, {"pass": True, "failed": 0})

    out_root = tmp_path / "out"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--version",
        "test-signoff-fail",
        "--out-root",
        str(out_root),
        "--calibration-envelope",
        str(envelope),
        "--provenance-manifest",
        str(provenance),
        "--uncertainty-report",
        str(uncertainty),
        "--holdout-metrics",
        str(holdout),
        "--drift-status",
        str(drift),
        "--compatibility-test-results",
        str(compat),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert res.returncode != 0
