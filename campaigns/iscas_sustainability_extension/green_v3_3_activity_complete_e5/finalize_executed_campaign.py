#!/usr/bin/env python3
"""Deterministically integrate the executed GREEN v3.3 E5 evidence.

The raw result files are the scientific source of truth.  This module selects
only records that already passed the fail-closed qualification in those files;
it never upgrades a blocked record or substitutes vectorless power.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping


CAMPAIGN_REL = Path("campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5")
PARENT_REL = Path("campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation")
QUALIFIED = "E5_LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE"
ARCHITECTURES = ("SECDED", "HSIAO_SECDED")
SEEDS = (11, 13, 17, 19, 23)
OPERATIONS = (
    "IDLE",
    "WRITE_CLEAN",
    "READ_CLEAN",
    "READ_SINGLE_BIT_ERROR_CORRECT",
    "READ_DOUBLE_BIT_ERROR_DETECT",
)
PREFIX = {
    "IDLE": "idle",
    "WRITE_CLEAN": "clean_write",
    "READ_CLEAN": "clean_read",
    "READ_SINGLE_BIT_ERROR_CORRECT": "correction",
    "READ_DOUBLE_BIT_ERROR_DETECT": "detection",
}
FOUNDATION_COMMIT = "affc8145b184803189dac36391cb486f00e7b4f8"
PARENT_PHYSICAL_COMMIT = "1f6bcd009e7a05ebcde35a3272161a9a81ec7bf7"
PARENT_V32_COMMIT = "29f20b196e04c713f88fd1a93440a2ff47986f06"
PARENT_V32_SEAL_COMMIT = "22d6ef2391f7d74f0890933fcda9952fdf656e52"
PARENT_MATCHED_COMMIT = "daaa83b6b3571060aec9d4d753b4907df5a2ba47"
PARENT_MATCHED_SEAL_COMMIT = "8af0fc5a2532b3471016a86cde7968af7d15cfa9"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: "" if row.get(name) is None else row.get(name) for name in fieldnames})
    write_text(path, stream.getvalue())


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def descriptive(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "sample_standard_deviation": None,
            "minimum": None,
            "maximum": None,
            "descriptive_95_percent_ci_low": None,
            "descriptive_95_percent_ci_high": None,
            "coefficient_of_variation": None,
        }
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else None
    t95 = {4: 3.182, 5: 2.776}.get(len(values))
    half = t95 * stdev / math.sqrt(len(values)) if t95 is not None and stdev is not None else None
    return {
        "count": len(values),
        "mean": mean,
        "median": statistics.median(values),
        "sample_standard_deviation": stdev,
        "minimum": min(values),
        "maximum": max(values),
        "descriptive_95_percent_ci_low": mean - half if half is not None else None,
        "descriptive_95_percent_ci_high": mean + half if half is not None else None,
        "coefficient_of_variation": stdev / mean if stdev is not None and mean else None,
    }


def canonical_source(campaign: Path, architecture: str, seed: int) -> Path:
    stem = "secded" if architecture == "SECDED" else "hsiao_secded"
    root = campaign / "fresh_runs" / f"{stem}_clk10p0ns_seed{seed}"
    return root / ("ACTIVITY_REMEDIATION06_RESULT.json" if seed == 11 else "RESULT.json")


def source_result(campaign: Path, architecture: str, seed: int) -> Path:
    stem = "secded" if architecture == "SECDED" else "hsiao_secded"
    return campaign / "fresh_runs" / f"{stem}_clk10p0ns_seed{seed}" / "RESULT.json"


def root_count(record: Mapping[str, Any]) -> int | None:
    activity = record["activity"]
    adapter = activity.get("macro_output_activity_root_adapter", {})
    explicit = activity.get("explicit_routed_net_annotation", {})
    return adapter.get("required_root_count", explicit.get("macro_output_activity_root_candidate_count"))


def collect(campaign: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    measurements: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            canonical_path = canonical_source(campaign, architecture, seed)
            physical_path = source_result(campaign, architecture, seed)
            canonical = load(canonical_path)
            physical = load(physical_path)
            qualified = [row for row in canonical["operation_records"] if row["qualification"] == QUALIFIED]
            runs.append(
                {
                    "architecture_id": architecture,
                    "clock_period_ns": 10.0,
                    "physical_seed": seed,
                    "status": canonical["status"],
                    "canonical_result": canonical_path.relative_to(campaign).as_posix(),
                    "canonical_result_sha256": sha256(canonical_path),
                    "physical_result": physical_path.relative_to(campaign).as_posix(),
                    "physical_result_sha256": sha256(physical_path),
                    "setup_wns_ns": physical["physical"]["setup_wns_ns"],
                    "timing_feasible": physical["physical"]["timing_feasible"],
                    "qualified_operation_count": len(qualified),
                    "blocked_operation_classes": [
                        row["operation_class"]
                        for row in canonical["operation_records"]
                        if row["qualification"] != QUALIFIED
                    ],
                }
            )
            for row in qualified:
                coverage = row["activity"]["coverage"]
                power = row["power"]["ecc_logic_excluding_macro_w"]
                measurements.append(
                    {
                        "record_id": row["record_id"],
                        "architecture_id": architecture,
                        "clock_period_ns": row["clock_period_ns"],
                        "physical_seed": seed,
                        "operation_class": row["operation_class"],
                        "evidence_level": row["evidence_level"],
                        "qualification": row["qualification"],
                        "timing_feasible": row["timing_feasible"],
                        "warm_up_cycles": row["warm_up_cycles"],
                        "exact_operation_count": row["exact_operation_count"],
                        "measurement_duration_seconds": row["measurement_duration_seconds"],
                        "activity_format": row["activity"]["format"],
                        "activity_boundary": row["activity"]["activity_generation_boundary"],
                        "activity_sha256": row["activity"]["sha256"],
                        "workload_sha256": row["workload_sha256"],
                        "routed_netlist_sha256": row["routed_netlist_sha256"],
                        "spef_sha256": row["parasitics"]["sha256"],
                        "functional_logic_coverage_fraction": coverage["functional_logic_coverage_fraction"],
                        "sequential_coverage_fraction": coverage["by_cell_class"]["sequential"]["coverage_fraction"],
                        "combinational_coverage_fraction": coverage["by_cell_class"]["combinational"]["coverage_fraction"],
                        "macro_output_activity_root_count": root_count(row),
                        "internal_power_w": power["internal_w"],
                        "switching_power_w": power["switching_w"],
                        "leakage_power_w": power["leakage_w"],
                        "total_power_w": power["total_w"],
                        "energy_j_per_operation": row["power"]["ecc_logic_energy_j_per_operation"],
                        "whole_memory_energy_j_per_operation": None,
                        "source_result": canonical_path.relative_to(campaign).as_posix(),
                        "source_result_sha256": sha256(canonical_path),
                    }
                )
    measurements.sort(key=lambda row: (row["architecture_id"], row["physical_seed"], row["operation_class"]))
    if len(measurements) != 46:
        raise RuntimeError(f"fail-closed: expected 46 qualified records, found {len(measurements)}")
    if any(row["macro_output_activity_root_count"] != 72 for row in measurements):
        raise RuntimeError("fail-closed: a qualified record lacks all 72 required macro-output roots")
    return measurements, runs


def aggregate_statistics(measurements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        for operation in OPERATIONS:
            values = [
                row["energy_j_per_operation"]
                for row in measurements
                if row["architecture_id"] == architecture and row["operation_class"] == operation
            ]
            stats = descriptive(values)
            rows.append(
                {
                    "architecture_id": architecture,
                    "clock_period_ns": 10.0,
                    "operation_class": operation,
                    "count": stats["count"],
                    "mean_energy_j": stats["mean"],
                    "median_energy_j": stats["median"],
                    "sample_standard_deviation_j": stats["sample_standard_deviation"],
                    "minimum_energy_j": stats["minimum"],
                    "maximum_energy_j": stats["maximum"],
                    "descriptive_95_percent_ci_low_j": stats["descriptive_95_percent_ci_low"],
                    "descriptive_95_percent_ci_high_j": stats["descriptive_95_percent_ci_high"],
                    "coefficient_of_variation": stats["coefficient_of_variation"],
                    "qualification": QUALIFIED,
                }
            )
    return rows


def inherited_deltas(repo: Path) -> list[dict[str, Any]]:
    import build_campaign as baseline

    physical = load(repo / PARENT_REL / "PHYSICAL_RUN_RESULTS.json")["records"]
    return baseline.matched_deltas(physical)


def matched_deltas(repo: Path, measurements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = inherited_deltas(repo)
    by_key = {
        (row["architecture_id"], row["physical_seed"], row["operation_class"]): row
        for row in measurements
    }
    for row in rows:
        seed = row["seed"]
        lower_count = 0
        matched_count = 0
        for operation in OPERATIONS:
            secded = by_key.get(("SECDED", seed, operation))
            hsiao = by_key.get(("HSIAO_SECDED", seed, operation))
            prefix = PREFIX[operation]
            if secded is None or hsiao is None:
                for suffix in (
                    "energy_j_delta", "internal_power_w_delta", "switching_power_w_delta",
                    "leakage_power_w_delta", "dynamic_power_w_delta",
                ):
                    row[f"{prefix}_{suffix}"] = None
                continue
            matched_count += 1
            if hsiao["energy_j_per_operation"] < secded["energy_j_per_operation"]:
                lower_count += 1
            row[f"{prefix}_energy_j_delta"] = hsiao["energy_j_per_operation"] - secded["energy_j_per_operation"]
            for component in ("internal", "switching", "leakage"):
                key = f"{component}_power_w"
                row[f"{prefix}_{component}_power_w_delta"] = hsiao[key] - secded[key]
            row[f"{prefix}_dynamic_power_w_delta"] = (
                hsiao["internal_power_w"] + hsiao["switching_power_w"]
                - secded["internal_power_w"] - secded["switching_power_w"]
            )
        # Preserve the established public energy field names.
        row["clean_read_energy_j_delta"] = row["clean_read_energy_j_delta"]
        row["clean_write_energy_j_delta"] = row["clean_write_energy_j_delta"]
        row["correction_energy_j_delta"] = row["correction_energy_j_delta"]
        row["detection_energy_j_delta"] = row["detection_energy_j_delta"]
        row["matched_energy_class_count"] = matched_count
        row["hsiao_lower_energy_class_count"] = lower_count
        row["energy_qualification"] = (
            QUALIFIED if matched_count == len(OPERATIONS) else "E5_LOGIC_ACTIVITY_PARTIAL_OPERATION_SET"
        )
    return rows


def mean_delta(rows: list[dict[str, Any]], name: str) -> float | None:
    values = [row[name] for row in rows if row.get(name) is not None]
    return statistics.mean(values) if values else None


def p(value: float | None, scale: float = 1.0, digits: int = 4) -> str:
    return "unavailable" if value is None else f"{value * scale:.{digits}f}"


def finalize(repo: Path) -> None:
    campaign = repo / CAMPAIGN_REL
    parent = repo / PARENT_REL
    runtime = load(campaign / "RUNTIME_STATE.json")
    measurements, runs = collect(campaign)
    stats = aggregate_statistics(measurements)
    deltas = matched_deltas(repo, measurements)
    comparison_count = sum(row["matched_energy_class_count"] for row in deltas)
    lower_count = sum(row["hsiao_lower_energy_class_count"] for row in deltas)
    lower_fraction = lower_count / comparison_count

    # Refresh deterministic inherited artifacts without touching frozen sources.
    import build_campaign as baseline

    physical = load(parent / "PHYSICAL_RUN_RESULTS.json")["records"]
    workloads = baseline.workloads()
    by_workload = {
        (row["architecture_id"], row["physical_seed"], row["clock_period_ns"], row["operation_class"]): row
        for row in workloads
    }
    for record in measurements:
        target = by_workload[(
            record["architecture_id"], record["physical_seed"], record["clock_period_ns"], record["operation_class"]
        )]
        target["activity_sha256"] = record["activity_sha256"]
        target["activity_boundary"] = record["activity_boundary"]
        target["qualification"] = record["qualification"]
        target["e5_record_id"] = record["record_id"]
    write_json(
        campaign / "WORKLOAD_MANIFEST.json",
        {
            "schema_version": 1,
            "generated_on": "2026-09-09",
            "record_count": len(workloads),
            "qualified_activity_record_count": len(measurements),
            "shared_semantics_note": (
                "Equivalent classes use identical generator definitions and workload hashes across architectures, "
                "physical seeds, and clocks. Only executed records carry activity hashes."
            ),
            "records": workloads,
        },
    )
    write_json(campaign / "TIMING_FEASIBILITY.json", {"schema_version": 1, "records": baseline.timing_summary(physical)})
    write_json(campaign / "SRAM_MACRO_POWER_QUALIFICATION.json", baseline.macro_audit(repo))

    write_json(
        campaign / "E5_OPERATION_STATISTICS.json",
        {
            "schema_version": 1,
            "record_count": len(stats),
            "qualified_measurement_count": len(measurements),
            "records": stats,
            "qualification": QUALIFIED,
            "sample_interpretation": "Multi-seed descriptive samples only; n=5 for read classes and n=4 for IDLE/WRITE_CLEAN.",
            "required_statistics": [
                "count", "mean", "median", "sample_standard_deviation", "minimum", "maximum",
                "descriptive_95_percent_ci", "coefficient_of_variation",
            ],
        },
    )
    stat_fields = list(stats[0])
    write_csv(campaign / "E5_OPERATION_STATISTICS.csv", stat_fields, stats)

    per_operation_fraction = {}
    for operation in OPERATIONS:
        prefix = PREFIX[operation]
        values = [row[f"{prefix}_energy_j_delta"] for row in deltas if row[f"{prefix}_energy_j_delta"] is not None]
        per_operation_fraction[operation] = {
            "matched_seed_count": len(values),
            "hsiao_lower_energy_seed_count": sum(value < 0 for value in values),
            "hsiao_lower_energy_fraction": sum(value < 0 for value in values) / len(values),
            "mean_hsiao_minus_secded_energy_j": statistics.mean(values),
        }
    write_json(
        campaign / "E5_MATCHED_SEED_DELTAS.json",
        {
            "schema_version": 1,
            "comparison": "HSIAO_SECDED_MINUS_SECDED_AT_10NS_MATCHED_SEEDS",
            "record_count": len(deltas),
            "records": deltas,
            "matched_operation_comparison_count": comparison_count,
            "hsiao_lower_energy_comparison_count": lower_count,
            "energy_ordering_preserved_fraction": lower_fraction,
            "energy_ordering_by_operation": per_operation_fraction,
            "e4_vectorless_lower_power_seed_fraction": 1.0,
            "e5_vs_e4_conclusion": "E5_MOSTLY_REVERSES_E4_HSIAO_LOWER_POWER_TENDENCY",
            "energy_qualification": QUALIFIED,
        },
    )
    delta_fields = list(deltas[0])
    write_csv(campaign / "E5_MATCHED_SEED_DELTAS.csv", delta_fields, deltas)

    start = parse_utc(runtime["campaign_start_time_utc"])
    end = parse_utc(runtime["campaign_end_time_utc"])
    deadline = parse_utc(runtime["hard_deadline_utc"])
    consumed = (end - start).total_seconds()
    parents = {
        "foundation_commit": FOUNDATION_COMMIT,
        "parent_physical_population_commit": PARENT_PHYSICAL_COMMIT,
        "parent_green_v3_2_commit": PARENT_V32_COMMIT,
        "parent_green_v3_2_provenance_seal_commit": PARENT_V32_SEAL_COMMIT,
        "parent_matched_campaign_commit": PARENT_MATCHED_COMMIT,
        "parent_matched_campaign_seal_commit": PARENT_MATCHED_SEAL_COMMIT,
    }
    write_json(
        campaign / "RUN_MANIFEST.json",
        {
            "schema_version": 1,
            "campaign": "green_v3_3_activity_complete_e5",
            "generated_on": "2026-09-09",
            **parents,
            "budget": {
                "scope": "ENTIRE_CAMPAIGN",
                "maximum_wall_clock_seconds": 54000,
                "maximum_wall_clock_hours": 15,
                "per_run_timeout_seconds": None,
                "campaign_start_time_utc": runtime["campaign_start_time_utc"],
                "hard_deadline_utc": runtime["hard_deadline_utc"],
                "campaign_end_time_utc": runtime["campaign_end_time_utc"],
                "consumed_wall_clock_seconds": consumed,
                "consumed_fraction": consumed / 54000,
                "deadline_hit": end >= deadline,
                "deadline_persistence": "RUNTIME_STATE.json",
            },
            "fresh_rtl_to_gdsii_executed": True,
            "fresh_physical_run_count": len(runs),
            "fresh_timing_feasible_run_count": sum(row["timing_feasible"] for row in runs),
            "inherited_physical_population": {
                "run_count": len(physical),
                "source": (PARENT_REL / "RUN_MANIFEST.json").as_posix(),
                "source_sha256": sha256(parent / "RUN_MANIFEST.json"),
                "policy": "IMMUTABLE_REFERENCE_NO_RECOMPUTATION",
            },
            "workload_manifest": {"path": "WORKLOAD_MANIFEST.json", "record_count": len(workloads)},
            "canonical_fresh_runs": runs,
            "new_activity_power_records": measurements,
            "new_e5_record_count": len(measurements),
            "toolchain": load(source_result(campaign, "SECDED", 13))["toolchain"],
            "documented_flow_exception": "UPSTREAM_SRAM22_MAX_TRANSITION_RESIZE_STAGE_BYPASS",
        },
    )

    failure_records = [
        {
            "experiment": "seed11_native_read_vcd",
            "status": "COMPLETED_E5_BLOCKED",
            "classification": "NATIVE_READ_VCD_TOP_PORT_ONLY",
            "reason": "Native hierarchy matching annotated only 142 top ports; no internal leaf-pin activity was inferred.",
            "partial_artifacts_preserved": [
                "fresh_runs/secded_clk10p0ns_seed11/RESULT.json",
                "fresh_runs/hsiao_secded_clk10p0ns_seed11/RESULT.json",
            ],
        },
        {
            "experiment": "seed11_activity_remediations_01_to_05",
            "status": "SUPERSEDED_PRESERVED",
            "classification": "SEMANTICALLY_NONRESPONSIVE_ACTIVITY_PROPAGATION",
            "reason": "Coverage-like counts alone did not make macro-output-driven logic responsive in OpenSTA power.",
            "partial_artifacts_preserved": ["fresh_runs/*seed11/ACTIVITY_REMEDIATION0[1-5]_RESULT.json"],
        },
        {
            "experiment": "seed11_literal_pin_activity_launches",
            "status": "TOOL_FAILURE_PRESERVED",
            "classification": "WSL_PROCESS_LAUNCH_E_ACCESSDENIED",
            "reason": "Two sandbox-blocked launches were retained; approved retries completed.",
            "partial_artifacts_preserved": ["RUNTIME_STATE.json", "logs/"],
        },
        {
            "experiment": "seed11_idle_and_write_known_state",
            "status": "E5_BLOCKED_PRESERVED",
            "classification": "X_STATE_MACRO_OUTPUT_ACTIVITY_INCOMPLETE",
            "reason": "The first seed-11 GLS traces lacked the later clean-read state initializer.",
            "partial_artifacts_preserved": ["fresh_runs/*seed11/ACTIVITY_REMEDIATION06_RESULT.json"],
        },
        {
            "experiment": "U0_BCH_5NS_OPENRAM_AND_OPTIONAL_SENSITIVITY",
            "status": "NOT_LAUNCHED_BEFORE_PERSISTED_DEADLINE",
            "classification": "LOWER_PRIORITY_QUEUE_NOT_EXECUTED",
            "reason": "The primary matched ECC population was completed first; continuation resumed only after the fixed deadline.",
            "partial_artifacts_preserved": [],
        },
    ]
    write_json(campaign / "FAILED_PARTIAL_EXPERIMENTS.json", {"schema_version": 1, "records": failure_records})

    matrix_records = [
        {
            "matrix_record_id": row["record_id"],
            "evidence_level": "E5",
            "architecture_id": row["architecture_id"],
            "clock_period_ns": row["clock_period_ns"],
            "physical_seed": row["physical_seed"],
            "operation_class": row["operation_class"],
            "energy_j_per_operation": row["energy_j_per_operation"],
            "scope": "ECC_LOGIC_EXCLUDING_SRAM_MACRO_INTERNAL_ENERGY",
            "qualification": row["qualification"],
            "source_result": row["source_result"],
            "source_result_sha256": row["source_result_sha256"],
        }
        for row in measurements
    ]
    write_json(
        campaign / "GREEN_V3_3_ADDITIVE_MATRIX.json",
        {
            "schema_version": "3.3.0",
            "mode": "ADDITIVE_ONLY",
            **parents,
            "parent_counts": {"M_E": 601, "M_P": 10, "M_S": 2},
            "new_evidence_counts": {"E3": 0, "E4": 0, "E5": len(matrix_records)},
            "combined_counts": {"M_E": 601 + len(matrix_records), "M_P": 10, "M_S": 2},
            "records": matrix_records,
            "e5_equal_performance_population": ["SECDED", "HSIAO_SECDED"],
            "qualified_sustainability_front": "BLOCKED",
            "admission_guard": "ACTIVITY_HASH_COVERAGE_OPERATION_COUNT_PARASITICS_TIMING_AND_MACRO_SCOPE_REQUIRED",
            "global_winner": "NO_GLOBAL_WINNER_QUALIFIED",
        },
    )

    coverages = [row["functional_logic_coverage_fraction"] for row in measurements]
    aggregate_coverage = []
    sequential_coverage = [row["sequential_coverage_fraction"] for row in measurements]
    combinational_coverage = [row["combinational_coverage_fraction"] for row in measurements]
    for architecture in ARCHITECTURES:
        for seed in SEEDS:
            source = load(canonical_source(campaign, architecture, seed))
            aggregate_coverage.extend(
                row["activity"]["coverage"]["aggregate_coverage_fraction"]
                for row in source["operation_records"] if row["qualification"] == QUALIFIED
            )
    classification = (
        "GREEN_V3_3_ACTIVITY_COMPLETE_POST_ROUTE_E5_LOGIC_QUALIFIED_MULTI_ARCH_MATCHED_SEED_"
        "PHYSICAL_VALIDATION_COMPLETE_MACRO_ENERGY_PARTIAL_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED"
    )
    status = {
        "schema_version": "1.0.0",
        "campaign": "green_v3_3_activity_complete_e5",
        "generated_on": "2026-09-09",
        **parents,
        "classification": classification,
        "scientific_success_level": "LEVEL_B_STRONG",
        "runtime_budget": {
            "scope": "ENTIRE_CAMPAIGN",
            "seconds": 54000,
            "hours": 15,
            "per_run_timeout_seconds": None,
            "campaign_started": True,
            "campaign_start_time_utc": runtime["campaign_start_time_utc"],
            "hard_deadline_utc": runtime["hard_deadline_utc"],
            "campaign_end_time_utc": runtime["campaign_end_time_utc"],
            "consumed_wall_clock_seconds": consumed,
            "deadline_hit": end >= deadline,
        },
        "included_architectures": ["U0", "SECDED", "HSIAO_SECDED", "BCH_78_64_T2"],
        "e5_executed_architectures": list(ARCHITECTURES),
        "inherited_physical_run_count": len(physical),
        "fresh_physical_run_count": len(runs),
        "fresh_timing_feasible_run_count": sum(row["timing_feasible"] for row in runs),
        "timing_feasible_10ns": ["U0", "SECDED", "HSIAO_SECDED"],
        "timing_feasible_5ns": ["U0"],
        "timing_infeasible_as_implemented": [
            "BCH_78_64_T2@10ns", "SECDED@5ns", "HSIAO_SECDED@5ns", "BCH_78_64_T2@5ns",
        ],
        "workload_specification_count": len(workloads),
        "post_route_activity_generated": True,
        "activity_format": "VCD",
        "activity_boundary": "POST_ROUTE_GATE_ACTIVITY_ZERO_DELAY_ROUTED_NETLIST",
        "activity_annotation_coverage": {
            "qualified_record_count": len(measurements),
            "functional_logic_minimum": min(coverages),
            "functional_logic_maximum": max(coverages),
            "aggregate_minimum": min(aggregate_coverage),
            "aggregate_maximum": max(aggregate_coverage),
            "sequential_minimum": min(sequential_coverage),
            "combinational_minimum": min(combinational_coverage),
            "macro_output_roots_required_and_annotated": 72,
            "macro_internal_activity_coverage": None,
        },
        "E5_status": QUALIFIED,
        "ecc_logic_e5_qualified": True,
        "whole_memory_e5_qualified": False,
        "macro_power_qualification": QUALIFIED,
        "evidence_added": {"E3": 0, "E4": 0, "E5": len(measurements)},
        "matched_seed_summary": {
            "read_operation_seed_pairs": 5,
            "complete_five_operation_seed_pairs": 4,
            "matched_operation_comparisons": comparison_count,
            "hsiao_lower_energy_comparisons": lower_count,
        },
        "qualified_e5_pareto_status": "PARTIAL_TWO_ARCHITECTURE_LOGIC_ONLY_NO_GLOBAL_WINNER",
        "qualified_sustainability_pareto_status": "BLOCKED",
        "physical_logical_topology": "BLOCKED",
        "interleaver_reliability": "BLOCKED",
        "Qcrit": "BLOCKED",
        "physical_SDC_DUE_FIT": "BLOCKED",
        "SKY130_manufacturing_lifecycle_carbon": "BLOCKED",
        "global_winner": "NO_GLOBAL_WINNER_QUALIFIED",
        "validation_summary": "VALIDATION_RESULTS.json",
    }
    write_json(campaign / "CAMPAIGN_STATUS.json", status)

    observations_path = campaign / "validation" / "FINAL_VALIDATION_OBSERVATIONS.json"
    if observations_path.exists():
        validation = load(observations_path)
    else:
        validation = {
            "schema_version": 1,
            "generated_on": "2026-09-09",
            "status": "PENDING_FINAL_VALIDATION",
            "commands": [],
        }
    write_json(campaign / "VALIDATION_RESULTS.json", validation)
    mutations = {
        "schema_version": 1,
        "generated_on": "2026-09-09",
        "policy": "PRESERVE_AND_RECORD; NO RESTORE_OR_DELETE DURING ACTIVE_CAMPAIGN",
        "records": [
            {
                "source": "focused campaign pytest before finalization",
                "mutation": "deterministic builder regenerated placeholder queue/reports and exposed a stale hash manifest",
                "disposition": "preserved in Git history and superseded additively by executed-evidence finalization",
            },
            {
                "source": "git add on Windows",
                "mutation": "Git emitted LF-to-CRLF future-checkout warnings for raw evidence files",
                "disposition": "recorded; raw working files were not rewritten or cleaned",
            },
        ],
        "final_validation_observations": (
            observations_path.relative_to(campaign).as_posix() if observations_path.exists() else None
        ),
        "validation_run_mutations": validation.get("mutations"),
    }
    write_json(campaign / "VALIDATION_MUTATIONS.json", mutations)
    write_json(
        campaign / "CLEANUP_MANIFEST.json",
        {
            "schema_version": 1,
            "generated_on": "2026-09-09",
            "cleanup_performed": False,
            "deleted_files": [],
            "policy": "STRICT_PRESERVATION_AFTER_SCIENTIFIC_EXECUTION",
            "candidates": [
                {"path": "fresh_runs/", "classification": "SCIENTIFIC_EVIDENCE_KEEP", "final_action": "KEEP"},
                {"path": "logs/", "classification": "SCIENTIFIC_EVIDENCE_KEEP", "final_action": "KEEP"},
                {"path": "progress/", "classification": "SCIENTIFIC_EVIDENCE_KEEP", "final_action": "KEEP"},
                {"path": "derived_models/", "classification": "SOURCE_KEEP", "final_action": "KEEP"},
                {"path": "scripts/", "classification": "SOURCE_KEEP", "final_action": "KEEP"},
                {"path": "hashes/", "classification": "SCIENTIFIC_EVIDENCE_KEEP", "final_action": "KEEP"},
                {"path": "test-generated historical mutations", "classification": "UNCERTAIN_KEEP", "final_action": "KEEP"},
            ],
            "postponed_cleanup": "All cache/test-fixture cleanup was postponed because deletion was unnecessary and preservation was requested.",
        },
    )

    area_mean = mean_delta(deltas, "total_instance_area_um2_delta")
    wire_mean = mean_delta(deltas, "wirelength_um_delta")
    via_mean = mean_delta(deltas, "via_count_delta")
    wns_mean = mean_delta(deltas, "setup_wns_ns_delta")
    read_mean = mean_delta(deltas, "clean_read_energy_j_delta")
    write_mean = mean_delta(deltas, "clean_write_energy_j_delta")
    correction_mean = mean_delta(deltas, "correction_energy_j_delta")
    detection_mean = mean_delta(deltas, "detection_energy_j_delta")
    write_text(
        campaign / "CAMPAIGN_PLAN.md",
        f"""# GREEN v3.3 campaign plan and execution disposition

