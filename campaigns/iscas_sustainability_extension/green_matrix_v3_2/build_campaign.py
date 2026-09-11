"""Build deterministic GREEN Matrix v3.2 evidence-aware artifacts.

The builder is an additive adapter over the frozen v3.1 population. It runs no
physical tool, performs no literature transfer, and promotes no inherited tier.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Mapping

from .core import (
    ActivityCompleteness,
    GreenVector,
    Objective,
    decision_admissibility,
    exact_pareto_ids,
    qualified_pareto_or_blocked,
    qualify_e5_activity,
    scenario_space_nondominance_fraction,
)


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
PARENT = BASE.parent / "green_matrix_v3_physical_population"
DATA = BASE / "data"
SCHEMA_VERSION = "3.2.0"
PARENT_COMMIT = "1f6bcd009e7a05ebcde35a3272161a9a81ec7bf7"
FOUNDATION_COMMIT = "affc8145b184803189dac36391cb486f00e7b4f8"
GENERATED_AT = "2026-09-08"
ARCHITECTURES = ("U0", "E0")
SEEDS = (11, 13, 17, 19, 23)
BASE_SCENARIO = "S_BASE_ABSOLUTE_SKY130"
DECISION_BOUNDARY = "SB_V3_2_MATCHED_U0_E0_SERVICE_LIFECYCLE_DECISION"
CONDITIONAL_BOUNDARY = "LOGICAL_MASK_CLASS_CONDITIONAL_RESPONSE_NOT_PHYSICAL_OCCURRENCE"

SOURCE_FILES = (
    "MATRIX_E_V3_1.json",
    "MATRIX_P_V3_1.json",
    "MATRIX_S_V3_1.json",
    "POST_ROUTE_ACTIVITY.json",
    "INTERLEAVER_PHYSICAL_RESULTS.json",
    "PHYSICAL_FAULT_TOPOLOGY.json",
    "LITERATURE_FAULT_EVIDENCE.json",
    "SERVICE_METRICS.json",
    "FROZEN_FOUNDATION_MANIFEST.json",
)

# v3.2 was sealed against CRLF-materialized v3.1 sources. Git stores the same
# scientific text with LF, so bind both representations explicitly rather than
# silently changing the frozen provenance fields.
PARENT_HASH_BINDINGS = {
    "FROZEN_FOUNDATION_MANIFEST.json": (
        "b7051cfa95f134c14987f2182377f2c34d8b0ea03a8eb845be6ce8c6f8402575",
        "5a5dda39b9674c34bd883a56877c13dba0378bd840ae8efdac32efa00e769687",
    ),
    "INTERLEAVER_PHYSICAL_RESULTS.json": (
        "0aabd9a176d3e0637c11b4829de8402099f9ddbdea7b052e9c565500cd53d148",
        "af9b2551dc2ca4feadd375b1f4b0406e425149423e2f089ec141575ad0fed6ba",
    ),
    "LITERATURE_FAULT_EVIDENCE.json": (
        "af61a21ae046e89645d24d951d3fb350644b1226ff2f7768d5218ac0c6e9f6a7",
        "244770ccee5d1006eeefabcd8b0b3cd7316ede09913b4d31255861c63734ded2",
    ),
    "MATRIX_E_V3_1.json": (
        "be77fd6b960b64bcaf7f3ca83f80b21612eb141b3f9cd7cde647ea0c1cc5627a",
        "d08d24a915a18d3c3fa49462b9f21c948f0c6ef5318201c0de0c3d7f074771c7",
    ),
    "MATRIX_P_V3_1.json": (
        "dfb284e45c55df60bf1e20db0741f2c17de8428e2e140491f725a8a59ec02ee2",
        "c5363eb42d1084a92c45b240f9808fd58444c1bbc860a19dadb0d3d7c02d7f95",
    ),
    "MATRIX_S_V3_1.json": (
        "b46f7cbceb50158ac236f44131fa3a1e5afc94d882558c69c802c563e57f5995",
        "af6e1c1c20654c279c62568966fda13577b233b69b3ec7d815082f51aa05847e",
    ),
    "PHYSICAL_FAULT_TOPOLOGY.json": (
        "d6675c1c53baed466c2ede8042674e8713e7972a817a516a7807f6e9157742c1",
        "b65eef06176cce309c6878fa61e2efe38f091fa2943b521963c306db28cfc614",
    ),
    "POST_ROUTE_ACTIVITY.json": (
        "9a4557775c6fd133b9789cfec40449aaf0ee93f8f2a9351d893c1ce04517e88e",
        "0928aa898d85cb02af26ac24375b3335d6cb6138440d2d3b20bca142adc90ad0",
    ),
    "SERVICE_METRICS.json": (
        "476e3aa4852febbd99ce81986ff93b5022fc0b1223228586120d86733ae8ca18",
        "93a45f45b160580b858434b6641ab48d24778429759dfd8ae9067ee66b78b120",
    ),
}


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parent_sha(path: Path) -> str:
    binding = PARENT_HASH_BINDINGS.get(path.name)
    if binding is None:
        return _sha(path)
    payload = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    canonical = hashlib.sha256(payload).hexdigest()
    return binding[1] if canonical == binding[0] else _sha(path)


def _record_sha(record: Mapping[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\r\n",
    )


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\r\n")


def _source_hashes() -> dict[str, str]:
    return {
        f"campaigns/iscas_sustainability_extension/green_matrix_v3_physical_population/{name}": _parent_sha(
            PARENT / name
        )
        for name in SOURCE_FILES
    }


def _reproducibility_hashes() -> dict[str, Any]:
    physical = _load(PARENT / "MATRIX_P_V3_1.json")
    rows = [
        row
        for row in physical["records"]
        if row.get("record_origin") == "V3_1_PHYSICAL_POPULATION"
        and row.get("architecture_id") in ARCHITECTURES
    ]
    return {
        "architecture_identifiers": list(ARCHITECTURES),
        "seed_identifiers": list(SEEDS),
        "implementation_hashes": sorted({row["implementation_hash"] for row in rows}),
        "netlist_hashes": sorted({row["netlist_hash"] for row in rows}),
        "configuration_hashes": sorted({row["physical_configuration_hash"] for row in rows}),
        "timing_constraint_hashes": sorted({row["timing_constraint_hash"] for row in rows}),
        "workload_hashes": sorted({row["workload_hash"] for row in rows if row.get("workload_hash")}),
        "activity_hashes": sorted(
            {row["activity_file_hash"] for row in rows if row.get("activity_file_hash")}
        ),
    }


def _envelope(artifact_type: str, campaign_commit: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "campaign_commit": campaign_commit,
        "parent_campaign_commit": PARENT_COMMIT,
        "foundation_commit": FOUNDATION_COMMIT,
        "generated_at": GENERATED_AT,
        "generator": "green_matrix_v3_2.build_campaign/3.2.0",
        "source_artifact_hashes": _source_hashes(),
        "reproducibility": _reproducibility_hashes(),
    }


def _architecture_from_parent(record: Mapping[str, Any]) -> str:
    architecture = record.get("architecture_id")
    if architecture:
        return str(architecture)
    entity = str(record.get("entity_id", ""))
    for candidate in ("U0", "E0", "E1"):
        if f"|{candidate}|" in entity:
            return candidate
    return "CROSS_ARCHITECTURE"


def _parent_semantic_status(record: Mapping[str, Any]) -> str:
    tier = str(record.get("evidence_tier", "E0"))
    kind = str(record.get("evidence_kind", "")).upper()
    value = record.get("value")
    if tier == "E0" or value in (None, "") or kind in {"UNAVAILABLE", "BLOCKED"}:
        return "STRUCTURALLY_MISSING"
    if "LITERATURE" in kind or "TECHNOLOGY_MISMATCH" in kind:
        return "LITERATURE_NATIVE"
    if tier == "E4" or kind in {"DIAGNOSTIC", "POST_ROUTE_ESTIMATE"}:
        return "DIAGNOSTIC"
    if kind in {"ANALYTICAL", "LOGICAL_CONTROL"}:
        return "ANALYTICAL"
    if "MEASURED" in kind:
        return "MEASURED"
    return "DERIVED"


def _parent_uncertainty(record: Mapping[str, Any], semantic: str) -> dict[str, Any]:
    detail = record.get("uncertainty_representation", "NOT_DECLARED_IN_PARENT")
    if semantic == "STRUCTURALLY_MISSING":
        form = "structurally_missing"
    elif semantic == "LITERATURE_NATIVE":
        form = "literature_native"
    elif semantic == "DIAGNOSTIC":
        form = "diagnostic"
    elif "FIVE_IMPLEMENTATION_SEEDS" in str(detail):
        form = "measured_distribution"
    elif semantic in {"ANALYTICAL", "DERIVED"}:
        form = "exact" if "DETERMINISTIC" in str(detail) else "unknown"
    else:
        form = "unknown"
    return {"form": form, "detail": detail}


def _adapt_parent_evidence(parent_records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Create a v3.2 view without modifying or upgrading any v3.1 record."""

    rows: list[dict[str, Any]] = []
    for parent in parent_records:
        semantic = _parent_semantic_status(parent)
        parent_id = str(parent.get("quantity_id", parent.get("record_id", "UNNAMED")))
        blocking = parent.get("blocking_reason", "")
        forbidden = ["EVIDENCE_TIER_PROMOTION", "BOUNDARY_EXPANSION"]
        if semantic in {"STRUCTURALLY_MISSING", "LITERATURE_NATIVE", "DIAGNOSTIC"}:
            forbidden.extend(
                ["ABSOLUTE_PHYSICAL_RATE", "QUALIFIED_LIFECYCLE_DECISION", "GLOBAL_WINNER"]
            )
        rows.append(
            {
                "record_id": f"V31::{parent_id}",
                "metric_identifier": str(parent.get("quantity_name", parent_id)),
                "architecture": _architecture_from_parent(parent),
                "scenario": str(parent.get("workload_id") or "V3_1_NATIVE_BOUNDARY"),
                "value": None if parent.get("value") in (None, "") else parent.get("value"),
                "units": str(parent.get("unit") or "declared_in_parent_record"),
                "uncertainty": _parent_uncertainty(parent, semantic),
                "evidence_tier": str(parent.get("evidence_tier", "E0")),
                "evidence_source": {
                    "id": parent.get("source_id", "V3_1_PARENT"),
                    "type": parent.get("source_type", parent.get("evidence_kind", "PARENT_RECORD")),
                    "citation": parent.get("citation", "v3.1 evidence matrix"),
                },
                "measurement_boundary": str(
                    parent.get("measurement_model_boundary") or "V3_1_PARENT_BOUNDARY"
                ),
                "provenance": {
                    "parent_record_id": parent_id,
                    "parent_record_sha256": _record_sha(parent),
                    "implementation_hash": parent.get("implementation_hash", ""),
                    "experiment_hash": parent.get("experiment_hash", ""),
                    "netlist_hash": parent.get("netlist_hash", ""),
                    "configuration_hash": parent.get("physical_configuration_hash", ""),
                    "constraint_hash": parent.get("timing_constraint_hash", ""),
                },
                "technology_process": {
                    "technology": parent.get("technology_id", "UNDECLARED"),
                    "process": parent.get("physical_configuration", "PARENT_DECLARED"),
                },
                "pvt": parent.get("pvt", "UNDECLARED"),
                "workload_activity": {
                    "workload_id": parent.get("workload_id", "UNDECLARED"),
                    "workload_hash": parent.get("workload_hash", ""),
                    "activity_hash": parent.get("activity_file_hash", ""),
                },
                "semantic_status": semantic,
                "qualification_status": str(
                    parent.get("qualification_status", "PARENT_STATUS_UNDECLARED")
                ),
                "blocking_reason": blocking,
                "permitted_downstream_uses": ["ONLY_AS_DECLARED_BY_FROZEN_V3_1"],
                "forbidden_downstream_uses": forbidden,
                "derived_from": [],
                "compatibility": {
                    "preserved_parent_boundary": True,
                    "v3_2_decision_compatibility": "REQUIRES_EXPLICIT_RULE_EVALUATION",
                },
                "record_origin": "FROZEN_V3_1_ADAPTER_VIEW",
            }
        )
    return rows


