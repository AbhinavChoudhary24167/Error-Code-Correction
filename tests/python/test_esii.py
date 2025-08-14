import subprocess
import sys
from pathlib import Path
import math
import json
import subprocess
import sys

import pytest

from esii import ESIIInputs, compute_esii, embodied_from_wire_area


def test_compute_esii():
    inp = ESIIInputs(
        fit_base=1000,
        fit_ecc=100,
        e_dyn=1.0,
        e_leak=0.5,
        ci_kg_per_kwh=0.2,
        embodied_kg=10,
        energy_units="kWh",
    )
    result = compute_esii(inp)
    expected = 900 / 10.3
    assert math.isclose(result["ESII"], expected)


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
        "--embodied-kg",
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
        ci_kg_per_kwh=0.2,
        embodied_kg=0.05,
        energy_units="J",
    )
    expected = compute_esii(inp)
    assert data["ESII"] == pytest.approx(expected["ESII"])
    assert data["basis"] == "per_gib"


def test_cli_esii_reports(tmp_path):
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    rel = tmp_path / "rel.json"
    energy = tmp_path / "energy.json"
    area = tmp_path / "area.json"
    json.dump(
        {
            "basis": "per_gib",
            "fit": {"base": 300.0, "ecc": 5.0},
            "mbu": "moderate",
            "scrub_s": 10,
            "node_nm": 14,
            "vdd": 0.8,
            "tempC": 75,
        },
        open(rel, "w"),
    )
    json.dump({"dynamic_kWh": 0.00058, "leakage_kWh": 0.00027}, open(energy, "w"))
    json.dump({"logic_mm2": 0.1, "macro_mm2": 0.2, "node_nm": 14}, open(area, "w"))
    out = tmp_path / "esii.json"
    cmd = [
        sys.executable,
        str(script),
        "esii",
        "--reliability",
        str(rel),
        "--energy",
        str(energy),
        "--area",
        str(area),
        "--ci",
        "0.55",
        "--embodied-override-kg",
        "none",
        "--basis",
        "per_gib",
        "--out",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    data = json.load(open(out))
    inp = ESIIInputs(
        fit_base=300.0,
        fit_ecc=5.0,
        e_dyn=0.00058,
        e_leak=0.00027,
        ci_kg_per_kwh=0.55,
        embodied_kg=0.1 * 0.8 + 0.2 * 1.0,
        energy_units="kWh",
    )
    expected = compute_esii(inp)
    assert data["ESII"] == pytest.approx(expected["ESII"])
    assert data["inputs"]["fit_base"] == 300.0
