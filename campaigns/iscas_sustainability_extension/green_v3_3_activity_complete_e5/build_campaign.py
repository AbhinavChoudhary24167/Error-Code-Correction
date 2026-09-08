#!/usr/bin/env python3
"""Build deterministic, additive GREEN v3.3 campaign artifacts.

This builder audits and references the frozen v3.2 population.  It deliberately
does not invent activity-aware power: no E5 record is emitted until an activity
file and power report satisfying the qualification gates exist.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import statistics
from typing import Any, Iterable, Mapping


CAMPAIGN_REL = Path("campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5")
PARENT_REL = Path("campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation")
MACRO_REL = Path(
    "campaigns/iscas_sustainability_extension/memory_compiler/"
    "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure/source_checkout"
)
GENERATED_ON = "2026-09-09"
FOUNDATION_COMMIT = "affc8145b184803189dac36391cb486f00e7b4f8"
PARENT_PHYSICAL_COMMIT = "1f6bcd009e7a05ebcde35a3272161a9a81ec7bf7"
PARENT_V32_COMMIT = "29f20b196e04c713f88fd1a93440a2ff47986f06"
PARENT_V32_SEAL_COMMIT = "22d6ef2391f7d74f0890933fcda9952fdf656e52"
PARENT_MATCHED_COMMIT = "daaa83b6b3571060aec9d4d753b4907df5a2ba47"
PARENT_MATCHED_SEAL_COMMIT = "8af0fc5a2532b3471016a86cde7968af7d15cfa9"
ARCHITECTURES = ("U0", "SECDED", "HSIAO_SECDED", "BCH_78_64_T2")
SEEDS = (11, 13, 17, 19, 23)
CLOCKS = (10.0, 5.0)
OPERATIONS = {
    "U0": ("IDLE", "WRITE_CLEAN", "READ_CLEAN"),
    "SECDED": (
        "IDLE", "WRITE_CLEAN", "READ_CLEAN",
        "READ_SINGLE_BIT_ERROR_CORRECT", "READ_DOUBLE_BIT_ERROR_DETECT",
    ),
    "HSIAO_SECDED": (
        "IDLE", "WRITE_CLEAN", "READ_CLEAN",
        "READ_SINGLE_BIT_ERROR_CORRECT", "READ_DOUBLE_BIT_ERROR_DETECT",
    ),
    "BCH_78_64_T2": (
        "IDLE", "WRITE_CLEAN", "READ_CLEAN",
        "READ_ONE_BIT_ERROR_CORRECT", "READ_TWO_BIT_ERROR_CORRECT",
    ),
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def descriptive(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0, "mean": None, "median": None, "sample_standard_deviation": None,
            "minimum": None, "maximum": None, "descriptive_95_percent_ci_low": None,
            "descriptive_95_percent_ci_high": None, "coefficient_of_variation": None,
        }
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else None
    half = 2.776 * stdev / math.sqrt(len(values)) if len(values) == 5 and stdev is not None else None
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


def normalized_operation(operation: str) -> str:
    return {
        "READ_ONE_BIT_ERROR_CORRECT": "READ_SINGLE_PAYLOAD_BIT_ERROR_CORRECT",
        "READ_SINGLE_BIT_ERROR_CORRECT": "READ_SINGLE_PAYLOAD_BIT_ERROR_CORRECT",
        "READ_TWO_BIT_ERROR_CORRECT": "READ_TWO_PAYLOAD_BIT_ERROR",
        "READ_DOUBLE_BIT_ERROR_DETECT": "READ_TWO_PAYLOAD_BIT_ERROR",
    }.get(operation, operation)


def workload_definition(operation: str) -> dict[str, Any]:
    semantic = normalized_operation(operation)
    fault_count = 0
    if semantic == "READ_SINGLE_PAYLOAD_BIT_ERROR_CORRECT":
        fault_count = 1
    elif semantic == "READ_TWO_PAYLOAD_BIT_ERROR":
        fault_count = 2
    return {
        "schema_version": 1,
        "semantic_operation_class": semantic,
        "rng_seed": 3301,
        "payload_pattern_generator": "xorshift64star(seed=3301,index=i)",
        "address_sequence": "address[i]=(19+73*i) mod 256",
        "error_injection_sequence": (
            "none" if fault_count == 0 else f"payload_bits[(7*i+3) mod 64 .. {fault_count} distinct bits]"
        ),
        "injected_logical_bits_per_operation": fault_count,
        "warm_up_cycles": 16,
        "measured_cycles": 256,
        "exact_operation_count": 256,
    }


def workloads() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        for clock in CLOCKS:
            for seed in SEEDS:
                for operation in OPERATIONS[architecture]:
                    definition = workload_definition(operation)
                    begin = definition["warm_up_cycles"] * clock
                    end = (definition["warm_up_cycles"] + definition["measured_cycles"]) * clock
                    records.append(
                        {
                            "workload_record_id": (
                                f"{architecture.lower()}_clk{str(clock).replace('.', 'p')}ns_"
                                f"seed{seed}_{operation.lower()}"
                            ),
                            "architecture_id": architecture,
                            "physical_seed": seed,
                            "clock_period_ns": clock,
                            "operation_class": operation,
                            **definition,
                            "activity_begin_timestamp_ns": begin,
                            "activity_end_timestamp_ns": end,
                            "workload_sha256": digest_value(definition),
                            "activity_sha256": None,
                            "activity_boundary": "NOT_YET_GENERATED",
                            "qualification": "E5_BLOCKED_NO_ACTIVITY_POWER_RUN",
                        }
                    )
    return records


def metric(record: Mapping[str, Any], group: str, name: str) -> Any:
    return record["metrics"][group][name]


def timing_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        for clock in CLOCKS:
            selected = [
                row for row in records
                if row["architecture_id"] == architecture and row["clock_period_ns"] == clock
            ]
            wns = [float(metric(row, "timing", "setup_wns_ns")) for row in selected]
            feasible = sum(value >= 0 for value in wns)
            groups.append(
                {
                    "architecture_id": architecture,
                    "clock_period_ns": clock,
                    "setup_wns_ns": descriptive(wns),
                    "setup_feasible_seed_count": feasible,
                    "seed_count": len(selected),
                    "implementation_class": (
                        "TIMING_FEASIBLE_10NS"
                        if clock == 10.0 and feasible == len(selected)
                        else "TIMING_FEASIBLE_5NS"
                        if clock == 5.0 and feasible == len(selected)
                        else "TIMING_INFEASIBLE_AS_IMPLEMENTED"
                    ),
                }
            )
    return groups


def macro_audit(repo: Path) -> dict[str, Any]:
    macro_files = [
        repo / MACRO_REL / "sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib",
        repo / MACRO_REL / "sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib",
    ]
    records: list[dict[str, Any]] = []
    for path in macro_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        counts = {
            "cell_leakage_power": len(re.findall(r"\bcell_leakage_power\s*:", text)),
            "internal_power_groups": len(re.findall(r"\binternal_power\s*\(", text)),
            "conditional_power_groups": len(re.findall(r"\bwhen\s*:", text)),
            "timing_groups": len(re.findall(r"\btiming\s*\(", text)),
            "memory_groups": len(re.findall(r"\bmemory\s*\(", text)),
            "address_or_data_dependent_internal_power": len(
                re.findall(r"internal_power\s*\([^}]+when\s*:\s*\"[^\"]*(?:addr|din)", text, re.I | re.S)
            ),
        }
        records.append(
            {
                "path": path.relative_to(repo).as_posix(),
                "sha256": sha256(path),
                "observed_construct_counts": counts,
            }
        )
    quantities = {
        "leakage": "AVAILABLE",
        "internal_read_power": "PARTIAL",
        "internal_write_power": "PARTIAL",
        "clock_control_transitions": "PARTIAL",
        "address_dependent_transitions": "ABSENT",
        "data_dependent_transitions": "ABSENT",
        "output_switching": "PARTIAL",
        "read_write_timing_arcs": "AVAILABLE",
        "state_dependent_internal_power": "PARTIAL",
    }
    return {
        "schema_version": 1,
        "generated_on": GENERATED_ON,
        "corner": "tt_025C_1v80",
        "macro_records": records,
        "required_quantity_classification": quantities,
        "whole_memory_e5_qualified": False,
        "qualification": "E5_LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE",
        "qualification_note": (
            "Leakage, timing, and CE/WE-conditioned clock-pin internal-power groups are present, "
            "but the audited views do not establish address/data/state-dependent macro-internal energy."
        ),
    }


def matched_deltas(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["architecture_id"], row["clock_period_ns"], row["seed"]): row for row in records}
    rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        secded = by_key[("SECDED", 10.0, seed)]
        hsiao = by_key[("HSIAO_SECDED", 10.0, seed)]
        row: dict[str, Any] = {
            "seed": seed,
            "clock_period_ns": 10.0,
            "delta_definition": "HSIAO_SECDED_MINUS_SECDED",
        }
        mappings = {
            "total_instance_area_um2_delta": ("floorplan_placement", "total_instance_area_um2"),
            "standard_cell_area_um2_delta": ("floorplan_placement", "standard_cell_area_um2"),
            "wirelength_um_delta": ("routing", "total_wirelength_um"),
            "via_count_delta": ("routing", "via_count"),
            "setup_wns_ns_delta": ("timing", "setup_wns_ns"),
            "e4_switching_power_w_delta": ("power", "switching_w"),
            "e4_internal_power_w_delta": ("power", "internal_w"),
            "e4_leakage_power_w_delta": ("power", "leakage_w"),
        }
        for name, (group, key) in mappings.items():
            left, right = metric(hsiao, group, key), metric(secded, group, key)
            row[name] = None if left is None or right is None else left - right
        row.update(
            {
                "clean_read_energy_j_delta": None,
                "clean_write_energy_j_delta": None,
                "correction_energy_j_delta": None,
                "detection_energy_j_delta": None,
                "energy_qualification": "E5_BLOCKED_NO_ACTIVITY_POWER_RUN",
            }
        )
        rows.append(row)
    return rows


def build(repo: Path) -> None:
    campaign = repo / CAMPAIGN_REL
    parent = repo / PARENT_REL
    physical_payload = json.loads((parent / "PHYSICAL_RUN_RESULTS.json").read_text(encoding="utf-8"))
    physical_records: list[dict[str, Any]] = physical_payload["records"]
    workload_records = workloads()
    timing = timing_summary(physical_records)
    macro = macro_audit(repo)
    deltas = matched_deltas(physical_records)

    parents = {
        "foundation_commit": FOUNDATION_COMMIT,
        "parent_physical_population_commit": PARENT_PHYSICAL_COMMIT,
        "parent_green_v3_2_commit": PARENT_V32_COMMIT,
        "parent_green_v3_2_provenance_seal_commit": PARENT_V32_SEAL_COMMIT,
        "parent_matched_campaign_commit": PARENT_MATCHED_COMMIT,
        "parent_matched_campaign_seal_commit": PARENT_MATCHED_SEAL_COMMIT,
    }
    write_json(
        campaign / "WORKLOAD_MANIFEST.json",
        {
            "schema_version": 1,
            "generated_on": GENERATED_ON,
            "record_count": len(workload_records),
            "shared_semantics_note": (
                "Equivalent classes use identical generator definitions and workload hashes across architectures, "
                "physical seeds, and clocks."
            ),
            "records": workload_records,
        },
    )
    write_json(campaign / "TIMING_FEASIBILITY.json", {"schema_version": 1, "records": timing})
    write_json(campaign / "SRAM_MACRO_POWER_QUALIFICATION.json", macro)

    empty_stats = {
        "schema_version": 1,
        "record_count": 0,
        "records": [],
        "qualification": "E5_BLOCKED_NO_ACTIVITY_POWER_RUN",
        "required_statistics": [
            "count", "mean", "median", "sample_standard_deviation", "minimum", "maximum",
            "descriptive_95_percent_ci", "coefficient_of_variation",
        ],
        "note": "No vectorless E4 power was converted into operation energy.",
    }
    write_json(campaign / "E5_OPERATION_STATISTICS.json", empty_stats)
    write_csv(
        campaign / "E5_OPERATION_STATISTICS.csv",
        [
            "architecture_id", "clock_period_ns", "operation_class", "count", "mean_energy_j",
            "median_energy_j", "sample_standard_deviation_j", "minimum_energy_j", "maximum_energy_j",
            "descriptive_95_percent_ci_low_j", "descriptive_95_percent_ci_high_j",
            "coefficient_of_variation", "qualification",
        ],
        [],
    )
    write_json(
        campaign / "E5_MATCHED_SEED_DELTAS.json",
        {
            "schema_version": 1,
            "comparison": "HSIAO_SECDED_MINUS_SECDED_AT_10NS_MATCHED_SEEDS",
            "record_count": len(deltas),
            "records": deltas,
            "energy_ordering_preserved_fraction": None,
            "energy_qualification": "E5_BLOCKED_NO_ACTIVITY_POWER_RUN",
        },
    )
    delta_fields = list(deltas[0])
    write_csv(campaign / "E5_MATCHED_SEED_DELTAS.csv", delta_fields, deltas)

    inherited_manifest_sha = sha256(parent / "RUN_MANIFEST.json")
    write_json(
        campaign / "RUN_MANIFEST.json",
        {
            "schema_version": 1,
            "campaign": "green_v3_3_activity_complete_e5",
            "generated_on": GENERATED_ON,
            **parents,
            "budget": {
                "scope": "ENTIRE_CAMPAIGN",
                "maximum_wall_clock_seconds": 54000,
                "maximum_wall_clock_hours": 15,
                "per_run_timeout_seconds": None,
                "deadline_persistence": "RUNTIME_STATE.json",
            },
            "fresh_rtl_to_gdsii_executed": False,
            "inherited_physical_population": {
                "run_count": len(physical_records),
                "source": (PARENT_REL / "RUN_MANIFEST.json").as_posix(),
                "source_sha256": inherited_manifest_sha,
                "policy": "IMMUTABLE_REFERENCE_NO_RECOMPUTATION",
            },
            "workload_manifest": {
                "path": "WORKLOAD_MANIFEST.json",
                "record_count": len(workload_records),
            },
            "new_activity_power_records": [],
            "new_e5_record_count": 0,
        },
    )
    write_json(
        campaign / "CAMPAIGN_QUEUE.json",
        {
            "schema_version": 1,
            "budget_scope": "ENTIRE_CAMPAIGN",
            "campaign_budget_seconds": 54000,
            "per_run_timeout_seconds": None,
            "jobs": [],
            "queue_state": "NOT_POPULATED_UNTIL_EXECUTABLE_ACTIVITY_FLOW_IS_AUDITED",
            "priority_policy": [
                "A: 10ns U0/SECDED/HSIAO seeds 11,13,17,19,23",
                "B: 10ns BCH diagnostic",
                "C: 5ns sensitivity population",
            ],
        },
    )

    failures = {
        "schema_version": 1,
        "records": [
            {
                "experiment": "activity_complete_post_route_power",
                "status": "NOT_EXECUTED_ENVIRONMENT_BLOCKED",
                "classification": "E5_BLOCKED_NO_ACTIVITY_POWER_RUN",
                "reason": (
                    "The native environment exposes no OpenROAD/OpenSTA executable and the v3.2 final netlist/SPEF "
                    "artifacts referenced by hash are not present for the complete four-architecture population."
                ),
                "partial_artifacts_preserved": ["WORKLOAD_MANIFEST.json", "TIMING_FEASIBILITY.json"],
            },
            {
                "experiment": "fresh_rtl_to_gdsii",
                "status": "NOT_EXECUTED_OPTIONAL",
                "classification": "INHERITED_40_RUN_POPULATION_REUSED",
                "reason": "The complete matched v3.2 routed/GDS population is referenced immutably; budget is reserved for E5 work.",
                "partial_artifacts_preserved": [],
            },
        ],
    }
    write_json(campaign / "FAILED_PARTIAL_EXPERIMENTS.json", failures)

    matrix = {
        "schema_version": "3.3.0",
        "mode": "ADDITIVE_ONLY",
        **parents,
        "parent_counts": {"M_E": 601, "M_P": 10, "M_S": 2},
        "new_evidence_counts": {"E3": 0, "E4": 0, "E5": 0},
        "combined_counts": {"M_E": 601, "M_P": 10, "M_S": 2},
        "records": [],
        "admission_guard": "NO_E5_RECORD_WITHOUT_ACTIVITY_HASH_COVERAGE_OPERATION_COUNT_PARASITICS_AND_MACRO_SCOPE",
        "global_winner": "NO_GLOBAL_WINNER_QUALIFIED",
    }
    write_json(campaign / "GREEN_V3_3_ADDITIVE_MATRIX.json", matrix)

    status = {
        "schema_version": "1.0.0",
        "campaign": "green_v3_3_activity_complete_e5",
        "generated_on": GENERATED_ON,
        **parents,
        "runtime_budget": {
            "scope": "ENTIRE_CAMPAIGN",
            "seconds": 54000,
            "hours": 15,
            "per_run_timeout_seconds": None,
            "campaign_started": False,
            "deadline_hit": False,
        },
        "included_architectures": list(ARCHITECTURES),
        "inherited_physical_run_count": 40,
        "fresh_physical_run_count": 0,
        "timing_feasible_10ns": ["U0", "SECDED", "HSIAO_SECDED"],
        "timing_feasible_5ns": ["U0"],
        "timing_infeasible_as_implemented": [
            "BCH_78_64_T2@10ns", "SECDED@5ns", "HSIAO_SECDED@5ns", "BCH_78_64_T2@5ns",
        ],
        "workload_specification_count": len(workload_records),
        "post_route_activity_generated": False,
        "activity_format": None,
        "activity_annotation_coverage": None,
        "macro_power_qualification": macro["qualification"],
        "whole_memory_e5_qualified": False,
        "ecc_logic_e5_qualified": False,
        "E5_status": "E5_BLOCKED_NO_ACTIVITY_POWER_RUN",
        "evidence_added": {"E3": 0, "E4": 0, "E5": 0},
        "qualified_e5_pareto_status": "BLOCKED",
        "qualified_sustainability_pareto_status": "BLOCKED",
        "physical_SDC_DUE_FIT": "BLOCKED",
        "Qcrit": "BLOCKED",
        "physical_logical_topology": "BLOCKED",
        "interleaver_reliability": "BLOCKED",
        "SKY130_manufacturing_lifecycle_carbon": "BLOCKED",
        "global_winner": "NO_GLOBAL_WINNER_QUALIFIED",
        "classification": (
            "GREEN_V3_3_ACTIVITY_WORKLOAD_AND_GLOBAL_RUNTIME_INFRASTRUCTURE_COMPLETE_"
            "INHERITED_MATCHED_PHYSICAL_POPULATION_E5_BLOCKED_NO_ACTIVITY_POWER_RUN_"
            "MACRO_ENERGY_INCOMPLETE_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED"
        ),
    }
    write_json(campaign / "CAMPAIGN_STATUS.json", status)

    write_text(
        campaign / "CAMPAIGN_PLAN.md",
        f"""# GREEN v3.3 activity-complete E5 campaign plan

