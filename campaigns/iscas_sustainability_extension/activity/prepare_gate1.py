#!/usr/bin/env python3
"""Freeze the exact Gate-1 W1/W2 power matrix without running experiments."""

from __future__ import annotations

import json
from pathlib import Path

from gate1_common import aggregate_hash, read_csv, sha256, write_csv, write_json


SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[3]
CAMPAIGN = REPO / "campaigns/iscas_sustainability_extension"
ACTIVITY = CAMPAIGN / "activity"
REV2_ROOT = Path("/var/lib/green-ecc-date2027-revision2")
BREADTH_ROOT = Path("/var/lib/green-ecc-date2027-breadth-remediation")
OUTPUT_ROOT = Path("/var/lib/green-ecc-iscas-sustainability/gate1_activity_power_attempt02")
SEEDS = (11, 13, 17, 19, 23)


ARCHITECTURES = {
    "secded_comb": {
        "implementation_id": "secded-rtl-combinational-72-64-v1",
        "family": "secded",
        "source": "revision2",
        "design_top": "gate04_secded_comb_72_64",
        "config": "scripts/revision2/configs/secded_comb.mk",
        "run_prefix": "secded-comb-seed-",
        "results_rel": "results/sky130hd/gate04_secded_comb_72_64/base",
        "trace_family": "conventional_secded",
    },
    "secded_pipe": {
        "implementation_id": "secded-rtl-pipelined-72-64-v1",
        "family": "secded",
        "source": "revision2",
        "design_top": "gate04_secded_pipe_72_64",
        "config": "scripts/revision2/configs/secded_pipe.mk",
        "run_prefix": "secded-pipe-seed-",
        "results_rel": "results/sky130hd/gate04_secded_pipe_72_64/base",
        "trace_family": "conventional_secded",
    },
    "hsiao_flat": {
        "implementation_id": "hsiao-algorithmic-combinational-72-64-rev2-v1",
        "family": "hsiao",
        "source": "breadth",
        "design_top": "gate04_rev2_hsiao_72_64",
        "config": "campaigns/date_2027_breadth_remediation/configs/A_hsiao_flat.mk",
        "run_prefix": "A/A-hsiao-flat-seed-",
        "results_rel": "results/sky130hd/gate04_rev2_hsiao_72_64/base",
        "trace_family": "hsiao",
    },
    "hsiao_hierarchical": {
        "implementation_id": "hsiao-hierarchical-nibble-decode-combinational-72-64-breadth-v1",
        "family": "hsiao",
        "source": "breadth",
        "design_top": "breadth_hsiao_hierarchical_72_64",
        "config": "campaigns/date_2027_breadth_remediation/configs/A_hsiao_hierarchical.mk",
        "run_prefix": "A/A-hsiao-hierarchical-seed-",
        "results_rel": "results/sky130hd/breadth_hsiao_hierarchical_72_64/base",
        "trace_family": "hsiao",
    },
}


