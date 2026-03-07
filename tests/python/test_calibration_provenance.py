import json
from pathlib import Path

import pytest

import calibration


def test_all_calibration_sources_resolve_in_manifest_strict():
    root = Path(__file__).resolve().parents[2]
    missing = calibration.validate_calibration_provenance(
        root / "tech_calib.json",
        root / "reports" / "calibration" / "provenance_manifest.json",
        strict=True,
    )
    assert missing == []


def test_load_calibration_soft_fails_with_explicit_warning_for_unresolved_sources(tmp_path):
    root = Path(__file__).resolve().parents[2]
    calib_data = json.loads((root / "tech_calib.json").read_text())
    calib_data["28"]["0.6"]["source"] = "unknown_source_id"

    bad_calib_path = tmp_path / "tech_calib_bad.json"
    bad_calib_path.write_text(json.dumps(calib_data))

    with pytest.warns(UserWarning, match="Unresolvable calibration provenance source token"):
        loaded = calibration.load_calibration(
            bad_calib_path,
            provenance_manifest_path=root
            / "reports"
            / "calibration"
            / "provenance_manifest.json",
        )

    assert 28 in loaded and 0.6 in loaded[28]