## Immutable foundation

This additive campaign starts from matched-campaign seal `{PARENT_MATCHED_SEAL_COMMIT}` and preserves all GREEN v3.2 files byte-for-byte. The 40 inherited U0, SECDED, Hsiao SECDED, and BCH(78,64,t=2) runs remain the physical population.

## One campaign budget

The hard limit is **15 hours (54,000 seconds for the entire campaign)**. It is not 15 hours per job, phase, architecture, seed, or resume invocation. `RUNTIME_STATE.json` is created once when execution begins and persists one start time and one hard deadline. Every subprocess is limited to `min(explicit_shorter_job_limit, time_remaining_to_campaign_deadline)`; with no shorter limit it receives only the remaining campaign time. New expensive work is not launched within the five-minute deadline guard.

Priority A is the 10 ns U0/SECDED/Hsiao five-seed E5 population. Priority B is timing-labelled 10 ns BCH. Priority C is the 5 ns sensitivity population. A fresh physical rerun is optional because the 40-run v3.2 population is already complete.

## Qualification gates

E5 requires an activity hash, workload hash, exact measurement window and operation count, annotation coverage, final-netlist and SPEF hashes, PVT/clock/seed provenance, and a declared macro-power boundary. Missing data remain null. Vectorless E4 power is never converted to E5 energy.
""",
    )
    write_text(
        campaign / "PROGRESS.md",
        """# GREEN v3.3 campaign progress

