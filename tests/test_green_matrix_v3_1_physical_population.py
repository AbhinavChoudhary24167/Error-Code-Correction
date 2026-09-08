from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from campaigns.iscas_sustainability_extension.green_matrix_v3_physical_population.build_campaign import (
    BASE,
    REPO,
    artifact_paths,
    build_all,
)
from campaigns.iscas_sustainability_extension.green_matrix_v3_physical_population.core import (
    EVIDENCE_KINDS,
    PhysicalCell,
    QCritRecord,
    ServiceMetrics,
    aggregate_physical_outcomes,
    classify_literature_transfer,
    classify_pareto_front,
    classify_secded_control,
    derive_energy_from_power,
    event_rate_from_qcrit,
    exact_pareto_indices,
    propagate_topology,
    validate_disjoint_power_partition,
    validate_interleaver_mapping,
    validate_probability_distribution,
)


def _json(name: str) -> dict[str, object]:
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_evidence_kind_contract_is_explicit_and_complete() -> None:
    assert EVIDENCE_KINDS == {
        "MEASURED",
        "DERIVED_FROM_MATCHED_MEASUREMENT",
        "ANALYTICAL",
        "POST_ROUTE_ESTIMATE",
        "LITERATURE_REFERENCE",
        "PARAMETRIC",
        "BOUND",
        "EXPLICIT_ZERO",
        "EXCLUDED",
        "UNAVAILABLE",
        "TECHNOLOGY_MISMATCH",
        "BLOCKED",
    }


def test_probability_normalization_validates_without_silent_renormalization() -> None:
    assert validate_probability_distribution({"SBU": 0.7, "DBU": 0.3}) == {
        "SBU": 0.7,
        "DBU": 0.3,
    }
    with pytest.raises(ValueError, match="sum to one"):
        validate_probability_distribution({"SBU": 0.7, "DBU": 0.2})
    with pytest.raises(ValueError, match="non-negative"):
        validate_probability_distribution({"SBU": 1.1, "DBU": -0.1})


def test_total_probability_keeps_corrected_due_and_sdc_separate() -> None:
    result = aggregate_physical_outcomes(
        {"SBU": 0.75, "DBU": 0.25},
        {
            "SBU": {"CORRECT": 0.0, "CORRECTED": 1.0, "DUE": 0.0, "SDC": 0.0},
            "DBU": {"CORRECT": 0.0, "CORRECTED": 0.0, "DUE": 0.8, "SDC": 0.2},
        },
    )
    assert result == pytest.approx({"CORRECT": 0.0, "CORRECTED": 0.75, "DUE": 0.2, "SDC": 0.05})
    assert result["DUE"] != result["SDC"]


def test_sbu_dbu_mbu_topology_propagates_through_codeword_mapping() -> None:
    cells = [
        PhysicalCell("r0c0", 0, 0, 0, 0, 0, 0, 0.0, 0.0),
        PhysicalCell("r0c1", 0, 1, 1, 0, 0, 0, 1.0, 0.0),
        PhysicalCell("r1c0", 1, 0, 2, 0, 0, 0, 0.0, 1.0),
        PhysicalCell("r2c0", 2, 0, 0, 1, 1, 0, 0.0, 2.0),
    ]
    sbu = propagate_topology(["r0c0"], cells, lambda _cw, mask: classify_secded_control(mask))
    dbu = propagate_topology(["r0c0", "r0c1"], cells, lambda _cw, mask: classify_secded_control(mask))
    mbu = propagate_topology(
        ["r0c0", "r0c1", "r1c0"],
        cells,
        lambda _cw, mask: "SDC" if mask.bit_count() == 3 else classify_secded_control(mask),
    )
    crossing = propagate_topology(
        ["r0c0", "r2c0"], cells, lambda _cw, mask: classify_secded_control(mask)
    )
    assert sbu["outcomes"] == {"0": "CORRECTED"}
    assert dbu["outcomes"] == {"0": "DUE"}
    assert mbu["outcomes"] == {"0": "SDC"}
    assert crossing["outcomes"] == {"0": "CORRECTED", "1": "CORRECTED"}


def test_technology_mismatch_blocks_130nm_numeric_transfer() -> None:
    assert (
        classify_literature_transfer("generic proprietary 130-nm bulk CMOS SRAM", "SKY130")
        == "LITERATURE_REFERENCE_TECHNOLOGY_MISMATCH"
    )
    assert classify_literature_transfer("SKY130", "SKY130") == "LITERATURE_REFERENCE"


def test_literature_registry_transfers_no_numeric_value_to_sky130() -> None:
    registry = _json("LITERATURE_FAULT_EVIDENCE.json")
    assert registry["technology_matched_count"] == 0
    assert registry["numeric_values_transferred_to_sky130"] == 0
    records = registry["records"]
    assert isinstance(records, list) and records
    assert all(record["evidence_kind"] == "TECHNOLOGY_MISMATCH" for record in records)
    assert all(record["numeric_value_transferred_to_sky130"] is False for record in records)


def test_qcrit_is_separate_from_particle_event_rate() -> None:
    qcrit = QCritRecord(2e-15, "declared double exponential pulse", "PARAMETRIC", "SKY130", "TT/25C/1.8V")
    with pytest.raises(ValueError, match="cannot establish a particle event rate"):
        event_rate_from_qcrit(qcrit)
    status = _json("CIRCUIT_UPSET_SUSCEPTIBILITY.json")
    assert status["qcrit_c"] is None
    assert status["qcrit_status"] == "E0_BLOCKED"


