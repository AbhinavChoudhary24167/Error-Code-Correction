import subprocess
import sys
from pathlib import Path

import pytest

from ser_model import flux_from_location


def run_cmd(
    qcrit: float,
    *,
    flux: float | None = None,
    alt: float = 0.0,
    latitude: float = 45.0,
) -> float:
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
        "--alt-km",
        str(alt),
        "--latitude",
        str(latitude),
    ]
    if flux is not None:
        cmd.extend(["--flux-rel", str(flux)])
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip().splitlines()[-1])


def test_qcrit_and_flux_scaling():
    base = run_cmd(1.2)
    higher_qcrit = run_cmd(1.3)
    high_alt = run_cmd(1.2, alt=10.0, latitude=60.0)
    manual_override = run_cmd(1.2, flux=2.0, alt=10.0, latitude=60.0)

    assert higher_qcrit < base
    assert high_alt > base

    base_flux = flux_from_location(0.0, 45.0)
    scaled_flux = flux_from_location(10.0, 60.0)
    assert high_alt == pytest.approx(base * (scaled_flux / base_flux), rel=1e-3)

    assert manual_override == pytest.approx(base * 2.0, rel=1e-3)

