from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from campaigns.iscas_sustainability_extension.green_refoundation_node_aware_carbon.green_matrix_v2.build_matrix_v2 import (
    BASE,
    EVIDENCE_CLASSES,
    NUMERIC_FIELDS,
    REQUIRED_V2_FIELDS,
    build,
)
from campaigns.iscas_sustainability_extension.green_refoundation_node_aware_carbon.pareto.build_selection import (
    build as build_selection,
)
from campaigns.iscas_sustainability_extension.green_refoundation_node_aware_carbon.pareto.selection import (
    Objective,
    exact_pareto_front,
    qualified_rows,
    robust_summary,
)


def _rows() -> list[dict[str, str]]:
    with (BASE / "green_matrix_v2" / "GREEN_MATRIX_V2_RAW.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_matrix_has_required_fields_and_exact_logical_controls() -> None:
    rows = _rows()
    assert len(rows) == 14
    assert set(REQUIRED_V2_FIELDS) <= set(rows[0])
    assert {row["architecture_id"] for row in rows} == {"U0", "E0"}
    for row in rows:
        count = int(row["logical_pattern_count"])
        successes = sum(
            int(row[name])
            for name in (
                "logical_success_normal_count",
                "logical_success_corrected_count",
                "logical_success_after_retry_count",
            )
        )
        assert float(row["logical_control_success_fraction"]) == pytest.approx(
            successes / count
        )


def test_unqualified_controls_are_not_promoted_to_event_rates_or_green_scores() -> None:
    forbidden = (
        "service_success_probability",
        "useful_service_bits",
        "GSE",
        "GCI",
        "GSE_relative",
        "SDC",
        "DUE",
        "corrected",
        "retry",
        "service_success",
        "operational_energy",
        "operational_carbon",
        "lifecycle_carbon",
    )
    for row in _rows():
        assert row["qualification_status"] == "UNQUALIFIED"
        for field in forbidden:
            assert row[field] == ""
            assert row[f"{field}_evidence"] == "NOT_QUALIFIED"


def test_every_numeric_field_has_valid_row_level_evidence() -> None:
    allowed = set(EVIDENCE_CLASSES)
    for row in _rows():
        for field in NUMERIC_FIELDS:
            evidence = row[f"{field}_evidence"]
            assert evidence in allowed
            if row[field]:
                assert evidence not in {"NOT_QUALIFIED", "NOT_MEASURED"}


def test_matrix_generation_is_byte_deterministic_and_hashes_inputs() -> None:
    paths = build()
    first = [_sha(path) for path in paths]
    paths = build()
    assert [_sha(path) for path in paths] == first
    metadata = json.loads(paths[2].read_text(encoding="utf-8"))
    for relative, expected in metadata["input_sha256"].items():
        assert _sha(BASE / relative) == expected


def test_exact_pareto_is_deterministic_and_preserves_tradeoffs() -> None:
    rows = [
        {"id": "A", "carbon": 1.0, "service": 0.8},
        {"id": "B", "carbon": 2.0, "service": 0.9},
        {"id": "C", "carbon": 3.0, "service": 0.7},
    ]
    objectives = [Objective("carbon", "min"), Objective("service", "max")]
    assert exact_pareto_front(rows, objectives) == [0, 1]
    assert exact_pareto_front(rows, objectives) == [0, 1]


def test_current_matrix_has_no_full_pareto_eligible_rows_or_winner() -> None:
    rows = _rows()
    assert qualified_rows(rows, ["GCI", "SDC", "DUE", "latency_ns"]) == []
    _, exact_json, _, robust_json = build_selection()
    exact = json.loads(exact_json.read_text(encoding="utf-8"))
    robust = json.loads(robust_json.read_text(encoding="utf-8"))
    assert exact["eligible_row_count"] == 0
    assert exact["winner"] is None
    assert exact["NSGA_II_used"] is False
    assert robust["selected_architecture"] is None
    assert robust["selected_policy"] is None


def test_robust_summary_reports_all_requested_risk_views() -> None:
    summary = robust_summary([1.0, 2.0, 3.0, 4.0])
    assert summary["mean"] == pytest.approx(2.5)
    assert summary["median"] == pytest.approx(2.5)
    assert summary["p05"] == pytest.approx(1.15)
    assert summary["worst_case_interval_lower"] == 1.0
    assert summary["worst_case_interval_upper"] == 4.0
