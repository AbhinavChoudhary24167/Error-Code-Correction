import json
import subprocess
import sys
from pathlib import Path

import pytest
from ser_model import HazuchaParams, ser_hazucha, flux_from_location
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
        "--alt-km",
        "2.0",
        "--latitude",
        "60.0",
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
    flux = flux_from_location(2.0, 60.0)
    hp = HazuchaParams(Qs_fC=0.25, flux_rel=flux, area_um2=0.08)
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
        "--alt-km",
        "2.0",
        "--latitude",
        "60.0",
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


def test_reliability_report_mbu_effect():
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    base_cmd = [
        sys.executable,
        str(script),
        "reliability",
        "report",
        "--qs",
        "0.25",
        "--area",
        "0.08",
        "--word-bits",
        "64",
        "--mbu",
        "moderate",
        "--node-nm",
        "14",
        "--vdd",
        "0.8",
        "--tempC",
        "75",
    ]
    cmd_ded = base_cmd + ["--ecc", "SEC-DED"]
    cmd_daec = base_cmd + ["--ecc", "SEC-DAEC"]

    res_ded = subprocess.run(cmd_ded, capture_output=True, text=True, check=True)
    res_daec = subprocess.run(cmd_daec, capture_output=True, text=True, check=True)

    def extract_fit_word_post(out: str) -> float:
        for line in out.splitlines():
            if line.startswith("fit_word_post"):
                return float(line.split()[1])
        raise AssertionError("fit_word_post not found")

    ded_val = extract_fit_word_post(res_ded.stdout)
    daec_val = extract_fit_word_post(res_daec.stdout)
    assert ded_val > daec_val


def test_reliability_report_unknown_node():
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        sys.executable,
        str(script),
        "reliability",
        "report",
        "--qs",
        "0.25",
        "--area",
        "0.08",
        "--node-nm",
        "16",
        "--vdd",
        "0.8",
        "--tempC",
        "75",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert (
        "error: Qcrit table for element 'sram6t' has no data for node_nm=16"
        in res.stderr
    )
