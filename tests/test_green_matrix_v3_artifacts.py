from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re

from campaigns.iscas_sustainability_extension.green_matrix_v3_imec_aligned.build_campaign import (
    BASE,
    LEGACY,
    artifact_paths,
    build_all,
)


def _json(name: str) -> object:
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def _csv(name: str) -> list[dict[str, str]]:
    with (BASE / name).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_required_core_artifacts_exist() -> None:
    required = {
        "FINAL_REPORT.md",
        "FRAMEWORK_SPECIFICATION.md",
        "RESEARCH_MODEL.md",
        "FUNCTIONAL_UNIT.md",
        "CAUSAL_GRAPH.md",
        "CAUSAL_GRAPH.json",
        "CSCI_DEFINITION.md",
        "CSCI_MATHEMATICAL_AUDIT.md",
        "MRCC_DEFINITION.md",
        "MRCC_MATHEMATICAL_AUDIT.md",
        "MANUFACTURING_CARBON_MODEL.md",
        "IMEC_ALIGNMENT.md",
        "IMEC_SOURCE_BOUNDARIES.md",
        "ACT_ACT3_CROSS_VALIDATION.md",
        "SYSTEM_BOUNDARIES.json",
        "ARCHITECTURE_REGISTRY.json",
        "TECHNOLOGY_REGISTRY.json",
        "PROCESS_ROUTE_REGISTRY.json",
        "SOURCE_REGISTRY.csv",
        "SOURCE_REGISTRY.json",
        "EVIDENCE_TAXONOMY.md",
        "QUALIFICATION_RULES.json",
        "MATRIX_P.csv",
        "MATRIX_E.csv",
        "MATRIX_S.csv",
        "GREEN_MATRIX_V3_VIEW.csv",
        "EVIDENCE_COVERAGE.csv",
        "PARTIAL_FRONTIERS.csv",
        "UNCERTAINTY_MODEL.json",
        "RESEARCH_QUESTIONS.md",
        "REGRESSION_STATUS.json",
        "FINAL_ARTIFACT_HASHES.json",
    }
    assert not [name for name in sorted(required) if not (BASE / name).is_file()]


def test_matrices_are_separate_sparse_and_schema_backed() -> None:
    physical = _csv("MATRIX_P.csv")
    evidence = _csv("MATRIX_E.csv")
    sustainability = _csv("MATRIX_S.csv")
    assert len(physical) == 14
    assert len(evidence) == 210
    assert len(sustainability) == 2
    assert "lifecycle_kgco2e" not in physical[0]
    assert "csci_kgco2e_per_correct_service" not in physical[0]
    assert "observed_macro_area_um2" not in sustainability[0]
    for name in ("MATRIX_P", "MATRIX_E", "MATRIX_S", "GREEN_MATRIX_V3_VIEW", "EVIDENCE_COVERAGE", "PARTIAL_FRONTIERS"):
        assert (BASE / f"{name}.schema.json").is_file()