def _new_evidence_record(
    *,
    record_id: str,
    metric: str,
    architecture: str,
    scenario: str,
    value: Any,
    units: str,
    uncertainty: Mapping[str, Any],
    tier: str,
    semantic_status: str,
    qualification_status: str,
    boundary: str,
    source: Mapping[str, Any],
    derived_from: Iterable[str] = (),
    blocking_reason: Any = "",
    permitted: Iterable[str] = (),
    forbidden: Iterable[str] = (),
    compatibility: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
    workload_activity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "metric_identifier": metric,
        "architecture": architecture,
        "scenario": scenario,
        "value": value,
        "units": units,
        "uncertainty": dict(uncertainty),
        "evidence_tier": tier,
        "evidence_source": dict(source),
        "measurement_boundary": boundary,
        "provenance": dict(provenance or {}),
        "technology_process": {
            "technology": "SKY130HD_WITH_SRAM22_RESEARCH_MACROS",
            "process": "ORFS_ATTEMPT09_UPSTREAM_ORIGINAL",
        },
        "pvt": "TT/25C/1.8V" if tier in {"E4", "E5"} else "LOGICAL_MODEL",
        "workload_activity": dict(
            workload_activity
            or {"workload_id": "NOT_APPLICABLE", "workload_hash": "", "activity_hash": ""}
        ),
        "semantic_status": semantic_status,
        "qualification_status": qualification_status,
        "blocking_reason": blocking_reason,
        "permitted_downstream_uses": list(permitted),
        "forbidden_downstream_uses": list(forbidden),
        "derived_from": list(derived_from),
        "compatibility": dict(compatibility or {}),
        "record_origin": "V3_2_EVIDENCE_AWARE_DECISION",
    }


PHYSICAL_SUMMARY_METRICS = (
    ("routed_total_area_um2", "um2"),
    ("wirelength_um", "um"),
    ("via_count", "count"),
    ("power_total_vectorless_w", "W"),
    ("setup_wns_ns", "ns"),
    ("hold_wns_ns", "ns"),
)


def _physical_population(parent_p: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in parent_p["records"]
        if row.get("record_origin") == "V3_1_PHYSICAL_POPULATION"
        and row.get("architecture_id") in ARCHITECTURES
    ]
    rows.sort(key=lambda row: (ARCHITECTURES.index(row["architecture_id"]), int(row["seed"])))
    expected = [(architecture, seed) for architecture in ARCHITECTURES for seed in SEEDS]
    observed = [(row["architecture_id"], int(row["seed"])) for row in rows]
    if observed != expected:
        raise RuntimeError("frozen v3.1 matched U0/E0 five-seed population is incomplete")
    return rows


