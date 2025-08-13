import subprocess
import sys
from pathlib import Path

import pytest


def run_cmd(qcrit: float, flux: float) -> float:
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        sys.executable,
        str(script),
        "reliability",
        "hazucha",
        "--qcrit",
        str(qcrit),
        "--qs",
        "0.25",
        "--area",
        "0.08",
        "--flux-rel",
        str(flux),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip().splitlines()[-1])


def test_qcrit_and_flux_scaling():
    base = run_cmd(1.2, 1.0)
    higher_qcrit = run_cmd(1.3, 1.0)
    higher_flux = run_cmd(1.2, 2.0)

    assert higher_qcrit < base
    assert higher_flux > base
    assert higher_flux == pytest.approx(base * 2.0, rel=1e-3)