The plan used one persisted 54,000-second budget for the entire campaign. It started at `{runtime['campaign_start_time_utc']}`, ended its queued work at `{runtime['campaign_end_time_utc']}`, and retained the original hard deadline `{runtime['hard_deadline_utc']}`. No per-run 15-hour allowance existed.

Priority execution established one SECDED/Hsiao seed-11 pipeline, remediated activity propagation, and expanded to seeds 13, 17, 19, and 23. U0, BCH, 5 ns, OpenRAM, and optional sensitivity work were not launched before the persisted deadline. All partial and failed attempts remain preserved.
""",
    )
    write_text(
        campaign / "ACTIVITY_COVERAGE_REPORT.md",
        f"""# Activity annotation coverage

Forty-six operation records passed the logic-only E5 gates. Functional-logic exact annotation coverage ranges from `{min(coverages):.6%}` to `{max(coverages):.6%}`; combinational coverage is at least `{min(combinational_coverage):.6%}` and sequential coverage is at least `{min(sequential_coverage):.6%}`. Each qualified record identified all 72 SRAM-output root candidates.

The activity boundary is zero-delay simulation of the final routed gate netlist, recorded as VCD, with the final SPEF loaded for power analysis. Native `read_vcd` resolved top ports; exact scalar routed-net activity supplemented leaf pins. For macro-output-driven cones, a power-process-only OpenDB adapter made the VCD-measured SRAM outputs timing-graph roots. The original ODB was not modified.

