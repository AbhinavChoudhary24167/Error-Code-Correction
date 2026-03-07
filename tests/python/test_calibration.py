import json
from pathlib import Path

import calibration


def test_load_calibration():
    path = Path(__file__).resolve().parents[2] / "tech_calib.json"
    data = calibration.load_calibration(path)
    assert 28 in data
    assert 0.6 in data[28]
    assert data[28][0.6]["gates"]["xor"] > 0


def test_load_calibration_signoff_density():
    path = Path(__file__).resolve().parents[2] / "tech_calib.json"
    data = calibration.load_calibration(path)

    for node in [28, 16, 7]:
        assert node in data
        assert len(data[node]) >= 4

    temp_points = {
        int(entry["tempC"])
        for node_data in data.values()
        for entry in node_data.values()
    }
    assert {-40, 25, 85, 125}.issubset(temp_points)


def test_calibration_envelope_fixtures_cover_nominal_and_corner_cases():
    root = Path(__file__).resolve().parents[2]
    calib = calibration.load_calibration(root / "tech_calib.json")
    envelope = calibration.get_calibration_envelope(calib)

    for fixture_name in [
        "calibration_envelope_nominal.json",
        "calibration_envelope_corner.json",
    ]:
        points = json.loads((root / "tests" / "fixtures" / fixture_name).read_text())
        for point in points:
            node = int(point["node_nm"])
            vdd = float(point["vdd"])
            assert envelope["node_nm_min"] <= node <= envelope["node_nm_max"]
            assert envelope["vdd_min"] <= vdd <= envelope["vdd_max"]
            assert float(point["tempC"]) in envelope["tempC_points"]
            assert point["corner"] in envelope["corners"]
            assert point["activity_class"] in envelope["activity_classes"]
            assert node in calib and vdd in calib[node]
