import subprocess
import sys
from pathlib import Path

import subprocess
import sys

from carbon import embodied_kgco2e, operational_kgco2e


def test_operational_sign():
    assert operational_kgco2e(1.0, 0.0, 0.5) == 0.5
    assert operational_kgco2e(1.0, 0.0, 0.5, 1.0) == 1.0


def test_embodied_additivity():
    assert embodied_kgco2e(0.1, 0.2, 1.0, 2.0) == 0.1 * 1.0 + 0.2 * 2.0


def test_cli_round_trip():
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        sys.executable,
        str(script),
        "carbon",
        "--areas",
        "0.05,0.20",
        "--alpha",
        "1.5,1.0",
        "--ci",
        "0.55",
        "--Edyn",
        "0.002",
        "--Eleak",
        "0.001",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = res.stdout.strip().splitlines()
    assert "Embodied" in lines[0]
    assert "Operational" in lines[1]