- Runtime campaign: `NOT_STARTED`
- Budget: `54000 seconds total across the entire campaign`
- Per-run 15-hour timeout: `DISABLED`
- Inherited physical evidence: `40/40 referenced`
- Workload specifications: `180/180 generated`
- Current experiment: `NONE`
- Post-route activity/power: `0 completed`
- E5-qualified records: `0`
- Blocker: `complete-population post-route artifacts and OpenROAD/OpenSTA execution are unavailable in the native environment`

The controller and qualification matrix are ready. Starting or resuming execution will use one persisted deadline; no job receives a renewed 15-hour allowance.
""",
    )
    write_text(
        campaign / "ACTIVITY_COVERAGE_REPORT.md",
        """# Activity coverage report

No VCD or SAIF has been generated in v3.3, so explicit annotation coverage is unavailable rather than zero. The deterministic workload specifications are complete, but they are not activity evidence. No RTL trace is described as post-route activity and no vectorless fallback is promoted to E5.

The admission gate requires activity source/hash, measurement window, operation count, sequential/combinational/macro coverage, final-netlist hash, SPEF hash, clock/PVT/seed, and macro scope. Current classification: `E5_BLOCKED_NO_ACTIVITY_POWER_RUN`.
""",
    )
    write_text(
        campaign / "SRAM_MACRO_POWER_AUDIT.md",
        f"""# SRAM22 macro-power audit

