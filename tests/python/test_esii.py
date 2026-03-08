import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from esii import ESIIInputs, compute_esii, embodied_from_wire_area
from gs import GSInputs, compute_gs


def test_compute_esii_bounded_and_finite():
    inp = ESIIInputs(
        fit_base=1000,
        fit_ecc=100,
        e_dyn=3_600_000.0,
        e_leak=1_800_000.0,
        e_scrub=0.0,
        ci_kgco2e_per_kwh=0.2,
        embodied_kgco2e=10,
    )
    result = compute_esii(inp)
    assert math.isfinite(result["ESII"])
    assert 0.0 <= result["ESII"] <= 1.0
    assert 0.0 <= result["reliability_score"] <= 1.0
    assert 0.0 <= result["energy_score"] <= 1.0
    assert 0.0 <= result["carbon_score"] <= 1.0


def test_embodied_from_wire_area():
    assert embodied_from_wire_area(5, 2) == 10
    with pytest.raises(ValueError):
        embodied_from_wire_area(-1, 2)


def test_cli_esii_outputs_result(tmp_path):
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    out = tmp_path / "esii.json"
    cmd = [
        sys.executable,
        str(script),
        "esii",
        "--fit-base",
        "1000",
        "--fit-ecc",
        "100",
        "--e-dyn-j",
        "1",
        "--e-leak-j",
        "0.5",
        "--ci",
        "0.2",
        "--embodied-kgco2e",
        "0.05",
        "--basis",
        "per_gib",
        "--out",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    data = json.load(open(out))
    inp = ESIIInputs(
        fit_base=1000,
        fit_ecc=100,
        e_dyn=1.0,
        e_leak=0.5,
        e_scrub=0.0,
        ci_kgco2e_per_kwh=0.2,
        embodied_kgco2e=0.05,
    )
    expected = compute_esii(inp)
    gs_exp = compute_gs(
        GSInputs(
            fit_base=inp.fit_base,
            fit_ecc=inp.fit_ecc,
            carbon_kg=expected["total_kgCO2e"],
            latency_ns=0.0,
        )
    )
    assert data["ESII"] == pytest.approx(expected["ESII"])
    assert data["NESII"] == 0.0
    assert data["GS"] == pytest.approx(gs_exp["GS"])
    assert data["basis"] == "per_gib"
    assert data["inputs"]["E_scrub_kWh"] == 0.0


def test_esii_monotone_ci():
    a = compute_esii(
        ESIIInputs(
            300,
            10,
            3000,
            2000,
            ci_kgco2e_per_kwh=0.6,
            embodied_kgco2e=0.05,
        )
    )
    b = compute_esii(
        ESIIInputs(
            300,
            10,
            3000,
            2000,
            ci_kgco2e_per_kwh=0.9,
            embodied_kgco2e=0.05,
        )
    )
    assert a["ESII"] > b["ESII"]


def test_esii_stronger_ecc():
    a = compute_esii(
        ESIIInputs(
            300,
            10,
            3000,
            2000,
            ci_kgco2e_per_kwh=0.6,
            embodied_kgco2e=0.05,
        )
    )
    c = compute_esii(
        ESIIInputs(
            300,
            5,
            3000,
            2000,
            ci_kgco2e_per_kwh=0.6,
            embodied_kgco2e=0.05,
        )
    )
    assert c["ESII"] > a["ESII"]


def test_esii_zero_or_tiny_inputs_stable():
    z = compute_esii(
        ESIIInputs(
            100,
            0,
            0.0,
            0.0,
            ci_kgco2e_per_kwh=0.0,
            embodied_kgco2e=0.0,
            e_scrub=0.0,
        )
    )
    assert math.isfinite(z["ESII"])
    assert 0.0 <= z["ESII"] <= 1.0
