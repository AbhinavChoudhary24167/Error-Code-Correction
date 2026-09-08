"""Build the qualification-preserving GREEN matrix v2.

The Attempt10 logical-control fractions are finite experiment summaries, not
physical event probabilities.  This builder therefore carries them in
diagnostic columns while leaving service, reliability-rate, carbon, and GREEN
metric fields empty until their evidence gates are satisfied.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable


BASE = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE / "green_matrix_v2"
SEED = 20260908

EVIDENCE_CLASSES = (
    "MEASURED",
    "TOOL_ESTIMATE",
    "SOURCE_CALIBRATED",
    "DERIVED",
    "PARAMETRIC",
    "EXTRAPOLATED",
    "BOUND",
    "NOT_QUALIFIED",
    "NOT_MEASURED",
)

REQUIRED_V2_FIELDS = (
    "metric_version",
    "functional_unit",
    "service_success_probability",
    "useful_service_bits",
    "GSE",
    "GCI",
    "GSE_relative",
    "technology_node",
    "process_route",
    "wafer_diameter",
    "fab_grid",
    "fab_CI",
    "process_maturity",
    "wafer_carbon",
    "wafer_energy",
    "scope1_carbon",
    "scope2_carbon",
    "upstream_carbon",
    "patterning_carbon",
    "lithography_route",
    "mask_layer_count",
    "multi_patterning_count",
    "maskset_NRE",
    "maskset_NRE_evidence",
    "yield",
    "yield_model",
    "defect_density",
    "gross_dies_per_wafer",
    "good_dies_per_wafer",
    "die_embodied_carbon",
    "incremental_ECC_embodied_carbon",
    "operational_energy",
    "operational_carbon",
    "lifecycle_carbon",
    "interleaving_id",
    "fault_topology_id",
    "scrub_policy",
    "SDC",
    "DUE",
    "corrected",
    "retry",
    "service_success",
    "evidence_tier",
    "uncertainty_class",
    "source_ids",
)

NUMERIC_FIELDS = (
    "service_success_probability",
    "useful_service_bits",
    "GSE",
    "GCI",
    "GSE_relative",
    "wafer_diameter",
    "fab_CI",
    "wafer_carbon",
    "wafer_energy",
    "scope1_carbon",
    "scope2_carbon",
    "upstream_carbon",
    "patterning_carbon",
    "mask_layer_count",
    "multi_patterning_count",
    "maskset_NRE",
    "yield",
    "defect_density",
    "gross_dies_per_wafer",
    "good_dies_per_wafer",
    "die_embodied_carbon",
    "incremental_ECC_embodied_carbon",
    "operational_energy",
    "operational_carbon",
    "lifecycle_carbon",
    "SDC",
    "DUE",
    "corrected",
    "retry",
    "service_success",
    "latency_ns",
    "observed_macro_area_um2",
    "activity_coverage_fraction",
    "diagnostic_tool_power_w",
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
)

UNITS = {
    "service_success_probability": "probability",
    "useful_service_bits": "correct_payload_bits",
    "GSE": "correct_payload_bits_per_kgCO2e",
    "GCI": "kgCO2e_per_correct_payload_bit",
    "GSE_relative": "ratio_to_matched_U0",
    "wafer_diameter": "mm",
    "fab_CI": "kgCO2e_per_kWh",
    "wafer_carbon": "kgCO2e_per_wafer",
    "wafer_energy": "kWh_per_wafer",
    "scope1_carbon": "kgCO2e_per_wafer",
    "scope2_carbon": "kgCO2e_per_wafer",
    "upstream_carbon": "kgCO2e_per_wafer",
    "patterning_carbon": "kgCO2e_per_wafer_diagnostic_subset",
    "mask_layer_count": "count",
    "multi_patterning_count": "count",
    "maskset_NRE": "kgCO2e_per_die",
    "yield": "fraction",
    "defect_density": "defects_per_cm2",
    "gross_dies_per_wafer": "expected_count",
    "good_dies_per_wafer": "expected_count",
    "die_embodied_carbon": "kgCO2e_per_good_die",
    "incremental_ECC_embodied_carbon": "kgCO2e_per_good_die",
    "operational_energy": "J_per_declared_service_horizon",
    "operational_carbon": "kgCO2e_per_declared_service_horizon",
    "lifecycle_carbon": "kgCO2e_per_declared_service_horizon",
    "SDC": "physical_event_probability",
    "DUE": "physical_event_probability",
    "corrected": "physical_event_probability",
    "retry": "physical_event_probability",
    "service_success": "physical_event_probability",
    "latency_ns": "ns",
    "observed_macro_area_um2": "um2",
    "activity_coverage_fraction": "fraction",
    "diagnostic_tool_power_w": "W",
    "logical_pattern_count": "count",
    "logical_success_normal_count": "count",
    "logical_success_corrected_count": "count",
    "logical_success_after_retry_count": "count",
    "logical_detected_failure_count": "count",
    "logical_sdc_count": "count",
    "logical_timeout_count": "count",
    "logical_control_success_fraction": "enumerated_mask_fraction_not_event_rate",
    "logical_control_due_fraction": "enumerated_mask_fraction_not_event_rate",
    "logical_control_sdc_fraction": "enumerated_mask_fraction_not_event_rate",
    "logical_control_corrected_fraction": "enumerated_mask_fraction_not_event_rate",
    "logical_control_retry_fraction": "enumerated_mask_fraction_not_event_rate",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _stable_sources(groups: Iterable[str]) -> str:
    seen: set[str] = set()
    values: list[str] = []
    for group in groups:
        for item in group.split(";"):
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                values.append(item)
    return ";".join(values)


def _evidence_column(field: str) -> str:
    return f"{field}_evidence"


CSV_FIELDS = (
    "row_id",
    "architecture_id",
    "ecc_family",
    "workload_id",
    "functional_control_id",
    "metric_version",
    "functional_unit",
    "service_success_probability",
    "service_success_probability_evidence",
    "useful_service_bits",
    "useful_service_bits_evidence",
    "GSE",
    "GSE_evidence",
    "GCI",
    "GCI_evidence",
    "GSE_relative",
    "GSE_relative_evidence",
    "technology_node",
    "process_route",
    "wafer_diameter",
    "wafer_diameter_evidence",
    "fab_grid",
    "fab_CI",
    "fab_CI_evidence",
    "process_maturity",
    "wafer_carbon",
    "wafer_carbon_evidence",
    "wafer_energy",
    "wafer_energy_evidence",
    "scope1_carbon",
    "scope1_carbon_evidence",
    "scope2_carbon",
    "scope2_carbon_evidence",
    "upstream_carbon",
    "upstream_carbon_evidence",
    "patterning_carbon",
    "patterning_carbon_evidence",
    "lithography_route",
    "mask_layer_count",
    "mask_layer_count_evidence",
    "multi_patterning_count",
    "multi_patterning_count_evidence",
    "maskset_NRE",
    "maskset_NRE_evidence",
    "yield",
    "yield_evidence",
    "yield_model",
    "defect_density",
    "defect_density_evidence",
    "gross_dies_per_wafer",
    "gross_dies_per_wafer_evidence",
    "good_dies_per_wafer",
    "good_dies_per_wafer_evidence",
    "die_embodied_carbon",
    "die_embodied_carbon_evidence",
    "incremental_ECC_embodied_carbon",
    "incremental_ECC_embodied_carbon_evidence",
    "operational_energy",
    "operational_energy_evidence",
    "operational_carbon",
    "operational_carbon_evidence",
    "lifecycle_carbon",
    "lifecycle_carbon_evidence",
    "interleaving_id",
    "fault_topology_id",
    "scrub_policy",
    "SDC",
    "SDC_evidence",
    "DUE",
    "DUE_evidence",
    "corrected",
    "corrected_evidence",
    "retry",
    "retry_evidence",
    "service_success",
    "service_success_evidence",
    "latency_ns",
    "latency_ns_evidence",
    "observed_macro_area_um2",
    "observed_macro_area_um2_evidence",
    "activity_coverage_fraction",
    "activity_coverage_fraction_evidence",
    "diagnostic_tool_power_w",
    "diagnostic_tool_power_w_evidence",
    "logical_pattern_count",
    "logical_pattern_count_evidence",
    "logical_success_normal_count",
    "logical_success_normal_count_evidence",
    "logical_success_corrected_count",
    "logical_success_corrected_count_evidence",
    "logical_success_after_retry_count",
    "logical_success_after_retry_count_evidence",
    "logical_detected_failure_count",
    "logical_detected_failure_count_evidence",
    "logical_sdc_count",
    "logical_sdc_count_evidence",
    "logical_timeout_count",
    "logical_timeout_count_evidence",
    "logical_control_success_fraction",
    "logical_control_success_fraction_evidence",
    "logical_control_due_fraction",
    "logical_control_due_fraction_evidence",
    "logical_control_sdc_fraction",
    "logical_control_sdc_fraction_evidence",
    "logical_control_corrected_fraction",
    "logical_control_corrected_fraction_evidence",
    "logical_control_retry_fraction",
    "logical_control_retry_fraction_evidence",
    "rate_semantics",
    "evidence_tier",
    "uncertainty_class",
    "qualification_status",
    "blocking_reasons",
    "source_ids",
)


def build_rows(base: Path = BASE) -> list[dict[str, str]]:
    reliability_path = base / "reliability" / "RELIABILITY_RESULTS.csv"
    energy_path = base / "energy" / "ENERGY_RESULTS.csv"
    cost_path = base / "interleaving" / "INTERLEAVING_COST.csv"

    reliability_rows = _read_csv(reliability_path)
    energy_by_arch = {
        row["architecture_id"]: row for row in _read_csv(energy_path)
    }
    macro_area_by_arch = {
        row["architecture_id"]: row["macro_area_um2"]
        for row in _read_csv(cost_path)
        if row["interleaving_id"] == "I0"
    }

    rows: list[dict[str, str]] = []
    for source in reliability_rows:
        architecture = source["architecture_id"]
        energy = energy_by_arch[architecture]
        pattern_count = int(source["pattern_count"])
        normal = int(source["success_normal_count"])
        corrected = int(source["success_corrected_count"])
        after_retry = int(source["success_after_retry_count"])
        due = int(source["detected_failure_count"])
        sdc = int(source["sdc_count"])
        timeout = int(source["timeout_count"])

        row = {field: "" for field in CSV_FIELDS}
        for field in NUMERIC_FIELDS:
            row[_evidence_column(field)] = "NOT_QUALIFIED"

        row.update(
            {
                "row_id": (
                    f"{architecture}|{source['fault_domain']}|"
                    f"{source['scrub_policy']}"
                ),
                "architecture_id": architecture,
                "ecc_family": "NONE_UNPROTECTED" if architecture == "U0" else "HSIAO_SECDED_72_64",
                "workload_id": energy["workload_id"],
                "functional_control_id": source["fault_domain"],
                "metric_version": "GSE_GCI_V1",
                "functional_unit": "correct_payload_bit_memory_service",
                "technology_node": "SKY130",
                "process_route": "SKY130HD_WITH_SRAM22_RESEARCH_MACROS",
                "fab_grid": "NOT_MEASURED",
                "process_maturity": "NOT_CALIBRATED",
                "lithography_route": "NOT_MEASURED",
                "yield_model": "NOT_CALIBRATED_FOR_SKY130",
                "interleaving_id": source["interleaving_id"],
                "fault_topology_id": source["fault_topology_id"],
                "scrub_policy": source["scrub_policy"],
                "observed_macro_area_um2": macro_area_by_arch[architecture],
                "observed_macro_area_um2_evidence": "TOOL_ESTIMATE",
                "activity_coverage_fraction": energy["activity_coverage_fraction"],
                "activity_coverage_fraction_evidence": "DERIVED",
                "diagnostic_tool_power_w": energy["diagnostic_tool_power_w"],
                "diagnostic_tool_power_w_evidence": "TOOL_ESTIMATE",
                "logical_pattern_count": str(pattern_count),
                "logical_success_normal_count": str(normal),
                "logical_success_corrected_count": str(corrected),
                "logical_success_after_retry_count": str(after_retry),
                "logical_detected_failure_count": str(due),
                "logical_sdc_count": str(sdc),
                "logical_timeout_count": str(timeout),
                "logical_control_success_fraction": format(
                    (normal + corrected + after_retry) / pattern_count, ".17g"
                ),
                "logical_control_due_fraction": format(due / pattern_count, ".17g"),
                "logical_control_sdc_fraction": format(sdc / pattern_count, ".17g"),
                "logical_control_corrected_fraction": format(corrected / pattern_count, ".17g"),
                "logical_control_retry_fraction": format(after_retry / pattern_count, ".17g"),
                "rate_semantics": source["rate_semantics"],
                "evidence_tier": "LOWEST_ACTIVE_TIER_T5",
                "uncertainty_class": "UNQUALIFIED_MIXED_INPUTS",
                "qualification_status": "UNQUALIFIED",
                "blocking_reasons": (
                    "PHYSICAL_EVENT_RATES_NOT_QUALIFIED;"
                    "OPERATIONAL_ENERGY_NOT_QUALIFIED;"
                    "SKY130_WAFER_CARBON_NOT_QUALIFIED;"
                    "LATENCY_NOT_MEASURED_FOR_SERVICE_POLICY"
                ),
                "source_ids": _stable_sources(
                    (
                        source["source_ids"],
                        energy["source_ids"],
                        "A10_INTERLEAVING_COST",
                        "SRC_SKYWATER_SKY130_PDK",
                    )
                ),
            }
        )
        for field in (
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
        ):
            row[_evidence_column(field)] = "DERIVED"
        rows.append(row)

    return rows


def _schema() -> dict[str, object]:
    columns: list[dict[str, object]] = []
    for name in CSV_FIELDS:
        item: dict[str, object] = {"name": name, "type": "string", "nullable": False}
        if name in NUMERIC_FIELDS:
            item.update(
                {
                    "type": "number_or_empty",
                    "nullable": True,
                    "unit": UNITS[name],
                    "evidence_column": _evidence_column(name),
                }
            )
        elif name.endswith("_evidence"):
            item["allowed_values"] = list(EVIDENCE_CLASSES)
        columns.append(item)
    return {
        "schema_version": 2,
        "metric_version": "GSE_GCI_V1",
        "null_encoding": "empty CSV field",
        "required_phase_x_fields": list(REQUIRED_V2_FIELDS),
        "evidence_classes": list(EVIDENCE_CLASSES),
        "columns": columns,
        "invariants": [
            "Every populated numerical cell has a same-row evidence companion.",
            "An empty numerical cell is never converted to zero.",
            "Enumerated logical-mask fractions are not physical event probabilities.",
            "GSE, GCI, and GSE_relative require qualified service and lifecycle carbon.",
            "Patterning carbon is a diagnostic subset of Scope 2 and is not added twice.",
        ],
    }


def build(base: Path = BASE) -> tuple[Path, Path, Path]:
    output_dir = base / "green_matrix_v2"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "GREEN_MATRIX_V2_RAW.csv"
    schema_path = output_dir / "GREEN_MATRIX_V2_SCHEMA.json"
    metadata_path = output_dir / "GREEN_MATRIX_V2_METADATA.json"
    rows = build_rows(base)

    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    schema_path.write_text(
        json.dumps(_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline=""
    )

    inputs = {
        "reliability/RELIABILITY_RESULTS.csv": _sha256(
            base / "reliability" / "RELIABILITY_RESULTS.csv"
        ),
        "energy/ENERGY_RESULTS.csv": _sha256(base / "energy" / "ENERGY_RESULTS.csv"),
        "interleaving/INTERLEAVING_COST.csv": _sha256(
            base / "interleaving" / "INTERLEAVING_COST.csv"
        ),
        "carbon/validation/SKY130_TRANSLATION_STATUS.json": _sha256(
            base / "carbon" / "validation" / "SKY130_TRANSLATION_STATUS.json"
        ),
    }
    metadata = {
        "schema_version": 2,
        "builder": "green_matrix_v2/build_matrix_v2.py",
        "deterministic_seed": SEED,
        "seed_use": "recorded for reproducibility; current exhaustive join uses no randomness",
        "input_sha256": inputs,
        "row_count": len(rows),
        "architecture_ids": sorted({row["architecture_id"] for row in rows}),
        "qualification_counts": {"UNQUALIFIED": len(rows)},
        "qualified_absolute_rows": 0,
        "qualified_relative_rows": 0,
        "green_metric_rows": 0,
        "classification": "MATRIX_SCHEMA_AND_LOGICAL_CONTROLS_POPULATED_GREEN_ROWS_UNQUALIFIED",
        "join_policy": (
            "Preserve exact logical controls and diagnostic physical/activity evidence; "
            "never coerce unavailable physical rates, energy, or carbon into scores."
        ),
        "blocking_inputs": [
            "physical SER/FIT and spatial event distribution",
            "activity-qualified SRAM and complete ECC operational energy",
            "matched absolute SKY130 wafer-carbon inventory",
            "service latency under a declared policy",
        ],
        "source_ids": [
            "A10_LOGICAL_CONTROLS",
            "A10_POSTROUTE_ACTIVITY_DIAGNOSTIC",
            "A10_INTERLEAVING_COST",
            "SRC_SKYWATER_SKY130_PDK",
        ],
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    return raw_path, schema_path, metadata_path


if __name__ == "__main__":
    build()
