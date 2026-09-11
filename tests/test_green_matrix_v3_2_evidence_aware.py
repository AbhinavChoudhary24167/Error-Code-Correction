from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import jsonschema
import pytest

from campaigns.iscas_sustainability_extension.green_matrix_v3_2.build_campaign import (
    BASE,
    PARENT,
    _parent_sha,
    artifact_paths,
    build_all,
)
from campaigns.iscas_sustainability_extension.green_matrix_v3_2.core import (
    ActivityCompleteness,
    GuardViolation,
    Objective,
    conditional_outcome_rate_per_hour,
    csci_kgco2e_per_correct_service,
    exact_pareto_ids,
    fit_from_event_rate,
    mrcc_kgco2e_per_additional_correct_service,
    qualify_e5_activity,
    qualified_pareto_or_blocked,
    require_numeric,
    validate_imec_language,
    validate_interleaver_reliability_claim,
    validate_literature_numeric_transfer,
    validate_manufacturing_label,
    validate_scenario_semantics,
    validate_throughput_claim,
)


def _json(relative: str) -> dict[str, object]:
    return json.loads((BASE / relative).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _complete_activity(**changes: object) -> ActivityCompleteness:
    values: dict[str, object] = {
        "annotation_coverage_fraction": 1.0,
        "unannotated_instance_pin_count": 0,
        "unmatched_activity_object_count": 0,
        "default_activity_used": False,
        "postroute_gate_level_activity": True,
        "macro_internal_activity_characterized": True,
        "whole_service_boundary_covered": True,
        "operation_window_isolated": True,
        "duration_s": 1.0e-6,
        "operation_count": 100,
        "clock_period_s": 1.0e-8,
        "workload_hash": "w",
        "activity_hash": "a",
        "implementation_hash": "i",
        "netlist_hash": "n",
        "configuration_hash": "c",
        "constraint_hash": "s",
        "power_report_hash": "p",
    }
    values.update(changes)
    return ActivityCompleteness(**values)  # type: ignore[arg-type]


def test_three_matrices_validate_against_v32_schema() -> None:
    schema = _json("schema/green_matrix_v3_2.schema.json")
    for name in (
        "data/EVIDENCE_MATRIX.json",
        "data/PHYSICAL_MATRIX.json",
        "data/SUSTAINABILITY_MATRIX.json",
    ):
        jsonschema.Draft202012Validator(schema).validate(_json(name))


def test_evidence_records_have_complete_semantics_and_dependency_integrity() -> None:
    evidence = _json("data/EVIDENCE_MATRIX.json")
    records = evidence["records"]
    assert isinstance(records, list) and len(records) == evidence["row_count"]
    required = {
        "record_id",
        "metric_identifier",
        "architecture",
        "scenario",
        "value",
        "units",
        "uncertainty",
        "evidence_tier",
        "evidence_source",
        "measurement_boundary",
        "provenance",
        "technology_process",
        "pvt",
        "workload_activity",
        "semantic_status",
        "qualification_status",
        "blocking_reason",
        "permitted_downstream_uses",
        "forbidden_downstream_uses",
        "derived_from",
        "compatibility",
    }
    ids = {row["record_id"] for row in records}
    assert len(ids) == len(records)
    for row in records:
        assert required <= set(row)
        assert all(parent in ids for parent in row["derived_from"])


def test_physical_matrix_cells_reference_evidence_matrix() -> None:
    evidence_ids = {row["record_id"] for row in _json("data/EVIDENCE_MATRIX.json")["records"]}
    physical = _json("data/PHYSICAL_MATRIX.json")
    assert physical["all_cells_reference_M_E"] is True
    for row in physical["records"]:
        for metric in row["metrics"].values():
            assert metric["evidence_ids"]
            assert set(metric["evidence_ids"]) <= evidence_ids


def test_guard_1_logical_frequency_cannot_be_physical_event_rate() -> None:
    record = {
        "value": 0.1,
        "source_kind": "LOGICAL_INJECTION_FREQUENCY",
        "semantic_status": "MEASURED",
        "qualification_status": "ABSOLUTE_QUALIFIED",
        "evidence_tier": "E7",
        "compatibility": {key: True for key in ("technology", "process", "pvt", "geometry", "environment")},
    }
    with pytest.raises(GuardViolation, match="forbidden source"):
        conditional_outcome_rate_per_hour(record, 0.2)


def test_guards_2_and_3_fit_sdc_due_require_qualified_physical_rate() -> None:
    blocked = {
        "value": None,
        "source_kind": "BLOCKED",
        "semantic_status": "BLOCKED",
        "qualification_status": "BLOCKED",
        "evidence_tier": "E0",
        "compatibility": {},
    }
    with pytest.raises(GuardViolation, match="PHYSICAL_EVENT_RATE_BLOCKED"):
        fit_from_event_rate(blocked, 0.1)
    for probability in (0.2, 0.3):
        with pytest.raises(GuardViolation, match="PHYSICAL_EVENT_RATE_BLOCKED"):
            conditional_outcome_rate_per_hour(blocked, probability)


def test_guard_4_mismatched_literature_numeric_transfer_is_forbidden() -> None:
    with pytest.raises(GuardViolation, match="TRANSFER_TO_SKY130_FORBIDDEN"):
        validate_literature_numeric_transfer(
            source_technology="proprietary 130-nm CMOS",
            target_technology="SKY130",
            numeric_transfer=True,
        )


def test_guard_5_e4_diagnostic_energy_cannot_be_called_e5() -> None:
    assert qualify_e5_activity(_complete_activity())["evidence_tier"] == "E5"
    incomplete = qualify_e5_activity(
        _complete_activity(
            annotation_coverage_fraction=0.4868421052631579,
            unannotated_instance_pin_count=312,
            default_activity_used=True,
        )
    )
    assert incomplete["evidence_tier"] == "E4"
    assert incomplete["qualification_status"] == "DIAGNOSTIC"


def test_guard_6_nominal_capacity_is_not_saturated_throughput() -> None:
    with pytest.raises(GuardViolation, match="independent saturation test"):
        validate_throughput_claim(
            label="MAXIMUM_SUSTAINABLE_THROUGHPUT", saturated_measurement_present=False
        )


def test_guard_7_interleaver_benefit_requires_route_and_mapping() -> None:
    with pytest.raises(GuardViolation, match="routed implementation"):
        validate_interleaver_reliability_claim(
            physically_implemented=False, physical_logical_mapping_complete=False
        )


def test_guard_8_reference_carbon_cannot_be_relabelled_sky130() -> None:
    with pytest.raises(GuardViolation, match="cannot be relabelled"):
        validate_manufacturing_label(
            label="SKY130_MANUFACTURING_CARBON", technology_matched_inventory=False
        )


def test_guards_9_and_10_qualified_front_and_global_winner_are_blocked() -> None:
    pareto = _json("data/PARETO_ANALYSIS.json")
    status = _json("CAMPAIGN_STATUS.json")
    assert pareto["qualified_front"]["status"] == "BLOCKED"
    assert pareto["qualified_front"]["front"] == []
    assert status["global_architecture_winner"] == "NO_GLOBAL_WINNER_QUALIFIED"
    direct = qualified_pareto_or_blocked(
        records=[{"architecture_id": "U0", "carbon": None}],
        objectives=[Objective("carbon", "min", "kgCO2e")],
        admissibility=[{"architecture": "U0", "qualified": False, "blocking_metrics": ["carbon"]}],
    )
    assert direct["front_classification"] == "QUALIFIED_FRONT_BLOCKED"


def test_guard_11_scenario_assumptions_are_not_measurements() -> None:
    with pytest.raises(GuardViolation, match="not measured evidence"):
        validate_scenario_semantics(
            semantic_status="SCENARIO_ASSUMPTION", promoted_to_evidence=True
        )
    scenarios = _json("data/SCENARIO_DEFINITIONS.json")
    assert all(row["promoted_to_evidence"] is False for row in scenarios["records"])


def test_guard_12_blocked_metric_cannot_be_dropped_before_optimization() -> None:
    with pytest.raises(GuardViolation, match="silently discarded"):
        exact_pareto_ids(
            [{"architecture_id": "U0", "area": 1.0}],
            [Objective("area", "min", "um2"), Objective("carbon", "min", "kgCO2e")],
        )


def test_guard_13_unknown_or_blocked_is_never_zero() -> None:
    for value in (None, ""):
        with pytest.raises(GuardViolation, match="cannot be treated as zero"):
            require_numeric(value, metric="PHYSICAL_EVENT_RATE")
    assert require_numeric(0.0, metric="JUSTIFIED_ZERO") == 0.0


def test_guard_14_imec_certification_language_is_rejected() -> None:
    with pytest.raises(GuardViolation, match="forbidden imec claim"):
        validate_imec_language("This framework is imec compliant.")
    validate_imec_language(
        "Methodologically informed by public imec SSTS concepts; no endorsement by imec is claimed."
    )
    validate_imec_language((BASE / "FINAL_REPORT.md").read_text(encoding="utf-8"))
    validate_imec_language((BASE / "ISCAS_METHODOLOGY.md").read_text(encoding="utf-8"))


def test_conditional_response_surfaces_are_exact_and_not_absolute_rates() -> None:
    artifact = _json("data/CONDITIONAL_RELIABILITY.json")
    assert artifact["record_count"] == 8
    rows = {(row["architecture"], row["topology_class"]): row for row in artifact["records"]}
    assert rows[("U0", "LOGICAL_SBU_ANY_BIT")]["probabilities"]["sdc"] == 1.0
    assert rows[("E0", "LOGICAL_SBU_ANY_BIT")]["probabilities"]["corrected"] == 1.0
    assert rows[("E0", "LOGICAL_DBU_ANY_PAIR")]["probabilities"]["due"] == 1.0
    assert rows[("E0", "LOGICAL_CONSECUTIVE_MBU_3")]["probabilities"]["sdc"] == pytest.approx(46 / 70)
    assert all(row["physical_event_probability"] is None for row in artifact["records"])
    assert all(row["physical_rate_claim_permitted"] is False for row in artifact["records"])


def test_scenario_fronts_and_robustness_have_conditional_semantics() -> None:
    pareto = _json("data/PARETO_ANALYSIS.json")
    robustness = _json("data/SCENARIO_ROBUSTNESS.json")
    assert pareto["enumeration"] == "EXACT_DETERMINISTIC"
    assert pareto["machine_learning_used"] is False
    assert all(
        row["front_classification"] == "CONDITIONAL_SCENARIO_FRONT"
        for row in pareto["conditional_scenario_fronts"]
    )
    assert robustness["fractions"] == {"E0": 1.0, "U0": 1.0}
    assert robustness["physical_probability"] is False
    assert robustness["probability_of_winning"] is False


def test_energy_interleaver_mapping_and_carbon_statuses_fail_closed() -> None:
    energy = _json("data/ENERGY_QUALIFICATION.json")
    interleaver = _json("data/INTERLEAVER_FEASIBILITY.json")
    mapping = _json("data/BITCELL_MAPPING_AUDIT.json")
    status = _json("CAMPAIGN_STATUS.json")
    assert energy["e5_measurement_count"] == 0
    assert all(row["qualification"]["evidence_tier"] == "E4" for row in energy["records"])
    assert interleaver["implemented_nontrivial_interleaver_count"] == 0
    assert all(
        row["physical_reliability_benefit_qualified"] is False
        for row in interleaver["records"]
    )
    assert mapping["mapping_improved_from_v3_1"] is False
    assert status["manufacturing_carbon_status"] == "BLOCKED"
    assert status["reference_manufacturing_scenario_count"] == 0


def test_literature_records_remain_native_and_never_transfer_to_sky130() -> None:
    policy = _json("data/LITERATURE_POLICY.json")
    assert policy["record_count"] == 5
    assert policy["numeric_values_transferred_to_sky130"] == 0
    assert all(row["numeric_value_transferred_to_sky130"] is False for row in policy["records"])
    evidence = _json("data/EVIDENCE_MATRIX.json")
    literature = [row for row in evidence["records"] if row["evidence_tier"] == "E2"]
    assert len(literature) == 5
    assert all(row["semantic_status"] == "LITERATURE_NATIVE" for row in literature)


def test_csci_and_mrcc_equations_are_valid_but_unavailable_operands_block_values() -> None:
    assert csci_kgco2e_per_correct_service(2.0, 4.0) == 0.5
    assert mrcc_kgco2e_per_additional_correct_service(1.5, 3.0) == 0.5
    with pytest.raises(GuardViolation, match="LIFECYCLE_CARBON"):
        csci_kgco2e_per_correct_service(None, 4.0)
    with pytest.raises(GuardViolation, match="DELTA_CORRECT_SERVICE_COUNT"):
        mrcc_kgco2e_per_additional_correct_service(1.0, None)
    equations = _json("data/EQUATION_STATUS.json")
    assert all(row["equation_status"] == "VALID" for row in equations["records"])
    assert all(row["quantity_status"] == "BLOCKED" for row in equations["records"])


def test_report_answers_all_35_questions_and_classification_is_derived() -> None:
    report = (BASE / "FINAL_REPORT.md").read_text(encoding="utf-8")
    numbers = [int(value) for value in re.findall(r"(?m)^(\d+)\. \*\*", report)]
    assert numbers == list(range(1, 36))
    status = _json("CAMPAIGN_STATUS.json")
    assert status["classification"] in report
    assert "NO_GLOBAL_WINNER_QUALIFIED" in report


def test_historical_hashes_are_preserved_and_v31_files_are_not_rewritten() -> None:
    history = _json("data/HISTORICAL_INTEGRITY.json")
    assert history["historical_artifacts_modified"] is False
    for name, digest in history["parent_artifact_hashes"].items():
        assert _parent_sha(PARENT / name) == digest


def test_builder_is_byte_deterministic_and_hash_manifest_is_complete() -> None:
    status = _json("CAMPAIGN_STATUS.json")
    paths = artifact_paths() + [BASE / "FINAL_ARTIFACT_HASHES.json"]
    before = {path.relative_to(BASE).as_posix(): _sha(path) for path in paths}
    build_all(campaign_commit=str(status["campaign_commit"]))
    after = {path.relative_to(BASE).as_posix(): _sha(path) for path in paths}
    assert after == before
    manifest = _json("FINAL_ARTIFACT_HASHES.json")
    expected = {path.relative_to(BASE).as_posix(): path for path in artifact_paths()}
    recorded = {row["path"]: row for row in manifest["artifacts"]}
    assert set(recorded) == set(expected)
    for relative, path in expected.items():
        assert recorded[relative]["sha256"] == _sha(path)
