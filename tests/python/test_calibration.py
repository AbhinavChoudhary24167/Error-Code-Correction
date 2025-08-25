from pathlib import Path

import calibration


def test_load_calibration():
    path = Path(__file__).resolve().parents[2] / "tech_calib.json"
    data = calibration.load_calibration(path)
    assert 28 in data
    assert 0.8 in data[28]
    assert data[28][0.8]["gates"]["xor"] > 0