The two inherited tt/25 C/1.80 V Liberty views were inspected by hash. Both contain leakage, memory/timing groups, and eight CE/WE-conditioned internal-power groups. They do not establish address-dependent or data-dependent macro-internal energy, and full state-dependent coverage has not been validated.

| Quantity | Classification |
|---|---|
""" + "\n".join(f"| {name} | `{classification}` |" for name, classification in macro["required_quantity_classification"].items()) + f"""

Whole-memory E5 is therefore not qualified. The allowed boundary is `{macro['qualification']}` if logic activity later passes its own gates; ECC-logic and whole-memory energy must remain separate.
""",
    )
    bch10 = next(row for row in timing if row["architecture_id"] == "BCH_78_64_T2" and row["clock_period_ns"] == 10.0)
    bch5 = next(row for row in timing if row["architecture_id"] == "BCH_78_64_T2" and row["clock_period_ns"] == 5.0)
    write_text(
        campaign / "BCH_TIMING_DIAGNOSIS.md",
        f"""# BCH timing diagnosis

BCH(78,64,t=2) is `TIMING_INFEASIBLE_AS_IMPLEMENTED` for all five inherited seeds at both constraints. Setup WNS is {bch10['setup_wns_ns']['minimum']:.6g} to {bch10['setup_wns_ns']['maximum']:.6g} ns at 10 ns (mean {bch10['setup_wns_ns']['mean']:.6g} ns) and {bch5['setup_wns_ns']['minimum']:.6g} to {bch5['setup_wns_ns']['maximum']:.6g} ns at 5 ns.

