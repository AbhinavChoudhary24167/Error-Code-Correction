from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ACTIVITY = ROOT / "campaigns/iscas_sustainability_extension/activity"
sys.path.insert(0, str(ACTIVITY))

from gate1_common import energy_per_op_pj, parse_power_report  # noqa: E402


def csv_rows(name: str) -> list[dict[str, str]]:
    with (ACTIVITY / name).open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_gate1_exact_matrix_and_origins() -> None:
    rows = csv_rows("activity_power_per_seed.csv")
    assert len(rows) == 60
    assert len({(row["architecture"], row["seed"], row["activity_class"]) for row in rows}) == 60
    assert {row["architecture"] for row in rows} == {
        "secded_comb",
        "secded_pipe",
        "hsiao_flat",
        "hsiao_hierarchical",
    }
    assert {row["seed"] for row in rows} == {"11", "13", "17", "19", "23"}
    assert {row["activity_class"] for row in rows} == {"W0", "W1", "W2"}
    assert sum(row["evidence_origin"] == "DATE_BASELINE" for row in rows) == 20
    assert sum(row["evidence_origin"] == "SUSTAINABILITY_EXTENSION" for row in rows) == 40


def test_gate1_energy_and_hash_join() -> None:
    for row in csv_rows("activity_power_per_seed.csv"):
        expected = energy_per_op_pj(
            float(row["total_power"]), int(row["trace_duration"]), int(row["useful_operations"])
        )
        assert math.isclose(float(row["energy_per_op"]), expected, rel_tol=1e-13, abs_tol=1e-13)
        for field in (
            "rtl_hash",
            "odb_hash",
            "spef_hash",
            "sdc_hash",
            "netlist_hash",
            "vcd_hash",
            "power_report_hash",
        ):
            assert len(row[field]) == 64
            int(row[field], 16)
        assert row["useful_operations"] == "100000"
        assert row["trace_duration"] == "1000100000"


def test_gate1_effect_tables_are_complete() -> None:
    action = csv_rows("activity_action_effects.csv")
    architecture = csv_rows("activity_architecture_effects.csv")
    assert len(action) == 40
    assert len(architecture) == 30
    assert {row["candidate_activity_class"] for row in action} == {"W1", "W2"}
    assert {row["comparison"] for row in architecture} == {
        "pipelined_vs_combinational",
        "hierarchical_vs_flat",
    }


def test_gate1_checkpoint_and_status() -> None:
    checkpoint = json.loads((ACTIVITY / "GATE1_INTERPRETATION.json").read_text(encoding="utf-8"))
    assert checkpoint["secded_pipeline_advantage_survives_W1"] is True
    assert checkpoint["secded_pipeline_advantage_survives_W2"] is True
    assert checkpoint["hsiao_hierarchical_penalty_survives_W1"] is True
    assert checkpoint["hsiao_hierarchical_penalty_survives_W2"] is True
    assert checkpoint["secded_seed_reversal_count_W1"] == 0
    assert checkpoint["secded_seed_reversal_count_W2"] == 0
    assert checkpoint["hsiao_seed_reversal_count_W1"] == 0
    assert checkpoint["hsiao_seed_reversal_count_W2"] == 0
    status = json.loads((ACTIVITY / "GATE1_STATUS.json").read_text(encoding="utf-8"))
    assert status["verdict"] == "PASS"
    assert status["evidence"]["new_point_count"] == 40
    assert status["evidence"]["joined_point_count"] == 60


def test_power_parser_accepts_frozen_report_accumulation_tolerance() -> None:
    report = ROOT / "campaigns/iscas_sustainability_extension/tests/fixtures/gate1_power_tolerance.rpt"
    parsed = parse_power_report(report)
    assert parsed["Total"]["total_power_w"] == 1.00000081e-2
