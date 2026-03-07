from pathlib import Path

import calibration


def test_get_calibration_envelope_min_max_metadata():
    path = Path(__file__).resolve().parents[2] / "tech_calib.json"
    calib = calibration.load_calibration(path)

    envelope = calibration.get_calibration_envelope(calib)

    assert envelope["nodes_nm"] == [7, 16, 28]
    assert envelope["node_nm_min"] == 7
    assert envelope["node_nm_max"] == 28
    assert envelope["vdd_points"] == [0.55, 0.6, 0.7, 0.8, 0.85]
    assert envelope["vdd_min"] == 0.55
    assert envelope["vdd_max"] == 0.85
    assert envelope["tempC_points"] == [-40.0, 25.0, 85.0, 125.0]
    assert envelope["tempC_min"] == -40.0
    assert envelope["tempC_max"] == 125.0
    assert envelope["corners"] == ["ff", "ss", "ssg", "tt"]
    assert envelope["activity_classes"] == ["compute", "idle", "nominal", "stress"]
