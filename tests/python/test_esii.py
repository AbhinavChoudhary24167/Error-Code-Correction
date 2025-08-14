import subprocess
import sys
from pathlib import Path
import math

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


def test_cli_esii_outputs_result():
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        sys.executable,
        str(script),
        "esii",
        "--fit-base",
        "1000",
        "--fit-ecc",
        "100",
        "--E-dyn",
        "1",
        "--E-leak",
        "0.5",
        "--ci",
        "0.2",
        "--wire-area-mm2",
        "5",
        "--wire-factor-kg-per-mm2",
        "2",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    first_line = res.stdout.splitlines()[0]
    assert first_line == "ESII: 87.379"
