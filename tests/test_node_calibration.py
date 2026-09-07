from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
    / "carbon"
    / "calibration"
)


def _rows(name: str) -> list[dict[str, str]]:
    with (CALIBRATION / name).open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_current_calibration_contains_only_text_supported_numeric_anchors() -> None:
    rows = _rows("IMEC_CURRENT_CALIBRATION.csv")
    ids = {row["calibration_id"] for row in rows}
    assert "IMEC23_N28_GRID_SENSITIVITY" in ids
    assert "IMEC23_A14_GRID_SENSITIVITY" in ids
    assert not any(row["metric"] == "absolute_wafer_carbon" for row in rows)
    assert all(row["source_id"] == "SRC_IMEC_IEDM_2023" for row in rows)


def test_historical_ratios_are_validation_only() -> None:
    rows = _rows("IMEC_HISTORICAL_CALIBRATION.csv")
    assert {row["metric"] for row in rows} == {
        "electricity_per_wafer",
        "ultrapure_water_per_wafer",
        "GHG_per_wafer",
    }
    assert all(row["production_use"] == "VALIDATION_ONLY" for row in rows)


def test_metadata_prohibits_sky130_substitution_and_graph_digitization() -> None:
    metadata = json.loads(
        (CALIBRATION / "IMEC_CALIBRATION_METADATA.json").read_text("utf-8")
    )
    assert metadata["numeric_admission"]["rejected"] == "manual digitization of graph coordinates"
    assert metadata["technology_translation"]["SKY130"] == "NO_EXACT_WAFER_COEFFICIENT"
    assert metadata["qualification"].startswith("PARTIAL_NUMERIC_CALIBRATION")


def test_live_public_app_status_does_not_claim_extracted_values() -> None:
    status = json.loads(
        (CALIBRATION / "IMEC_PUBLIC_ACCESS_STATUS.json").read_text("utf-8")
    )
    assert status["numeric_dashboard"] == "PUBLIC_ACCOUNT_REQUIRED"
    assert status["account_created"] is False
    assert status["numeric_outputs_extracted"] is False


def test_model_evolution_never_subtracts_invalid_boundaries() -> None:
    rows = _rows("IMEC_MODEL_EVOLUTION.csv")
    invalid = [row for row in rows if row["comparison_validity"] == "INVALID_NUMERIC"]
    assert invalid
    assert all(row["difference"] == "NOT_COMPUTABLE" for row in invalid)