def test_latency_initiation_interval_and_throughput_are_separate() -> None:
    metrics = ServiceMetrics(latency_cycles=4, initiation_interval_cycles=1, clock_period_s=2e-9)
    assert metrics.latency_s == pytest.approx(8e-9)
    assert metrics.nominal_initiation_capacity_services_per_s == pytest.approx(5e8)
    assert metrics.latency_cycles != metrics.initiation_interval_cycles
    records = _json("SERVICE_METRICS.json")["records"]
    assert all(record["registered_service_latency_cycles"] == 1 for record in records)
    assert all(record["initiation_interval_cycles"] == 1 for record in records)
    assert all(record["maximum_sustainable_throughput_services_per_s"] == "UNAVAILABLE" for record in records)


def test_power_is_integrated_before_being_reported_as_energy() -> None:
    derived = derive_energy_from_power(
        2.0,
        5.0,
        10,
        source_kind="POST_ROUTE_ESTIMATE",
        functional_unit="one service",
    )
    assert derived.window_energy_j == 10.0
    assert derived.energy_per_service_j == 1.0
    assert derived.derived_kind == "POST_ROUTE_ESTIMATE"
    with pytest.raises(ValueError, match="cannot derive energy"):
        derive_energy_from_power(2.0, 5.0, 10, source_kind="UNAVAILABLE", functional_unit="one service")


def test_internal_switching_and_leakage_form_disjoint_total() -> None:
    activity = _json("POST_ROUTE_ACTIVITY.json")
    for row in activity["postroute_rows"]:
        validate_disjoint_power_partition(
            row["power_total_w"],
            {
                "internal": row["power_internal_w"],
                "switching": row["power_switching_w"],
                "leakage": row["power_leakage_w"],
            },
            tolerance_w=1e-9,
        )
        assert row["energy_evidence_kind"] == "POST_ROUTE_ESTIMATE"
        assert row["energy_qualification_status"] == "DIAGNOSTIC_ONLY_NOT_E5"


def test_interleaver_mapping_requires_complete_bijection() -> None:
    validate_interleaver_mapping({"c0": (0, 0), "c1": (0, 1)}, expected_cell_count=2)
    with pytest.raises(ValueError, match="incomplete"):
        validate_interleaver_mapping({"c0": (0, 0)}, expected_cell_count=2)
    with pytest.raises(ValueError, match="bijective"):
        validate_interleaver_mapping({"c0": (0, 0), "c1": (0, 0)}, expected_cell_count=2)
    results = _json("INTERLEAVER_PHYSICAL_RESULTS.json")
    assert results["implemented_nontrivial_interleaver_count"] == 0
    assert results["reliability_benefit_qualified"] is False


def test_qualification_gates_keep_physical_reliability_and_e5_blocked() -> None:
    assessment = _json("QUALIFICATION_ASSESSMENT_V3_1.json")
    assert assessment["e5_measurement_count"] == 0
    indexed = {row["metric"]: row for row in assessment["metrics"]}
    assert indexed["physical_sdc_due_fit"]["status"] == "PHYSICAL_SDC_DUE_BLOCKED"
    assert indexed["matched_trace_energy_per_requested_service"]["highest_tier"] == "E4"
    assert indexed["rtl_service_latency"]["highest_tier"] == "E3"


def test_exact_pareto_is_deterministic_and_classified_by_evidence() -> None:
    assert exact_pareto_indices([(1.0, 2.0), (2.0, 1.0), (3.0, 3.0)]) == [0, 1]
    assert (
        classify_pareto_front(["E4"], physical_probabilities_qualified=False, sustainability_qualified=False)
        == "DIAGNOSTIC_FRONT"
    )
    artifact = _json("EXACT_PARETO_V3_1.json")
    assert artifact["enumeration"] == "EXACT"
    assert artifact["front_classification"] == "DIAGNOSTIC_FRONT"
    assert artifact["global_winner_qualified"] is False


def test_v31_outputs_are_additive_and_preserve_parent_records() -> None:
    physical = _json("MATRIX_P_V3_1.json")
    evidence = _json("MATRIX_E_V3_1.json")
    sustainability = _json("MATRIX_S_V3_1.json")
    assert physical["new_row_count"] == 10
    assert physical["row_count"] == 24
    assert evidence["new_row_count"] == 262
    assert evidence["row_count"] == 472
    assert sustainability["new_row_count"] == 0
    assert sustainability["row_count"] == 2
    new_evidence = [row for row in evidence["records"] if row["record_origin"] == "V3_1_PHYSICAL_POPULATION"]
    assert {row["evidence_tier"] for row in new_evidence} == {"E0", "E3", "E4"}
    assert not any(row["evidence_tier"] == "E5" for row in new_evidence)


def test_frozen_foundation_hashes_and_legacy_contract_are_intact() -> None:
    manifest = _json("FROZEN_FOUNDATION_MANIFEST.json")
    assert manifest["legacy_v1_v2_modified"] is False
    for record in manifest["records"]:
        assert _sha(REPO / record["path"]) == record["sha256"]


def test_builder_is_byte_deterministic() -> None:
    before = {path.name: _sha(path) for path in artifact_paths()}
    build_all()
    after = {path.name: _sha(path) for path in artifact_paths()}
    assert after == before
