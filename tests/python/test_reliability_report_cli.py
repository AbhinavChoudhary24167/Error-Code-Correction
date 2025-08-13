import json
import subprocess
import sys
from pathlib import Path

import pytest
from ser_model import HazuchaParams, ser_hazucha


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
        "--json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    hp = HazuchaParams(Qs_fC=0.25, flux_rel=1.0, area_um2=0.08)
    expected = ser_hazucha(1.2, hp)
    assert data["fit_bit"] == pytest.approx(expected)
    assert "fit_bit" in res.stderr
