#!/usr/bin/env python3
"""Build provenance-aware GREEN, carbon, and Pareto campaign artifacts.

The builder deliberately separates measured values from assumptions.  It imports
the frozen Attempt09 matched physical results, conditionally imports a complete
five-seed research-corrected Liberty sensitivity view, and refuses to calculate
carbon or normalized objectives until every required evidence gate is satisfied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCRIPT = Path(__file__).resolve()
CAMPAIGN = SCRIPT.parents[1]
REPO = SCRIPT.parents[5]
ATTEMPT09 = CAMPAIGN.parent / "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"

MISSING = ("NOT_QUALIFIED", "NOT_MEASURED", "NOT_APPLICABLE", "PROVENANCE_LIMITED")
CANONICAL_SEEDS = (11, 13, 17, 19, 23)
ARCHITECTURES = ("U0", "E0")

PHYSICAL_COLUMNS = [
    "row_id",
    "architecture_id",
    "ecc_family",
    "ecc_parameters",
    "payload_bits",
    "stored_bits",
    "redundancy_bits",
    "code_rate",
    "memory_macro_configuration",
    "macro_width",
    "macro_depth",
    "macro_count",
    "bank_count",
    "interleaving_configuration",
    "technology",
    "pvt",
    "frequency",
    "seed",
    "liberty_model",
    "area_standard_cell_um2",
    "area_macro_um2",
    "area_total_um2",
    "core_area_um2",
    "utilization",
    "wirelength_um",
    "via_count",
    "setup_wns_ns",
    "hold_wns_ns",
    "max_frequency_estimate",
    "latency_ns",
    "power_internal_w",
    "power_switching_w",
    "power_leakage_w",
    "power_total_w",
    "power_evidence_level",
    "energy_read_j",
    "energy_write_j",
    "energy_access_j",
    "energy_evidence_level",
    "SER",
    "FIT",
    "SDC_rate",
    "DUE_rate",
    "corrected_error_rate",
    "uncorrectable_error_rate",
    "SBU_coverage",
    "DBU_coverage",
    "MBU_coverage",
    "burst_coverage",
    "scrub_policy",
    "scrub_interval",
    "embodied_carbon_kgCO2e",
    "operational_carbon_kgCO2e",
    "recovery_carbon_kgCO2e",
    "total_lifecycle_carbon_kgCO2e",
    "EPC",
    "ESII",
    "NESII",
    "GREEN_score",
    "evidence_quality",
    "qualification_status",
    "source_provenance",
    "source_artifact_sha256",
    "gate3_status",
    "external_drv_status",
    "class_c_provenance_status",
    "macro_internal_drc_status",
    "physical_lvs_status",
    "power_qualification",
    "energy_qualification",
]

CARBON_COLUMNS = [
    "carbon_row_id",
    "physical_row_id",
    "architecture_id",
    "liberty_model",
    "physical_seed",
    "workload_id",
    "workload_seed",
    "technology",
    "process_node_nm",
    "area_total_um2",
    "energy_access_j",
    "energy_evidence_level",
    "lifetime_years",
    "accesses_per_day",
    "total_lifetime_accesses",
    "grid_scenario",
    "grid_carbon_intensity_kgCO2e_per_kWh",
    "embodied_carbon_kgCO2e",
    "operational_carbon_kgCO2e",
    "recovery_carbon_kgCO2e",
    "total_lifecycle_carbon_kgCO2e",
    "embodied_qualification",
    "operational_qualification",
    "recovery_qualification",
    "carbon_qualification",
    "blocking_reasons",
    "source_provenance",
]

OBJECTIVES: dict[str, dict[str, str]] = {
    "energy_access_j": {"direction": "min", "unit": "J/access"},
    "total_lifecycle_carbon_kgCO2e": {"direction": "min", "unit": "kgCO2e/lifetime"},
    "area_total_um2": {"direction": "min", "unit": "um2"},
    "latency_ns": {"direction": "min", "unit": "ns"},
    "SDC_rate": {"direction": "min", "unit": "events/access"},
    "DUE_rate": {"direction": "min", "unit": "events/access"},
    "corrected_error_rate": {"direction": "max", "unit": "events/access"},
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    if isinstance(value, bool):
        return str(value).lower()
    return value


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: csv_value(row.get(column, "")) for column in columns})


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def first(mapping: Mapping[str, Any], names: Iterable[str], default: Any = "NOT_MEASURED") -> Any:
    for name in names:
        if name in mapping and mapping[name] is not None:
            return mapping[name]
    return default


def architecture_fields(architecture: str) -> dict[str, Any]:
    if architecture == "U0":
        return {
            "architecture_id": "U0",
            "ecc_family": "NONE_UNPROTECTED",
            "ecc_parameters": "NOT_APPLICABLE",
            "payload_bits": 64,
            "stored_bits": 64,
            "redundancy_bits": 0,
            "code_rate": 1.0,
            "memory_macro_configuration": [
                {"macro": "sram22_256x64m4w8", "width_bits": 64, "depth_words": 256, "count": 1}
            ],
            "macro_width": [64],
            "macro_depth": 256,
            "bank_count": "NOT_MEASURED",
            "interleaving_configuration": "I0_NO_EXPLICIT_PHYSICAL_BIT_INTERLEAVING",
        }
    if architecture == "E0":
        return {
            "architecture_id": "E0",
            "ecc_family": "HSIAO_SECDED",
            "ecc_parameters": {"n": 72, "k": 64, "minimum_distance": 4, "capability": "SEC-DED"},
            "payload_bits": 64,
            "stored_bits": 72,
            "redundancy_bits": 8,
            "code_rate": 64.0 / 72.0,
            "memory_macro_configuration": [
                {"macro": "sram22_256x64m4w8", "width_bits": 64, "depth_words": 256, "count": 1},
                {"macro": "sram22_256x8m8w1", "width_bits": 8, "depth_words": 256, "count": 1},
            ],
            "macro_width": [64, 8],
            "macro_depth": 256,
            "bank_count": "NOT_MEASURED",
            "interleaving_configuration": "I0_NO_EXPLICIT_PHYSICAL_BIT_INTERLEAVING",
        }
    raise ValueError(f"unknown architecture: {architecture}")


def missing_scientific_fields() -> dict[str, str]:
    fields = {
        "max_frequency_estimate": "NOT_MEASURED",
        "latency_ns": "NOT_MEASURED",
        "energy_read_j": "NOT_QUALIFIED",
        "energy_write_j": "NOT_QUALIFIED",
        "energy_access_j": "NOT_QUALIFIED",
        "energy_evidence_level": "NOT_QUALIFIED",
        "SER": "NOT_QUALIFIED",
        "FIT": "NOT_QUALIFIED",
        "SDC_rate": "NOT_QUALIFIED",
        "DUE_rate": "NOT_QUALIFIED",
        "corrected_error_rate": "NOT_QUALIFIED",
        "uncorrectable_error_rate": "NOT_QUALIFIED",
        "SBU_coverage": "NOT_QUALIFIED",
        "DBU_coverage": "NOT_QUALIFIED",
        "MBU_coverage": "NOT_QUALIFIED",
        "burst_coverage": "NOT_QUALIFIED",
        "scrub_policy": "NOT_MEASURED",
        "scrub_interval": "NOT_MEASURED",
        "embodied_carbon_kgCO2e": "NOT_QUALIFIED",
        "operational_carbon_kgCO2e": "NOT_QUALIFIED",
        "recovery_carbon_kgCO2e": "NOT_MEASURED",
        "total_lifecycle_carbon_kgCO2e": "NOT_QUALIFIED",
        "EPC": "NOT_QUALIFIED",
        "ESII": "NOT_QUALIFIED",
        "NESII": "NOT_QUALIFIED",
        "GREEN_score": "NOT_QUALIFIED",
    }
    return fields


def manifest_record(manifest: Mapping[str, Any], relative_path: str) -> Mapping[str, Any]:
    for record in manifest.get("files", []):
        if record.get("path") == relative_path:
            return record
    raise ValueError(f"Attempt09 evidence manifest does not contain {relative_path}")


def physical_row(
    architecture: str,
    seed: int,
    metrics: Mapping[str, Any],
    *,
    liberty_model: str,
    source_path: Path,
    source_pointer: str,
    source_hash: str,
    original_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    power = metrics.get("power_w") if isinstance(metrics.get("power_w"), Mapping) else {}
    fmax = first(metrics, ("max_frequency_estimate_hz", "max_frequency_estimate"))
    if is_number(fmax) and float(fmax) > 1e6:
        fmax = float(fmax) / 1e6
    row = {
        **architecture_fields(architecture),
        **missing_scientific_fields(),
        "row_id": f"{architecture}-{liberty_model}-seed{seed}",
        "technology": "SKY130HD_WITH_SRAM22_RESEARCH_MACROS",
        "pvt": "TT/25C/1.8V",
        "frequency": 100.0,
        "seed": seed,
        "liberty_model": liberty_model,
        "macro_count": first(metrics, ("macro_count",), 1 if architecture == "U0" else 2),
        "area_standard_cell_um2": first(metrics, ("standard_cell_area_um2", "area_standard_cell_um2")),
        "area_macro_um2": first(metrics, ("macro_area_um2", "area_macro_um2")),
        "area_total_um2": first(metrics, ("total_placed_design_area_um2", "area_total_um2")),
        "core_area_um2": first(metrics, ("core_area_um2",)),
        "utilization": first(metrics, ("achieved_utilization_fraction", "utilization")),
        "wirelength_um": first(metrics, ("wirelength_um",)),
        "via_count": first(metrics, ("vias", "via_count")),
        "setup_wns_ns": first(metrics, ("setup_wns_ns",)),
        "hold_wns_ns": first(metrics, ("worst_hold_slack_ns", "hold_wns_ns")),
        "max_frequency_estimate": fmax,
        "power_internal_w": first(power, ("internal", "power_internal_w"), first(metrics, ("power_internal_w",))),
        "power_switching_w": first(power, ("switching", "power_switching_w"), first(metrics, ("power_switching_w",))),
        "power_leakage_w": first(power, ("leakage", "power_leakage_w"), first(metrics, ("power_leakage_w",))),
        "power_total_w": first(power, ("total", "power_total_w"), first(metrics, ("power_total_w",))),
        "power_evidence_level": first(
            power,
            ("evidence_level",),
            first(metrics, ("power_evidence_level",), "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE"),
        ),
        "evidence_quality": "PROVENANCE_LIMITED_COMPARATIVE_POST_ROUTE_ESTIMATE",
        "qualification_status": "DIAGNOSTIC_ONLY_RESIDUAL_SRAM_INPUT_DRV_FAIL",
        "source_artifact_sha256": source_hash,
        "gate3_status": "FAIL_ATTEMPT09_FROZEN",
        "external_drv_status": "RESIDUAL_SRAM_INPUT_DRV_FAIL",
        "class_c_provenance_status": "PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV",
        "macro_internal_drc_status": "NOT_QUALIFIED",
        "physical_lvs_status": "NOT_INDEPENDENTLY_REPRODUCED",
        "power_qualification": "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE",
        "energy_qualification": "NOT_QUALIFIED",
    }
    provenance: dict[str, Any] = {
        "campaign": source_path.parent.name,
        "artifact": source_path.relative_to(REPO).as_posix(),
        "json_pointer": source_pointer,
        "artifact_sha256": source_hash,
    }
    if original_manifest is not None:
        record = manifest_record(original_manifest, source_path.name)
        provenance.update(
            {
                "attempt09_manifest": (ATTEMPT09 / "ATTEMPT09_EVIDENCE_MANIFEST.json").relative_to(REPO).as_posix(),
                "manifest_expected_sha256": record["sha256"],
                "manifest_hash_match": record["sha256"] == source_hash,
            }
        )
        if not provenance["manifest_hash_match"]:
            raise ValueError(f"frozen Attempt09 source hash mismatch: {source_path}")
    else:
        run_status = str(metrics.get("run_status", "COMPLETE"))
        external_count = metrics.get("genuine_external_slew_violations", "NOT_MEASURED")
        row.update(
            {
                "gate3_status": "FAIL_DIAGNOSTIC_NOT_ELIGIBLE_FOR_REASSESSMENT",
                "external_drv_status": (
                    f"FAIL_NON_OUTPUT_SLEW_VIOLATIONS_{external_count}"
                    if is_number(external_count) and external_count > 0
                    else ("ABORTED_UNCLOSED_RSTB_RSZ0090" if run_status == "ABORTED_RSZ_0090" else "NOT_MEASURED")
                ),
                "qualification_status": ("RESEARCH_CORRECTED_DIAGNOSTIC_ONLY" if run_status == "COMPLETE" else f"RESEARCH_CORRECTED_DIAGNOSTIC_{run_status}"),
                "class_c_provenance_status": "RESEARCH_CORRECTED_CHARACTERIZATION_CONSISTENT_DIAGNOSTIC",
            }
        )
    row["source_provenance"] = provenance
    return row


def _normal_token(value: Any) -> str:
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def _corrected_view(value: Any) -> bool:
    token = _normal_token(value)
    return (
        token == "RESEARCH_CORRECTED_DIAGNOSTIC"
        or token == "CORRECTED"
        or ("CORRECTED" in token and "COUNTERFACTUAL" not in token and "ORIGINAL" not in token)
    )


def extract_corrected_sensitivity(data: Any) -> tuple[dict[tuple[str, int], Mapping[str, Any]], list[str]]:
    """Find corrected U0/E0 per-seed records in flat or nested sensitivity JSON."""

    found: dict[tuple[str, int], tuple[int, Mapping[str, Any]]] = {}
    view_keys = {
        "ORIGINAL",
        "UPSTREAM_ORIGINAL",
        "UPSTREAM_ORIGINAL_LIBERTY",
        "CORRECTED",
        "RESEARCH_CORRECTED_DIAGNOSTIC",
        "PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL",
        "COUNTERFACTUAL",
    }
    metric_names = {
        "standard_cell_area_um2",
        "area_standard_cell_um2",
        "total_placed_design_area_um2",
        "area_total_um2",
        "wirelength_um",
        "setup_wns_ns",
        "worst_hold_slack_ns",
        "hold_wns_ns",
        "power_total_w",
        "power_w",
    }

    def walk(node: Any, context: dict[str, Any]) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, dict(context))
            return
        if not isinstance(node, Mapping):
            return
        here = dict(context)
        architecture = first(node, ("architecture_id", "architecture", "design"), None)
        if architecture is not None and _normal_token(architecture) in ARCHITECTURES:
            here["architecture"] = _normal_token(architecture)
        seed = first(node, ("seed", "physical_seed", "flow_seed"), None)
        if seed is not None:
            try:
                here["seed"] = int(seed)
            except (TypeError, ValueError):
                pass
        view = first(node, ("liberty_model", "view", "condition", "liberty_view", "model"), None)
        if view is not None:
            here["view"] = view
        if (
            here.get("architecture") in ARCHITECTURES
            and here.get("seed") in CANONICAL_SEEDS
            and _corrected_view(here.get("view", ""))
            and metric_names.intersection(node)
        ):
            score = sum(name in node for name in metric_names)
            key = (here["architecture"], here["seed"])
            if key not in found or score > found[key][0]:
                found[key] = (score, node)
        for key, child in node.items():
            child_context = dict(here)
            key_token = _normal_token(key)
            if key_token in ARCHITECTURES:
                child_context["architecture"] = key_token
            if key_token in view_keys or "COUNTERFACTUAL" in key_token or "CORRECTED" in key_token:
                child_context["view"] = key_token
            if key_token.startswith("SEED"):
                try:
                    child_context["seed"] = int(key_token.removeprefix("SEED").lstrip("_"))
                except ValueError:
                    pass
            walk(child, child_context)

    walk(data, {})
    # Attempt10's canonical flat rows include honest aborted rows without PPA
    # metrics.  Preserve these as NOT_MEASURED corrected-baseline records rather
    # than dropping the whole view.
    if isinstance(data, Mapping) and isinstance(data.get("rows"), list):
        for node in data["rows"]:
            if not isinstance(node, Mapping) or _normal_token(node.get("model", "")) != "CORRECTED":
                continue
            architecture = _normal_token(node.get("design", node.get("architecture_id", "")))
            try:
                seed = int(node.get("seed"))
            except (TypeError, ValueError):
                continue
            if architecture in ARCHITECTURES and seed in CANONICAL_SEEDS:
                found[(architecture, seed)] = (100, node)
    records = {key: value for key, (_, value) in found.items()}
    expected = {(architecture, seed) for architecture in ARCHITECTURES for seed in CANONICAL_SEEDS}
    missing = [f"{architecture}/seed{seed}" for architecture, seed in sorted(expected - records.keys())]
    return records, missing


def build_physical(
    *,
    attempt09_multiseed: Path,
    attempt09_manifest: Path,
    sensitivity_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    multi = load_json(attempt09_multiseed)
    manifest = load_json(attempt09_manifest)
    original_hash = sha256(attempt09_multiseed)
    manifest_record(manifest, attempt09_multiseed.name)
    rows: list[dict[str, Any]] = []
    source_seeds = {int(entry["seed"]): entry for entry in multi["seeds"]}
    if tuple(sorted(source_seeds)) != CANONICAL_SEEDS:
        raise ValueError(f"Attempt09 seed set changed: {sorted(source_seeds)}")
    for seed in CANONICAL_SEEDS:
        for architecture in ARCHITECTURES:
            rows.append(
                physical_row(
                    architecture,
                    seed,
                    source_seeds[seed][architecture],
                    liberty_model="UPSTREAM_ORIGINAL",
                    source_path=attempt09_multiseed,
                    source_pointer=f"/seeds/{list(CANONICAL_SEEDS).index(seed)}/{architecture}",
                    source_hash=original_hash,
                    original_manifest=manifest,
                )
            )

    sensitivity_meta: dict[str, Any] = {
        "path": sensitivity_path.relative_to(REPO).as_posix() if sensitivity_path.is_relative_to(REPO) else str(sensitivity_path),
        "status": "NOT_AVAILABLE_NOT_IMPORTED",
        "rows_imported": 0,
        "required_complete_keys": [f"{architecture}/seed{seed}" for seed in CANONICAL_SEEDS for architecture in ARCHITECTURES],
    }
    if sensitivity_path.exists():
        sensitivity_hash = sha256(sensitivity_path)
        sensitivity_data = load_json(sensitivity_path)
        records, missing = extract_corrected_sensitivity(sensitivity_data)
        flat_indices = {}
        if isinstance(sensitivity_data, Mapping):
            for index, item in enumerate(sensitivity_data.get("rows", [])):
                if isinstance(item, Mapping) and _normal_token(item.get("model", "")) == "CORRECTED":
                    try:
                        flat_indices[(_normal_token(item.get("design", "")), int(item.get("seed")))] = index
                    except (TypeError, ValueError):
                        pass
        sensitivity_meta.update({"sha256": sensitivity_hash, "missing_corrected_keys": missing})
        if missing:
            sensitivity_meta["status"] = "AVAILABLE_BUT_INCOMPLETE_NOT_IMPORTED"
        else:
            sensitivity_meta["status"] = "COMPLETE_KEYSET_RESEARCH_CORRECTED_DIAGNOSTIC_IMPORTED_WITH_EXPLICIT_ABORTED_ROWS"
            for seed in CANONICAL_SEEDS:
                for architecture in ARCHITECTURES:
                    rows.append(
                        physical_row(
                            architecture,
                            seed,
                            records[(architecture, seed)],
                            liberty_model="RESEARCH_CORRECTED_DIAGNOSTIC",
                            source_path=sensitivity_path,
                            source_pointer=(f"/rows/{flat_indices[(architecture, seed)]}" if (architecture, seed) in flat_indices else f"/corrected/{architecture}/seed{seed}"),
                            source_hash=sensitivity_hash,
                        )
                    )
            sensitivity_meta["rows_imported"] = 10

    meta = {
        "attempt09_source": {
            "path": attempt09_multiseed.relative_to(REPO).as_posix(),
            "sha256": original_hash,
            "manifest": attempt09_manifest.relative_to(REPO).as_posix(),
            "manifest_sha256": sha256(attempt09_manifest),
            "classification": multi["classification"],
        },
        "corrected_sensitivity": sensitivity_meta,
        "row_count": len(rows),
        "liberty_model_counts": dict(Counter(row["liberty_model"] for row in rows)),
    }
    return rows, meta


def schema() -> dict[str, Any]:
    numeric_or_missing = {"oneOf": [{"type": "number"}, {"enum": list(MISSING)}]}
    integer_or_missing = {"oneOf": [{"type": "integer"}, {"enum": list(MISSING)}]}
    structured_or_missing = {
        "oneOf": [{"type": "object"}, {"type": "array"}, {"enum": list(MISSING)}]
    }
    properties: dict[str, Any] = {column: {"type": "string"} for column in PHYSICAL_COLUMNS}
    units = {
        "payload_bits": "bit",
        "stored_bits": "bit",
        "redundancy_bits": "bit",
        "code_rate": "dimensionless",
        "macro_depth": "word",
        "macro_count": "macro",
        "frequency": "MHz",
        "area_standard_cell_um2": "um2",
        "area_macro_um2": "um2",
        "area_total_um2": "um2",
        "core_area_um2": "um2",
        "utilization": "fraction",
        "wirelength_um": "um",
        "via_count": "via",
        "setup_wns_ns": "ns",
        "hold_wns_ns": "ns",
        "max_frequency_estimate": "MHz",
        "latency_ns": "ns",
        "power_internal_w": "W",
        "power_switching_w": "W",
        "power_leakage_w": "W",
        "power_total_w": "W",
        "energy_read_j": "J/read",
        "energy_write_j": "J/write",
        "energy_access_j": "J/access",
        "SER": "errors/bit-hour",
        "FIT": "failures/1e9 device-hours",
        "SDC_rate": "events/access",
        "DUE_rate": "events/access",
        "corrected_error_rate": "events/access",
        "uncorrectable_error_rate": "events/access",
        "SBU_coverage": "fraction",
        "DBU_coverage": "fraction",
        "MBU_coverage": "fraction",
        "burst_coverage": "fraction",
        "scrub_interval": "s",
        "embodied_carbon_kgCO2e": "kgCO2e/lifetime allocation",
        "operational_carbon_kgCO2e": "kgCO2e/lifetime",
        "recovery_carbon_kgCO2e": "kgCO2e/lifetime",
        "total_lifecycle_carbon_kgCO2e": "kgCO2e/lifetime",
        "EPC": "J/corrected error",
        "ESII": "dimensionless",
        "NESII": "dimensionless [0,100]",
        "GREEN_score": "dimensionless [0,100]",
    }
    integer_fields = {"payload_bits", "stored_bits", "redundancy_bits", "macro_depth", "macro_count", "bank_count", "seed", "via_count"}
    structured_fields = {"ecc_parameters", "memory_macro_configuration", "macro_width", "source_provenance"}
    for name, unit in units.items():
        properties[name] = dict(integer_or_missing if name in integer_fields else numeric_or_missing)
        properties[name]["x-unit"] = unit
    # Seed is an integer provenance key rather than a measured quantity and is
    # therefore outside the units table, but it must still match the row type.
    properties["seed"] = dict(integer_or_missing)
    properties["seed"]["x-unit"] = "seed identifier"
    for name in structured_fields:
        properties[name] = dict(structured_or_missing)
    properties["architecture_id"] = {"enum": list(ARCHITECTURES)}
    properties["liberty_model"] = {
        "enum": ["UPSTREAM_ORIGINAL", "RESEARCH_CORRECTED_DIAGNOSTIC"]
    }
    properties["source_artifact_sha256"] = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "GREEN_MATRIX_SCHEMA.json",
        "title": "Attempt10 provenance-aware GREEN physical matrix",
        "description": "Schema for GREEN_MATRIX_PHYSICAL.json. Missing scientific evidence uses explicit sentinels; numeric zero is never used as a missing value.",
        "type": "object",
        "required": ["schema_version", "rows"],
        "properties": {
            "schema_version": {"const": 1},
            "row_count": {"type": "integer", "minimum": 0},
            "provenance": {"type": "object"},
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": PHYSICAL_COLUMNS,
                    "properties": properties,
                    "additionalProperties": False,
                },
            },
        },
        "additionalProperties": False,
        "x-missing-value-sentinels": list(MISSING),
        "x-claim-policy": "Only numeric values with a compatible qualified evidence field may enter carbon, normalization, or Pareto calculations.",
    }


def default_carbon_assumptions() -> dict[str, Any]:
    calibration_path = REPO / "carbon_calib.json"
    defaults_path = REPO / "carbon_defaults.json"
    calibration = load_json(calibration_path)
    region_provenance = calibration["grid_defaults"].get("region_provenance", {})
    scenarios = []
    for name, intensity in sorted(calibration["grid_defaults"]["regions_kgco2e_per_kwh"].items()):
        scenarios.append(
            {
                "id": name,
                "carbon_intensity_kgCO2e_per_kWh": intensity,
                "source": region_provenance.get(name, "unspecified in repository calibration"),
                "qualification_status": "PROVENANCE_LIMITED_REPOSITORY_PROXY",
                "use_for_claims": False,
            }
        )
    scenarios.extend(
        [
            {
                "id": "stress_test_best_case",
                "carbon_intensity_kgCO2e_per_kWh": calibration["grid_defaults"]["best_case_kgco2e_per_kwh"],
                "source": calibration["grid_defaults"].get("scenario_provenance", "unspecified"),
                "qualification_status": "PROVENANCE_LIMITED_STRESS_ENVELOPE",
                "use_for_claims": False,
            },
            {
                "id": "stress_test_worst_case",
                "carbon_intensity_kgCO2e_per_kWh": calibration["grid_defaults"]["worst_case_kgco2e_per_kwh"],
                "source": calibration["grid_defaults"].get("scenario_provenance", "unspecified"),
                "qualification_status": "PROVENANCE_LIMITED_STRESS_ENVELOPE",
                "use_for_claims": False,
            },
        ]
    )
    life = calibration["lifetime_defaults"]
    return {
        "schema_version": 1,
        "campaign_carbon_status": "NOT_QUALIFIED",
        "model_equations": {
            "embodied": "area_total_um2 * 1e-8 cm2/um2 * manufacturing_intensity_kgCO2e_per_cm2 * yield_allocation_factor * lifetime_allocation_factor",
            "operational": "energy_access_j * total_lifetime_accesses / 3.6e6 J/kWh * grid_carbon_intensity_kgCO2e_per_kWh",
            "recovery": "qualified recovery events and recovery energy/carbon model; unavailable in the current campaign",
            "total": "embodied + operational + recovery, only when all three terms are qualified",
        },
        "calibration_provenance": {
            "carbon_calib_path": calibration_path.relative_to(REPO).as_posix(),
            "carbon_calib_sha256": sha256(calibration_path),
            "carbon_defaults_path": defaults_path.relative_to(REPO).as_posix(),
            "carbon_defaults_sha256": sha256(defaults_path),
            "documentation": "docs/carbon_calibration.md",
            "preservation_policy": "READ_ONLY; no values changed by Attempt10",
            "warning": "carbon_defaults.json identifies its factors as placeholders; carbon_calib.json has no exact SKY130/130 nm manufacturing entry",
        },
        "technology": {
            "campaign_technology": "SKY130HD_WITH_SRAM22_RESEARCH_MACROS",
            "nominal_process_node_nm": 130,
            "exact_node_in_carbon_calib": False,
            "nearest_node_extrapolation_allowed": False,
            "qualification_status": "NOT_QUALIFIED_NO_EXACT_SKY130_MANUFACTURING_CALIBRATION",
        },
        "manufacturing": {
            "manufacturing_intensity_kgCO2e_per_cm2": "NOT_QUALIFIED",
            "yield_allocation_factor": "NOT_QUALIFIED",
            "lifetime_allocation_factor": "NOT_QUALIFIED",
            "qualification_status": "NOT_QUALIFIED",
            "use_for_claims": False,
        },
        "lifetime": {
            "years": life["years"],
            "accesses_per_day": life["accesses_per_day"],
            "total_lifetime_accesses": life["years"] * 365.0 * life["accesses_per_day"],
            "source": "carbon_calib.json repository default; no campaign-specific workload/lifetime justification",
            "qualification_status": "PROVENANCE_LIMITED_REPOSITORY_DEFAULT",
            "use_for_claims": False,
        },
        "grid": {
            "nominal_scenario": "global_avg",
            "scenarios": scenarios,
            "qualification_status": "PROVENANCE_LIMITED",
        },
        "recovery": {
            "model": "NOT_MEASURED",
            "recovery_carbon_kgCO2e_per_lifetime": "NOT_MEASURED",
            "qualification_status": "NOT_MEASURED",
            "use_for_claims": False,
        },
        "computation_gate": {
            "required": [
                "numeric physical area and explicit process identity",
                "exact process manufacturing calibration with source and claim authorization",
                "ACTIVITY_QUALIFIED energy/access matched to architecture, physical seed, and workload",
                "qualified lifetime accesses and grid intensity",
                "qualified or explicitly NOT_APPLICABLE recovery term",
            ],
            "nearest_node_fallback_for_campaign": False,
        },
    }


def ensure_carbon_assumptions(path: Path) -> dict[str, Any]:
    if not path.exists():
        write_json(path, default_carbon_assumptions())
    return load_json(path)


def grid_scenarios(assumptions: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scenarios = assumptions.get("grid", {}).get("scenarios", [])
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("carbon assumptions require at least one grid scenario")
    return scenarios


def carbon_row(
    physical: Mapping[str, Any],
    energy: Mapping[str, Any],
    assumptions: Mapping[str, Any],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    lifetime = assumptions["lifetime"]
    manufacturing = assumptions["manufacturing"]
    technology = assumptions["technology"]
    recovery = assumptions["recovery"]
    reasons: list[str] = []

    area = physical.get("area_total_um2")
    if not is_number(area):
        reasons.append("AREA_TOTAL_NOT_NUMERIC")
    exact_node = bool(technology.get("exact_node_in_carbon_calib", False))
    if not exact_node or not manufacturing.get("use_for_claims", False):
        reasons.append("SKY130_MANUFACTURING_ASSUMPTIONS_NOT_QUALIFIED")
    manufacturing_terms = (
        manufacturing.get("manufacturing_intensity_kgCO2e_per_cm2"),
        manufacturing.get("yield_allocation_factor"),
        manufacturing.get("lifetime_allocation_factor"),
    )
    if not all(is_number(value) for value in manufacturing_terms):
        reasons.append("MANUFACTURING_TERMS_NOT_NUMERIC")
    embodied_ok = not any(
        reason in reasons
        for reason in ("AREA_TOTAL_NOT_NUMERIC", "SKY130_MANUFACTURING_ASSUMPTIONS_NOT_QUALIFIED", "MANUFACTURING_TERMS_NOT_NUMERIC")
    )
    embodied = (
        float(area)
        * 1e-8
        * float(manufacturing_terms[0])
        * float(manufacturing_terms[1])
        * float(manufacturing_terms[2])
        if embodied_ok
        else "NOT_QUALIFIED"
    )

    energy_value = energy.get("energy_access_j", "NOT_QUALIFIED")
    energy_evidence = energy.get("energy_evidence_level", "NOT_QUALIFIED")
    if not is_number(energy_value) or energy_evidence not in {"ACTIVITY_QUALIFIED", "SIGNOFF_QUALIFIED"}:
        reasons.append("ENERGY_ACCESS_NOT_ACTIVITY_QUALIFIED")
    energy_seed = energy.get("physical_seed")
    if energy_seed not in {physical.get("seed"), str(physical.get("seed"))}:
        reasons.append("ENERGY_NOT_MATCHED_TO_PHYSICAL_SEED")
    if not lifetime.get("use_for_claims", False) or not is_number(lifetime.get("total_lifetime_accesses")):
        reasons.append("LIFETIME_WORKLOAD_NOT_QUALIFIED")
    if not scenario.get("use_for_claims", False) or not is_number(scenario.get("carbon_intensity_kgCO2e_per_kWh")):
        reasons.append("GRID_INTENSITY_NOT_QUALIFIED")
    operational_ok = not any(
        reason in reasons
        for reason in (
            "ENERGY_ACCESS_NOT_ACTIVITY_QUALIFIED",
            "ENERGY_NOT_MATCHED_TO_PHYSICAL_SEED",
            "LIFETIME_WORKLOAD_NOT_QUALIFIED",
            "GRID_INTENSITY_NOT_QUALIFIED",
        )
    )
    operational = (
        float(energy_value)
        * float(lifetime["total_lifetime_accesses"])
        / 3.6e6
        * float(scenario["carbon_intensity_kgCO2e_per_kWh"])
        if operational_ok
        else "NOT_QUALIFIED"
    )

    recovery_value = recovery.get("recovery_carbon_kgCO2e_per_lifetime")
    recovery_ok = recovery.get("use_for_claims", False) and is_number(recovery_value)
    if not recovery_ok:
        reasons.append("RECOVERY_CARBON_NOT_QUALIFIED")
    recovery_carbon = float(recovery_value) if recovery_ok else "NOT_MEASURED"
    total_ok = embodied_ok and operational_ok and recovery_ok
    total = float(embodied) + float(operational) + float(recovery_carbon) if total_ok else "NOT_QUALIFIED"

    row_id = f"{physical['row_id']}-{energy.get('workload_id', 'NOT_MEASURED')}-{scenario['id']}"
    return {
        "carbon_row_id": row_id,
        "physical_row_id": physical["row_id"],
        "architecture_id": physical["architecture_id"],
        "liberty_model": physical["liberty_model"],
        "physical_seed": physical["seed"],
        "workload_id": energy.get("workload_id", "NOT_MEASURED"),
        "workload_seed": energy.get("workload_seed", "NOT_MEASURED"),
        "technology": physical["technology"],
        "process_node_nm": technology.get("nominal_process_node_nm", "NOT_QUALIFIED"),
        "area_total_um2": area,
        "energy_access_j": energy_value,
        "energy_evidence_level": energy_evidence,
        "lifetime_years": lifetime.get("years", "NOT_QUALIFIED"),
        "accesses_per_day": lifetime.get("accesses_per_day", "NOT_QUALIFIED"),
        "total_lifetime_accesses": lifetime.get("total_lifetime_accesses", "NOT_QUALIFIED"),
        "grid_scenario": scenario["id"],
        "grid_carbon_intensity_kgCO2e_per_kWh": scenario.get("carbon_intensity_kgCO2e_per_kWh", "NOT_QUALIFIED"),
        "embodied_carbon_kgCO2e": embodied,
        "operational_carbon_kgCO2e": operational,
        "recovery_carbon_kgCO2e": recovery_carbon,
        "total_lifecycle_carbon_kgCO2e": total,
        "embodied_qualification": "QUALIFIED" if embodied_ok else "NOT_QUALIFIED",
        "operational_qualification": "QUALIFIED" if operational_ok else "NOT_QUALIFIED",
        "recovery_qualification": "QUALIFIED" if recovery_ok else recovery.get("qualification_status", "NOT_MEASURED"),
        "carbon_qualification": "QUALIFIED" if total_ok else "NOT_QUALIFIED",
        "blocking_reasons": reasons,
        "source_provenance": {
            "physical_row": physical["row_id"],
            "physical_source_sha256": physical["source_artifact_sha256"],
            "energy_results": "energy/ENERGY_RESULTS.json",
            "energy_results_sha256": sha256(CAMPAIGN / "energy" / "ENERGY_RESULTS.json") if (CAMPAIGN / "energy" / "ENERGY_RESULTS.json").exists() else "NOT_MEASURED",
            "carbon_assumptions": "carbon/CARBON_ASSUMPTIONS.json",
        },
    }


def placeholder_energy(architecture: str) -> dict[str, Any]:
    return {
        "architecture_id": architecture,
        "workload_id": "NOT_MEASURED",
        "workload_seed": "NOT_MEASURED",
        "physical_seed": "NOT_MEASURED",
        "energy_access_j": "NOT_QUALIFIED",
        "energy_read_j": "NOT_QUALIFIED",
        "energy_write_j": "NOT_QUALIFIED",
        "energy_evidence_level": "NOT_QUALIFIED",
    }


def build_carbon(
    physical_rows: Sequence[Mapping[str, Any]],
    energy_path: Path,
    assumptions: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    energy_rows = load_json(energy_path).get("rows", []) if energy_path.exists() else []
    by_arch: dict[str, list[Mapping[str, Any]]] = {architecture: [] for architecture in ARCHITECTURES}
    for row in energy_rows:
        if row.get("architecture_id") in by_arch:
            by_arch[row["architecture_id"]].append(row)
    for architecture in ARCHITECTURES:
        if not by_arch[architecture]:
            by_arch[architecture] = [placeholder_energy(architecture)]
    scenarios = grid_scenarios(assumptions)
    nominal_id = assumptions["grid"].get("nominal_scenario")
    nominal = next((scenario for scenario in scenarios if scenario.get("id") == nominal_id), scenarios[0])
    results: list[dict[str, Any]] = []
    sensitivity: list[dict[str, Any]] = []
    for physical in physical_rows:
        for energy in by_arch[physical["architecture_id"]]:
            results.append(carbon_row(physical, energy, assumptions, nominal))
            for scenario in scenarios:
                sensitivity.append(carbon_row(physical, energy, assumptions, scenario))
    meta = {
        "energy_source_status": "AVAILABLE" if energy_path.exists() else "NOT_AVAILABLE",
        "energy_source_sha256": sha256(energy_path) if energy_path.exists() else "NOT_MEASURED",
        "physical_rows": len(physical_rows),
        "energy_rows": len(energy_rows),
        "result_rows": len(results),
        "sensitivity_rows": len(sensitivity),
        "qualified_result_rows": sum(row["carbon_qualification"] == "QUALIFIED" for row in results),
    }
    return results, sensitivity, meta


def qualification_failures(row: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    for metric in OBJECTIVES:
        value = row.get(metric)
        if not is_number(value):
            failures.append(f"{metric}:VALUE_NOT_NUMERIC_OR_ABSENT")
            continue
        if metric == "energy_access_j" and row.get("energy_evidence_level") not in {"ACTIVITY_QUALIFIED", "SIGNOFF_QUALIFIED"}:
            failures.append(f"{metric}:EVIDENCE_NOT_QUALIFIED")
        elif metric == "total_lifecycle_carbon_kgCO2e" and row.get("carbon_qualification") != "QUALIFIED":
            failures.append(f"{metric}:EVIDENCE_NOT_QUALIFIED")
        elif metric in {"SDC_rate", "DUE_rate", "corrected_error_rate"} and row.get("reliability_qualification") not in {
            "PHYSICAL_RELIABILITY_QUALIFIED",
            "SIGNOFF_QUALIFIED",
        }:
            failures.append(f"{metric}:EVIDENCE_NOT_QUALIFIED")
        elif metric == "latency_ns" and row.get("latency_qualification") not in {
            "COMPARATIVE_POST_ROUTE_ESTIMATE",
            "SIGNOFF_QUALIFIED",
        }:
            failures.append(f"{metric}:EVIDENCE_NOT_QUALIFIED")
    return failures


def build_raw_matrix(
    physical_rows: Sequence[Mapping[str, Any]],
    energy_path: Path,
    reliability_path: Path,
    carbon_results: Sequence[Mapping[str, Any]],
    nominal_grid_scenario: str,
) -> list[dict[str, Any]]:
    energies = load_json(energy_path).get("rows", []) if energy_path.exists() else []
    reliabilities = load_json(reliability_path).get("rows", []) if reliability_path.exists() else []
    energy_by_arch = {architecture: [] for architecture in ARCHITECTURES}
    reliability_by_arch = {architecture: [] for architecture in ARCHITECTURES}
    for row in energies:
        if row.get("architecture_id") in energy_by_arch:
            energy_by_arch[row["architecture_id"]].append(row)
    for row in reliabilities:
        if row.get("architecture_id") in reliability_by_arch:
            reliability_by_arch[row["architecture_id"]].append(row)
    for architecture in ARCHITECTURES:
        energy_by_arch[architecture] = energy_by_arch[architecture] or [placeholder_energy(architecture)]
        reliability_by_arch[architecture] = reliability_by_arch[architecture] or [
            {
                "architecture_id": architecture,
                "interleaving_configuration": "NOT_MEASURED",
                "fault_family": "NOT_MEASURED",
                "scrub_policy": "NOT_MEASURED",
                "scrub_interval": "NOT_MEASURED",
                "qualification_status": "NOT_QUALIFIED",
            }
        ]
    carbon_index = {
        (row["physical_row_id"], row["workload_id"], row["grid_scenario"]): row
        for row in carbon_results
    }
    raw: list[dict[str, Any]] = []
    reliability_fields = (
        "SER",
        "FIT",
        "SDC_rate",
        "DUE_rate",
        "corrected_error_rate",
        "uncorrectable_error_rate",
        "SBU_coverage",
        "DBU_coverage",
        "MBU_coverage",
        "burst_coverage",
    )
    energy_fields = ("energy_read_j", "energy_write_j", "energy_access_j", "energy_evidence_level")
    for physical in physical_rows:
        architecture = physical["architecture_id"]
        for energy in energy_by_arch[architecture]:
            carbon = carbon_index[(physical["row_id"], energy.get("workload_id", "NOT_MEASURED"), nominal_grid_scenario)]
            for reliability in reliability_by_arch[architecture]:
                row = dict(physical)
                for name in energy_fields:
                    row[name] = energy.get(name, row.get(name, "NOT_QUALIFIED"))
                for name in reliability_fields:
                    row[name] = reliability.get(name, row.get(name, "NOT_QUALIFIED"))
                row.update(
                    {
                        "row_id": "|".join(
                            [
                                physical["row_id"],
                                str(energy.get("workload_id", "NOT_MEASURED")),
                                str(reliability.get("interleaving_configuration", "NOT_MEASURED")),
                                str(reliability.get("fault_family", "NOT_MEASURED")),
                                str(reliability.get("scrub_policy", "NOT_MEASURED")),
                                str(reliability.get("scrub_interval", "NOT_MEASURED")),
                            ]
                        ),
                        "physical_row_id": physical["row_id"],
                        "workload_id": energy.get("workload_id", "NOT_MEASURED"),
                        "workload_seed": energy.get("workload_seed", "NOT_MEASURED"),
                        "activity_evidence_level": energy.get("activity_evidence_level", "NOT_MEASURED"),
                        "interleaving_configuration": reliability.get("interleaving_configuration", "NOT_MEASURED"),
                        "fault_family": reliability.get("fault_family", "NOT_MEASURED"),
                        "scrub_policy": reliability.get("scrub_policy", "NOT_MEASURED"),
                        "scrub_interval": reliability.get("scrub_interval", "NOT_MEASURED"),
                        "reliability_qualification": reliability.get("qualification_status", "NOT_QUALIFIED"),
                        "latency_qualification": "NOT_QUALIFIED",
                        "embodied_carbon_kgCO2e": carbon["embodied_carbon_kgCO2e"],
                        "operational_carbon_kgCO2e": carbon["operational_carbon_kgCO2e"],
                        "recovery_carbon_kgCO2e": carbon["recovery_carbon_kgCO2e"],
                        "total_lifecycle_carbon_kgCO2e": carbon["total_lifecycle_carbon_kgCO2e"],
                        "carbon_qualification": carbon["carbon_qualification"],
                        "carbon_row_id": carbon["carbon_row_id"],
                        "energy_source_provenance": "energy/ENERGY_RESULTS.json",
                        "reliability_source_provenance": "green_matrix/GREEN_MATRIX_RELIABILITY.json",
                    }
                )
                failures = qualification_failures(row)
                row["raw_matrix_eligibility"] = "ELIGIBLE" if not failures else "INELIGIBLE"
                row["missing_or_unqualified_objectives"] = failures
                raw.append(row)
    return raw


def quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot calculate quantile of empty values")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def normalize_rows(raw_rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    eligible = [row for row in raw_rows if not qualification_failures(row)]
    excluded = [
        {"row_id": row["row_id"], "reasons": qualification_failures(row)}
        for row in raw_rows
        if qualification_failures(row)
    ]
    metadata: dict[str, Any] = {
        "method": "5th/95th percentile winsorization followed by direction-aware min-max scaling",
        "normalized_orientation": "0=best, 1=worst for every objective",
        "source_units_validated": bool(eligible),
        "eligible_row_count": len(eligible),
        "excluded_row_count": len(excluded),
        "excluded_rows": excluded,
        "bounds": {},
    }
    if not eligible:
        metadata["status"] = "BLOCKED_NO_FULLY_QUALIFIED_ROWS"
        return [], metadata
    bounds: dict[str, tuple[float, float]] = {}
    for metric, objective in OBJECTIVES.items():
        values = [float(row[metric]) for row in eligible]
        lower, upper = quantile(values, 0.05), quantile(values, 0.95)
        bounds[metric] = (lower, upper)
        metadata["bounds"][metric] = {
            "lower_p05": lower,
            "upper_p95": upper,
            "observed_min": min(values),
            "observed_max": max(values),
            **objective,
        }
    normalized = []
    for source in eligible:
        row: dict[str, Any] = {
            "row_id": source["row_id"],
            "architecture_id": source["architecture_id"],
            "liberty_model": source["liberty_model"],
            "seed": source["seed"],
            "workload_id": source.get("workload_id", "NOT_MEASURED"),
            "interleaving_configuration": source.get("interleaving_configuration", "NOT_MEASURED"),
            "fault_family": source.get("fault_family", "NOT_MEASURED"),
            "scrub_policy": source.get("scrub_policy", "NOT_MEASURED"),
            "normalization_eligible": True,
        }
        for metric, objective in OBJECTIVES.items():
            lower, upper = bounds[metric]
            clipped = min(upper, max(lower, float(source[metric])))
            scaled = 0.0 if upper == lower else (clipped - lower) / (upper - lower)
            if objective["direction"] == "max":
                scaled = 1.0 - scaled
            row[f"normalized_{metric}"] = scaled
        normalized.append(row)
    metadata["status"] = "NORMALIZED_QUALIFIED_ROWS"
    return normalized, metadata


def dominates(left: Mapping[str, Any], right: Mapping[str, Any], eps: float = 1e-12) -> bool:
    strictly = False
    for metric, objective in OBJECTIVES.items():
        lv, rv = float(left[metric]), float(right[metric])
        if objective["direction"] == "min":
            if lv > rv + eps:
                return False
            strictly = strictly or lv < rv - eps
        else:
            if lv < rv - eps:
                return False
            strictly = strictly or lv > rv + eps
    return strictly


def pareto_partition(rows: Sequence[Mapping[str, Any]]) -> tuple[list[int], list[int]]:
    frontier: list[int] = []
    dominated_rows: list[int] = []
    for index, row in enumerate(rows):
        if any(dominates(other, row) for other_index, other in enumerate(rows) if other_index != index):
            dominated_rows.append(index)
        else:
            frontier.append(index)
    return frontier, dominated_rows


def build_pareto(
    raw_rows: Sequence[Mapping[str, Any]], normalized_rows: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    eligible = [row for row in raw_rows if not qualification_failures(row)]
    frontier_indices, dominated_indices = pareto_partition(eligible) if eligible else ([], [])
    frontier_ids = {eligible[index]["row_id"] for index in frontier_indices}
    dominated_ids = {eligible[index]["row_id"] for index in dominated_indices}
    csv_rows: list[dict[str, Any]] = []
    exclusions = []
    for row in raw_rows:
        reasons = qualification_failures(row)
        if reasons:
            classification = "EXCLUDED_UNQUALIFIED"
            exclusions.append({"row_id": row["row_id"], "reasons": reasons})
        elif row["row_id"] in frontier_ids:
            classification = "PARETO_FRONTIER"
        elif row["row_id"] in dominated_ids:
            classification = "DOMINATED"
        else:
            raise AssertionError("eligible row was not partitioned")
        csv_rows.append(
            {
                "row_id": row["row_id"],
                "architecture_id": row["architecture_id"],
                "liberty_model": row["liberty_model"],
                "seed": row["seed"],
                "workload_id": row.get("workload_id", "NOT_MEASURED"),
                "interleaving_configuration": row.get("interleaving_configuration", "NOT_MEASURED"),
                "fault_family": row.get("fault_family", "NOT_MEASURED"),
                "scrub_policy": row.get("scrub_policy", "NOT_MEASURED"),
                "pareto_eligible": not reasons,
                "classification": classification,
                "missing_or_unqualified_objectives": reasons,
            }
        )
    normalized_index = {row["row_id"]: row for row in normalized_rows}
    scenario_winner: Any = "NOT_QUALIFIED"
    if eligible and all(row["row_id"] in normalized_index for row in eligible):
        scenario_winner = min(
            eligible,
            key=lambda row: (
                sum(normalized_index[row["row_id"]][f"normalized_{metric}"] for metric in OBJECTIVES),
                row["row_id"],
            ),
        )["row_id"]
    payload = {
        "schema_version": 1,
        "status": "COMPUTED" if eligible else "BLOCKED_NO_FULLY_QUALIFIED_ROWS",
        "method": "exact deterministic non-dominated sorting; NSGA-II is unnecessary for this finite enumerated matrix and is not run while evidence is blocked",
        "objectives": OBJECTIVES,
        "eligible_row_count": len(eligible),
        "excluded_row_count": len(exclusions),
        "frontier_row_ids": sorted(frontier_ids),
        "dominated_row_ids": sorted(dominated_ids),
        "excluded_rows": exclusions,
        "hypervolume": "NOT_COMPUTED_NO_QUALIFIED_NORMALIZED_FRONT" if not eligible else "NOT_COMPUTED_HIGH_DIMENSION_EXACT_FRONT",
        "knee_point": "NOT_COMPUTED_NO_QUALIFIED_NORMALIZED_FRONT" if not eligible else "NOT_COMPUTED_REQUIRES_PREREGISTERED_PROJECTION",
        "scenario_dependent_winner": scenario_winner,
        "static_selector_baseline": {
            "status": "PRESERVED_UNMODIFIED",
            "implementation": "existing deterministic selector outside Attempt10",
            "comparison": "NOT_QUALIFIED",
        },
    }
    return payload, csv_rows


def all_raw_columns(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    preferred = PHYSICAL_COLUMNS + [
        "physical_row_id",
        "workload_id",
        "workload_seed",
        "activity_evidence_level",
        "fault_family",
        "reliability_qualification",
        "latency_qualification",
        "carbon_qualification",
        "carbon_row_id",
        "energy_source_provenance",
        "reliability_source_provenance",
        "raw_matrix_eligibility",
        "missing_or_unqualified_objectives",
    ]
    seen: set[str] = set()
    return [name for name in preferred if not (name in seen or seen.add(name))]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensitivity", type=Path, default=CAMPAIGN / "liberty" / "LIBERTY_SENSITIVITY_RESULTS.json")
    parser.add_argument("--carbon-assumptions", type=Path, default=CAMPAIGN / "carbon" / "CARBON_ASSUMPTIONS.json")
    args = parser.parse_args(argv)

    green_dir = CAMPAIGN / "green_matrix"
    carbon_dir = CAMPAIGN / "carbon"
    pareto_dir = CAMPAIGN / "pareto"
    energy_path = CAMPAIGN / "energy" / "ENERGY_RESULTS.json"
    reliability_path = green_dir / "GREEN_MATRIX_RELIABILITY.json"

    physical_rows, physical_meta = build_physical(
        attempt09_multiseed=ATTEMPT09 / "MULTISEED_EXTERNAL_CLOSURE.json",
        attempt09_manifest=ATTEMPT09 / "ATTEMPT09_EVIDENCE_MANIFEST.json",
        sensitivity_path=args.sensitivity.resolve(),
    )
    write_json(green_dir / "GREEN_MATRIX_SCHEMA.json", schema())
    write_json(
        green_dir / "GREEN_MATRIX_PHYSICAL.json",
        {"schema_version": 1, "row_count": len(physical_rows), "provenance": physical_meta, "rows": physical_rows},
    )
    write_csv(green_dir / "GREEN_MATRIX_PHYSICAL.csv", physical_rows, PHYSICAL_COLUMNS)

    assumptions = ensure_carbon_assumptions(args.carbon_assumptions.resolve())
    carbon_results, sensitivity_rows, carbon_meta = build_carbon(physical_rows, energy_path, assumptions)
    write_json(
        carbon_dir / "CARBON_RESULTS.json",
        {
            "schema_version": 1,
            "status": "QUALIFIED" if carbon_meta["qualified_result_rows"] else "NOT_QUALIFIED",
            "provenance": carbon_meta,
            "rows": carbon_results,
        },
    )
    write_csv(carbon_dir / "CARBON_RESULTS.csv", carbon_results, CARBON_COLUMNS)
    write_csv(carbon_dir / "CARBON_SENSITIVITY.csv", sensitivity_rows, CARBON_COLUMNS)

    raw_rows = build_raw_matrix(
        physical_rows,
        energy_path,
        reliability_path,
        carbon_results,
        assumptions["grid"]["nominal_scenario"],
    )
    normalized_rows, normalization = normalize_rows(raw_rows)
    raw_columns = all_raw_columns(raw_rows)
    normalized_columns = [
        "row_id",
        "architecture_id",
        "liberty_model",
        "seed",
        "workload_id",
        "interleaving_configuration",
        "fault_family",
        "scrub_policy",
        "normalization_eligible",
        *[f"normalized_{metric}" for metric in OBJECTIVES],
    ]
    write_csv(green_dir / "GREEN_MATRIX_RAW.csv", raw_rows, raw_columns)
    write_csv(green_dir / "GREEN_MATRIX_NORMALIZED.csv", normalized_rows, normalized_columns)
    source_hashes = {
        "GREEN_MATRIX_PHYSICAL.json": sha256(green_dir / "GREEN_MATRIX_PHYSICAL.json"),
        "ENERGY_RESULTS.json": sha256(energy_path) if energy_path.exists() else "NOT_MEASURED",
        "GREEN_MATRIX_RELIABILITY.json": sha256(reliability_path) if reliability_path.exists() else "NOT_MEASURED",
        "CARBON_RESULTS.json": sha256(carbon_dir / "CARBON_RESULTS.json"),
    }
    write_json(
        green_dir / "GREEN_MATRIX_METADATA.json",
        {
            "schema_version": 1,
            "raw_matrix": {
                "row_grain": "physical architecture/liberty/seed x workload x interleaving/fault/scrub scenario",
                "row_count": len(raw_rows),
                "eligible_row_count": sum(row["raw_matrix_eligibility"] == "ELIGIBLE" for row in raw_rows),
                "join_policy": "architecture identity; evidence remains unqualified unless physical seed and scenario traceability also match",
            },
            "normalization": normalization,
            "objectives": OBJECTIVES,
            "source_hashes": source_hashes,
            "score_policy": "EPC, ESII, NESII, and GREEN_score remain NOT_QUALIFIED until their full evidence inputs and reference cohort are qualified",
        },
    )

    pareto_payload, pareto_rows = build_pareto(raw_rows, normalized_rows)
    write_json(pareto_dir / "PARETO_RESULTS.json", pareto_payload)
    write_csv(
        pareto_dir / "PARETO_RESULTS.csv",
        pareto_rows,
        [
            "row_id",
            "architecture_id",
            "liberty_model",
            "seed",
            "workload_id",
            "interleaving_configuration",
            "fault_family",
            "scrub_policy",
            "pareto_eligible",
            "classification",
            "missing_or_unqualified_objectives",
        ],
    )
    (carbon_dir / "CARBON_MODEL.md").write_text(
        "# Attempt10 carbon model\n\n"
        "The model separates embodied, operational, recovery, and total lifecycle carbon. "
        "Equations and units are machine-readable in `CARBON_ASSUMPTIONS.json`. Embodied carbon requires a SKY130-specific manufacturing intensity, yield allocation, and lifetime allocation; none is supplied. Operational carbon requires activity-qualified energy/access plus a qualified lifetime workload and grid factor. Recovery carbon requires a recovery-event model.\n\n"
        "The repository's `carbon_calib.json` and `carbon_defaults.json` are hashed and preserved read-only. Their grid values are retained as provenance-limited sensitivity scenarios, but the nearest-node fallback is disabled because it would substitute 28 nm data for SKY130. The activity study has incomplete mapped-net coverage and no validated SRAM internal-energy characterization. Consequently embodied, operational, recovery, and total carbon remain **NOT_QUALIFIED**. `CARBON_SENSITIVITY.csv` records the full grid/workload scenario space without promoting those scenarios to claims.\n\n"
        "No instantaneous power is multiplied by an arbitrary time. No carbon value enters normalization or selection until every computation gate is satisfied.\n",
        encoding="utf-8",
    )
    (pareto_dir / "PARETO_ANALYSIS.md").write_text(
        "# Attempt10 Pareto analysis\n\n"
        f"The raw matrix contains {len(raw_rows)} scenario rows. None has the complete, unit-validated energy, lifecycle-carbon, latency, and physical-reliability evidence required by the declared objective set, so the eligible set is empty. The normalized matrix retains explicit ineligibility markers and no scores.\n\n"
        "`PARETO_RESULTS.json` therefore reports no frontier, dominated solutions, hypervolume, knee point, or scenario winner. Exact deterministic non-dominated sorting is implemented for a future qualified finite matrix; NSGA-II is unnecessary for an enumerated set and is not run on missing evidence. The repository's deterministic selector remains the baseline and is unchanged.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