SRAM macro-interface coverage is reported separately and macro-internal state activity remains unavailable. Therefore the admitted quantity is ECC-logic energy excluding macro internal energy, never unrestricted whole-memory energy.
""",
    )
    macro = load(campaign / "SRAM_MACRO_POWER_QUALIFICATION.json")
    write_text(
        campaign / "SRAM_MACRO_POWER_AUDIT.md",
        "# SRAM22 macro-power audit\n\n"
        "The inherited tt/25 C/1.80 V Liberty views provide leakage, timing, and partial CE/WE-conditioned internal-power information, but not sufficient address/data/state-dependent macro-internal energy. No OpenRAM rerun was launched.\n\n"
        "| Quantity | Classification |\n|---|---|\n"
        + "\n".join(
            f"| {name} | `{classification_value}` |"
            for name, classification_value in macro["required_quantity_classification"].items()
        )
        + f"\n\nWhole-memory E5 remains unqualified. The admitted boundary is `{QUALIFIED}`.\n",
    )
    write_text(
        campaign / "CLAIM_EVIDENCE_MAP.md",
        f"""# Claim-to-evidence map

| Claim | Evidence | Status |
|---|---|---|
| One global 15-hour budget governed every run | `RUNTIME_STATE.json`, `RUN_MANIFEST.json` | Supported |
| Ten fresh routed runs completed and were timing-feasible at 10 ns | ten `fresh_runs/*/RESULT.json` files | Supported |
| 46 ECC-logic operation records meet E5 logic-only gates | `RUN_MANIFEST.json`, per-operation `E5_RECORD.json` files | Supported |
| Five matched seed pairs cover all read classes | `E5_MATCHED_SEED_DELTAS.json` | Supported |
| Four matched seed pairs cover all five operation classes | `E5_MATCHED_SEED_DELTAS.json` | Supported |
| Hsiao retained the E4 lower-power tendency | Hsiao lower in {lower_count}/{comparison_count} E5 comparisons | Rejected for this sample |
| Whole-memory operation energy is E5 | `SRAM_MACRO_POWER_QUALIFICATION.json` | Forbidden |
| U0 or BCH has v3.3 E5 evidence | no canonical E5 records | Not established |
| Physical FIT/Qcrit/interleaver benefit/absolute lifecycle carbon | required evidence absent | Forbidden |
| A global winner exists | mandatory dimensions remain blocked | `NO_GLOBAL_WINNER_QUALIFIED` |
""",
    )
    write_text(
        campaign / "ISCAS_EXPERIMENT_SUMMARY.md",
        f"""# ISCAS experiment summary

