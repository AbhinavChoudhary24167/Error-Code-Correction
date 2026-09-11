#!/usr/bin/env python3
"""Execute and collect the pinned matched multi-seed ORFS campaign in WSL."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


CAMPAIGN_REL = Path("campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation")
MACRO_REL = Path(
    "campaigns/iscas_sustainability_extension/memory_compiler/"
    "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
)
DEFAULT_EXTERNAL_ROOT = Path("/var/lib/green-ecc-v32-matched-openram-orfs-validation")
IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
SEEDS = [11, 13, 17, 19, 23]
CLOCKS = [10.0, 5.0]
ARCHITECTURES = {
    "U0": {
        "top": "u0_matched_sram_top",
        "config": "u0.mk",
        "placement": "macro_placement_u0.tcl",
        "rtl": [],
        "physical_stored_bits": 16384,
        "macro_count": 1,
    },
    "SECDED": {
        "top": "secded_matched_sram_top",
        "config": "secded.mk",
        "placement": "macro_placement_72.tcl",
        "rtl": ["scripts/gate03r/rtl/secded_characterization_tops.sv"],
        "physical_stored_bits": 18432,
        "macro_count": 2,
    },
    "HSIAO_SECDED": {
        "top": "hsiao_matched_sram_top",
        "config": "hsiao.mk",
        "placement": "macro_placement_72.tcl",
        "rtl": [
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv",
        ],
        "physical_stored_bits": 18432,
        "macro_count": 2,
        "architecture_specific_exceptions": [
            {
                "id": "HSIAO_COMBINATIONAL_SYNDROME_ROM_INFERENCE_THRESHOLD",
                "setting": "SYNTH_MEMORY_MAX_BITS=20000",
                "reason": "The explicit syndrome case table is recognized as a 256x73 combinational ROM and must reach memory_map for standard-cell lowering.",
                "semantic_change": False,
                "matched_boundary_change": False,
            }
        ],
    },
    "BCH_78_64_T2": {
        "top": "bch_t2_matched_sram_top",
        "config": "bch_t2.mk",
        "placement": "macro_placement_bch.tcl",
        "rtl": ["asic/rtl/bch/bch_78_64_t2_v1.sv"],
        "physical_stored_bits": 20480,
        "macro_count": 3,
    },
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def metric(payload: dict[str, Any], name: str) -> Any:
    value = payload.get(name)
    return value if isinstance(value, (int, float)) else None


def compress_log(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_stream, destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output_stream:
            shutil.copyfileobj(input_stream, output_stream)


def parse_cell_counts(path: Path) -> dict[str, int | None]:
    if not path.is_file():
        return {
            "mapped_cell_count": None,
            "combinational_cells": None,
            "sequential_cells": None,
            "buffers_inverters": None,
            "xor_xnor_cells": None,
            "register_count": None,
        }
    cells: dict[str, int] = {}
    total = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        total_match = re.match(r"\s*Number of cells:\s+(\d+)", line)
        if total_match:
            total = int(total_match.group(1))
        table_total_match = re.match(r"\s*(\d+)\s+\S+\s+\d+\s+\S+\s+cells\s*$", line)
        if table_total_match:
            total = int(table_total_match.group(1))
        cell_match = re.match(r"\s*(\d+)\s+\S+\s+\d+\s+\S+\s+(sky130_fd_sc_hd__\S+)\s*$", line)
        if cell_match:
            cells[cell_match.group(2)] = int(cell_match.group(1))
        legacy_cell_match = re.match(r"\s*(sky130_fd_sc_hd__\S+)\s+(\d+)\s*$", line)
        if legacy_cell_match:
            cells[legacy_cell_match.group(1)] = int(legacy_cell_match.group(2))
    sequential = sum(count for name, count in cells.items() if "__df" in name or "__dl" in name)
    buffers = sum(count for name, count in cells.items() if "__buf_" in name or "__inv_" in name or "__clkinv_" in name)
    xor_count = sum(count for name, count in cells.items() if "xor" in name)
    standard_cells = sum(cells.values())
    return {
        "mapped_cell_count": total,
        "combinational_cells": standard_cells - sequential,
        "sequential_cells": sequential,
        "buffers_inverters": buffers,
        "xor_xnor_cells": xor_count,
        "register_count": sequential,
    }


def collect_metrics(run_root: Path, top: str, variant: str, clock: float) -> tuple[dict[str, Any], dict[str, str]]:
    results = run_root / "results/sky130hd" / top / variant
    logs = run_root / "logs/sky130hd" / top / variant
    reports = run_root / "reports/sky130hd" / top / variant
    synth = read_json(logs / "1_synth.json")
    floorplan = read_json(logs / "2_4_floorplan_pdn.json")
    grt = read_json(logs / "5_1_grt.json")
    route = read_json(logs / "5_2_route.json")
    finish = read_json(logs / "6_report.json")
    cell_counts = parse_cell_counts(reports / "synth_stat.txt")
    setup_ws = metric(finish, "finish__timing__setup__ws")
    fmax = metric(finish, "finish__timing__fmax")
    metrics: dict[str, Any] = {
        "synthesis": {
            **cell_counts,
            "synthesized_area_um2": metric(synth, "synth__design__instance__area__stdcell"),
            "macro_count": metric(synth, "synth__design__instance__count__macros"),
        },
        "floorplan_placement": {
            "core_area_um2": metric(finish or floorplan, "finish__design__core__area")
            if finish
            else metric(floorplan, "floorplan__design__core__area"),
            "die_area_um2": metric(finish or floorplan, "finish__design__die__area")
            if finish
            else metric(floorplan, "floorplan__design__die__area"),
            "macro_area_um2": metric(finish, "finish__design__instance__area__macros"),
            "standard_cell_area_um2": metric(finish, "finish__design__instance__area__stdcell"),
            "total_instance_area_um2": metric(finish, "finish__design__instance__area"),
            "utilization": metric(finish, "finish__design__instance__utilization"),
            "standard_cell_utilization": metric(finish, "finish__design__instance__utilization__stdcell"),
            "placement_density_target": 0.30,
            "row_count": metric(finish, "finish__design__rows"),
        },
        "timing": {
            "setup_wns_ns": setup_ws,
            "setup_tns_ns": metric(finish, "finish__timing__setup__tns"),
            "setup_violation_count": metric(finish, "finish__timing__drv__setup_violation_count"),
            "hold_wns_ns": metric(finish, "finish__timing__hold__ws"),
            "hold_tns_ns": metric(finish, "finish__timing__hold__tns"),
            "hold_violation_count": metric(finish, "finish__timing__drv__hold_violation_count"),
            "critical_path_delay_ns": None,
            "derived_fmax_hz": fmax,
            "derived_frequency_qualified": False,
            "derived_frequency_limit": "Tool-reported fmax is diagnostic and is not maximum sustainable architectural throughput.",
            "requested_clock_period_ns": clock,
        },
        "clock": {
            "clock_buffer_count": metric(finish, "finish__design__instance__count__class:clock_buffer"),
            "clock_inverter_count": metric(finish, "finish__design__instance__count__class:clock_inverter"),
            "clock_tree_depth": None,
            "setup_skew_ns": metric(finish, "finish__clock__skew__setup"),
            "hold_skew_ns": metric(finish, "finish__clock__skew__hold"),
            "latency_ns": None,
        },
        "routing": {
            "total_wirelength_um": metric(route, "detailedroute__route__wirelength"),
            "wirelength_by_layer_um": None,
            "via_count": metric(route, "detailedroute__route__vias"),
            "route_overflow": metric(grt, "globalroute__design__violations"),
            "congestion_metric": None,
            "detailed_route_drc_errors": metric(route, "detailedroute__route__drc_errors"),
            "antenna_violating_nets": metric(route, "detailedroute__antenna__violating__nets"),
        },
        "power": {
            "internal_w": metric(finish, "finish__power__internal__total"),
            "switching_w": metric(finish, "finish__power__switching__total"),
            "leakage_w": metric(finish, "finish__power__leakage__total"),
            "clock_w": None,
            "total_w": metric(finish, "finish__power__total"),
            "qualification": "E4_DIAGNOSTIC_VECTORLESS",
            "activity_hash": None,
            "workload_hash": None,
        },
        "physical_outputs": {
            "synthesis_odb_generated": (results / "1_synth.odb").is_file(),
            "floorplan_odb_generated": (results / "2_floorplan.odb").is_file(),
            "placement_odb_generated": (results / "3_place.odb").is_file(),
            "cts_odb_generated": (results / "4_cts.odb").is_file(),
            "route_odb_generated": (results / "5_route.odb").is_file(),
            "final_odb_generated": (results / "6_final.odb").is_file(),
            "def_generated": (results / "6_final.def").is_file(),
            "gds_generated": (results / "6_final.gds").is_file(),
            "spef_generated": (results / "6_final.spef").is_file(),
            "netlist_generated": (results / "6_final.v").is_file(),
        },
    }
    important = [
        "1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_cts.odb",
        "5_route.odb", "6_final.odb", "6_final.def", "6_final.gds",
        "6_final.spef", "6_final.sdc", "6_final.v",
    ]
    hashes = {name: sha256(results / name) for name in important if (results / name).is_file()}
    return metrics, hashes


def stage_classification(metrics: dict[str, Any]) -> str:
    outputs = metrics["physical_outputs"]
    routing = metrics["routing"]
    if outputs["gds_generated"] and outputs["route_odb_generated"] and routing["detailed_route_drc_errors"] == 0:
        return "OPEN_SOURCE_RTL_TO_GDS_FLOW_VALIDATED"
    if outputs["route_odb_generated"]:
        return "ROUTING_VALIDATED"
    if outputs["placement_odb_generated"]:
        return "PLACEMENT_VALIDATED"
    if outputs["synthesis_odb_generated"]:
        return "SYNTHESIS_VALIDATED"
    return "RTL_VALIDATED_ONLY"


def run_one(repo: Path, external_root: Path, arch: str, clock: float, seed: int) -> dict[str, Any]:
    spec = ARCHITECTURES[arch]
    clock_tag = str(clock).replace(".", "p")
    run_id = f"{arch.lower()}_clk{clock_tag}ns_seed{seed}"
    variant = f"clk{clock_tag}ns_seed{seed}"
    run_root = external_root / "runs" / run_id
    metadata_path = run_root / "run-metadata.json"
    if metadata_path.is_file():
        return read_json(metadata_path)
    if run_root.exists():
        raise RuntimeError(f"refusing to overwrite incomplete physical run: {run_root}")
    run_root.mkdir(parents=True)
    top = spec["top"]
    config = f"/repo/{(CAMPAIGN_REL / 'orfs' / spec['config']).as_posix()}"
    target = f"/campaign-run/results/sky130hd/{top}/{variant}/3_3_place_gp.odb"
    base_make = [
        "make", f"DESIGN_CONFIG={config}", "WORK_HOME=/campaign-run", f"FLOW_VARIANT={variant}",
        f"GPL_RANDOM_SEED={seed}", f"GRT_SEED={seed}", f"OR_SEED={seed}",
        f"CLOCK_PERIOD={clock}", f"ABC_CLOCK_PERIOD_IN_PS={int(clock * 1000)}",
    ]
    docker_prefix = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--volume", f"{run_root}:/campaign-run",
        "--volume", f"{repo}:/repo:ro",
        "--workdir", "/OpenROAD-flow-scripts/flow", IMAGE,
    ]
    start = now()
    place_command = [*docker_prefix, *base_make, target]
    with (run_root / "place-driver.log").open("w", encoding="utf-8", newline="\n") as log:
        try:
            place = subprocess.run(place_command, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=7200, check=False)
            place_exit = place.returncode
        except subprocess.TimeoutExpired:
            place_exit = 124
    results = run_root / "results/sky130hd" / top / variant
    bypass_applied = False
    finish_exit: int | None = None
    finish_command: list[str] | None = None
    if place_exit == 0 and (results / "3_3_place_gp.odb").is_file():
        shutil.copy2(results / "3_3_place_gp.odb", results / "3_4_place_resized.odb")
        bypass_applied = True
        finish_command = [*docker_prefix, *base_make, "finish"]
        with (run_root / "finish-driver.log").open("w", encoding="utf-8", newline="\n") as log:
            try:
                finish = subprocess.run(finish_command, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=7200, check=False)
                finish_exit = finish.returncode
            except subprocess.TimeoutExpired:
                finish_exit = 124

    metrics, artifact_hashes = collect_metrics(run_root, top, variant, clock)
    route_clean = metrics["routing"]["detailed_route_drc_errors"] == 0
    gds = metrics["physical_outputs"]["gds_generated"]
    macro_base = repo / MACRO_REL
    macro_files = [
        macro_base / "source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.lef",
        macro_base / "source_checkout/sram22_256x64m4w8/sram22_256x64m4w8_tt_025C_1v80.lib",
        macro_base / "raw/derived_gds/sram22_256x64m4w8.gds",
    ]
    if spec["macro_count"] > 1:
        macro_files.extend(
            [
                macro_base / "source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.lef",
                macro_base / "source_checkout/sram22_256x8m8w1/sram22_256x8m8w1_tt_025C_1v80.lib",
                macro_base / "raw/derived_gds/sram22_256x8m8w1.gds",
            ]
        )
    rtl_files = [repo / path for path in spec["rtl"]]
    rtl_files.append(repo / CAMPAIGN_REL / "validation/rtl/matched_memory_tops.sv")
    config_files = [
        repo / CAMPAIGN_REL / "orfs/common.mk",
        repo / CAMPAIGN_REL / "orfs" / spec["config"],
        repo / CAMPAIGN_REL / "orfs" / spec["placement"],
        repo / CAMPAIGN_REL / "orfs/pdn_sram22.tcl",
        repo / CAMPAIGN_REL / "orfs/pre_io_placement.tcl",
    ]
    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "architecture_id": arch,
        "seed": seed,
        "clock_period_ns": clock,
        "start_time_utc": start,
        "end_time_utc": now(),
        "external_evidence_root": str(run_root),
        "toolchain": {
            "orfs_commit": "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2",
            "openroad_commit": "ab6fd26351dc449e69059684dc6aa9ae9046eb36",
            "openroad_version": "26Q3-1080-gab6fd26351",
            "openroad_binary_sha256": "2fc67d3a82df36014b615e710ce2e68600b592b27b051e4533c30248a2e2eb91",
            "yosys_version": "0.68+post",
            "opensta_version": "3.1.0",
            "container_image": IMAGE,
        },
        "pdk": {
            "platform": "sky130hd",
            "corner": "tt_025C_1v80",
            "voltage_v": 1.8,
            "temperature_c": 25,
            "release": "NOT_SEPARATELY_EXPOSED_BY_PINNED_IMAGE",
            "standard_cell_liberty_sha256": "ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9",
        },
        "user_payload_capacity_bits": 16384,
        "physical_stored_bits": spec["physical_stored_bits"],
        "macro_count": spec["macro_count"],
        "place_exit_code": place_exit,
        "finish_exit_code": finish_exit,
        "commands": {"place": place_command, "finish": finish_command},
        "common_documented_exception": {
            "id": "UPSTREAM_SRAM22_MAX_TRANSITION_RESIZE_STAGE_BYPASS",
            "applied": bypass_applied,
            "scope": "All architectures, timing conditions, and seeds",
            "semantics": "Copies the routed-input 3_3 placement ODB to the 3_4 handoff; no Liberty, LEF, GDS, RTL, or SDC value is modified. Final DRVs remain reported.",
            "compliance_claimed": False,
        },
        "architecture_specific_exceptions": spec.get("architecture_specific_exceptions", []),
        "rtl_sha256": {path.relative_to(repo).as_posix(): sha256(path) for path in rtl_files},
        "config_sha256": {path.relative_to(repo).as_posix(): sha256(path) for path in config_files},
        "constraint_sha256": sha256(repo / CAMPAIGN_REL / "configs/common.sdc"),
        "macro_sha256": {path.relative_to(repo).as_posix(): sha256(path) for path in macro_files},
        "final_artifact_sha256": artifact_hashes,
        "metrics": metrics,
        "physical_validation_classification": stage_classification(metrics),
        "route_success": bool(route_clean and metrics["physical_outputs"]["route_odb_generated"]),
        "gds_success": bool(gds),
        "drc_state": "DRC_CLEAN_EXTERNAL_ROUTING_MACRO_INTERNAL_NOT_REVERIFIED" if route_clean else "DRC_NON_ARRAY_FAILURE_OR_UNAVAILABLE",
        "lvs_state": "LVS_UNAVAILABLE_NOT_INDEPENDENTLY_REPRODUCED",
        "parasitic_extraction_state": "SPEF_GENERATED" if metrics["physical_outputs"]["spef_generated"] else "UNAVAILABLE",
        "energy_evidence": "E4_DIAGNOSTIC",
        "e5_qualified": False,
    }
    write_json(metadata_path, record)

    repo_report = repo / CAMPAIGN_REL / "reports/runs" / run_id
    repo_report.mkdir(parents=True, exist_ok=True)
    write_json(repo_report / "run-metadata.json", record)
    for name in ("1_synth.json", "2_4_floorplan_pdn.json", "5_1_grt.json", "5_2_route.json", "6_report.json"):
        source = run_root / "logs/sky130hd" / top / variant / name
        if source.is_file():
            shutil.copy2(source, repo_report / name)
    for name in ("synth_stat.txt", "5_global_route.rpt", "5_route_drc.rpt", "6_finish.rpt"):
        source = run_root / "reports/sky130hd" / top / variant / name
        if source.is_file():
            shutil.copy2(source, repo_report / name)
    for stage in ("place", "finish"):
        source = run_root / f"{stage}-driver.log"
        if source.is_file():
            compress_log(source, repo_report / f"{stage}-driver.log.gz")
    print(
        f"ORFS_RUN_COMPLETE run={run_id} class={record['physical_validation_classification']} "
        f"route={record['route_success']} gds={record['gds_success']}",
        flush=True,
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--external-root", type=Path, default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument("--architectures", nargs="*", choices=sorted(ARCHITECTURES), default=sorted(ARCHITECTURES))
    parser.add_argument("--seeds", nargs="*", type=int, default=SEEDS)
    parser.add_argument("--clocks", nargs="*", type=float, default=CLOCKS)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    repo = args.repo.resolve()
    external_root = args.external_root.resolve()
    external_root.mkdir(parents=True, exist_ok=True)
    matrix = [(arch, clock, seed) for arch in args.architectures for clock in args.clocks for seed in args.seeds]
    records: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_one, repo, external_root, arch, clock, seed) for arch, clock, seed in matrix]
        for future in concurrent.futures.as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda item: (item["architecture_id"], item["clock_period_ns"], item["seed"]))
    payload = {
        "schema_version": 1,
        "external_evidence_root": str(external_root),
        "requested_run_count": len(matrix),
        "completed_record_count": len(records),
        "architectures": sorted(args.architectures),
        "seeds": sorted(args.seeds),
        "clock_periods_ns": sorted(args.clocks, reverse=True),
        "records": records,
    }
    write_json(external_root / "PHYSICAL_RUN_RECORDS.json", payload)
    write_json(repo / CAMPAIGN_REL / "manifests/PHYSICAL_RUN_RECORDS.json", payload)
    success = all(record["route_success"] and record["gds_success"] for record in records)
    print(f"ORFS_MATRIX_COMPLETE runs={len(records)} route_and_gds={sum(r['route_success'] and r['gds_success'] for r in records)}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
