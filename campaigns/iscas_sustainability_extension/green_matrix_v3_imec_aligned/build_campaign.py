"""Deterministically build GREEN Matrix 3.0 publication artifacts.

The generator reads immutable GREEN Matrix v2 seed evidence and v3
configuration.  It never writes into the historical campaign tree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
LEGACY = BASE.parent / "green_refoundation_node_aware_carbon"
BASELINE_COMMIT = "4c3e106"
GENERATION_DATE = "2026-09-08"
SCHEMA_VERSION = "3.0.0"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from campaigns.iscas_sustainability_extension.green_matrix_v3_imec_aligned.core import (  # noqa: E402
    EvidenceRecord,
    EvidenceRequirement,
    EvidenceTier,
    Objective,
    QualificationRule,
    exact_pareto_indices,
    qualify,
)


MODULAR_DIRECTORIES = (
    "physical",
    "reliability",
    "energy",
    "latency",
    "interleaving",
    "manufacturing",
    "carbon",
    "workloads",
    "service_policy",
    "evidence",
    "uncertainty",
    "metrics",
    "pareto",
    "validation",
    "sources",
    "matrix",
    "figures",
    "integrity",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )


def write_csv(path: Path, rows: Sequence[Mapping[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config(name: str) -> Any:
    return load_json(BASE / "config" / name)


def git_output(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=REPO, text=True, encoding="utf-8"
    ).strip()


def field_schema(
    name: str,
    field_type: str,
    *,
    unit: str | None = None,
    nullable: bool = True,
    description: str | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "name": name,
        "type": field_type,
        "nullable": nullable,
    }
    if unit is not None:
        item["unit"] = unit
    if description is not None:
        item["description"] = description
    return item


P_FIELDS = (
    "record_id",
    "design_id",
    "architecture_id",
    "ecc_family",
    "payload_bits",
    "codeword_bits",
    "parity_bits",
    "correction_capability_bits",
    "detection_capability_bits",
    "decoder_architecture",
    "pipeline_stages",
    "initiation_interval_cycles",
    "technology_id",
    "process_route_id",
    "compiler_id",
    "implementation_id",
    "interleaving_id",
    "physical_interleaver_implemented",
    "workload_id",
    "service_policy_id",
    "fault_environment_id",
    "clock_hz",
    "voltage_v",
    "temperature_c",
    "observed_macro_area_um2",
    "activity_coverage_fraction",
    "diagnostic_tool_power_w",
    "latency_s",
    "throughput_services_per_s",
    "logical_pattern_count",
    "logical_success_normal_count",
    "logical_success_corrected_count",
    "logical_success_after_retry_count",
    "logical_detected_failure_count",
    "logical_sdc_count",
    "logical_timeout_count",
    "logical_control_success_fraction",
    "logical_control_due_fraction",
    "logical_control_sdc_fraction",
    "logical_control_corrected_fraction",
    "logical_control_retry_fraction",
    "rate_semantics",
    "source_record_id",
)


E_FIELDS = (
    "quantity_id",
    "entity_id",
    "quantity_name",
    "value",
    "unit",
    "source_id",
    "source_type",
    "implementation_hash",
    "experiment_hash",
    "technology_id",
    "pvt",
    "workload_id",
    "measurement_model_boundary",
    "evidence_tier",
    "evidence_kind",
    "uncertainty_representation",
    "citation",
    "date_version",
    "qualification_status",
    "blocking_reason",
)


S_FIELDS = (
    "translation_id",
    "design_id",
    "technology_id",
    "fab_scenario_id",
    "manufacturing_grid_id",
    "use_grid_id",
    "lifetime_scenario_id",
    "system_boundary_id",
    "allocation_method",
    "scope1_kgco2e",
    "scope2_kgco2e",
    "upstream_declared_kgco2e",
    "mask_nre_kgco2e",
    "packaging_kgco2e",
    "operational_kgco2e",
    "lifecycle_kgco2e",
    "request_count",
    "correct_service_probability",
    "correct_service_count",
    "csci_kgco2e_per_correct_service",
    "csci_bit_kgco2e_per_correct_payload_bit",
    "result_class",
    "qualification_status",
    "blocking_reasons",
)


def build_registries() -> list[Path]:
    outputs: list[Path] = []
    mappings = {
        "architectures.json": "ARCHITECTURE_REGISTRY.json",
        "technologies.json": "TECHNOLOGY_REGISTRY.json",
        "process_routes.json": "PROCESS_ROUTE_REGISTRY.json",
        "system_boundaries.json": "SYSTEM_BOUNDARIES.json",
        "metrics.json": "METRIC_REGISTRY.json",
        "uncertainty.json": "UNCERTAINTY_MODEL.json",
    }
    for source, destination in mappings.items():
        path = BASE / destination
        write_json(path, config(source))
        outputs.append(path)

    scenarios = config("scenario_registries.json")
    for key, destination in (
        ("workloads", "WORKLOAD_REGISTRY.json"),
        ("fault_models", "FAULT_MODEL_REGISTRY.json"),
        ("interleaving", "INTERLEAVING_REGISTRY.json"),
        ("fab_scenarios", "FAB_SCENARIO_REGISTRY.json"),
        ("grid_scenarios", "GRID_SCENARIO_REGISTRY.json"),
        ("service_policies", "SERVICE_POLICY_REGISTRY.json"),
    ):
        payload = {
            "schema_version": scenarios["schema_version"],
            key: scenarios[key],
        }
        path = BASE / destination
        write_json(path, payload)
        outputs.append(path)
    rules = config("qualification_rules.json")
    path = BASE / "QUALIFICATION_RULES.json"
    write_json(path, rules)
    outputs.append(path)
    return outputs


def build_source_registry() -> list[Path]:
    legacy = load_json(LEGACY / "carbon" / "sources" / "SOURCE_REGISTRY.json")
    rows: list[dict[str, object]] = []
    for item in legacy["sources"]:
        rows.append(
            {
                "source_id": item["source_id"],
                "organization": item["publisher"],
                "publication": item["title"],
                "url_or_doi": item.get("doi") or item.get("url") or "",
                "publication_date": str(item["year"]),
                "model_tool_version": (
                    "imec.netzero v1.5.67"
                    if item["source_id"] == "SRC_IMEC_IEDM_2023"
                    else ""
                ),
                "retrieved_date": item["access_date"],
                "original_node": item["node_coverage"],
                "original_process": item.get("assumptions", ""),
                "original_metric": "; ".join(item.get("usable_fields", [])),
                "original_units": item["units"],
                "original_system_boundary": item["system_boundary"],
                "original_geography": "UNDECLARED" if "generic" in item["system_boundary"].lower() else "SOURCE_SPECIFIC_OR_UNDECLARED",
                "original_grid_ci": "0.454 kgCO2e/kWh" if item["source_id"] == "SRC_IMEC_IEDM_2023" else "UNDECLARED_OR_NOT_APPLICABLE",
                "original_yield_assumptions": "86% Murphy die yield; 90% line yield" if item["source_id"] == "SRC_IMEC_IEDM_2023" else "SOURCE_SPECIFIC_OR_UNDECLARED",
                "evidence_kind": "MODELLED_OR_PROJECTED" if "model" in item["source_type"].lower() else "PUBLISHED",
                "allowed_use": item["calibration_use"],
                "prohibited_translation": (
                    "NEVER_RELABEL_AS_SKY130_MEASUREMENT"
                    if item["source_id"].startswith("SRC_IMEC")
                    else "BOUNDARY_MATCH_REQUIRED_FOR_NUMERIC_TRANSFER"
                ),
                "notes": item["limitations"],
            }
        )
    fields = tuple(rows[0])
    json_path = BASE / "SOURCE_REGISTRY.json"
    csv_path = BASE / "SOURCE_REGISTRY.csv"
    write_json(
        json_path,
        {
            "schema_version": SCHEMA_VERSION,
            "source_registry_provenance": str(
                (LEGACY / "carbon" / "sources" / "SOURCE_REGISTRY.json").relative_to(REPO)
            ).replace("\\", "/"),
            "source_registry_sha256": sha256(
                LEGACY / "carbon" / "sources" / "SOURCE_REGISTRY.json"
            ),
            "sources": rows,
        },
    )
    write_csv(csv_path, rows, fields)
    return [json_path, csv_path]


def read_legacy_rows() -> list[dict[str, str]]:
    with (LEGACY / "green_matrix_v2" / "GREEN_MATRIX_V2_RAW.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def build_matrix_p() -> tuple[list[dict[str, object]], list[Path]]:
    architectures = {
        item["architecture_id"]: item
        for item in config("architectures.json")["architectures"]
    }
    rows: list[dict[str, object]] = []
    for legacy in read_legacy_rows():
        architecture = architectures[legacy["architecture_id"]]
        design_id = (
            f"{legacy['architecture_id']}|SKY130|I0|W0_READ_DOMINANT_SEED|"
            "P0_NO_SCRUB_NO_RETRY"
        )
        rows.append(
            {
                "record_id": f"MP|{legacy['row_id']}",
                "design_id": design_id,
                "architecture_id": legacy["architecture_id"],
                "ecc_family": architecture["ecc_family"],
                "payload_bits": architecture["payload_bits"],
                "codeword_bits": architecture["codeword_bits"],
                "parity_bits": architecture["parity_bits"],
                "correction_capability_bits": architecture["correction_capability_bits"],
                "detection_capability_bits": architecture["detection_capability_bits"],
                "decoder_architecture": architecture["decoder_architecture"],
                "pipeline_stages": architecture["pipeline_stages"] if architecture["pipeline_stages"] is not None else "",
                "initiation_interval_cycles": architecture["initiation_interval_cycles"] if architecture["initiation_interval_cycles"] is not None else "",
                "technology_id": "SKY130",
                "process_route_id": "SKY130_ROUTE_UNCHARACTERIZED",
                "compiler_id": "SRAM22_RESEARCH_MACROS",
                "implementation_id": f"A10_{legacy['architecture_id']}_ORIGINAL_LIBERTY",
                "interleaving_id": "I0",
                "physical_interleaver_implemented": False,
                "workload_id": "W0_READ_DOMINANT_SEED",
                "service_policy_id": "P0_NO_SCRUB_NO_RETRY",
                "fault_environment_id": legacy["functional_control_id"],
                "clock_hz": "",
                "voltage_v": "",
                "temperature_c": "",
                "observed_macro_area_um2": legacy["observed_macro_area_um2"],
                "activity_coverage_fraction": legacy["activity_coverage_fraction"],
                "diagnostic_tool_power_w": legacy["diagnostic_tool_power_w"],
                "latency_s": "",
                "throughput_services_per_s": "",
                "logical_pattern_count": legacy["logical_pattern_count"],
                "logical_success_normal_count": legacy["logical_success_normal_count"],
                "logical_success_corrected_count": legacy["logical_success_corrected_count"],
                "logical_success_after_retry_count": legacy["logical_success_after_retry_count"],
                "logical_detected_failure_count": legacy["logical_detected_failure_count"],
                "logical_sdc_count": legacy["logical_sdc_count"],
                "logical_timeout_count": legacy["logical_timeout_count"],
                "logical_control_success_fraction": legacy["logical_control_success_fraction"],
                "logical_control_due_fraction": legacy["logical_control_due_fraction"],
                "logical_control_sdc_fraction": legacy["logical_control_sdc_fraction"],
                "logical_control_corrected_fraction": legacy["logical_control_corrected_fraction"],
                "logical_control_retry_fraction": legacy["logical_control_retry_fraction"],
                "rate_semantics": "ENUMERATED_MASK_FREQUENCY_NOT_EVENT_RATE",
                "source_record_id": legacy["row_id"],
            }
        )
    csv_path = BASE / "MATRIX_P.csv"
    json_path = BASE / "MATRIX_P.json"
    schema_path = BASE / "MATRIX_P.schema.json"
    write_csv(csv_path, rows, P_FIELDS)
    write_json(
        json_path,
        {
            "schema_version": SCHEMA_VERSION,
            "matrix_symbol": "M_P",
            "row_count": len(rows),
            "records": rows,
        },
    )
    units = {
        "clock_hz": "Hz",
        "voltage_v": "V",
        "temperature_c": "degree_C",
        "observed_macro_area_um2": "um2",
        "diagnostic_tool_power_w": "W",
        "latency_s": "s",
        "throughput_services_per_s": "services_per_s",
    }
    schema = {
        "schema_version": SCHEMA_VERSION,
        "matrix_symbol": "M_P",
        "primary_key": ["record_id"],
        "description": "Physical/architectural observations only; no GREEN scalar or sustainability translation.",
        "fields": [
            field_schema(
                field,
                "number_or_empty" if field in units or field.endswith("_fraction") or field.endswith("_count") else "string_or_boolean",
                unit=units.get(field),
                nullable=field not in {"record_id", "design_id", "architecture_id", "technology_id"},
            )
            for field in P_FIELDS
        ],
    }
    write_json(schema_path, schema)
    return rows, [csv_path, json_path, schema_path]


def build_matrix_e(p_rows: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, object]], list[Path]]:
    experiment_path = LEGACY / "green_matrix_v2" / "GREEN_MATRIX_V2_RAW.csv"
    experiment_hash = sha256(experiment_path)
    records: list[dict[str, object]] = []

    specs = (
        ("observed_macro_area_um2", "um2", "E4", "DIAGNOSTIC", "POST_ROUTE_TOOL_ESTIMATE", "TOOL_ESTIMATE", "No matched independent characterization."),
        ("activity_coverage_fraction", "probability", "E3", "DIAGNOSTIC", "DERIVED_ACTIVITY_COVERAGE", "DERIVED", "Coverage is incomplete and is not workload energy."),
        ("diagnostic_tool_power_w", "W", "E4", "DIAGNOSTIC", "POST_ROUTE_TOOL_DIAGNOSTIC", "TOOL_ESTIMATE", "Diagnostic power is not activity-qualified access energy."),
        ("logical_pattern_count", "count", "E3", "LOGICAL_CONTROL", "EXACT_LOGICAL_ENUMERATION", "DERIVED", "Logical mask count is not a physical event rate."),
        ("logical_control_success_fraction", "probability", "E3", "LOGICAL_CONTROL", "EXACT_LOGICAL_ENUMERATION", "DERIVED", "Conditioned on enumerated masks; no P(f)."),
        ("logical_control_due_fraction", "probability", "E3", "LOGICAL_CONTROL", "EXACT_LOGICAL_ENUMERATION", "DERIVED", "Conditioned on enumerated masks; no P(f)."),
        ("logical_control_sdc_fraction", "probability", "E3", "LOGICAL_CONTROL", "EXACT_LOGICAL_ENUMERATION", "DERIVED", "Conditioned on enumerated masks; no P(f)."),
        ("logical_control_corrected_fraction", "probability", "E3", "LOGICAL_CONTROL", "EXACT_LOGICAL_ENUMERATION", "DERIVED", "Conditioned on enumerated masks; no P(f)."),
        ("logical_control_retry_fraction", "probability", "E3", "LOGICAL_CONTROL", "EXACT_LOGICAL_ENUMERATION", "DERIVED", "Conditioned on enumerated masks; no P(f)."),
        ("latency_s", "s", "E0", "UNQUALIFIED", "ABSENT", "UNAVAILABLE", "Latency is not measured for the declared service policy."),
        ("operational_energy_j", "J", "E0", "UNQUALIFIED", "ABSENT", "UNAVAILABLE", "Activity-qualified architecture energy is unavailable."),
        ("physical_fault_probability", "probability", "E0", "UNQUALIFIED", "ABSENT", "UNAVAILABLE", "Physical SBU/DBU/MBU event probabilities are unavailable."),
        ("physical_sdc_probability", "probability", "E0", "UNQUALIFIED", "ABSENT", "UNAVAILABLE", "Logical mask frequencies cannot establish physical SDC."),
        ("physical_due_probability", "probability", "E0", "UNQUALIFIED", "ABSENT", "UNAVAILABLE", "Logical mask frequencies cannot establish physical DUE."),
        ("manufacturing_carbon_kgco2e", "kgCO2e", "E0", "UNQUALIFIED", "ABSENT", "UNAVAILABLE", "Matched SKY130 manufacturing inventory is unavailable."),
    )
    for row in p_rows:
        implementation_hash = canonical_hash(dict(row))
        for name, unit, tier, result_class, source_type, qualification, reason in specs:
            value = row.get(name, "")
            source_ids = (
                "A10_LOGICAL_CONTROLS;A10_POSTROUTE_ACTIVITY_DIAGNOSTIC;"
                "SRC_SKYWATER_SKY130_PDK"
            )
            if name == "manufacturing_carbon_kgco2e":
                source_ids = "SRC_SKYWATER_SKY130_PDK"
            records.append(
                {
                    "quantity_id": f"ME|{row['record_id']}|{name}",
                    "entity_id": row["record_id"],
                    "quantity_name": name,
                    "value": value,
                    "unit": unit,
                    "source_id": source_ids,
                    "source_type": source_type,
                    "implementation_hash": implementation_hash,
                    "experiment_hash": experiment_hash,
                    "technology_id": row["technology_id"],
                    "pvt": "UNDECLARED",
                    "workload_id": row["workload_id"],
                    "measurement_model_boundary": "SB_MP_IMPLEMENTATION_ONLY" if tier != "E0" else "REQUIRED_BOUNDARY_UNAVAILABLE",
                    "evidence_tier": tier,
                    "evidence_kind": result_class,
                    "uncertainty_representation": "NOT_QUANTIFIED" if tier != "E0" else "MISSING",
                    "citation": str(experiment_path.relative_to(REPO)).replace("\\", "/"),
                    "date_version": GENERATION_DATE,
                    "qualification_status": qualification,
                    "blocking_reason": reason,
                }
            )
    csv_path = BASE / "MATRIX_E.csv"
    json_path = BASE / "MATRIX_E.json"
    schema_path = BASE / "MATRIX_E.schema.json"
    write_csv(csv_path, records, E_FIELDS)
    write_json(
        json_path,
        {
            "schema_version": SCHEMA_VERSION,
            "matrix_symbol": "M_E",
            "record_count": len(records),
            "records": records,
            "tier_warning": "Higher tier is not universally better; relevance and boundary match remain metric-specific.",
        },
    )
    write_json(
        schema_path,
        {
            "schema_version": SCHEMA_VERSION,
            "matrix_symbol": "M_E",
            "primary_key": ["quantity_id"],
            "foreign_key": {"entity_id": "M_P.record_id"},
            "fields": [
                field_schema(field, "string_or_number", nullable=field in {"value"})
                for field in E_FIELDS
            ],
        },
    )
    return records, [csv_path, json_path, schema_path]


def build_matrix_s(p_rows: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, object]], list[Path]]:
    designs = sorted({str(row["design_id"]) for row in p_rows})
    rows: list[dict[str, object]] = []
    for design in designs:
        rows.append(
            {
                "translation_id": f"MS|{design}|FAB_SKY130_UNAVAILABLE",
                "design_id": design,
                "technology_id": "SKY130",
                "fab_scenario_id": "FAB_SKY130_UNAVAILABLE",
                "manufacturing_grid_id": "",
                "use_grid_id": "",
                "lifetime_scenario_id": "UNDECLARED",
                "system_boundary_id": "SB_CSCI_MEMORY_SERVICE_CANDIDATE",
                "allocation_method": "NO_ALLOCATION_INSUFFICIENT_EVIDENCE",
                "scope1_kgco2e": "",
                "scope2_kgco2e": "",
                "upstream_declared_kgco2e": "",
                "mask_nre_kgco2e": "",
                "packaging_kgco2e": "",
                "operational_kgco2e": "",
                "lifecycle_kgco2e": "",
                "request_count": "",
                "correct_service_probability": "",
                "correct_service_count": "",
                "csci_kgco2e_per_correct_service": "",
                "csci_bit_kgco2e_per_correct_payload_bit": "",
                "result_class": "UNQUALIFIED",
                "qualification_status": "BLOCKED",
                "blocking_reasons": "SKY130_MANUFACTURING_CARBON_NOT_QUALIFIED;OPERATIONAL_ENERGY_NOT_QUALIFIED;PHYSICAL_SERVICE_PROBABILITY_NOT_QUALIFIED;LIFETIME_NOT_DECLARED",
            }
        )
    csv_path = BASE / "MATRIX_S.csv"
    json_path = BASE / "MATRIX_S.json"
    schema_path = BASE / "MATRIX_S.schema.json"
    write_csv(csv_path, rows, S_FIELDS)
    write_json(
        json_path,
        {
            "schema_version": SCHEMA_VERSION,
            "matrix_symbol": "M_S",
            "records": rows,
            "recomputation_contract": "M_S depends on M_P identifiers and scenario registries; scenario changes do not require RTL/PnR reruns.",
        },
    )
    write_json(
        schema_path,
        {
            "schema_version": SCHEMA_VERSION,
            "matrix_symbol": "M_S",
            "primary_key": ["translation_id"],
            "foreign_keys": {"design_id": "M_P.design_id", "system_boundary_id": "SYSTEM_BOUNDARIES.boundary_id"},
            "fields": [field_schema(field, "string_or_number_or_empty") for field in S_FIELDS],
        },
    )
    return rows, [csv_path, json_path, schema_path]


def build_view(
    p_rows: Sequence[Mapping[str, object]], s_rows: Sequence[Mapping[str, object]]
) -> list[Path]:
    sustainability = {str(row["design_id"]): row for row in s_rows}
    fields = (
        "record_id",
        "design_id",
        "architecture_id",
        "technology_id",
        "fault_environment_id",
        "interleaving_id",
        "workload_id",
        "service_policy_id",
        "fab_scenario_id",
        "lifetime_scenario_id",
        "observed_macro_area_um2",
        "logical_control_sdc_fraction",
        "logical_control_due_fraction",
        "physical_sdc_probability",
        "physical_due_probability",
        "operational_energy_j",
        "lifecycle_kgco2e",
        "csci_kgco2e_per_correct_service",
        "qualification_status",
        "blocking_reasons",
    )
    rows: list[dict[str, object]] = []
    for physical in p_rows:
        translation = sustainability[str(physical["design_id"])]
        rows.append(
            {
                "record_id": physical["record_id"],
                "design_id": physical["design_id"],
                "architecture_id": physical["architecture_id"],
                "technology_id": physical["technology_id"],
                "fault_environment_id": physical["fault_environment_id"],
                "interleaving_id": physical["interleaving_id"],
                "workload_id": physical["workload_id"],
                "service_policy_id": physical["service_policy_id"],
                "fab_scenario_id": translation["fab_scenario_id"],
                "lifetime_scenario_id": translation["lifetime_scenario_id"],
                "observed_macro_area_um2": physical["observed_macro_area_um2"],
                "logical_control_sdc_fraction": physical["logical_control_sdc_fraction"],
                "logical_control_due_fraction": physical["logical_control_due_fraction"],
                "physical_sdc_probability": "",
                "physical_due_probability": "",
                "operational_energy_j": "",
                "lifecycle_kgco2e": "",
                "csci_kgco2e_per_correct_service": "",
                "qualification_status": translation["qualification_status"],
                "blocking_reasons": translation["blocking_reasons"],
            }
        )
    csv_path = BASE / "GREEN_MATRIX_V3_VIEW.csv"
    json_path = BASE / "GREEN_MATRIX_V3_VIEW.json"
    schema_path = BASE / "GREEN_MATRIX_V3_VIEW.schema.json"
    write_csv(csv_path, rows, fields)
    write_json(
        json_path,
        {
            "schema_version": SCHEMA_VERSION,
            "derived": True,
            "source_matrices": ["M_P", "M_E", "M_S"],
            "conceptual_tensor": "G[A,N,F,I,W,P,G,L,M]",
            "records": rows,
        },
    )
    write_json(
        schema_path,
        {
            "schema_version": SCHEMA_VERSION,
            "derived": True,
            "fields": [field_schema(field, "string_or_number_or_empty") for field in fields],
        },
    )
    return [csv_path, json_path, schema_path]


def _record(
    quantity: str, tier: str, result_class: str, reason: str | None = None
) -> EvidenceRecord:
    return EvidenceRecord(
        quantity,
        EvidenceTier[tier],
        result_class,
        "SB_MP_IMPLEMENTATION_ONLY",
        blocking_reason=reason,
    )


def load_rules() -> list[QualificationRule]:
    result: list[QualificationRule] = []
    for item in config("qualification_rules.json")["rules"]:
        requirements = tuple(
            EvidenceRequirement(
                requirement["quantity"],
                EvidenceTier[requirement["minimum_tier"]],
                tuple(requirement["allowed_classes"]),
            )
            for requirement in item["requirements"]
        )
        result.append(
            QualificationRule(
                item["metric_id"], requirements, item["permits_parametric"]
            )
        )
    return result


def build_qualification_and_coverage(
    p_rows: Sequence[Mapping[str, object]]
) -> list[Path]:
    designs = sorted({str(row["design_id"]) for row in p_rows})
    assessments: list[dict[str, object]] = []
    for design in designs:
        records = {
            "area": _record("area", "E4", "DIAGNOSTIC"),
            "logical_outcome": _record("logical_outcome", "E3", "LOGICAL_CONTROL"),
            "operational_energy": _record("operational_energy", "E0", "UNQUALIFIED", "activity-qualified energy unavailable"),
            "latency": _record("latency", "E0", "UNQUALIFIED", "latency unavailable"),
            "physical_fault_probability": _record("physical_fault_probability", "E0", "UNQUALIFIED", "physical P(f) unavailable"),
            "physical_outcome_model": _record("physical_outcome_model", "E0", "UNQUALIFIED", "physical outcomes unavailable"),
            "lifecycle_carbon": _record("lifecycle_carbon", "E0", "UNQUALIFIED", "SKY130 and operational carbon unavailable"),
            "correct_service_probability": _record("correct_service_probability", "E0", "UNQUALIFIED", "physical service probability unavailable"),
            "service_count_lifetime": _record("service_count_lifetime", "E0", "UNQUALIFIED", "lifetime activity unavailable"),
            "matched_lifecycle_carbon": _record("matched_lifecycle_carbon", "E0", "UNQUALIFIED", "matched carbon unavailable"),
            "matched_correct_service": _record("matched_correct_service", "E0", "UNQUALIFIED", "matched service unavailable"),
        }
        for rule in load_rules():
            result = qualify(rule, records)
            assessments.append(
                {
                    "design_id": design,
                    "metric_id": rule.metric_id,
                    "status": result.status,
                    "reasons": ";".join(result.reasons),
                }
            )
    qualification_path = BASE / "evidence" / "QUALIFICATION_ASSESSMENT.json"
    write_json(
        qualification_path,
        {
            "schema_version": SCHEMA_VERSION,
            "assessments": assessments,
            "qualified_winner": None,
        },
    )

    coverage_rows: list[dict[str, object]] = []
    for design in designs:
        architecture = design.split("|", 1)[0]
        coverage_rows.append(
            {
                "design_id": design,
                "scenario": f"{architecture}/I0/SKY130",
                "area": "E4_DIAGNOSTIC",
                "operational_energy": "E0",
                "latency": "E0",
                "logical_outcomes": "E3_LOGICAL_CONTROL",
                "physical_SDC": "E0",
                "physical_DUE": "E0",
                "manufacturing_carbon": "E0",
                "lifecycle_carbon": "E0",
                "CSCI": "BLOCKED",
                "MRCC": "BLOCKED",
                "next_evidence": "physical event probabilities; activity-qualified energy/latency; matched SKY130 inventory; declared lifetime",
            }
        )
    coverage_fields = tuple(coverage_rows[0])
    coverage_csv = BASE / "EVIDENCE_COVERAGE.csv"
    coverage_json = BASE / "EVIDENCE_COVERAGE.json"
    coverage_schema = BASE / "EVIDENCE_COVERAGE.schema.json"
    write_csv(coverage_csv, coverage_rows, coverage_fields)
    write_json(
        coverage_json,
        {
            "schema_version": SCHEMA_VERSION,
            "records": coverage_rows,
            "interpretation": "Cells report evidence class, never an imputed value.",
        },
    )
    write_json(
        coverage_schema,
        {
            "schema_version": SCHEMA_VERSION,
            "fields": [field_schema(field, "string", nullable=False) for field in coverage_fields],
        },
    )
    return [qualification_path, coverage_csv, coverage_json, coverage_schema]


def build_partial_frontiers(p_rows: Sequence[Mapping[str, object]]) -> list[Path]:
    rows: list[dict[str, object]] = []
    for fault in sorted({str(row["fault_environment_id"]) for row in p_rows}):
        candidates = [row for row in p_rows if row["fault_environment_id"] == fault]
        objectives = [
            Objective("observed_macro_area_um2", "min"),
            Objective("logical_control_sdc_fraction", "min"),
            Objective("logical_control_due_fraction", "min"),
        ]
        numeric = [
            {
                "observed_macro_area_um2": float(row["observed_macro_area_um2"]),
                "logical_control_sdc_fraction": float(row["logical_control_sdc_fraction"]),
                "logical_control_due_fraction": float(row["logical_control_due_fraction"]),
            }
            for row in candidates
        ]
        front = set(exact_pareto_indices(numeric, objectives))
        for index, row in enumerate(candidates):
            rows.append(
                {
                    "analysis_id": "LOGICAL_CONTROL_AREA_DIAGNOSTIC",
                    "fault_environment_id": fault,
                    "record_id": row["record_id"],
                    "architecture_id": row["architecture_id"],
                    "observed_macro_area_um2": row["observed_macro_area_um2"],
                    "logical_control_sdc_fraction": row["logical_control_sdc_fraction"],
                    "logical_control_due_fraction": row["logical_control_due_fraction"],
                    "pareto_nondominated": index in front,
                    "result_class": "LOGICAL_CONTROL",
                    "selection_eligible": False,
                    "qualification_note": "Exact diagnostic frontier only; logical enumeration frequency is not P(f).",
                }
            )
    fields = tuple(rows[0])
    csv_path = BASE / "PARTIAL_FRONTIERS.csv"
    json_path = BASE / "PARTIAL_FRONTIERS.json"
    schema_path = BASE / "PARTIAL_FRONTIERS.schema.json"
    write_csv(csv_path, rows, fields)
    write_json(
        json_path,
        {
            "schema_version": SCHEMA_VERSION,
            "exact_enumeration": True,
            "NSGA_II_used": False,
            "records": rows,
            "blocked_frontiers": [
                {"frontier": "IMPLEMENTATION_FRONTIER", "reasons": ["OPERATIONAL_ENERGY_E0", "LATENCY_E0"]},
                {"frontier": "PHYSICAL_RELIABILITY_FRONTIER", "reasons": ["PHYSICAL_EVENT_PROBABILITY_E0", "OPERATIONAL_ENERGY_E0"]},
                {"frontier": "SUSTAINABILITY_FRONTIER", "reasons": ["LIFECYCLE_CARBON_E0", "PHYSICAL_RELIABILITY_E0", "LATENCY_E0"]},
                {"frontier": "INCREMENTAL_ECC_FRONTIER", "reasons": ["MATCHED_LIFECYCLE_CARBON_E0", "MATCHED_CORRECT_SERVICE_E0"]},
            ],
            "qualified_architecture_winner": None,
        },
    )
    write_json(
        schema_path,
        {
            "schema_version": SCHEMA_VERSION,
            "fields": [field_schema(field, "string_or_number_or_boolean") for field in fields],
        },
    )
    return [csv_path, json_path, schema_path]


def build_causal_graph() -> Path:
    nodes = [
        ("technology", "scenario"),
        ("process_route", "model_structure"),
        ("process_steps", "inventory"),
        ("fab_energy", "physical_quantity"),
        ("process_gases", "physical_inventory"),
        ("manufacturing_grid_ci", "scenario_parameter"),
        ("wafer_carbon", "derived_quantity"),
        ("die_area", "physical_observation"),
        ("gross_dies", "derived_quantity"),
        ("yield", "modelled_or_measured_parameter"),
        ("good_die_carbon", "derived_quantity"),
        ("ecc_architecture", "design_variable"),
        ("interleaving", "design_variable"),
        ("implementation_cost", "physical_observation"),
        ("physical_mapping", "physical_observation"),
        ("fault_topology_distribution", "physical_environment"),
        ("conditional_outcome", "logical_or_physical_model"),
        ("sdc_due", "reliability_outcome"),
        ("workload", "scenario"),
        ("service_policy", "scenario"),
        ("activity", "physical_observation"),
        ("operational_energy", "derived_quantity"),
        ("use_grid_ci", "scenario_parameter"),
        ("operational_carbon", "derived_quantity"),
        ("lifecycle_carbon", "derived_quantity"),
        ("correct_service_probability", "reliability_outcome"),
        ("correct_services", "functional_output"),
        ("csci", "decision_metric"),
    ]
    edges = [
        ("technology", "process_route"),
        ("process_route", "process_steps"),
        ("process_steps", "fab_energy"),
        ("process_steps", "process_gases"),
        ("fab_energy", "wafer_carbon"),
        ("manufacturing_grid_ci", "wafer_carbon"),
        ("process_gases", "wafer_carbon"),
        ("die_area", "gross_dies"),
        ("die_area", "yield"),
        ("gross_dies", "good_die_carbon"),
        ("yield", "good_die_carbon"),
        ("wafer_carbon", "good_die_carbon"),
        ("ecc_architecture", "implementation_cost"),
        ("interleaving", "implementation_cost"),
        ("ecc_architecture", "physical_mapping"),
        ("interleaving", "physical_mapping"),
        ("physical_mapping", "conditional_outcome"),
        ("fault_topology_distribution", "sdc_due"),
        ("conditional_outcome", "sdc_due"),
        ("workload", "activity"),
        ("service_policy", "activity"),
        ("implementation_cost", "activity"),
        ("activity", "operational_energy"),
        ("operational_energy", "operational_carbon"),
        ("use_grid_ci", "operational_carbon"),
        ("good_die_carbon", "lifecycle_carbon"),
        ("operational_carbon", "lifecycle_carbon"),
        ("sdc_due", "correct_service_probability"),
        ("workload", "correct_services"),
        ("service_policy", "correct_services"),
        ("correct_service_probability", "correct_services"),
        ("lifecycle_carbon", "csci"),
        ("correct_services", "csci"),
    ]
    path = BASE / "CAUSAL_GRAPH.json"
    write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "nodes": [{"id": node, "kind": kind} for node, kind in nodes],
            "edges": [{"from": left, "to": right} for left, right in edges],
            "double_count_guards": [
                "patterning_scope2_is_subset_not_addend",
                "correction_energy_either_in_read_or_incremental_not_both",
                "mask_NRE_amortized_once_across_production",
                "base_memory_and_incremental_ECC_allocations_are_disjoint",
            ],
        },
    )
    return path


def build_validations() -> list[Path]:
    act = {
        "schema_version": SCHEMA_VERSION,
        "matched_synthetic_vector": {
            "area_cm2": 0.5,
            "fab_ci_kgco2e_per_kwh": 0.4,
            "energy_per_area_kwh_per_cm2": 2.0,
            "gas_per_area_kgco2e_per_cm2": 0.3,
            "materials_per_area_kgco2e_per_cm2": 0.2,
            "yield_fraction": 0.8,
            "expected_kgco2e": 0.8125,
        },
        "algebra": "Area*(CI*EPA+GPA+MPA)/Yield",
        "classification": "EXACT_REPRODUCTION",
        "boundary_id": "SB_ACT_MATCHED_SYNTHETIC_VALIDATION",
        "ACT_defaults_adopted": False,
        "ACT3_defaults_adopted": False,
        "unmatched_comparison": "NOT_COMPARABLE",
    }
    act_path = BASE / "validation" / "ACT_ACT3_CROSS_VALIDATION.json"
    write_json(act_path, act)
    imec = {
        "schema_version": SCHEMA_VERSION,
        "alignment_label": "IMEC_PUBLIC_EVIDENCE_ALIGNED",
        "comparisons": [
            {"claim": "fab energy rises with advanced process-route complexity in the cited N28-to-A14 study", "classification": "TREND_REPRODUCTION", "source_id": "SRC_IMEC_IEDM_2023"},
            {"claim": "Scope 2 changes linearly with electricity CI for fixed energy", "classification": "EXACT_REPRODUCTION", "source_id": "SRC_IMEC_SSTS_2022"},
            {"claim": "abatement reduces direct process-gas emissions", "classification": "EXACT_REPRODUCTION", "source_id": "SRC_IMEC_SSTS_2022"},
            {"claim": "EUV route effects depend on eliminated deposition/etch/clean steps, not scanner power alone", "classification": "QUALITATIVE_ONLY", "source_id": "SRC_IMEC_IEDM_2023;SRC_IMEC_LITHO_2024"},
            {"claim": "absolute SKY130 wafer carbon from imec advanced-node values", "classification": "NOT_COMPARABLE", "source_id": "SRC_IMEC_IEDM_2023;SRC_SKYWATER_SKY130_PDK"},
        ],
        "certified_or_compliant_claim": False,
    }
    imec_path = BASE / "validation" / "IMEC_CROSS_VALIDATION.json"
    write_json(imec_path, imec)
    legacy = {
        "schema_version": SCHEMA_VERSION,
        "legacy_metrics": ["ESII", "NESII", "legacy GREEN Score", "GSE", "GCI"],
        "classification": "LEGACY_OR_COMPARISON_METRIC",
        "candidate_set_dependence_counterexample": {
            "weighted_minmax_preferences": {"cost": 0.6, "reliability": 0.4},
            "candidates_initial": {"A": {"cost": 2, "reliability": 8}, "B": {"cost": 3, "reliability": 10}},
            "initial_scores": {"A": 0.6, "B": 0.4},
            "candidate_added": {"C": {"cost": 100, "reliability": 9}},
            "scores_after_addition": {"A": 0.6, "B": 0.9938775510204082, "C": 0.2},
            "rank_reversal": "A_over_B becomes B_over_A without changing A or B",
        },
        "v3_response": "fixed physical quantities, external constraints, fixed baselines, and exact Pareto analysis",
        "epsilon_floors": False,
    }
    legacy_path = BASE / "validation" / "LEGACY_COMPARISON_TESTS.json"
    write_json(legacy_path, legacy)
    adversarial = {
        "schema_version": SCHEMA_VERSION,
        "properties": [
            "dimensional_consistency",
            "positivity_of_inputs",
            "zero_denominator_is_undefined",
            "zero_carbon_is_zero_when_service_positive",
            "zero_correct_service_is_undefined",
            "lifetime_scaling",
            "zero_operational_energy",
            "embodied_dominated_regime",
            "operational_dominated_regime",
            "grid_CI_scaling",
            "reliability_monotonicity_at_fixed_carbon",
            "carbon_monotonicity_at_fixed_service",
            "candidate_set_independence",
            "payload_scaling",
            "explicit_unit_conversion",
            "fixed_baseline_dependence_of_MRCC",
            "access_vs_bit_rank_reversal_possible",
            "missing_data_remains_missing",
            "uncertainty_status_propagation",
            "asymptotic_embodied_amortization",
        ],
        "implementation_test_file": "tests/test_green_matrix_v3_core.py",
        "epsilon_floors": False,
    }
    adversarial_path = BASE / "validation" / "METRIC_ADVERSARIAL_AUDIT.json"
    write_json(adversarial_path, adversarial)
    return [act_path, imec_path, legacy_path, adversarial_path]


def build_support_artifacts() -> list[Path]:
    unit_path = BASE / "UNIT_SYSTEM.json"
    write_json(
        unit_path,
        {
            "schema_version": SCHEMA_VERSION,
            "canonical_units": {"energy": "J", "power": "W", "time": "s", "carbon": "kgCO2e", "area": "cm2", "probability": "probability", "failure_rate": "failures_per_hour"},
            "explicit_conversions": {"kWh_to_J": 3600000, "kgCO2e_to_gCO2e": 1000, "cm2_to_mm2": 100, "mm2_to_um2": 1000000, "ppm_to_probability": 0.000001, "FIT_to_failures_per_hour": 1e-9},
            "silent_coercion_allowed": False,
        },
    )
    voi_path = BASE / "uncertainty" / "VALUE_OF_INFORMATION.json"
    write_json(
        voi_path,
        {
            "schema_version": SCHEMA_VERSION,
            "status": "FOUNDATION_ONLY_NO_DECISION_DISTRIBUTION",
            "priority_measurement": "CALIBRATED_PHYSICAL_SBU_DBU_MBU_TOPOLOGY_AND_RATE_DATA",
            "reason": "It converts existing conditional logical controls into physical SDC/DUE and enables hard feasibility; no sustainability winner is admissible without this gate.",
            "other_high_value_measurements": ["matched post-route workload energy and latency", "matched SKY130 process-step manufacturing inventory", "physical interleaver PPA and mapping"],
        },
    )
    figures_path = BASE / "figures" / "FIGURE_PLAN.json"
    figures = [
        "framework architecture",
        "causal graph",
        "M_P / M_E / M_S relationship",
        "manufacturing-carbon decomposition",
        "yield sensitivity",
        "carbon-vs-grid scenario",
        "embodied/operational crossover",
        "CSCI vs reliability",
        "MRCC vs reliability improvement",
        "energy-latency Pareto",
        "reliability-energy Pareto",
        "sustainability Pareto",
        "interleaving topology",
        "uncertainty sensitivity",
        "evidence-coverage heatmap",
    ]
    write_json(
        figures_path,
        {
            "schema_version": SCHEMA_VERSION,
            "figures": [
                {"figure_id": f"F{index:02d}", "title": title, "status": "SUPPORTED_AS_STRUCTURE_ONLY" if index in {1, 2, 3, 15} else "BLOCKED_BY_CURRENT_EVIDENCE"}
                for index, title in enumerate(figures, start=1)
            ],
            "visual_claim_rule": "Every plotted quantity must carry evidence classification; unqualified values are never shown as measured truth.",
        },
    )
    data_model_path = BASE / "matrix" / "DATA_MODEL.json"
    write_json(
        data_model_path,
        {
            "schema_version": SCHEMA_VERSION,
            "conceptual_tensor": "G[A,N,F,I,W,P,G,L,M]",
            "implementation": "normalized sparse CSV+JSON datasets",
            "relations": {"M_P": "record_id/design_id", "M_E": "entity_id -> M_P.record_id", "M_S": "design_id -> M_P.design_id"},
            "dense_array_required": False,
        },
    )
    regression_path = BASE / "REGRESSION_STATUS.json"
    if not regression_path.exists():
        write_json(
            regression_path,
            {
                "schema_version": SCHEMA_VERSION,
                "status": "PENDING",
                "required_commands": {"make": "PENDING", "make test": "PENDING", "python3 -m pytest -q": "PENDING"},
            },
        )
    return [unit_path, voi_path, figures_path, data_model_path, regression_path]


def build_provenance() -> list[Path]:
    v2_tree = git_output(
        "rev-parse",
        f"{BASELINE_COMMIT}:campaigns/iscas_sustainability_extension/green_refoundation_node_aware_carbon",
    )
    v2_manifest = LEGACY / "integrity" / "FINAL_ARTIFACT_HASHES.json"
    base_manifest = LEGACY / "BASELINE_MANIFEST.json"
    protected = load_json(base_manifest).get("protected_tree_fingerprints", {})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "campaign": "green_matrix_v3_imec_aligned",
        "starting_scientific_baseline": BASELINE_COMMIT,
        "baseline_full_commit": git_output("rev-parse", BASELINE_COMMIT),
        "v2_git_tree_sha1": v2_tree,
        "v2_final_artifact_manifest_sha256": sha256(v2_manifest),
        "v2_baseline_manifest_sha256": sha256(base_manifest),
        "historical_protected_tree_fingerprints": protected,
        "immutability_rule": "Historical GREEN v2, GSE/GCI, legacy metrics, Attempt09, Attempt10, DATE results, and prior artifacts are read-only provenance.",
        "files_modified_in_historical_tree": [],
    }
    json_path = BASE / "integrity" / "PROVENANCE_FREEZE.json"
    write_json(json_path, payload)
    audit_path = BASE / "integrity" / "LEGACY_AUDIT.json"
    write_json(
        audit_path,
        {
            "schema_version": SCHEMA_VERSION,
            "reused_components": ["source registry provenance", "exact logical-control rows", "observed macro area", "diagnostic activity coverage and power labels", "ACT algebra", "yield equations"],
            "not_reused_as_primary_model": ["flat v2 matrix", "GSE/GCI primary selection", "legacy GREEN score", "candidate normalization", "NSGA-II"],
            "historical_interpretation_changed": False,
        },
    )
    return [json_path, audit_path]


def build_modular_manifests() -> list[Path]:
    roles = {
        "physical": "physical and implementation observations referenced by M_P",
        "reliability": "logical controls and future calibrated physical outcome datasets",
        "energy": "activity-qualified energy datasets; current diagnostic power is not promoted",
        "latency": "service-policy-specific latency and throughput datasets",
        "interleaving": "physical bit-to-codeword mappings and separately measured costs",
        "manufacturing": "process routes, steps, equipment/recipe inventories, yield, and good-die accounting",
        "carbon": "scenario translations and lifecycle terms",
        "workloads": "read/write/activity distributions",
        "service_policy": "scrub, retry, correction-credit, timeout, and SLA semantics",
        "evidence": "metric-specific provenance and qualification",
        "uncertainty": "epistemic/aleatory representations and future value of information",
        "metrics": "CSCI, CSCI_bit, MRCC, baseline ratios, and legacy adapters",
        "pareto": "exact deterministic fronts and blocked-analysis explanations",
        "validation": "imec trend/boundary and ACT/ACT3 matched-assumption cross-checks",
        "sources": "external source registry and boundary metadata",
        "matrix": "normalized M_P/M_E/M_S relationships and derived views",
        "figures": "evidence-qualified figure plan and data status",
        "integrity": "provenance freeze, regression, and artifact hashes",
    }
    outputs: list[Path] = []
    for directory in MODULAR_DIRECTORIES:
        path = BASE / directory / "MODULE_MANIFEST.json"
        write_json(
            path,
            {
                "schema_version": SCHEMA_VERSION,
                "module": directory,
                "role": roles[directory],
                "configuration_driven": True,
                "missing_values_are_zero": False,
            },
        )
        outputs.append(path)
    return outputs


def artifact_paths() -> list[Path]:
    paths: list[Path] = []
    for path in BASE.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(BASE)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if relative.as_posix() == "FINAL_ARTIFACT_HASHES.json":
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(BASE).as_posix())


def build_hashes() -> Path:
    rows = [
        {
            "path": path.relative_to(BASE).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in artifact_paths()
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "hash_algorithm": "SHA-256",
        "artifact_count": len(rows),
        "artifacts": rows,
        "self_excluded": True,
    }
    path = BASE / "FINAL_ARTIFACT_HASHES.json"
    write_json(path, result)
    return path


def build_all() -> None:
    for directory in MODULAR_DIRECTORIES:
        (BASE / directory).mkdir(parents=True, exist_ok=True)
    build_registries()
    build_source_registry()
    p_rows, _ = build_matrix_p()
    build_matrix_e(p_rows)
    s_rows, _ = build_matrix_s(p_rows)
    build_view(p_rows, s_rows)
    build_qualification_and_coverage(p_rows)
    build_partial_frontiers(p_rows)
    build_causal_graph()
    build_validations()
    build_support_artifacts()
    build_provenance()
    build_modular_manifests()
    build_hashes()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hash-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.hash_only:
        build_hashes()
    else:
        build_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