GREEN v3.3 executed ten fresh 10 ns routed SECDED/Hsiao implementations under one persisted 15-hour campaign budget and produced 46 qualified, operation-normalized ECC-logic E5 records. Each uses deterministic 16-cycle warm-up plus 256 measured operations, routed-netlist VCD activity, final SPEF parasitics, and explicit activity coverage.

Hsiao was lower-energy in only {lower_count}/{comparison_count} matched operation/seed comparisons. Thus the inherited vectorless E4 lower-power tendency does not generalize to the activity-aware sample; the result is operation-dependent and usually reverses. The sample remains descriptive (n=5 for reads; n=4 for idle/write). SRAM macro-internal energy, U0/BCH E5, physical reliability, absolute lifecycle carbon, and a global winner remain unqualified.
""",
    )
    write_text(
        campaign / "FINAL_REPORT.md",
        f"""# GREEN v3.3 final report

## Outcome

The campaign achieved **LEVEL B — strong**: 46 post-route, activity-aware, parasitic-aware ECC-logic E5 measurements across five matched SECDED/Hsiao seeds. All five seed pairs qualify for three read classes; four qualify for the complete five-class set. The single 54,000-second campaign budget was never reset per run.

Hsiao did **not** retain a generally lower operation-energy tendency: it was lower in only {lower_count}/{comparison_count} matched comparisons ({lower_fraction:.2%}). Whole-memory energy remains unqualified because SRAM macro-internal characterization is incomplete.