def test_seed_observations_match_immutable_v2_values() -> None:
    physical = {row["source_record_id"]: row for row in _csv("MATRIX_P.csv")}
    with (LEGACY / "green_matrix_v2" / "GREEN_MATRIX_V2_RAW.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        legacy = list(csv.DictReader(handle))
    for row in legacy:
        seed = physical[row["row_id"]]
        assert seed["observed_macro_area_um2"] == row["observed_macro_area_um2"]
        assert seed["activity_coverage_fraction"] == row["activity_coverage_fraction"]
        assert seed["diagnostic_tool_power_w"] == row["diagnostic_tool_power_w"]
        assert seed["logical_control_sdc_fraction"] == row["logical_control_sdc_fraction"]
        assert seed["rate_semantics"] == "ENUMERATED_MASK_FREQUENCY_NOT_EVENT_RATE"


def test_missing_physical_and_carbon_evidence_is_not_fabricated() -> None:
    evidence = _csv("MATRIX_E.csv")
    missing_names = {
        "operational_energy_j",
        "latency_s",
        "physical_fault_probability",
        "physical_sdc_probability",
        "physical_due_probability",
        "manufacturing_carbon_kgco2e",
    }
    missing = [row for row in evidence if row["quantity_name"] in missing_names]
    assert len(missing) == 14 * len(missing_names)
    for row in missing:
        assert row["value"] == ""
        assert row["evidence_tier"] == "E0"
        assert row["evidence_kind"] == "UNQUALIFIED"
        assert row["blocking_reason"]
    for row in _csv("MATRIX_S.csv"):
        assert row["scope1_kgco2e"] == ""
        assert row["lifecycle_kgco2e"] == ""
        assert row["csci_kgco2e_per_correct_service"] == ""
        assert row["qualification_status"] == "BLOCKED"


def test_master_view_keeps_all_conceptual_axes_explicit() -> None:
    data = _json("GREEN_MATRIX_V3_VIEW.json")
    assert data["conceptual_tensor"] == "G[A,N,F,I,W,P,G,L,M]"  # type: ignore[index]
    row = data["records"][0]  # type: ignore[index]
    for field in (
        "architecture_id",
        "technology_id",
        "fault_environment_id",
        "interleaving_id",
        "workload_id",
        "service_policy_id",
        "fab_scenario_id",
        "lifetime_scenario_id",
    ):
        assert field in row


def test_evidence_coverage_reports_gaps_without_global_erasure() -> None:
    rows = _csv("EVIDENCE_COVERAGE.csv")
    assert len(rows) == 2
    for row in rows:
        assert row["area"] == "E4_DIAGNOSTIC"
        assert row["logical_outcomes"] == "E3_LOGICAL_CONTROL"
        assert row["physical_SDC"] == "E0"
        assert row["manufacturing_carbon"] == "E0"
        assert row["CSCI"] == "BLOCKED"


def test_qualification_engine_explains_every_rejection() -> None:
    assessment = _json("evidence/QUALIFICATION_ASSESSMENT.json")
    rows = assessment["assessments"]  # type: ignore[index]
    assert assessment["qualified_winner"] is None  # type: ignore[index]
    for row in rows:
        if row["status"] == "BLOCKED":
            assert row["reasons"]
        if row["metric_id"] == "LOGICAL_CONTROL_AREA_DIAGNOSTIC":
            assert row["status"] == "QUALIFIED"


def test_partial_frontiers_are_exact_diagnostic_and_never_selection_eligible() -> None:
    data = _json("PARTIAL_FRONTIERS.json")
    assert data["exact_enumeration"] is True  # type: ignore[index]
    assert data["NSGA_II_used"] is False  # type: ignore[index]
    assert data["qualified_architecture_winner"] is None  # type: ignore[index]
    assert len(data["blocked_frontiers"]) == 4  # type: ignore[index]
    records = data["records"]  # type: ignore[index]
    assert len(records) == 14
    assert all(row["result_class"] == "LOGICAL_CONTROL" for row in records)
    assert all(row["selection_eligible"] is False for row in records)


def test_registries_are_configuration_driven_and_future_ready() -> None:
    architecture = _json("ARCHITECTURE_REGISTRY.json")
    assert {row["architecture_id"] for row in architecture["architectures"]} == {"U0", "E0", "E1"}  # type: ignore[index]
    interleaving = _json("INTERLEAVING_REGISTRY.json")
    assert {row["interleaving_id"] for row in interleaving["interleaving"]} == {"I0", "I1", "I2"}  # type: ignore[index]
    process = _json("PROCESS_ROUTE_REGISTRY.json")
    assert "DRY_ETCH" in process["process_module_vocabulary"]  # type: ignore[index]
    technology = _json("TECHNOLOGY_REGISTRY.json")
    sky = next(row for row in technology["technologies"] if row["technology_id"] == "SKY130")  # type: ignore[index]
    assert sky["manufacturing_inventory_status"] == "SKY130_MANUFACTURING_CARBON_NOT_QUALIFIED"


def test_source_registry_has_boundary_and_transfer_metadata() -> None:
    rows = _csv("SOURCE_REGISTRY.csv")
    assert rows
    required = {
        "source_id",
        "organization",
        "publication",
        "url_or_doi",
        "publication_date",
        "model_tool_version",
        "retrieved_date",
        "original_node",
        "original_process",
        "original_metric",
        "original_units",
        "original_system_boundary",
        "original_geography",
        "original_grid_ci",
        "original_yield_assumptions",
        "evidence_kind",
        "allowed_use",
        "prohibited_translation",
        "notes",
    }
    assert required <= set(rows[0])
    imec = [row for row in rows if row["source_id"].startswith("SRC_IMEC")]
    assert imec
    assert all(row["prohibited_translation"] == "NEVER_RELABEL_AS_SKY130_MEASUREMENT" for row in imec)


def test_imec_and_act_validations_do_not_overclaim() -> None:
    imec = _json("validation/IMEC_CROSS_VALIDATION.json")
    assert imec["alignment_label"] == "IMEC_PUBLIC_EVIDENCE_ALIGNED"  # type: ignore[index]
    assert imec["certified_or_compliant_claim"] is False  # type: ignore[index]
    assert any(row["classification"] == "NOT_COMPARABLE" for row in imec["comparisons"])  # type: ignore[index]
    act = _json("validation/ACT_ACT3_CROSS_VALIDATION.json")
    assert act["classification"] == "EXACT_REPRODUCTION"  # type: ignore[index]
    assert act["matched_synthetic_vector"]["expected_kgco2e"] == 0.8125  # type: ignore[index]
    assert act["ACT_defaults_adopted"] is False  # type: ignore[index]


def test_legacy_comparison_records_rank_reversal_and_no_epsilon() -> None:
    legacy = _json("validation/LEGACY_COMPARISON_TESTS.json")
    assert legacy["classification"] == "LEGACY_OR_COMPARISON_METRIC"  # type: ignore[index]
    assert legacy["epsilon_floors"] is False  # type: ignore[index]
    assert "A_over_B becomes B_over_A" in legacy["candidate_set_dependence_counterexample"]["rank_reversal"]  # type: ignore[index]


def test_causal_graph_has_required_chains_and_double_count_guards() -> None:
    graph = _json("CAUSAL_GRAPH.json")
    edges = {(edge["from"], edge["to"]) for edge in graph["edges"]}  # type: ignore[index]
    assert ("process_route", "process_steps") in edges
    assert ("die_area", "yield") in edges
    assert ("physical_mapping", "conditional_outcome") in edges
    assert ("operational_energy", "operational_carbon") in edges
    assert ("correct_services", "csci") in edges
    assert len(graph["double_count_guards"]) >= 4  # type: ignore[arg-type,index]


def test_final_report_answers_all_57_questions() -> None:
    report = (BASE / "FINAL_REPORT.md").read_text(encoding="utf-8")
    numbers = [int(value) for value in re.findall(r"(?m)^(\d+)\. \*\*", report)]
    assert numbers == list(range(1, 58))
    assert "NO_GLOBAL_WINNER_QUALIFIED" in report
    assert "SKY130_MANUFACTURING_CARBON_NOT_QUALIFIED" in report


def test_provenance_freeze_pins_v2_and_reports_no_historical_edits() -> None:
    freeze = _json("integrity/PROVENANCE_FREEZE.json")
    assert freeze["starting_scientific_baseline"] == "4c3e106"  # type: ignore[index]
    assert len(freeze["v2_git_tree_sha1"]) == 40  # type: ignore[arg-type,index]
    assert freeze["files_modified_in_historical_tree"] == []  # type: ignore[index]
    assert freeze["historical_protected_tree_fingerprints"]  # type: ignore[index]


def test_campaign_status_withholds_winner_and_preserves_previous_classification() -> None:
    status = _json("CAMPAIGN_STATUS.json")
    assert status["previous_classification_preserved"] == "GREEN_METRIC_REFOUNDED_PARTIAL_QUALIFICATION"  # type: ignore[index]
    assert status["historical_artifacts_modified"] is False  # type: ignore[index]
    assert status["selection"]["qualified_winner"] is None  # type: ignore[index]
    assert status["selection"]["classification"] == "NO_GLOBAL_WINNER_QUALIFIED"  # type: ignore[index]
    assert status["selection"]["epsilon_floors_used"] is False  # type: ignore[index]


def test_generation_is_byte_deterministic_for_publication_tables() -> None:
    names = [
        "MATRIX_P.csv",
        "MATRIX_E.csv",
        "MATRIX_S.csv",
        "GREEN_MATRIX_V3_VIEW.csv",
        "EVIDENCE_COVERAGE.csv",
        "PARTIAL_FRONTIERS.csv",
        "CAUSAL_GRAPH.json",
    ]
    before = {name: _sha(BASE / name) for name in names}
    build_all()
    after = {name: _sha(BASE / name) for name in names}
    assert after == before


def test_final_hash_manifest_covers_every_nonself_artifact() -> None:
    manifest = _json("FINAL_ARTIFACT_HASHES.json")
    recorded = {item["path"]: item for item in manifest["artifacts"]}  # type: ignore[index]
    expected = {path.relative_to(BASE).as_posix(): path for path in artifact_paths()}
    assert set(recorded) == set(expected)
    assert manifest["artifact_count"] == len(expected)  # type: ignore[index]
    for relative, path in expected.items():
        assert recorded[relative]["bytes"] == path.stat().st_size
        assert recorded[relative]["sha256"] == _sha(path)