def by_key(rows: list[dict[str, str]], *fields: str) -> dict[tuple[str, ...], dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in result:
            raise SystemExit(f"duplicate source row for key {key}")
        result[key] = row
    return result


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise SystemExit(f"refusing to prepare against an existing Gate-1 output root: {OUTPUT_ROOT}")

    baseline_rows = read_csv(CAMPAIGN / "baseline_results.csv")
    baseline_index = by_key(baseline_rows, "architecture", "seed", "clock_period_ns")
    pair_rows = read_csv(REPO / "campaigns/date_2027_breadth_remediation/analysis/A_structural_pair_per_seed.csv")
    pair_index = by_key(pair_rows, "architecture", "seed")
    trace_manifest_path = REPO / "docs/date2027/rigour_gate_03f/ACTIVITY_TRACE_MANIFEST.json"
    trace_manifest = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    trace_index = {row["file"]: row for row in trace_manifest["traces"]}

    runs: list[dict[str, object]] = []
    point_rows: list[dict[str, object]] = []
    for architecture, spec in ARCHITECTURES.items():
        for seed in SEEDS:
            seed_text = str(seed)
            if spec["source"] == "revision2":
                source_row = baseline_index[(architecture, seed_text, "10.0")]
                input_root = REV2_ROOT / "runs" / f"{spec['run_prefix']}{seed}"
                rtl_hash = source_row["rtl_sha256"]
                source_hashes = json.loads(source_row["rtl_sources_json"])
                physical_hashes = {
                    "odb": source_row["final_odb_sha256"],
                    "sdc": source_row["final_sdc_sha256"],
                    "spef": source_row["final_spef_sha256"],
                    "netlist": source_row["final_netlist_sha256"],
                }
            else:
                pair_arch = "A_hsiao_flat" if architecture == "hsiao_flat" else "A_hsiao_hierarchical"
                source_row = pair_index[(pair_arch, seed_text)]
                input_root = BREADTH_ROOT / "runs" / f"{spec['run_prefix']}{seed}"
                source_hashes = json.loads(source_row["source_hashes_json"])
                rtl_hash = aggregate_hash(source_hashes)
                physical_hashes = {
                    "odb": source_row["final_odb_sha256"],
                    "sdc": source_row["final_sdc_sha256"],
                    "spef": source_row["final_spef_sha256"],
                    "netlist": source_row["final_netlist_sha256"],
                }
            results = input_root / str(spec["results_rel"])
            artifacts = {
                "odb": {"path": str(results / "6_final.odb"), "sha256": physical_hashes["odb"]},
                "sdc": {"path": str(results / "6_final.sdc"), "sha256": physical_hashes["sdc"]},
                "spef": {"path": str(results / "6_final.spef"), "sha256": physical_hashes["spef"]},
                "netlist": {"path": str(results / "6_final.v"), "sha256": physical_hashes["netlist"]},
            }
            traces = []
            for activity_class, suffix, semantic in (
                ("W1", "single_error", "successful_correction"),
                ("W2", "double_error", "successful_detection_not_correction"),
            ):
                filename = f"{spec['trace_family']}-10ns-{suffix}.vcd.gz"
                trace = trace_index[filename]
                trace_path = REV2_ROOT / "policy/traces" / filename
                record = {
                    "activity_class": activity_class,
                    "semantic_action": semantic,
                    "path": str(trace_path),
                    "sha256": trace["compressed_sha256"],
                    "uncompressed_sha256": trace["uncompressed_sha256"],
                    "trace_duration_ps": int(trace["total_time_ps"]),
                    "useful_operations": int(trace["useful_operations"]),
                    "payload_seed": int(trace["payload_seed"]),
                    "fault_schedule_seed": int(trace["fault_schedule_seed"]),
                }
                traces.append(record)
                point_rows.append(
                    {
                        "run_id": f"{architecture}-seed-{seed}",
                        "hardware_identity": spec["implementation_id"],
                        "architecture": architecture,
                        "seed": seed,
                        "activity_class": activity_class,
                        "odb_path": artifacts["odb"]["path"],
                        "sdc_path": artifacts["sdc"]["path"],
                        "spef_path": artifacts["spef"]["path"],
                        "vcd_path": trace_path,
                        "output_path": OUTPUT_ROOT / "runs" / f"{architecture}-seed-{seed}" / "power",
                    }
                )
            runs.append(
                {
                    "run_id": f"{architecture}-seed-{seed}",
                    "hardware_identity": spec["implementation_id"],
                    "family": spec["family"],
                    "architecture": architecture,
                    "seed": seed,
                    "target_ns": 10.0,
                    "technology": "SKY130HD",
                    "corner": "tt_025C_1v80",
                    "voltage_v": 1.8,
                    "temperature_c": 25,
                    "source_evidence_root": str(REV2_ROOT if spec["source"] == "revision2" else BREADTH_ROOT),
                    "input_run_root": str(input_root),
                    "source_kind": spec["source"],
                    "design_top": spec["design_top"],
                    "config": spec["config"],
                    "results_relative_path": spec["results_rel"],
                    "rtl_hash": rtl_hash,
                    "rtl_sources": source_hashes,
                    "physical_artifacts": artifacts,
                    "traces": traces,
                    "eligibility": "TIMING_FEASIBLE_10NS",
                }
            )

    contract = {
        "schema_version": 1,
        "gate": "Gate 1 - activity-conditioned post-route power",
        "state": "FROZEN_BEFORE_EXECUTION",
        "baseline_commit": "9968f9b15f949d38faf944a3546ea736cfab63df",
        "physical_evidence_commit": "b51291442bbd04346dac939dea6ba7d532b9c5c4",
        "branch": "codex/ecc-lifecycle-sustainability",
        "container_image": "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e",
        "openroad_commit": "ab6fd26351dc449e69059684dc6aa9ae9046eb36",
        "orfs_commit": "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2",
        "trace_scope": "gate04_trace_top",
        "seeds": list(SEEDS),
        "new_power_point_count": len(point_rows),
        "container_invocation_count": len(runs),
        "output_root": str(OUTPUT_ROOT),
        "execution_attempt": 2,
        "preserved_predecessor": {
            "path": "/var/lib/green-ecc-iscas-sustainability/gate1_activity_power",
            "classification": "INFRASTRUCTURE_FAIL_BEFORE_OPENROAD_POWER_ANALYSIS",
            "reason": "unquoted shell metacharacters in the trace-specification environment value",
            "scientific_power_points_produced": 0,
        },
        "non_repetition": {
            "physical_design": False,
            "synthesis": False,
            "w0_power": False,
            "formal": False,
            "trace_generation": False,
            "new_operations": ["W1 post-route power", "W2 post-route power"],
        },
        "reporting_boundary": {
            "authoritative": "report_power -digits 12 Total and common power-group rows",
            "retained": [
                "internal power",
                "switching power",
                "leakage power",
                "total power",
                "sequential group power",
                "combinational group power",
                "clock group power",
                "activity annotation coverage",
            ],
            "per_instance": "NOT_QUALIFIED_IN_FROZEN_W0_COMMON_BOUNDARY",
            "per_net": "NOT_QUALIFIED_IN_FROZEN_W0_COMMON_BOUNDARY",
            "glitch_claim": "FORBIDDEN",
        },
        "trace_manifest": {"path": str(trace_manifest_path), "sha256": sha256(trace_manifest_path)},
        "runs": runs,
    }
    write_json(ACTIVITY / "gate1_contract.json", contract)
    write_csv(
        ACTIVITY / "gate1_job_matrix.csv",
        [
            "run_id",
            "hardware_identity",
            "architecture",
            "seed",
            "activity_class",
            "odb_path",
            "sdc_path",
            "spef_path",
            "vcd_path",
            "output_path",
        ],
        point_rows,
    )
    print(f"GATE1_PREPARE_PASS points={len(point_rows)} invocations={len(runs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