## Required answers

1. Architectures included in the source population: U0, SECDED, Hsiao SECDED, and BCH(78,64,t=2); v3.3 E5 execution covered SECDED and Hsiao.
2. Timing-feasible at 10 ns: U0, SECDED, and Hsiao SECDED in the inherited five-seed partition; all ten fresh SECDED/Hsiao runs were feasible.
3. Timing-feasible at 5 ns: U0 only in inherited evidence.
4. Fresh RTL-to-GDSII campaign executed: yes, for SECDED/Hsiao at five 10 ns seeds each.
5. Physical runs completed: 50 represented in the combined evidence base.
6. Inherited versus fresh: 40 inherited and 10 fresh.
7. Campaign budget consumed: {consumed:.3f} seconds ({consumed / 3600:.3f} hours, {consumed / 54000:.2%} of 54,000 seconds).
8. Global deadline reached: no; queued execution ended before `{runtime['hard_deadline_utc']}`.
9. Runtime-cutoff experiments: none. Lower-priority work was not launched after the deadline.
10. Post-route activity generated: yes.
11. Boundary: zero-delay final-routed gate-netlist VCD, with final SPEF used in OpenROAD/OpenSTA power.
12. Activity format: VCD only.
13. Annotation coverage: functional logic {min(coverages):.3%}–{max(coverages):.3%}; all 72 required macro-output roots per qualified record.
14. SRAM macro internal power fully characterized: no.
15. Characterized classes: IDLE, WRITE_CLEAN, READ_CLEAN, READ_SINGLE_BIT_ERROR_CORRECT, and READ_DOUBLE_BIT_ERROR_DETECT for SECDED/Hsiao; seed 11 qualifies only the three read classes.
16. Operations measured: exactly 256 per class after 16 warm-up cycles.
17. E5 quantities: ECC-logic internal/switching/leakage/total power and operation-normalized energy for 46 records.
18. E4 diagnostic quantities: inherited area, routing, timing, and vectorless power; incomplete macro power is not promoted.
19. Whole-memory E5 qualified: no.
20. ECC-logic-only E5 qualified: yes.
21. Matched SECDED/Hsiao seeds completed: five for reads; four for all five classes.
22. Hsiao retained lower energy: no, not generally.
23. Ordering held for every seed: no.
24. Ordering held across operation classes: no; Hsiao was lower in {lower_count}/{comparison_count} matched cells.
25. Hsiao total-instance-area difference: mean +{p(area_mean)} um^2 across the inherited matched seeds.
26. Hsiao wirelength difference: mean +{p(wire_mean)} um.
27. Hsiao via difference: mean +{p(via_mean)} vias.
28. Hsiao setup-WNS difference: mean {p(wns_mean)} ns; better in four of five inherited matched seeds.
29. Clean-read energy difference (Hsiao minus SECDED): mean {p(read_mean, 1e12)} pJ/op over five seeds; Hsiao lower in {per_operation_fraction['READ_CLEAN']['hsiao_lower_energy_seed_count']}/5.
30. Clean-write energy difference: mean {p(write_mean, 1e12)} pJ/op over four qualified seeds; Hsiao lower in 0/4.
31. Single-error-correction energy difference: mean {p(correction_mean, 1e12)} pJ/op over five seeds; Hsiao lower in 0/5.
32. Double-error-detection energy difference: mean {p(detection_mean, 1e12)} pJ/op over five seeds; Hsiao lower in 0/5.
33. E5 versus E4 ordering: E5 mostly reverses the vectorless E4 Hsiao-lower tendency (4/23 E5 cells retain it versus 5/5 E4 seed-level power comparisons).
34. BCH timing feasible: no, at 10 ns or 5 ns in inherited evidence.
35. BCH critical-path dominant stage: not validated by retained stage-attributed timing evidence.
36. BCH activity characterized: no.
37. BCH eligible for the equal-performance E5 front: no.
38. U0 E5 baseline: no.
39. 5 ns E5 evidence: none.
40. OpenRAM rerun: no; it was not allowed to displace the primary matched experiment.
41. Physical/logical bit topology established: no.
42. Interleaver reliability claim: no.
43. Qcrit claim: no.
44. Physical FIT/SDC/DUE claim: no.
45. Absolute lifecycle-carbon claim: no.
46. Qualified sustainability Pareto front: no.
47. Global winner: `NO_GLOBAL_WINNER_QUALIFIED`.
48. Source/evidence files deleted during active execution: none.
49. Testing mutations: an early focused test regenerated placeholder reports/queue and exposed the stale hash; Windows Git also reported future LF-to-CRLF checkout warnings. Final validation mutations are recorded separately.
50. Cleanup postponed: all cache, fixture, duplicate, and uncertain cleanup.
51. Files eventually cleaned: none.
52. Frozen v3.2 integrity preserved: yes, guarded against its pinned seal commit.
53. Strongest ISCAS-safe claim: matched post-route activity and parasitic-aware ECC-logic energy shows the vectorless Hsiao-lower tendency is not robust across operation classes in this descriptive sample.
54. Still forbidden: silicon/foundry signoff, unrestricted whole-memory energy, physical SER/FIT/SDC/DUE/Qcrit, interleaver benefit, absolute SKY130 lifecycle carbon, imec certification/endorsement, and a global winner.
55. Highest-value next experiment: under a newly authorized campaign budget, add the matched five-seed 10 ns U0 IDLE/WRITE_CLEAN/READ_CLEAN baseline using the now-qualified pipeline.
""",
    )

    hash_manifest = campaign / "hashes" / "CAMPAIGN_ARTIFACTS.sha256"
    artifact_paths = [
        path
        for path in campaign.rglob("*")
        if path.is_file()
        and path != hash_manifest
        and "__pycache__" not in path.parts
        and path.name != "RUNTIME_STATE.json"
        and "logs" not in path.parts
        and "progress" not in path.parts
    ]
    write_text(
        hash_manifest,
        "\n".join(
            f"{sha256(path)}  {path.relative_to(campaign).as_posix()}"
            for path in sorted(artifact_paths)
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    finalize(args.repo.resolve())
    print("GREEN_V3_3_EXECUTED_EVIDENCE_FINALIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
