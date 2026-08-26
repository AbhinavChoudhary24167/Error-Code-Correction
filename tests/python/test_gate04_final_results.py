from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_04_final"


def _json(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_gate04_required_final_outputs_exist() -> None:
    for name in (
        "GATE04_FINAL_ECC_SET.json",
        "GATE04_EXPERIMENT_MANIFEST.json",
        "GATE04_POWER_PRECISION_ADJUDICATION.md",
        "GATE04_RAW_RESULTS.json",
        "GATE04_NORMALIZED_RESULTS.json",
        "GATE04_TIMING_FEASIBILITY.json",
        "GATE04_PHYSICAL_RESULTS.csv",
        "GATE04_POWER_RESULTS.csv",
        "GATE04_ADJUDICATION.md",
    ):
        assert (OUT / name).is_file()


def test_gate04_matrix_preserves_attempts_and_replacements_transparently() -> None:
    matrix = _json("MATRIX_EXECUTION.json")
    assert matrix["planned_run_count"] == 4
    assert matrix["executed_run_count"] == 4
    assert matrix["replacement_attempt_count"] == 2
    assert [row["run_id"] for row in matrix["outcomes"]] == [
        "secded-comb-final-01",
        "secded-pipe-final-01",
        "hsiao-final-01",
        "bch78-final-01",
    ]
    assert [row["replacement_of_excluded_infrastructure_attempt"] for row in matrix["outcomes"]] == [
        True,
        True,
        False,
        False,
    ]
    assert matrix["outcomes"][2]["process_exit_status"] == 2


def test_gate04_physical_statuses_and_timing_are_not_hidden() -> None:
    raw = _json("GATE04_RAW_RESULTS.json")
    rows = {row["implementation_id"]: row for row in raw["physical_results"]}
    assert len(rows) == 4
    assert rows["secded-rtl-combinational-72-64-v1"]["characterization_status"] == (
        "PHYSICAL_CHARACTERIZATION_PASS_TIMING_MET"
    )
    assert rows["secded-rtl-pipelined-72-64-v1"]["characterization_status"] == (
        "PHYSICAL_CHARACTERIZATION_PASS_TIMING_MET"
    )
    hsiao = rows["hsiao-generated-combinational-72-64-v1"]
    assert hsiao["characterization_status"] == "PHYSICAL_CHARACTERIZATION_PARTIAL"
    assert hsiao["physical_failure_reason"] == "FROZEN_ORFS_SYNTH_MEMORY_MAX_BITS_EXCEEDED"
    assert all(value is None for value in hsiao["metrics"].values())
    bch = rows["shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"]
    assert bch["characterization_status"] == "PHYSICAL_CHARACTERIZATION_PASS_TIMING_MISSED"
    assert bch["timing_feasibility"] == "FAILS_10NS"
    assert bch["metrics"]["wns_ns"] == -4.78052
    assert bch["metrics"]["final_drc_count"] == 0


def test_gate04_power_uses_full_precision_and_timing_feasibility_labels() -> None:
    raw = _json("GATE04_RAW_RESULTS.json")
    rows = raw["power_results"]
    assert len(rows) == 9
    secded = next(
        row for row in rows
        if row["implementation_id"] == "secded-rtl-combinational-72-64-v1" and row["trace_class"] == "no_error"
    )
    assert secded["metrics"]["total_power_w"] == 1.457479409873e-02
    assert secded["metrics"]["native_rounded_json_total_power_w"] == 1.46e-02
    assert secded["classification"] == "POWER_TIMING_FEASIBLE"
    assert secded["metrics"]["achievable_total_energy_pj_per_operation"] is not None
    bch = next(
        row for row in rows
        if row["implementation_id"] == "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"
        and row["trace_class"] == "no_error"
    )
    assert bch["classification"] == "POWER_AT_TARGET_CONSTRAINT_TIMING_INFEASIBLE"
    assert bch["metrics"]["total_energy_pj_per_operation_estimate"] > 8_000
    assert bch["metrics"]["achievable_total_energy_pj_per_operation"] is None


def test_gate04_normalization_uses_conventional_secded_reference() -> None:
    normalized = _json("GATE04_NORMALIZED_RESULTS.json")
    assert normalized["reference_implementation_id"] == "secded-rtl-combinational-72-64-v1"
    assert normalized["timing_slack_ratios_computed"] is False
    by_id = {row["implementation_id"]: row for row in normalized["physical"]}
    assert by_id["secded-rtl-combinational-72-64-v1"]["percent_delta_vs_secded"][
        "standard_cell_instance_area_um2"
    ] == 0.0
    assert by_id["secded-rtl-pipelined-72-64-v1"]["percent_delta_vs_secded"][
        "standard_cell_instance_area_um2"
    ] > 36.0
    assert by_id["hsiao-generated-combinational-72-64-v1"]["percent_delta_vs_secded"][
        "standard_cell_instance_area_um2"
    ] is None


def test_gate04_verdict_is_conditional_and_gate05_ready() -> None:
    verdict = _json("GATE04_VERDICT.json")
    assert verdict["verdict"] == "GATE_04_CONDITIONAL_PASS"
    assert verdict["gate05_state"] == "GATE_05_READY"
    assert verdict["valid_physical_result_count"] == 3
    assert verdict["valid_power_implementation_count"] == 3
    assert verdict["conditions"]["all_four_physical_runs_valid"] is False
    assert verdict["conditions"]["failed_namespace_excluded"] is True
    report = (OUT / "GATE04_ADJUDICATION.md").read_text(encoding="utf-8")
    assert report.rstrip().endswith("`GATE_05_READY`")
    assert "target estimate; timing infeasible" in report


def test_gate04_published_evidence_hashes_verify() -> None:
    for line in (OUT / "GATE04_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = OUT / relative.removeprefix("./")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_gate04_csvs_have_four_physical_and_nine_power_rows() -> None:
    with (OUT / "GATE04_PHYSICAL_RESULTS.csv").open(encoding="utf-8", newline="") as stream:
        physical = list(csv.DictReader(stream))
    with (OUT / "GATE04_POWER_RESULTS.csv").open(encoding="utf-8", newline="") as stream:
        power = list(csv.DictReader(stream))
    assert len(physical) == 4
    assert len(power) == 9
    assert {row["trace_class"] for row in power} == {"no_error", "single_error", "double_error"}
