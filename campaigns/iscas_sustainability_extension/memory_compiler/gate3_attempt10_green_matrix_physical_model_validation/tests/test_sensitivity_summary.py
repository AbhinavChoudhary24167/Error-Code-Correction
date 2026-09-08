import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "liberty" / "LIBERTY_SENSITIVITY_RESULTS.json").read_text(encoding="utf-8"))


def test_strict_matrix_outcomes_are_complete_and_explicit():
    rows = DATA["rows"]
    assert DATA["strict_runs_executed"] == 30
    assert len(rows) == 30
    assert sum(row["run_status"] == "COMPLETE" for row in rows) == 20
    assert sum(row["run_status"] == "ABORTED_RSZ_0090" for row in rows) == 10


def test_original_runs_exactly_reproduce_attempt09_deterministic_evidence():
    reproduction = DATA["original_attempt09_reproduction"]
    assert reproduction["metrics_and_deterministic_artifacts_exact_pair_count"] == 10
    assert all(row["metrics_and_deterministic_artifacts_exact"] for row in reproduction["pairs"])


def test_diagnostic_e0_models_are_identical_and_material():
    assert DATA["corrected_and_no_global_e0_metrics_identical"] is True
    assert DATA["ppa_material_change_observed"]["E0"] is True
    corrected = next(row for row in DATA["paired_mean_deltas"] if row["model"] == "CORRECTED" and row["design"] == "E0")
    assert corrected["matched_pairs"] == 5
    assert abs(corrected["mean_relative_fraction"]["area_standard_cell_um2"]) > 0.05


def test_u0_diagnostic_ppa_remains_unqualified():
    assert DATA["ppa_material_change_observed"]["U0"] == "NOT_QUALIFIED_STRICT_RUN_ABORTED"
    u0_diagnostic = [row for row in DATA["rows"] if row["model"] != "ORIGINAL" and row["design"] == "U0"]
    assert len(u0_diagnostic) == 10
    assert all("finish_metrics" in row["missing"] and "area_total_um2" not in row for row in u0_diagnostic)


def test_historical_gate3_result_is_not_promoted():
    assert DATA["historical_attempt09"]["gate3_status"] == "FAIL"
    assert DATA["historical_attempt09"]["classification"] == "RESIDUAL_SRAM_INPUT_DRV_FAIL"