def _physical_summary_evidence(
    physical_population: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        population = [row for row in physical_population if row["architecture_id"] == architecture]
        for metric, units in PHYSICAL_SUMMARY_METRICS:
            values = [float(row[metric]) for row in population]
            parents = [
                f"V31::ME31|MP31_{architecture}_UPSTREAM_ORIGINAL_seed{seed}_I0|{metric}"
                for seed in SEEDS
            ]
            rows.append(
                _new_evidence_record(
                    record_id=f"ME32|{architecture}|I0|FIVE_SEED_MEAN|{metric}",
                    metric=f"five_seed_mean_{metric}",
                    architecture=architecture,
                    scenario=BASE_SCENARIO,
                    value=fmean(values),
                    units=units,
                    uncertainty={
                        "form": "diagnostic",
                        "detail": {"sample_count": 5, "minimum": min(values), "maximum": max(values)},
                    },
                    tier="E4",
                    semantic_status="DIAGNOSTIC",
                    qualification_status="DIAGNOSTIC_FIVE_SEED_POST_ROUTE_SUMMARY",
                    boundary="SB_V3_1_MATCHED_U0_E0_IMPLEMENTATION_AND_SERVICE",
                    source={"id": "V3_1_MATCHED_FIVE_SEED_POPULATION", "type": "DERIVED"},
                    derived_from=parents,
                    blocking_reason="post-route tool estimate with inherited residual SRAM transition diagnostics",
                    permitted=("DIAGNOSTIC_IMPLEMENTATION_COMPARISON", "CONDITIONAL_SCENARIO_ANALYSIS"),
                    forbidden=("SILICON_SIGNOFF", "LIFECYCLE_CLAIM", "GLOBAL_WINNER"),
                    compatibility={
                        "technology": True,
                        "process": True,
                        "pvt": True,
                        "workload": metric != "power_total_vectorless_w",
                        "activity": False if metric == "power_total_vectorless_w" else "NOT_APPLICABLE",
                        "architecture": True,
                    },
                    provenance={"seed_identifiers": list(SEEDS)},
                )
            )
    return rows


TOPOLOGY_MAP = {
    "SBU_ALL_COORDINATES": "LOGICAL_SBU_ANY_BIT",
    "DBU_ALL_PAIRS": "LOGICAL_DBU_ANY_PAIR",
    "LOGICAL_CONSECUTIVE_3": "LOGICAL_CONSECUTIVE_MBU_3",
    "LOGICAL_CONSECUTIVE_4": "LOGICAL_CONSECUTIVE_MBU_4",
}


def _conditional_rows(parent_p: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_rows = [
        row
        for row in parent_p["records"]
        if row.get("record_origin") == "V3_FOUNDATION"
        and row.get("architecture_id") in ARCHITECTURES
        and row.get("fault_environment_id") in TOPOLOGY_MAP
        and str(row["record_id"]).endswith("|none")
    ]
    source_rows.sort(
        key=lambda row: (
            ARCHITECTURES.index(row["architecture_id"]),
            list(TOPOLOGY_MAP).index(row["fault_environment_id"]),
        )
    )
    evidence: list[dict[str, Any]] = []
    surfaces: list[dict[str, Any]] = []
    metric_map = {
        "corrected": "logical_control_corrected_fraction",
        "detected": "logical_control_due_fraction",
        "sdc": "logical_control_sdc_fraction",
        "due": "logical_control_due_fraction",
    }
    for row in source_rows:
        architecture = row["architecture_id"]
        topology = TOPOLOGY_MAP[row["fault_environment_id"]]
        probabilities: dict[str, float] = {}
        refs: dict[str, str] = {}
        for outcome, parent_metric in metric_map.items():
            value = float(row[parent_metric])
            record_id = f"ME32|{architecture}|{topology}|conditional_{outcome}_probability"
            parent_id = f"V31::ME|{row['record_id']}|{parent_metric}"
            evidence.append(
                _new_evidence_record(
                    record_id=record_id,
                    metric=f"conditional_{outcome}_probability",
                    architecture=architecture,
                    scenario=topology,
                    value=value,
                    units="probability",
                    uncertainty={
                        "form": "conditional",
                        "detail": {
                            "enumeration": "EXACT",
                            "logical_pattern_count": int(row["logical_pattern_count"]),
                        },
                    },
                    tier="E3",
                    semantic_status="CONDITIONAL",
                    qualification_status="QUALIFIED_CONDITIONAL_LOGICAL_RESPONSE",
                    boundary=CONDITIONAL_BOUNDARY,
                    source={"id": row["record_id"], "type": "EXACT_LOGICAL_ENUMERATION"},
                    derived_from=(parent_id,),
                    blocking_reason="physical occurrence probability and physical-to-logical topology mapping unavailable",
                    permitted=("CONDITIONAL_LOGICAL_RESPONSE", "DECLARED_SCENARIO_ANALYSIS"),
                    forbidden=("PHYSICAL_SDC_RATE", "PHYSICAL_DUE_RATE", "FIT", "SILICON_CLAIM"),
                    compatibility={
                        "architecture": True,
                        "logical_fault_class": True,
                        "physical_topology": False,
                        "technology": "NOT_REQUIRED_FOR_LOGICAL_CONDITIONAL",
                    },
                    provenance={"source_record_id": row["record_id"]},
                )
            )
            probabilities[outcome] = value
            refs[outcome] = record_id
        surfaces.append(
            {
                "architecture": architecture,
                "topology_class": topology,
                "source_fault_environment": row["fault_environment_id"],
                "logical_pattern_count": int(row["logical_pattern_count"]),
                "probabilities": probabilities,
                "evidence_ids": refs,
                "status": "CONDITIONAL",
                "abstraction_boundary": CONDITIONAL_BOUNDARY,
                "physical_event_probability": None,
                "physical_rate_claim_permitted": False,
            }
        )
    return evidence, {"records": surfaces, "record_count": len(surfaces)}


BLOCKED_METRICS = (
    ("PHYSICAL_EVENT_RATE", "events_per_hour", "no matched SKY130 particle-event rate/fluence evidence"),
    ("PHYSICAL_SDC_RATE", "events_per_hour", "physical event occurrence and topology mapping are unavailable"),
    ("PHYSICAL_DUE_RATE", "events_per_hour", "physical event occurrence and topology mapping are unavailable"),
    ("FIT", "failures_per_1e9_device_hours", "qualified physical event rate is unavailable"),
    ("QCRIT", "C", "no transistor-level transient-injection evidence with waveform/model/PVT provenance"),
    ("BITCELL_XY_COORDINATES", "mapping", "GDS bitcell coordinates are not joined to electrical hierarchy"),
    ("ADDRESS_COLUMN_TO_BITCELL_MAP", "mapping", "address/column selection is not joined to bitcell identity"),
    ("MAXIMUM_SUSTAINABLE_THROUGHPUT", "services_per_s", "no independent saturation/backpressure experiment"),
    ("NORMAL_READ_ENERGY", "J_per_service", "activity is incomplete and operation window is not isolated"),
    ("WRITE_ENERGY", "J_per_service", "activity is incomplete and operation window is not isolated"),
    ("CORRECTED_READ_ENERGY", "J_per_service", "activity is incomplete and correction energy is not separated"),
    ("DETECTED_UNCORRECTABLE_EVENT_ENERGY", "J_per_service", "activity is incomplete and DUE service is not isolated"),
    ("RETRY_ENERGY", "J_per_service", "retry service is not implemented/isolated in the matched power run"),
    ("SCRUB_ENERGY", "J_per_service", "scrub service is not implemented/isolated in the matched power run"),
    ("I1_PHYSICAL_OVERHEAD", "multi_metric", "I1 is a proposal and has no routed implementation"),
    ("I2_PHYSICAL_OVERHEAD", "multi_metric", "I2 is a proposal and has no routed implementation"),
    ("SKY130_MANUFACTURING_CARBON", "kgCO2e", "no matched SKY130 manufacturing inventory"),
    ("LIFECYCLE_CARBON", "kgCO2e", "manufacturing, operational, lifetime, and allocation operands are incomplete"),
    ("CSCI", "kgCO2e_per_correct_service", "lifecycle and absolute correct-service operands are unqualified"),
    ("MRCC", "kgCO2e_per_additional_correct_service", "matched lifecycle and correct-service operands are unqualified"),
)


def _blocked_evidence() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        for metric, units, reason in BLOCKED_METRICS:
            rows.append(
                _new_evidence_record(
                    record_id=f"ME32|{architecture}|{BASE_SCENARIO}|{metric}",
                    metric=metric,
                    architecture=architecture,
                    scenario=BASE_SCENARIO,
                    value=None,
                    units=units,
                    uncertainty={"form": "structurally_missing", "detail": reason},
                    tier="E0",
                    semantic_status="STRUCTURALLY_MISSING",
                    qualification_status="BLOCKED",
                    boundary=DECISION_BOUNDARY,
                    source={"id": "REPOSITORY_ARTIFACT_AUDIT", "type": "ABSENCE_AUDIT"},
                    blocking_reason=reason,
                    permitted=("BLOCKING_SET", "VALUE_OF_INFORMATION"),
                    forbidden=(
                        "ZERO_SUBSTITUTION",
                        "IMPUTATION",
                        "QUALIFIED_PARETO",
                        "GLOBAL_WINNER",
                    ),
                    compatibility={
                        "technology": False,
                        "process": False,
                        "pvt": False,
                        "measurement_boundary": False,
                    },
                )
            )
    return rows


def _literature_evidence(parent_literature: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for parent in parent_literature["records"]:
        dataset_id = parent["dataset_id"]
        rows.append(
            _new_evidence_record(
                record_id=f"ME32|LITERATURE|{dataset_id}|TRANSFER_POLICY",
                metric="literature_numeric_transfer_to_sky130",
                architecture="CROSS_ARCHITECTURE",
                scenario="LITERATURE_NATIVE_BOUNDARY",
                value=False,
                units="boolean_policy",
                uncertainty={
                    "form": "literature_native",
                    "detail": parent.get("measurement_uncertainty", "not quantified"),
                },
                tier="E2",
                semantic_status="LITERATURE_NATIVE",
                qualification_status="TECHNOLOGY_PROCESS_GEOMETRY_MISMATCH_TO_SKY130",
                boundary=parent["experimental_model_boundary"],
                source={
                    "id": dataset_id,
                    "type": "PUBLISHED_LITERATURE_NATIVE",
                    "title": parent["title"],
                    "citation": parent["citation"],
                    "url": parent["url"],
                    "native_technology_process": parent["technology_process"],
                },
                blocking_reason="not independently matched to SKY130 SRAM22 technology/process/geometry/PVT",
                permitted=parent["allowed_uses"],
                forbidden=("ABSOLUTE_SKY130_CALIBRATION", "FEATURE_SIZE_SCALING_TRANSFER"),
                compatibility={
                    "technology": False,
                    "process": False,
                    "geometry": False,
                    "pvt": False,
                    "native_boundary_retained": True,
                },
                provenance={
                    "parent_dataset_id": dataset_id,
                    "parent_record_sha256": _record_sha(parent),
                },
            )
        )
    return rows


def _evidence_matrix(
    campaign_commit: str,
    parent_e: Mapping[str, Any],
    physical_summary: list[dict[str, Any]],
    conditional: list[dict[str, Any]],
    literature: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
) -> dict[str, Any]:
    inherited = _adapt_parent_evidence(parent_e["records"])
    new_records = physical_summary + conditional + literature + blocked
    records = inherited + new_records
    total_tiers = Counter(row["evidence_tier"] for row in records)
    new_tiers = Counter(row["evidence_tier"] for row in new_records)
    result = _envelope("EVIDENCE_MATRIX", campaign_commit)
    result.update(
        {
            "matrix_symbol": "M_E",
            "parent_matrix_schema_version": parent_e["schema_version"],
            "parent_matrix_sha256": _parent_sha(PARENT / "MATRIX_E_V3_1.json"),
            "parent_record_count": len(inherited),
            "records": records,
            "row_count": len(records),
            "new_row_count": len(new_records),
            "evidence_tier_counts": dict(sorted(total_tiers.items())),
            "new_evidence_tier_counts": dict(sorted(new_tiers.items())),
            "tier_semantics_preserved": True,
            "inherited_records_modified": False,
        }
    )
    return result


def _physical_matrix(
    campaign_commit: str,
    physical_population: list[dict[str, Any]],
    physical_summary: list[dict[str, Any]],
    parent_activity: Mapping[str, Any],
) -> dict[str, Any]:
    summary_by_id = {row["record_id"]: row for row in physical_summary}
    activity_by_arch = {row["architecture_id"]: row for row in parent_activity["postroute_rows"]}
    records: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        population = [row for row in physical_population if row["architecture_id"] == architecture]
        metrics: dict[str, Any] = {}
        for metric, units in PHYSICAL_SUMMARY_METRICS:
            evidence_id = f"ME32|{architecture}|I0|FIVE_SEED_MEAN|{metric}"
            evidence = summary_by_id[evidence_id]
            metrics[f"five_seed_mean_{metric}"] = {
                "value": evidence["value"],
                "units": units,
                "evidence_ids": [evidence_id],
                "status": "DIAGNOSTIC",
                "uncertainty": evidence["uncertainty"],
            }
        energy_id = (
            f"V31::ME31|MP31_{architecture}_UPSTREAM_ORIGINAL_seed11_I0|"
            "diagnostic_total_energy_per_requested_service_j"
        )
        metrics["diagnostic_energy_per_requested_service_j"] = {
            "value": activity_by_arch[architecture]["diagnostic_energy_per_requested_service_j"],
            "units": "J_per_requested_service",
            "evidence_ids": [energy_id],
            "status": "DIAGNOSTIC",
            "uncertainty": {"form": "diagnostic", "detail": "seed-11 partial annotation"},
        }
        latency_refs = [
            f"V31::ME31|MP31_{architecture}_UPSTREAM_ORIGINAL_seed{seed}_I0|registered_service_latency_s"
            for seed in SEEDS
        ]
        ii_refs = [
            f"V31::ME31|MP31_{architecture}_UPSTREAM_ORIGINAL_seed{seed}_I0|initiation_interval_cycles"
            for seed in SEEDS
        ]
        metrics["rtl_service_latency_s"] = {
            "value": 1.0e-8,
            "units": "s",
            "evidence_ids": latency_refs,
            "status": "QUALIFIED",
            "uncertainty": {"form": "exact", "detail": "one synchronous 10 ns RTL cycle"},
        }
        metrics["rtl_initiation_interval_cycles"] = {
            "value": 1,
            "units": "cycle",
            "evidence_ids": ii_refs,
            "status": "QUALIFIED",
            "uncertainty": {"form": "exact", "detail": "one RTL request per cycle"},
        }
        records.append(
            {
                "architecture": architecture,
                "scenario": BASE_SCENARIO,
                "interleaving": "I0",
                "seed_identifiers": list(SEEDS),
                "implementation_hashes": [row["implementation_hash"] for row in population],
                "netlist_hashes": [row["netlist_hash"] for row in population],
                "configuration_hashes": [row["physical_configuration_hash"] for row in population],
                "constraint_hashes": [row["timing_constraint_hash"] for row in population],
                "workload_hashes": sorted(
                    {row["workload_hash"] for row in population if row.get("workload_hash")}
                ),
                "activity_hashes": sorted(
                    {row["activity_file_hash"] for row in population if row.get("activity_file_hash")}
                ),
                "metrics": metrics,
                "qualification_status": "DIAGNOSTIC_IMPLEMENTATION_MATRIX_WITH_QUALIFIED_RTL_TIMING",
            }
        )
    result = _envelope("PHYSICAL_MATRIX", campaign_commit)
    result.update(
        {
            "matrix_symbol": "M_P",
            "parent_matrix_sha256": _parent_sha(PARENT / "MATRIX_P_V3_1.json"),
            "records": records,
            "row_count": len(records),
            "new_row_count": len(records),
            "all_cells_reference_M_E": True,
            "maximum_sustainable_throughput": "UNQUALIFIED",
        }
    )
    return result


def _decision_admissibility_rows(blocked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mandatory = (
        "PHYSICAL_EVENT_RATE",
        "PHYSICAL_SDC_RATE",
        "PHYSICAL_DUE_RATE",
        "NORMAL_READ_ENERGY",
        "SKY130_MANUFACTURING_CARBON",
        "LIFECYCLE_CARBON",
    )
    rows: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        metric_records = {
            row["metric_identifier"]: row
            for row in blocked
            if row["architecture"] == architecture
        }
        rows.append(
            decision_admissibility(
                architecture=architecture,
                scenario=BASE_SCENARIO,
                metric_records=metric_records,
                mandatory_metrics=mandatory,
                target_context={"measurement_boundary": DECISION_BOUNDARY},
            )
        )
    return rows


def _sustainability_matrix(
    campaign_commit: str,
    physical_matrix: Mapping[str, Any],
    conditional_artifact: Mapping[str, Any],
    admissibility: list[dict[str, Any]],
) -> dict[str, Any]:
    physical_by_arch = {row["architecture"]: row for row in physical_matrix["records"]}
    records: list[dict[str, Any]] = []
    for decision in admissibility:
        architecture = decision["architecture"]
        physical = physical_by_arch[architecture]["metrics"]
        vector = GreenVector(
            reliability_consequence={
                "value": None,
                "status": "CONDITIONAL",
                "conditional_surface_reference": "data/CONDITIONAL_RELIABILITY.json",
                "absolute_rate_status": "BLOCKED",
            },
            operational_resource_consequence={
                "value": physical["diagnostic_energy_per_requested_service_j"]["value"],
                "units": "J_per_requested_service",
                "status": "DIAGNOSTIC",
                "evidence_ids": physical["diagnostic_energy_per_requested_service_j"]["evidence_ids"],
            },
            physical_implementation_cost={
                "area_um2": physical["five_seed_mean_routed_total_area_um2"],
                "wirelength_um": physical["five_seed_mean_wirelength_um"],
                "via_count": physical["five_seed_mean_via_count"],
                "status": "DIAGNOSTIC",
            },
            environmental_lifecycle_consequence={"value": None, "status": "BLOCKED"},
            evidence_quality={
                "decision_status": "BLOCKED",
                "conditional_response_status": "QUALIFIED_WITHIN_LOGICAL_BOUNDARY",
                "blocking_set": decision["blocking_metrics"],
            },
        )
        records.append(
            {
                "architecture": architecture,
                "scenario": BASE_SCENARIO,
                "green_vector": vector.as_dict(),
                "status": "BLOCKED",
                "blocking_set": decision["blocking_metrics"],
                "global_winner_eligible": False,
            }
        )
    result = _envelope("SUSTAINABILITY_MATRIX", campaign_commit)
    result.update(
        {
            "matrix_symbol": "M_S",
            "records": records,
            "row_count": len(records),
            "new_row_count": len(records),
            "parent_matrix_sha256": _parent_sha(PARENT / "MATRIX_S_V3_1.json"),
            "global_architecture_winner": "NO_GLOBAL_WINNER_QUALIFIED",
            "conditional_surface_count": conditional_artifact["record_count"],
        }
    )
    return result


def _scenario_definitions(campaign_commit: str) -> dict[str, Any]:
    scenarios = [
        ("S_LOGICAL_SBU_ONLY", [1.0, 0.0, 0.0, 0.0]),
        ("S_LOGICAL_DBU_ONLY", [0.0, 1.0, 0.0, 0.0]),
        ("S_LOGICAL_MBU3_ONLY", [0.0, 0.0, 1.0, 0.0]),
        ("S_LOGICAL_MBU4_ONLY", [0.0, 0.0, 0.0, 1.0]),
        ("S_LOGICAL_EQUAL_MIX", [0.25, 0.25, 0.25, 0.25]),
    ]
    topology_order = list(TOPOLOGY_MAP.values())
    records = []
    for scenario_id, values in scenarios:
        records.append(
            {
                "scenario_id": scenario_id,
                "semantic_status": "SCENARIO_ASSUMPTION",
                "promoted_to_evidence": False,
                "assumption_measure": "finite uniform counting measure over declared scenarios",
                "logical_topology_weights": dict(zip(topology_order, values)),
                "weight_sum": sum(values),
                "physical_probability_interpretation": "FORBIDDEN",
                "permitted_use": "CONDITIONAL_LOGICAL_RESPONSE_TRADE_SPACE_ONLY",
                "forbidden_uses": ["PHYSICAL_EVENT_PMF", "SER", "FIT", "CONFIDENCE_PROBABILITY"],
            }
        )
    result = _envelope("SCENARIO_DEFINITIONS", campaign_commit)
    result.update(
        {
            "scenario_space_id": "S32_FINITE_DECLARED_LOGICAL_TOPOLOGY_SPACE",
            "records": records,
            "scenario_count": len(records),
            "scenario_values_are_measurements": False,
        }
    )
    return result


def _pareto_and_robustness(
    campaign_commit: str,
    scenarios: Mapping[str, Any],
    conditional: Mapping[str, Any],
    physical_matrix: Mapping[str, Any],
    admissibility: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    physical_by_arch = {row["architecture"]: row["metrics"] for row in physical_matrix["records"]}
    response = {
        (row["architecture"], row["topology_class"]): row["probabilities"]
        for row in conditional["records"]
    }
    conditional_objectives = (
        Objective("conditional_sdc_probability", "min", "probability"),
        Objective("routed_total_area_um2", "min", "um2"),
        Objective("vectorless_power_w", "min", "W"),
    )
    scenario_fronts: dict[str, list[str]] = {}
    scenario_records: list[dict[str, Any]] = []
    for scenario in scenarios["records"]:
        candidates = []
        for architecture in ARCHITECTURES:
            conditional_sdc = sum(
                weight * response[(architecture, topology)]["sdc"]
                for topology, weight in scenario["logical_topology_weights"].items()
            )
            metrics = physical_by_arch[architecture]
            candidates.append(
                {
                    "architecture_id": architecture,
                    "conditional_sdc_probability": conditional_sdc,
                    "routed_total_area_um2": metrics["five_seed_mean_routed_total_area_um2"]["value"],
                    "vectorless_power_w": metrics["five_seed_mean_power_total_vectorless_w"]["value"],
                }
            )
        front = exact_pareto_ids(candidates, conditional_objectives)
        scenario_fronts[scenario["scenario_id"]] = front
        scenario_records.append(
            {
                "scenario_id": scenario["scenario_id"],
                "front_classification": "CONDITIONAL_SCENARIO_FRONT",
                "front": front,
                "candidates": candidates,
                "scenario_assumptions": scenario["logical_topology_weights"],
                "qualification_state": "CONDITIONAL",
                "physical_probability_interpretation": False,
                "normalization": "NONE",
                "architectures_included": list(ARCHITECTURES),
                "architectures_excluded": [],
            }
        )
    diagnostic_objectives = (
        Objective("routed_total_area_um2", "min", "um2"),
        Objective("wirelength_um", "min", "um"),
        Objective("vectorless_power_w", "min", "W"),
    )
    diagnostic_candidates = [
        {
            "architecture_id": architecture,
            "routed_total_area_um2": physical_by_arch[architecture][
                "five_seed_mean_routed_total_area_um2"
            ]["value"],
            "wirelength_um": physical_by_arch[architecture]["five_seed_mean_wirelength_um"]["value"],
            "vectorless_power_w": physical_by_arch[architecture][
                "five_seed_mean_power_total_vectorless_w"
            ]["value"],
        }
        for architecture in ARCHITECTURES
    ]
    diagnostic_front = exact_pareto_ids(diagnostic_candidates, diagnostic_objectives)
    qualified = qualified_pareto_or_blocked(
        records=[
            {
                "architecture_id": architecture,
                "physical_sdc_rate": None,
                "lifecycle_carbon_kgco2e": None,
                "operational_energy_j": None,
            }
            for architecture in ARCHITECTURES
        ],
        objectives=(
            Objective("physical_sdc_rate", "min", "events_per_hour"),
            Objective("lifecycle_carbon_kgco2e", "min", "kgCO2e"),
            Objective("operational_energy_j", "min", "J_per_service"),
        ),
        admissibility=admissibility,
    )
    pareto = _envelope("PARETO_ANALYSIS", campaign_commit)
    pareto.update(
        {
            "enumeration": "EXACT_DETERMINISTIC",
            "machine_learning_used": False,
            "diagnostic_front": {
                "front_classification": "DIAGNOSTIC_FRONT",
                "front": diagnostic_front,
                "candidates": diagnostic_candidates,
                "dimensions": [objective.__dict__ for objective in diagnostic_objectives],
                "normalization": "NONE",
                "qualification_state": "DIAGNOSTIC",
                "reason_global_winner_forbidden": "reliability and lifecycle dimensions are blocked",
            },
            "conditional_scenario_fronts": scenario_records,
            "qualified_front": {
                **qualified,
                "dimensions": [
                    {"metric": "physical_sdc_rate", "direction": "min", "units": "events_per_hour"},
                    {"metric": "lifecycle_carbon_kgco2e", "direction": "min", "units": "kgCO2e"},
                    {"metric": "operational_energy_j", "direction": "min", "units": "J_per_service"},
                ],
                "normalization": "NONE",
                "missing_dimensions_discarded": False,
            },
            "global_architecture_winner": "NO_GLOBAL_WINNER_QUALIFIED",
        }
    )
    fractions = {
        architecture: scenario_space_nondominance_fraction(architecture, scenario_fronts)
        for architecture in ARCHITECTURES
    }
    robustness = _envelope("SCENARIO_ROBUSTNESS", campaign_commit)
    robustness.update(
        {
            "metric_name": "SCENARIO_SPACE_NONDOMINANCE_FRACTION",
            "scenario_space_id": scenarios["scenario_space_id"],
            "measure": "finite uniform counting measure over the five explicitly declared scenarios",
            "scenario_fronts": scenario_fronts,
            "fractions": fractions,
            "physical_probability": False,
            "design_yield": False,
            "confidence_probability": False,
            "probability_of_winning": False,
        }
    )
    return pareto, robustness


def _provenance_hash(source_provenance: Mapping[str, str], suffix: str) -> str:
    matches = [value for key, value in source_provenance.items() if key.endswith(suffix)]
    return matches[0] if matches else ""


def _energy_qualification(
    campaign_commit: str,
    parent_activity: Mapping[str, Any],
    physical_population: list[dict[str, Any]],
) -> dict[str, Any]:
    seed11 = {
        row["architecture_id"]: row
        for row in physical_population
        if int(row["seed"]) == 11
    }
    records = []
    for row in parent_activity["postroute_rows"]:
        architecture = row["architecture_id"]
        provenance = row["source_provenance"]
        physical = seed11[architecture]
        activity = ActivityCompleteness(
            annotation_coverage_fraction=float(row["annotated_pin_fraction"]),
            unannotated_instance_pin_count=int(row["unannotated_pin_count"]),
            unmatched_activity_object_count=int(row["unannotated_pin_count"]),
            default_activity_used=True,
            postroute_gate_level_activity=False,
            macro_internal_activity_characterized=False,
            whole_service_boundary_covered=False,
            operation_window_isolated=False,
            duration_s=float(row["duration_s"]),
            operation_count=int(row["service_count"]),
            clock_period_s=1.0e-8,
            workload_hash=physical["workload_hash"],
            activity_hash=physical["activity_file_hash"],
            implementation_hash=physical["implementation_hash"],
            netlist_hash=physical["netlist_hash"],
            configuration_hash=physical["physical_configuration_hash"],
            constraint_hash=physical["timing_constraint_hash"],
            power_report_hash=_provenance_hash(provenance, "/power.rpt"),
        )
        qualification = qualify_e5_activity(activity)
        records.append(
            {
                "architecture": architecture,
                "observed": {
                    "annotation_coverage_fraction": activity.annotation_coverage_fraction,
                    "annotated_pin_count": row["annotated_pin_count"],
                    "unannotated_pin_count": activity.unannotated_instance_pin_count,
                    "duration_s": activity.duration_s,
                    "service_count": activity.operation_count,
                    "clock_period_s": activity.clock_period_s,
                    "diagnostic_energy_per_requested_service_j": row[
                        "diagnostic_energy_per_requested_service_j"
                    ],
                },
                "qualification": qualification,
                "operation_energy_status": {
                    "normal_read": "BLOCKED",
                    "write": "BLOCKED",
                    "corrected_read": "BLOCKED",
                    "detected_uncorrectable_event": "BLOCKED",
                    "retry": "BLOCKED",
                    "scrub": "BLOCKED",
                },
                "provenance": {
                    "workload_hash": activity.workload_hash,
                    "activity_hash": activity.activity_hash,
                    "implementation_hash": activity.implementation_hash,
                    "netlist_hash": activity.netlist_hash,
                    "configuration_hash": activity.configuration_hash,
                    "constraint_hash": activity.constraint_hash,
                    "power_report_hash": activity.power_report_hash,
                },
            }
        )
    result = _envelope("ENERGY_QUALIFICATION", campaign_commit)
    result.update(
        {
            "e5_activity_completeness_criterion": {
                "criterion_id": "E5_ACTIVITY_COMPLETE_V3_2",
                "logic": "ALL requirements must pass; a numeric energy alone never qualifies",
                "requirements": [
                    "annotation coverage fraction equals 1.0",
                    "zero unannotated instance pins",
                    "zero unmatched activity objects",
                    "no default activity",
                    "post-route gate-level activity including glitch behavior",
                    "macro-internal activity characterized for the declared operation",
                    "whole implemented service boundary covered",
                    "operation window isolated with positive duration and count",
                    "clock period declared",
                    "workload, activity, implementation, netlist, configuration, constraint, and power hashes present",
                ],
            },
            "records": records,
            "e5_measurement_count": sum(row["qualification"]["qualified"] for row in records),
            "highest_energy_tier": "E5"
            if any(row["qualification"]["qualified"] for row in records)
            else "E4",
            "classification": "PARTIAL_ANNOTATION_DIAGNOSTIC_ONLY_NOT_E5",
        }
    )
    return result


def _interleaver_feasibility(
    campaign_commit: str, parent_interleaver: Mapping[str, Any]
) -> dict[str, Any]:
    records = []
    for parent in parent_interleaver["records"]:
        interleaving = parent["interleaving_id"]
        implemented = interleaving == "I0"
        records.append(
            {
                "interleaving_id": interleaving,
                "status": "ROUTED_BASELINE"
                if implemented
                else "PROPOSAL_NOT_PHYSICALLY_IMPLEMENTED",
                "routed_implementation": implemented,
                "physical_logical_mapping_complete": False,
                "physical_reliability_benefit_qualified": False,
                "overhead": {
                    "delta_area_um2": 0.0 if implemented else None,
                    "delta_wirelength_um": 0.0 if implemented else None,
                    "delta_vias": 0 if implemented else None,
                    "delta_power_w": 0.0 if implemented else None,
                    "delta_energy_j": 0.0 if implemented else None,
                    "delta_latency_cycles": 0 if implemented else None,
                    "delta_initiation_interval_cycles": 0 if implemented else None,
                    "delta_slack_ns": 0.0 if implemented else None,
                    "delta_congestion": 0.0 if implemented else None,
                },
                "mapping_proposal": parent["stored_word_mapping"],
                "blocking_reasons": []
                if implemented
                else [
                    "no routed lane-transpose/read-modify-write wrapper",
                    "no matched five-seed physical results",
                    "no activity-qualified overhead",
                    "no complete address/column-to-bitcell physical map",
                ],
            }
        )
    result = _envelope("INTERLEAVER_FEASIBILITY", campaign_commit)
    result.update(
        {
            "records": records,
            "implemented_nontrivial_interleaver_count": 0,
            "classification": "I0_ROUTED_BASELINE_I1_I2_PROPOSALS_BLOCKED",
            "repository_audit_result": "no v3.1 artifact contains a routed I1/I2 implementation",
        }
    )
    return result


def _bitcell_mapping_audit(
    campaign_commit: str, parent_topology: Mapping[str, Any]
) -> dict[str, Any]:
    levels = [
        {
            "level": "MACRO_GEOMETRY",
            "status": "ESTABLISHED",
            "detail": "LEF extent plus DEF origin/orientation for the matched seeds",
        },
        {
            "level": "ELECTRICAL_ORGANIZATION",
            "status": "PARTIAL",
            "detail": "SPICE hierarchy exposes storage-cell instance counts and electrical row/column organization",
        },
        {
            "level": "LOGICAL_ROW_COLUMN",
            "status": "PARTIAL",
            "detail": "logical depth/width and RTL address/data pins are known; internal decode join is not independently reproduced",
        },
        {
            "level": "ADDRESS_TO_COLUMN_GROUP",
            "status": "BLOCKED",
            "detail": "m4/m8 column mux and address-select mapping are not joined into a verified table",
        },
        {
            "level": "BITCELL_INSTANCE_IDENTITY",
            "status": "BLOCKED",
            "detail": "hierarchical storage-cell counts do not provide a verified logical identity per instance",
        },
        {
            "level": "BITCELL_XY_COORDINATES",
            "status": "BLOCKED",
            "detail": "no GDS coordinate extraction joined to bitcell instances",
        },
        {
            "level": "PHYSICAL_TO_LOGICAL_ECC_BIT_IDENTITY",
            "status": "BLOCKED",
            "detail": "macro data-pin identity does not establish physical adjacency or bitcell XY",
        },
    ]
    source_paths: dict[str, str] = {}
    for record in parent_topology["macro_geometry_records"]:
        source_paths.update(record["source_provenance"])
    result = _envelope("BITCELL_MAPPING_AUDIT", campaign_commit)
    result.update(
        {
            "levels": levels,
            "source_artifacts_examined": dict(sorted(source_paths.items())),
            "mapping_improved_from_v3_1": False,
            "highest_established_level": "MACRO_GEOMETRY_WITH_PARTIAL_ELECTRICAL_ORGANIZATION",
            "macro_dimensions_never_treated_as_bitcell_mapping": True,
        }
    )
    return result


def _qualification_rules(campaign_commit: str) -> dict[str, Any]:
    result = _envelope("QUALIFICATION_RULES", campaign_commit)
    result.update(
        {
            "compatibility_dimensions": [
                "technology",
                "process",
                "pvt",
                "measurement_boundary",
                "workload",
                "activity",
                "architecture",
                "spatial_mapping",
                "lifecycle_boundary",
            ],
            "rules": [
                {
                    "decision": "ABSOLUTE_RELIABILITY",
                    "requirements": [
                        {"metric": "PHYSICAL_EVENT_RATE", "minimum_tier": "E2", "status": "MEASURED_AND_ABSOLUTE_QUALIFIED"},
                        {"metric": "PHYSICAL_TO_LOGICAL_MAPPING", "minimum_tier": "E3", "status": "QUALIFIED"},
                        {"metric": "CONDITIONAL_OUTCOME_MODEL", "minimum_tier": "E3", "status": "CONDITIONAL_QUALIFIED"},
                    ],
                },
                {
                    "decision": "E5_OPERATIONAL_ENERGY",
                    "requirements": [{"criterion": "E5_ACTIVITY_COMPLETE_V3_2", "logic": "ALL"}],
                },
                {
                    "decision": "QUALIFIED_SUSTAINABILITY_FRONT",
                    "requirements": [
                        {"metric": "PHYSICAL_SDC_RATE", "status": "QUALIFIED"},
                        {"metric": "OPERATIONAL_ENERGY", "minimum_tier": "E5", "status": "QUALIFIED"},
                        {"metric": "SKY130_MANUFACTURING_CARBON", "status": "QUALIFIED"},
                        {"metric": "LIFECYCLE_CARBON", "status": "QUALIFIED"},
                    ],
                    "missing_dimension_policy": "BLOCK_FRONT",
                },
                {
                    "decision": "GLOBAL_WINNER",
                    "requirements": [{"metric": "QUALIFIED_SUSTAINABILITY_FRONT", "status": "QUALIFIED"}],
                    "failure_result": "NO_GLOBAL_WINNER_QUALIFIED",
                },
            ],
            "default_literature_policy": "LITERATURE_NUMERIC_TRANSFER_TO_SKY130_FORBIDDEN",
            "unknown_numeric_policy": "UNKNOWN_BLOCKED_VALUES_ARE_NEVER_ZERO",
        }
    )
    return result


def _literature_policy(
    campaign_commit: str, parent_literature: Mapping[str, Any]
) -> dict[str, Any]:
    result = _envelope("LITERATURE_POLICY", campaign_commit)
    records = []
    for parent in parent_literature["records"]:
        records.append(
            {
                "dataset_id": parent["dataset_id"],
                "title": parent["title"],
                "citation": parent["citation"],
                "url": parent["url"],
                "native_technology_process": parent["technology_process"],
                "native_boundary": parent["experimental_model_boundary"],
                "native_record_sha256": _record_sha(parent),
                "compatibility_with_sky130": "TECHNOLOGY_PROCESS_GEOMETRY_MISMATCH",
                "numeric_value_transferred_to_sky130": False,
                "allowed_uses": parent["allowed_uses"],
                "forbidden_use": parent["prohibited_use"],
            }
        )
    result.update(
        {
            "default_policy": "LITERATURE_NUMERIC_TRANSFER_TO_SKY130_FORBIDDEN",
            "record_count": len(records),
            "records": records,
            "numeric_values_transferred_to_sky130": 0,
        }
    )
    return result


def _equation_status(campaign_commit: str) -> dict[str, Any]:
    result = _envelope("EQUATION_STATUS", campaign_commit)
    result.update(
        {
            "records": [
                {
                    "metric": "CSCI",
                    "equation": "lifecycle_carbon_kgco2e / correct_service_count",
                    "equation_status": "VALID",
                    "executable_guard": "VALID",
                    "quantity_status": "BLOCKED",
                    "blocking_operands": ["LIFECYCLE_CARBON", "ABSOLUTE_CORRECT_SERVICE_COUNT"],
                },
                {
                    "metric": "MRCC",
                    "equation": "delta_lifecycle_carbon_kgco2e / delta_correct_service_count",
                    "equation_status": "VALID",
                    "executable_guard": "VALID",
                    "quantity_status": "BLOCKED",
                    "blocking_operands": [
                        "MATCHED_DELTA_LIFECYCLE_CARBON",
                        "MATCHED_DELTA_CORRECT_SERVICE_COUNT",
                    ],
                },
            ],
            "mathematical_validity_implies_parameter_availability": False,
        }
    )
    return result


def _figure_specification(campaign_commit: str) -> dict[str, Any]:
    result = _envelope("FIGURE_SPECIFICATION", campaign_commit)
    nodes = [
        ("physical_event_source", "Physical Event Source", "BLOCKED"),
        ("topology_mapping", "Topology / Physical Mapping", "BLOCKED"),
        ("logical_corruption", "Logical Corruption", "ANALYTICAL"),
        ("ecc_interleaving", "ECC + Interleaving Response", "CONDITIONAL"),
        ("service_outcome", "Service Outcome", "CONDITIONAL"),
        ("operational_cost", "Operational Cost", "DIAGNOSTIC"),
        ("lifecycle_scenario", "Lifecycle Scenario", "BLOCKED"),
    ]
    result.update(
        {
            "title": "GREEN Matrix v3.2 evidence-gated causal decision path",
            "nodes": [
                {"id": node_id, "label": label, "state": state}
                for node_id, label, state in nodes
            ],
            "edges": [
                {"from": nodes[index][0], "to": nodes[index + 1][0], "gated_by": "M_E"}
                for index in range(len(nodes) - 1)
            ],
            "evidence_gate": {
                "label": "M_E: tier + boundary + provenance + compatibility + status",
                "applies_to_every_transition": True,
                "missing_evidence_action": "STOP_DOWNSTREAM_ABSOLUTE_CLAIM",
            },
            "visual_encoding": {
                "measured": "solid green",
                "conditional": "blue dashed",
                "diagnostic": "amber dotted",
                "blocked": "red stop marker",
            },
        }
    )
    return result


def _historical_integrity(campaign_commit: str) -> dict[str, Any]:
    result = _envelope("HISTORICAL_INTEGRITY", campaign_commit)
    result.update(
        {
            "protected_commits": [FOUNDATION_COMMIT, PARENT_COMMIT],
            "protected_directories": [
                "campaigns/iscas_sustainability_extension/green_matrix_v3_imec_aligned",
                "campaigns/iscas_sustainability_extension/green_matrix_v3_physical_population",
            ],
            "parent_artifact_hashes": {
                name: _parent_sha(PARENT / name) for name in SOURCE_FILES
            },
            "historical_artifacts_modified": False,
            "v3_1_classification_preserved": (
                "GREEN_MATRIX_V3_1_PHYSICAL_POPULATION_PARTIAL_E4_E3_"
                "PHYSICAL_SDC_DUE_BLOCKED"
            ),
        }
    )
    return result


def _value_of_information(campaign_commit: str) -> dict[str, Any]:
    result = _envelope("VALUE_OF_INFORMATION", campaign_commit)
    result.update(
        {
            "highest_value_ultimate_reliability_experiment": (
                "MATCHED_SKY130_SRAM_PARTICLE_BEAM_EVENT_COORDINATES_FLUENCE_"
                "AND_VERIFIED_BITCELL_LOGICAL_MAP"
            ),
            "highest_value_accessible_next_measurements": [
                "ACTIVITY_COMPLETE_E5_OPERATIONAL_ENERGY",
                "OPERATION_SEPARATED_READ_WRITE_CORRECT_DUE_RETRY_SCRUB_ENERGY",
                "PHYSICALLY_ROUTED_I1_I2_INTERLEAVERS",
                "STRONGER_ADDRESS_COLUMN_BITCELL_MAPPING",
                "CONDITIONAL_TOPOLOGY_RESPONSE_WITH_VERIFIED_MAPPING",
                "SATURATED_THROUGHPUT",
                "MATCHED_MANUFACTURING_LIFECYCLE_INVENTORY_IF_DEFENSIBLE",
            ],
            "particle_beam_access_required_to_complete_v3_2": False,
        }
    )
    return result


def _derive_classification(
    *, energy: Mapping[str, Any], pareto: Mapping[str, Any], conditional: Mapping[str, Any]
) -> str:
    conditional_validated = conditional["record_count"] > 0
    qualified_front_blocked = pareto["qualified_front"]["status"] == "BLOCKED"
    no_e5 = energy["e5_measurement_count"] == 0
    if conditional_validated and qualified_front_blocked and no_e5:
        return (
            "GREEN_MATRIX_V3_2_EVIDENCE_AWARE_DECISION_MODEL_CONDITIONAL_FRONT_"
            "VALIDATED_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED"
        )
    if qualified_front_blocked:
        return "GREEN_MATRIX_V3_2_EVIDENCE_AWARE_DECISION_MODEL_QUALIFIED_FRONT_BLOCKED"
    return "GREEN_MATRIX_V3_2_EVIDENCE_AWARE_DECISION_MODEL_QUALIFIED_FRONT"


def _campaign_status(
    campaign_commit: str,
    evidence: Mapping[str, Any],
    physical: Mapping[str, Any],
    sustainability: Mapping[str, Any],
    conditional: Mapping[str, Any],
    scenarios: Mapping[str, Any],
    robustness: Mapping[str, Any],
    energy: Mapping[str, Any],
    interleaver: Mapping[str, Any],
    pareto: Mapping[str, Any],
) -> dict[str, Any]:
    classification = _derive_classification(energy=energy, pareto=pareto, conditional=conditional)
    result = _envelope("CAMPAIGN_STATUS", campaign_commit)
    result.update(
        {
            "classification": classification,
            "architectures": list(ARCHITECTURES),
            "seed_identifiers": list(SEEDS),
            "matrix_counts": {
                "M_E": evidence["row_count"],
                "M_E_new": evidence["new_row_count"],
                "M_P": physical["row_count"],
                "M_S": sustainability["row_count"],
            },
            "evidence_tier_counts": evidence["evidence_tier_counts"],
            "new_evidence_tier_counts": evidence["new_evidence_tier_counts"],
            "newly_populated_metrics": [
                "FIVE_SEED_IMPLEMENTATION_SUMMARIES_E4_DIAGNOSTIC",
                "CONDITIONAL_CORRECTED_DETECTED_SDC_DUE_RESPONSE_SURFACES_E3",
                "SCENARIO_SPACE_NONDOMINANCE_FRACTION_CONDITIONAL",
            ],
            "conditional_reliability_status": "QUALIFIED_WITHIN_LOGICAL_MASK_CLASS_BOUNDARY",
            "conditional_response_surface_count": conditional["record_count"],
            "physical_event_rate_status": "BLOCKED",
            "physical_sdc_status": "BLOCKED",
            "physical_due_status": "BLOCKED",
            "fit_status": "BLOCKED",
            "qcrit_status": "BLOCKED",
            "e5_status": "BLOCKED" if energy["e5_measurement_count"] == 0 else "QUALIFIED",
            "e5_measurement_count": energy["e5_measurement_count"],
            "interleaver_status": interleaver["classification"],
            "manufacturing_carbon_status": "BLOCKED",
            "reference_manufacturing_scenario_count": 0,
            "lifecycle_carbon_status": "BLOCKED",
            "csci_status": "EQUATION_VALID_GUARD_VALID_QUANTITY_BLOCKED",
            "mrcc_status": "EQUATION_VALID_GUARD_VALID_QUANTITY_BLOCKED",
            "diagnostic_pareto_status": "DIAGNOSTIC_FRONT",
            "conditional_pareto_status": "CONDITIONAL_SCENARIO_FRONT",
            "qualified_pareto_status": "BLOCKED",
            "scenario_count": scenarios["scenario_count"],
            "scenario_space_nondominance_fractions": robustness["fractions"],
            "global_architecture_winner": "NO_GLOBAL_WINNER_QUALIFIED",
            "historical_artifacts_modified": False,
        }
    )
    return result


def _final_report(
    campaign_commit: str,
    status: Mapping[str, Any],
    physical: Mapping[str, Any],
    energy: Mapping[str, Any],
    pareto: Mapping[str, Any],
    robustness: Mapping[str, Any],
) -> str:
    fractions = robustness["fractions"]
    return f"""# GREEN Matrix v3.2 final scientific report

Schema version: `{SCHEMA_VERSION}`

Campaign commit: `{campaign_commit}`

Parent campaign commit: `{PARENT_COMMIT}`

Foundation commit: `{FOUNDATION_COMMIT}`

Generation date: `{GENERATED_AT}`

## Outcome

GREEN Matrix v3.2 implements an additive **Evidence -> Qualification ->
Conditional Model -> Decision** framework. It preserves the frozen v3.1
physical population, makes `M_E`, `M_P`, and `M_S` first-class artifacts,
populates exact conditional logical-response surfaces, and performs exact
diagnostic and conditional-scenario Pareto enumeration. Absolute physical
reliability and lifecycle conclusions remain blocked.

Final classification:
`{status['classification']}`.

The sustainability method is methodologically informed by publicly available
imec SSTS/imec.netzero bottom-up principles. No certification, compliance,
validation, standardization, or endorsement by imec is claimed, and no public
imec datum is represented as SKY130 manufacturing data.

## Required questions

1. **What changed from GREEN 3.1 to 3.2?** Evidence is now an executable operand of every decision: each quantity carries tier, boundary, uncertainty/status, provenance, compatibility, allowed uses, forbidden uses, and dependencies. Exact conditional response, admissibility, scenario robustness, and three distinct Pareto objects were added.
2. **Which new quantities became populated?** Five-seed E4 diagnostic means/intervals for six implementation metrics per architecture; E3 conditional corrected, detected, SDC, and DUE probabilities for four logical mask classes per U0/E0; and conditional scenario-space non-dominance fractions.
3. **Did any quantity reach E5?** No. `E5_MEASUREMENT_COUNT = {energy['e5_measurement_count']}`.
4. **What exact criterion defines E5 activity completeness?** All ten requirements in `data/ENERGY_QUALIFICATION.json` must pass: complete annotation, zero unmatched/unannotated objects, no default activity, post-route gate/glitch activity, macro-internal characterization, whole-service coverage, isolated positive operation window/count, declared clock, and complete provenance hashes.
5. **Were read/write/correct/retry/scrub energies separately established?** No; all remain `BLOCKED`. Only the inherited seed-11 partial-annotation total is retained as E4 diagnostic energy per requested service.
6. **Were I1/I2 physically implemented?** No. I0 remains the routed baseline; I1/I2 remain proposals.
7. **What physical overhead did they incur?** No I1/I2 overhead is reported: area, wirelength, vias, power, energy, latency, II, slack, and congestion are unavailable rather than imputed.
8. **Is any physical reliability benefit attributable to interleaving?** No; neither a routed nontrivial interleaver nor a complete physical/logical mapping exists.
9. **Was bitcell/logical mapping improved?** No. Macro geometry and partial electrical organization remain available; address-to-column group, bitcell identity, bitcell XY, and physical-to-logical ECC-bit identity remain blocked.
10. **Was Qcrit established?** No. `QCRIT = BLOCKED`.
11. **Was any physical event-rate model established?** No. Logical injection/enumeration frequencies are explicitly forbidden as event-rate substitutes.
12. **Can physical SDC now be calculated?** No; the event occurrence and mapping operands are missing.
13. **Can physical DUE now be calculated?** No; the same absolute-probability guard blocks it.
14. **Can FIT now be calculated?** No; no qualified physical event rate exists.
15. **Were conditional SDC/DUE response surfaces established?** Yes, for U0/E0 over logical SBU-any-bit, DBU-any-pair, consecutive-MBU-3, and consecutive-MBU-4 classes, using exact inherited logical enumeration.
16. **What exactly is conditional vs absolute reliability?** Conditional results are `P(outcome | declared logical mask class, architecture)`. Absolute rates require `P(T_i)` or an event rate plus a verified physical-to-logical topology map; those operands remain unavailable.
17. **Was any literature quantity transferred into SKY130?** No. The five v3.1 literature records remain native, technology/process/geometry-mismatched references. `LITERATURE_NUMERIC_TRANSFER_TO_SKY130 = FORBIDDEN`.
18. **Was manufacturing carbon established?** No. `SKY130_MANUFACTURING_CARBON = BLOCKED`.
19. **Were external manufacturing scenarios added?** No; the reference-manufacturing-scenario count is zero.
20. **What claims may those scenarios support?** None were added. A future mismatched reference scenario could support declared sensitivity analysis only, never an absolute SKY130 carbon claim.
21. **Can CSCI be populated?** No. The equation/guard may be audited, but lifecycle carbon and absolute correct-service operands are blocked.
22. **Can MRCC be populated?** No. Its equation/guard remains separable from unavailable matched lifecycle/reliability operands.
23. **Does a qualified Pareto front exist?** No: `{pareto['qualified_front']['front_classification']}`.
24. **Does a diagnostic Pareto front exist?** Yes: `DIAGNOSTIC_FRONT`, over route area, wirelength, and vectorless tool power.
25. **Does a conditional scenario front exist?** Yes: five exact `CONDITIONAL_SCENARIO_FRONT` objects.
26. **Which dimensions were used?** Conditional SDC probability, five-seed mean routed area, and five-seed mean vectorless power; the diagnostic front uses area, wirelength, and vectorless power. No normalization was applied and all directions are minimization.
27. **What scenario assumptions were required?** Five explicit logical-topology mixtures: four pure mask classes and one equal mixture. They are researcher-declared assumptions, not physical PMFs or evidence.
28. **What is each architecture's scenario-space non-dominance fraction?** U0 = `{fractions['U0']}` and E0 = `{fractions['E0']}` under finite uniform counting over the five declared scenarios.
29. **Is that fraction a physical probability?** No. It is not yield, confidence, silicon optimality, or probability of winning.
30. **Is a global architecture winner qualified?** No: `NO_GLOBAL_WINNER_QUALIFIED`.
31. **What remains structurally blocked?** Physical event rate/PMF, complete bitcell mapping, Qcrit, absolute SDC/DUE/FIT, E5 and operation-separated energy, saturated throughput, routed I1/I2 overhead, SKY130 manufacturing/lifecycle carbon, CSCI, MRCC, and a qualified sustainability front.
32. **What is now the highest-value accessible next experiment?** An activity-complete, operation-isolated post-route campaign that satisfies `E5_ACTIVITY_COMPLETE_V3_2`, followed by matched routed I1/I2 experiments.
33. **What is the highest-value ultimate reliability experiment?** `MATCHED_SKY130_SRAM_PARTICLE_BEAM_EVENT_COORDINATES_FLUENCE_AND_VERIFIED_BITCELL_LOGICAL_MAP`.
34. **What claims are appropriate for ISCAS?** The evidence-aware cross-layer method; exact conditional logical-response surfaces; explicit boundary/compatibility guards; a reproducible five-seed diagnostic implementation demonstration; and exact conditional trade-space analysis with visible blockers.
35. **What claims remain forbidden?** Silicon or radiation validation, Qcrit, physical SKY130 SDC/DUE/SER/FIT, E5 energy, saturated throughput, routed interleaver benefit, absolute manufacturing/lifecycle carbon, CSCI/MRCC values, a qualified sustainability front, imec endorsement, or a global winner.

## Scientific interpretation

The established causal order is physical event topology -> logical corruption
-> ECC/interleaving response -> service outcome -> operational resource
consequence -> lifecycle consequence. `M_E` gates every transition. Missing
evidence stops downstream absolute claims, while exact conditional analysis is
retained inside its declared logical abstraction boundary.
"""


def _iscas_methodology(campaign_commit: str, status: Mapping[str, Any]) -> str:
    return f"""# ISCAS methodology summary: GREEN Matrix v3.2

Schema version: `{SCHEMA_VERSION}`

Campaign commit: `{campaign_commit}`

Parent campaign commit: `{PARENT_COMMIT}`

Generation date: `{GENERATED_AT}`

## Problem and gap

Semiconductor reliability/sustainability optimization commonly combines
quantities with radically different evidence quality. Open-PDK research flows
may lack the physical event occurrence, bitcell mapping, activity-complete
energy, and manufacturing inventory required for absolute decisions; replacing
them with logical injection frequency or transferred literature values creates
unsupported precision.

## Methodology and contribution

GREEN Matrix v3.2 represents each architecture/scenario as the vector
`[reliability consequence, operational resource consequence, physical
implementation cost, lifecycle consequence, evidence quality]`. Every operand
is carried by `M_E`; `M_P` contains implementation consequences; and `M_S`
returns `QUALIFIED`, `CONDITIONAL`, `DIAGNOSTIC`, or `BLOCKED` plus a blocking
set. Qualification checks tier and technology, process, PVT, measurement
boundary, workload/activity, architecture, spatial mapping, and lifecycle
compatibility. A high tier cannot override a boundary mismatch.

Contributions:

- executable guards separating event occurrence from conditional response;
- exact U0/E0 conditional response surfaces for four declared logical mask classes;
- exact diagnostic, conditional-scenario, and qualified-or-blocked Pareto objects;
- `SCENARIO_SPACE_NONDOMINANCE_FRACTION`, explicitly not a physical probability;
- an auditable all-of criterion for E5 activity completeness;
- dependency-traceable evidence records and fail-closed decision admissibility.

## Demonstration and result

The demonstration reuses the frozen v3.1 U0/E0 five-seed matched physical
population. It establishes conditional logical-response tradeoffs and E4
diagnostic implementation summaries. It does not establish E5 energy, a routed
I1/I2 interleaver, physical event rates, absolute SDC/DUE/FIT, Qcrit, SKY130
manufacturing/lifecycle carbon, CSCI/MRCC, a qualified sustainability front, or
a global winner. Final classification: `{status['classification']}`.

## Claim-to-evidence map

| Claim | Required evidence | Current status |
|---|---|---|
| Conditional ECC response | Exact logical patterns and decoder outcome | E3 `CONDITIONAL` |
| Implementation tradeoff | Matched routed U0/E0 population | E4 `DIAGNOSTIC` |
| Operation energy | Complete matched activity and isolated service window | `BLOCKED`, E4 only |
| Physical SDC/DUE/FIT | Matched event rate/PMF and verified spatial map | `BLOCKED` |
| Interleaver physical benefit | Routed I1/I2 plus verified topology map | `BLOCKED` |
| SKY130 manufacturing carbon | Matched manufacturing inventory/boundary | `BLOCKED` |
| CSCI/MRCC | Qualified reliability, energy, lifecycle, and lifetime operands | `BLOCKED` |
| Qualified sustainability front/global winner | Every declared mandatory dimension qualified | `BLOCKED` |

## Limitations and threats to validity

The logical mask classes are not measured physical topology distributions.
Vectorless power and partial-annotation energy are tool diagnostics with
residual v3.1 limitations. The finite scenario set is researcher-declared and
its uniform counting measure is not epistemic confidence. Macro dimensions and
SPICE instance counts do not establish bitcell XY or adjacency. Literature
records are technology/process/geometry mismatches. Manufacturing and lifetime
boundaries are incomplete. These limitations are encoded as guards rather than
hidden through imputation.

## Figure specification

```text
Physical Event Source [BLOCKED]
        |  M_E gate
        v
Topology / Physical Mapping [BLOCKED]
        |  M_E gate
        v
Logical Corruption [ANALYTICAL]
        |  M_E gate
        v
ECC + Interleaving Response [CONDITIONAL]
        |  M_E gate
        v
Service Outcome [CONDITIONAL]
        |  M_E gate
        v
Operational Cost [DIAGNOSTIC]
        |  M_E gate
        v
Lifecycle Scenario [BLOCKED]
```

Use solid green for measured, blue dashed for conditional, amber dotted for
diagnostic, and a red stop marker for blocked transitions. The sidecar
`data/FIGURE_SPECIFICATION.json` is the machine-readable source.

## Scientific principle

Unknown physical quantities remain unknown; exact conditional analysis is
reported only within its declared boundary. The method is informed by public
imec SSTS/imec.netzero bottom-up concepts, but no certification, compliance,
validation, standardization, endorsement, or SKY130 manufacturing datum from
imec is claimed.
"""


GENERATED_ARTIFACT_NAMES = (
    "data/EVIDENCE_MATRIX.json",
    "data/PHYSICAL_MATRIX.json",
    "data/SUSTAINABILITY_MATRIX.json",
    "data/CONDITIONAL_RELIABILITY.json",
    "data/SCENARIO_DEFINITIONS.json",
    "data/PARETO_ANALYSIS.json",
    "data/SCENARIO_ROBUSTNESS.json",
    "data/ENERGY_QUALIFICATION.json",
    "data/INTERLEAVER_FEASIBILITY.json",
    "data/BITCELL_MAPPING_AUDIT.json",
    "data/DECISION_ADMISSIBILITY.json",
    "data/QUALIFICATION_RULES.json",
    "data/LITERATURE_POLICY.json",
    "data/EQUATION_STATUS.json",
    "data/FIGURE_SPECIFICATION.json",
    "data/HISTORICAL_INTEGRITY.json",
    "data/VALUE_OF_INFORMATION.json",
    "CAMPAIGN_STATUS.json",
    "FINAL_REPORT.md",
    "ISCAS_METHODOLOGY.md",
)


def artifact_paths() -> list[Path]:
    return [BASE / name for name in GENERATED_ARTIFACT_NAMES]


def _artifact_hash_manifest(campaign_commit: str) -> dict[str, Any]:
    result = _envelope("ARTIFACT_HASH_MANIFEST", campaign_commit)
    records = [
        {
            "path": path.relative_to(BASE).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha(path),
        }
        for path in artifact_paths()
    ]
    result.update({"artifact_count": len(records), "artifacts": records, "self_excluded": True})
    return result


def build_all(*, campaign_commit: str = "UNCOMMITTED_VALIDATION_BUILD") -> dict[str, Any]:
    if not campaign_commit.strip():
        raise ValueError("campaign_commit must not be empty")
    parent_e = _load(PARENT / "MATRIX_E_V3_1.json")
    parent_p = _load(PARENT / "MATRIX_P_V3_1.json")
    parent_activity = _load(PARENT / "POST_ROUTE_ACTIVITY.json")
    parent_interleaver = _load(PARENT / "INTERLEAVER_PHYSICAL_RESULTS.json")
    parent_topology = _load(PARENT / "PHYSICAL_FAULT_TOPOLOGY.json")
    parent_literature = _load(PARENT / "LITERATURE_FAULT_EVIDENCE.json")

    population = _physical_population(parent_p)
    physical_summary = _physical_summary_evidence(population)
    conditional_evidence, conditional_body = _conditional_rows(parent_p)
    literature_evidence = _literature_evidence(parent_literature)
    blocked = _blocked_evidence()
    evidence = _evidence_matrix(
        campaign_commit,
        parent_e,
        physical_summary,
        conditional_evidence,
        literature_evidence,
        blocked,
    )
    conditional = _envelope("CONDITIONAL_RELIABILITY", campaign_commit)
    conditional.update(
        {
            **conditional_body,
            "causal_factorization": (
                "P(outcome/hour)=lambda(T_i)*P(outcome|T_i,a); only the conditional "
                "logical response term is populated"
            ),
            "event_occurrence_status": "UNKNOWN_UNQUALIFIED",
            "physical_mapping_status": "BLOCKED",
            "silicon_measurement_claim": False,
        }
    )
    physical = _physical_matrix(campaign_commit, population, physical_summary, parent_activity)
    admissibility_rows = _decision_admissibility_rows(blocked)
    decision = _envelope("DECISION_ADMISSIBILITY", campaign_commit)
    decision.update(
        {
            "decision_boundary": DECISION_BOUNDARY,
            "mandatory_metrics": [
                "PHYSICAL_EVENT_RATE",
                "PHYSICAL_SDC_RATE",
                "PHYSICAL_DUE_RATE",
                "NORMAL_READ_ENERGY",
                "SKY130_MANUFACTURING_CARBON",
                "LIFECYCLE_CARBON",
            ],
            "records": admissibility_rows,
            "qualified_decision_count": sum(row["qualified"] for row in admissibility_rows),
        }
    )
    sustainability = _sustainability_matrix(
        campaign_commit, physical, conditional, admissibility_rows
    )
    scenarios = _scenario_definitions(campaign_commit)
    pareto, robustness = _pareto_and_robustness(
        campaign_commit, scenarios, conditional, physical, admissibility_rows
    )
    energy = _energy_qualification(campaign_commit, parent_activity, population)
    interleaver = _interleaver_feasibility(campaign_commit, parent_interleaver)
    mapping = _bitcell_mapping_audit(campaign_commit, parent_topology)
    rules = _qualification_rules(campaign_commit)
    literature_policy = _literature_policy(campaign_commit, parent_literature)
    equation_status = _equation_status(campaign_commit)
    figure = _figure_specification(campaign_commit)
    history = _historical_integrity(campaign_commit)
    value = _value_of_information(campaign_commit)
    status = _campaign_status(
        campaign_commit,
        evidence,
        physical,
        sustainability,
        conditional,
        scenarios,
        robustness,
        energy,
        interleaver,
        pareto,
    )

    artifacts = {
        "data/EVIDENCE_MATRIX.json": evidence,
        "data/PHYSICAL_MATRIX.json": physical,
        "data/SUSTAINABILITY_MATRIX.json": sustainability,
        "data/CONDITIONAL_RELIABILITY.json": conditional,
        "data/SCENARIO_DEFINITIONS.json": scenarios,
        "data/PARETO_ANALYSIS.json": pareto,
        "data/SCENARIO_ROBUSTNESS.json": robustness,
        "data/ENERGY_QUALIFICATION.json": energy,
        "data/INTERLEAVER_FEASIBILITY.json": interleaver,
        "data/BITCELL_MAPPING_AUDIT.json": mapping,
        "data/DECISION_ADMISSIBILITY.json": decision,
        "data/QUALIFICATION_RULES.json": rules,
        "data/LITERATURE_POLICY.json": literature_policy,
        "data/EQUATION_STATUS.json": equation_status,
        "data/FIGURE_SPECIFICATION.json": figure,
        "data/HISTORICAL_INTEGRITY.json": history,
        "data/VALUE_OF_INFORMATION.json": value,
        "CAMPAIGN_STATUS.json": status,
    }
    for relative, content in artifacts.items():
        _write_json(BASE / relative, content)
    _write_text(BASE / "FINAL_REPORT.md", _final_report(campaign_commit, status, physical, energy, pareto, robustness))
    _write_text(BASE / "ISCAS_METHODOLOGY.md", _iscas_methodology(campaign_commit, status))
    _write_json(BASE / "FINAL_ARTIFACT_HASHES.json", _artifact_hash_manifest(campaign_commit))
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign-commit",
        default="UNCOMMITTED_VALIDATION_BUILD",
        help="validated campaign implementation commit recorded in every generated artifact",
    )
    args = parser.parse_args()
    status = build_all(campaign_commit=args.campaign_commit)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
