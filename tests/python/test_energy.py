import json
import subprocess
from pathlib import Path


def test_energy_cli_json(tmp_path):
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        "python3",
        str(script),
        "energy",
        "--code",
        "sec-daec",
        "--node",
        "14",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--ops",
        "1e3",
        "--lifetime-h",
        "1",
        "--report",
        "json",
    ]
    out = subprocess.check_output(cmd)
    data = json.loads(out)
    assert "dynamic_kWh" in data
    assert "leakage_kWh" in data