The compact v3.2 records do not preserve a stage-attributed critical-path report, so encoder, syndrome, error-location, correction-mux, and macro-interface contributions remain `NOT_VALIDATED`. No stage is guessed from RTL structure. BCH is retained for labelled diagnostics and excluded from the equal-performance E5 Pareto population. No pipelined replacement was introduced.
""",
    )
    write_text(
        campaign / "CLAIM_EVIDENCE_MAP.md",
        """# Claim-to-evidence map

| Claim | Evidence | Status |
|---|---|---|
| The physical population contains 40 matched routed/GDS runs | Frozen v3.2 `RUN_MANIFEST.json`, hash pinned in this campaign | Supported (inherited E4) |
| U0, SECDED, and Hsiao are setup-feasible at 10 ns | `TIMING_FEASIBILITY.json`, five seeds each | Supported |
| Only U0 is setup-feasible at 5 ns | `TIMING_FEASIBILITY.json`, five seeds each | Supported |
| Workloads are deterministic and semantically matched | `WORKLOAD_MANIFEST.json` | Supported as infrastructure only |
| Activity-aware operation energy is E5 | No qualifying activity/power record | Forbidden |
| Whole-memory E5 energy is qualified | `SRAM_MACRO_POWER_QUALIFICATION.json` | Forbidden |
| Hsiao retains lower operation energy than SECDED | No E5 energy measurements | Unresolved |
| BCH is equal-performance at 10 ns | Negative WNS for 5/5 seeds | Forbidden |
| Physical FIT/Qcrit/interleaver benefit/absolute lifecycle carbon | Required evidence absent | Forbidden |
| A global winner exists | Mandatory dimensions remain blocked | `NO_GLOBAL_WINNER_QUALIFIED` |
""",
    )
    write_text(
        campaign / "ISCAS_EXPERIMENT_SUMMARY.md",
        """# ISCAS experiment summary

