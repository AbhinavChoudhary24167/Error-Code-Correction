import subprocess
import sys
from pathlib import Path
import math

from esii import compute_esii


def test_compute_esii():
    result = compute_esii(1000, 100, 1.0, 0.5, 0.2, 10)
    expected = 900 / 10.3
    assert math.isclose(result, expected)


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
        "--EC-embodied",
        "10",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    first_line = res.stdout.splitlines()[0]
    assert first_line == "ESII: 87.379"
