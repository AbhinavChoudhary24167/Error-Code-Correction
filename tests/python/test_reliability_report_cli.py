import json
import subprocess
import sys
from pathlib import Path

import pytest
from ser_model import HazuchaParams, ser_hazucha
from fit import compute_fit_pre, compute_fit_post, ecc_coverage_factory, fit_system


def test_reliability_report_json():
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        sys.executable,
        str(script),
        "reliability",
        "report",
        "--qcrit",
        "1.2",
        "--qs",
        "0.25",
        "--area",
        "0.08",
        "--flux-rel",
        "1.0",
        "--scrub-interval",
        "3600",
        "--capacity-gib",
        "1.0",
        "--basis",
        "per_gib",
        "--mbu",
        "none",
        "--node-nm",
        "14",
        "--vdd",
        "0.8",
        "--tempC",
        "75",
        "--json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    hp = HazuchaParams(Qs_fC=0.25, flux_rel=1.0, area_um2=0.08)
    fit_bit = ser_hazucha(1.2, hp)
    fit_pre = compute_fit_pre(64, fit_bit, {})
    coverage = ecc_coverage_factory("SEC-DED")
    fit_post = compute_fit_post(64, fit_bit, {}, coverage, 3600)
    expected_base = fit_system(1.0, fit_pre)
    expected_ecc = fit_system(1.0, fit_post)
    base_nom = (
        expected_base.nominal if hasattr(expected_base, "nominal") else expected_base
    )
    ecc_nom = (
        expected_ecc.nominal if hasattr(expected_ecc, "nominal") else expected_ecc
    )
    assert data["fit"]["base"] == pytest.approx(base_nom)
    assert data["fit"]["ecc"] == pytest.approx(ecc_nom)
    assert data["basis"] == "per_gib"
    assert "fit_bit" in res.stderr


def test_reliability_report_text():
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        sys.executable,
        str(script),
        "reliability",
        "report",
        "--qcrit",
        "1.2",
        "--qs",
        "0.25",
        "--area",
        "0.08",
        "--flux-rel",
        "1.0",
        "--scrub-interval",
        "3600",
        "--capacity-gib",
        "1.0",
        "--node-nm",
        "14",
        "--vdd",
        "0.8",
        "--tempC",
        "75",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = {line.split()[0] for line in res.stdout.strip().splitlines()}
    # Ensure all metrics are present in the text report
    assert {
        "qcrit",
        "qs",
        "flux_rel",
        "fit_bit",
        "fit_word_pre",
        "fit_word_post",
        "fit_system",
        "mttf",
    }.issubset(lines)