GREEN v3.3 adds deterministic operation-class workload definitions, explicit timing-feasibility partitioning, an SRAM macro-power audit, and a restart-safe global runtime controller. The controller enforces one 15-hour budget across the full campaign, not per run.

The inherited 40-run physical population supports E4 physical comparisons. No new VCD/SAIF power analysis was executable in the available native environment, so no energy value was promoted to E5. Macro-internal energy also remains incomplete. The strongest current claim is therefore readiness and fail-closed qualification infrastructure for a matched activity-aware campaign, while operational-energy ordering remains unresolved.
""",
    )
    write_text(
        campaign / "FINAL_REPORT.md",
        """# GREEN v3.3 final report

## Outcome

The campaign infrastructure and evidence audit are complete, but activity-aware power execution is blocked in this environment. This is an honest partial result: **zero E5 records were created**. The one persisted 15-hour campaign budget is implemented and regression-tested; it is never renewed for individual OpenROAD/OpenRAM jobs.

## Required answers

1. Architectures: U0, SECDED, Hsiao SECDED, and BCH(78,64,t=2).
2. Timing-feasible at 10 ns: U0, SECDED, Hsiao SECDED (5/5 setup-feasible seeds each).
3. Timing-feasible at 5 ns: U0 only (5/5 setup-feasible seeds).
4. Fresh RTL-to-GDSII executed: no; it was optional and the complete inherited population was reused.
5. Physical runs completed: 40 inherited, 0 fresh.
6. Fifteen-hour deadline hit: no; expensive execution was not started.
7. Runtime-cutoff runs: none.
8. Post-route activity generated: no.
9. Netlist boundary: not established for activity.
10. Activity format: neither VCD nor SAIF.
11. Explicit annotation fraction: unavailable, not reported as zero.
12. SRAM macro internal power fully characterized: no.
13. Operation classes specified: IDLE/WRITE_CLEAN/READ_CLEAN for U0; those plus single-correct/double-detect for SECDED/Hsiao; those plus one- and two-bit-correct for BCH.
14. Operations planned per class: 256 after 16 warm-up cycles.
15. Quantities promoted to E5: none.
16. E4 diagnostic quantities: inherited area, routing, timing, and vectorless power.
17. Whole-memory E5: not qualified.
18. ECC-logic E5: not yet qualified.
19. Hsiao lower-energy tendency: unresolved.
20. Five-seed operation-energy ordering: unresolved.
21. Hsiao area delta: recorded per seed in `E5_MATCHED_SEED_DELTAS.csv` as inherited physical evidence.
22. Hsiao wirelength delta: recorded per seed in the same table.
23. Hsiao via delta: recorded per seed in the same table.
24. Hsiao timing delta: recorded per seed; Hsiao and SECDED are both feasible at 10 ns.
25. Clean-read energy difference: unavailable.
26. Clean-write energy difference: unavailable.
27. Single-error correction energy difference: unavailable.
28. BCH timing feasible: no, at 10 ns or 5 ns.
29. BCH dominant critical-path stage: not validated by the retained compact reports.
30. BCH in equal-performance E5 Pareto set: no.
31. Globally dominant architecture: none qualified.
32. E5 alteration of E4 ordering: none; there is no E5 evidence.
33. OpenRAM rerun: no; incomplete macro fidelity is documented rather than hidden.
34. Physical/logical topology: not established.
35. Interleaver reliability claim: forbidden.
36. Qcrit claim: forbidden.
37. Physical FIT/SDC/DUE claim: forbidden.
38. Absolute lifecycle-carbon claim: forbidden.
39. Qualified sustainability Pareto front: blocked.
40. Global winner: `NO_GLOBAL_WINNER_QUALIFIED`.
41. Strongest ISCAS-safe claim: a reproducible, timing-partitioned matched physical foundation and deterministic activity-campaign protocol with fail-closed evidence admission.
42. Forbidden: silicon/signoff, E5 energy, complete macro energy, physical reliability, Qcrit, interleaver benefit, absolute SKY130 lifecycle carbon, and a global winner.
43. Highest-value next experiment: execute post-route activity-aware clean read/write and correction power for the 10 ns SECDED/Hsiao matched five-seed set under the shared campaign deadline.
""",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    build(args.repo.resolve())
    print("GREEN_V3_3_ARTIFACTS_BUILT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

