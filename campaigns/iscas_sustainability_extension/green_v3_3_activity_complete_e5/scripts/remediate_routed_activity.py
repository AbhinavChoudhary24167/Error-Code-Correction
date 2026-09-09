#!/usr/bin/env python3
"""Remediate the pinned OpenSTA VCD-name mapping without repeating PnR or GLS.

Attempt 01 demonstrated that the routed VCD is functional and contains the
flat routed nets, while native ``read_vcd`` resolves only top ports against the
ODB.  This additive adapter extracts scalar activity at the exact ``tb/dut``
scope and applies it to matching ODB nets with ``set_power_activity``.  The
original VCD, power reports, result, and physical implementation remain intact.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import time
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import execute_e5_job as e  # noqa: E402


def next_remediation(local_run: Path) -> tuple[int, Path]:
    number = 1
    while (local_run / f"activity_remediation{number:02d}").exists():
        number += 1
    path = local_run / f"activity_remediation{number:02d}"
    path.mkdir(parents=True, exist_ok=False)
    return number, path


def logic_power(groups: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        component: groups["Total"][component] - groups["Macro"][component]
        for component in ("internal_w", "switching_w", "leakage_w", "total_w")
    }


def run(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    _, deadline = e.load_deadline(args.runtime_state)
    original_path = args.original_result.resolve()
    local_run = original_path.parent
    final_path = local_run / "ACTIVITY_REMEDIATION_RESULT.json"
    if final_path.is_file() and not args.new_remediation:
        print(f"GREEN_V33_ACTIVITY_REMEDIATION_REUSE result={final_path}", flush=True)
        return 0
    original = json.loads(original_path.read_text(encoding="utf-8"))
    if original.get("status") != "COMPLETED":
        raise RuntimeError("activity remediation requires a completed preserved source attempt")
    number, local_output = next_remediation(local_run)
    if args.new_remediation:
        final_path = local_run / f"ACTIVITY_REMEDIATION{number:02d}_RESULT.json"
    external_attempt = Path(original["external_attempt_root"])
    external_output = external_attempt / f"power_explicit_activity/remediation{number:02d}"
    external_output.mkdir(parents=True, exist_ok=False)
    top = str(original["physical"]["top"])
    variant = str(original["physical"]["variant"])
    macro_instances = original["activity_support"]["macro_instances"].values()
    netlist = external_attempt / f"results/sky130hd/{top}/{variant}/6_final.v"
    start = e.now_utc()
    result: dict[str, Any] = {
        "schema_version": 1,
        "run_id": original["run_id"] + "_explicit_routed_activity_remediation",
        "architecture_id": original["architecture_id"],
        "physical_seed": original["seed"],
        "clock_period_ns": original["clock_period_ns"],
        "start_time_utc": start,
        "end_time_utc": None,
        "status": "RUNNING",
        "budget_scope": "ENTIRE_CAMPAIGN",
        "campaign_budget_seconds": 54000,
        "per_run_timeout_seconds": None,
        "hard_deadline_utc": json.loads(args.runtime_state.read_text(encoding="utf-8"))["hard_deadline_utc"],
        "source_result": original_path.relative_to(repo).as_posix(),
        "source_result_sha256": e.sha256(original_path),
        "source_activity_outcome": "NATIVE_READ_VCD_RESOLVED_ONLY_TOP_PORTS_E5_BLOCKED",
        "method": (
            "Exact scalar transition density and duty were extracted from the preserved post-route "
            "gate VCD at tb/dut and assigned to same-named ODB nets. Native top-port VCD annotation "
            "was retained; no activity was synthesized for unknown or absent VCD signals."
        ),
        "operation_records": [],
        "commands": {},
    }
    e.write_json(local_output / "REMEDIATION_STATE.json", result)
    try:
        for old_record in original["operation_records"]:
            operation = old_record["operation_class"]
            operation_external = external_output / operation
            operation_local = local_output / operation
            operation_external.mkdir(parents=True, exist_ok=False)
            operation_local.mkdir(parents=True, exist_ok=False)
            vcd = Path(old_record["activity"]["external_raw_path"])
            begin_ns = float(old_record["measurement_begin_ns"])
            end_ns = float(old_record["measurement_end_ns"])
            activities = e.routed_scalar_activity(vcd, begin_ns=begin_ns, end_ns=end_ns)
            activity_tcl = operation_external / "routed_net_activity.tcl"
            explicit = e.write_routed_activity_tcl(activity_tcl, activities, netlist=netlist)
            output_mount_path = f"/campaign-run/power_explicit_activity/remediation{number:02d}/{operation}"
            tcl = operation_external / "power.tcl"
            e.write_text(
                tcl,
                e.power_tcl(
                    top=top,
                    variant=variant,
                    operation=operation,
                    macro_instances=macro_instances,
                    output_path=output_mount_path,
                    vcd_path=f"/campaign-run/activity/{operation}.vcd",
                    routed_activity_tcl_path=f"{output_mount_path}/routed_net_activity.tcl",
                ),
            )
            container_name = (
                f"green_v33_remediate_{original['architecture_id'].lower()}_s{original['seed']}_"
                f"{operation.lower()}_{number:02d}"
            )
            command = [
                *e.docker_prefix(name=container_name, writable_root=external_attempt, repo=repo, cpus=1),
                e.OPENROAD, "-exit", f"{output_mount_path}/power.tcl",
            ]
            log = operation_external / "openroad.log"
            if e.run_until_deadline(command, log_path=log, deadline=deadline, docker_name=container_name) != 0:
                raise RuntimeError(f"explicit routed-net power failed for {operation}")
            for name in (
                "routed_net_activity.tcl", "power.tcl", "openroad.log", "annotation.rpt",
                "annotated.rpt", "unannotated.rpt", "power.rpt", "power.json", "macros.power.rpt",
            ):
                source = operation_external / name
                if source.is_file():
                    e.copy_preserved(source, operation_local / name)
            groups = e.parse_power_report(operation_external / "power.rpt")
            coverage = e.coverage_report(
                annotated_path=operation_external / "annotated.rpt",
                unannotated_path=operation_external / "unannotated.rpt",
                netlist=netlist,
            )
            functional_coverage = coverage["functional_logic_coverage_fraction"]
            macro_output_roots = explicit["macro_output_activity_root_candidate_count"]
            required_macro_output_roots = 72
            qualified = bool(
                old_record["timing_feasible"]
                and functional_coverage is not None
                and functional_coverage >= 0.95
                and macro_output_roots == required_macro_output_roots
            )
            logic = logic_power(groups)
            updated = copy.deepcopy(old_record)
            updated["record_id"] += "_explicit_routed_activity"
            updated["activity"]["coverage"] = coverage
            updated["activity"]["explicit_routed_net_annotation"] = explicit
            updated["activity"]["macro_output_activity_root_adapter"] = {
                "required_root_count": required_macro_output_roots,
                "annotated_root_count": macro_output_roots,
                "all_required_roots_annotated": macro_output_roots == required_macro_output_roots,
                "odb_mutation_scope": "IN_MEMORY_POWER_ANALYSIS_PROCESS_ONLY",
                "original_odb_modified": False,
                "purpose": (
                    "Seed VCD-measured SRAM outputs as OpenSTA activity roots for the logic-only boundary"
                ),
            }
            updated["activity"]["native_read_vcd_annotation_outcome"] = (
                "TOP_PORT_ONLY; supplemented by exact scalar routed-net annotations"
            )
            updated["power"] = {
                "whole_design_including_partial_macro_w": groups["Total"],
                "macro_reported_partial_w": groups["Macro"],
                "ecc_logic_excluding_macro_w": logic,
                "ecc_logic_energy_j_per_operation": (
                    logic["total_w"] * float(updated["measurement_duration_seconds"]) / 256
                ),
                "whole_memory_energy_j_per_operation": None,
                "whole_memory_energy_blocker": "SRAM_MACRO_INTERNAL_ENERGY_INCOMPLETE",
                "report_sha256": e.sha256(operation_external / "power.rpt"),
            }
            updated["qualification_thresholds"]["required_macro_output_activity_roots"] = (
                required_macro_output_roots
            )
            updated["qualification"] = (
                "E5_LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE"
                if qualified else "E5_BLOCKED_ACTIVITY_COVERAGE_OR_TIMING"
            )
            updated["evidence_level"] = "E5" if qualified else "E4_DIAGNOSTIC"
            updated["ecc_logic_e5_qualified"] = qualified
            e.write_json(operation_local / "E5_RECORD.json", updated)
            result["operation_records"].append(updated)
            result["commands"][operation] = command
            e.write_json(local_output / "REMEDIATION_STATE.json", result)
        result.update(
            {
                "end_time_utc": e.now_utc(),
                "status": "COMPLETED",
                "e5_logic_record_count": sum(
                    bool(row["ecc_logic_e5_qualified"]) for row in result["operation_records"]
                ),
                "whole_memory_e5_record_count": 0,
                "fresh_physical_run_repeated": False,
                "gate_simulation_repeated": False,
            }
        )
        e.write_json(local_output / "REMEDIATION_STATE.json", result)
        e.write_json(final_path, result)
        print(
            f"GREEN_V33_ACTIVITY_REMEDIATION_COMPLETE run_id={result['run_id']} "
            f"e5_logic_records={result['e5_logic_record_count']}",
            flush=True,
        )
        return 0
    except e.CampaignCutoff:
        result.update({"end_time_utc": e.now_utc(), "status": "CAMPAIGN_RUNTIME_CUTOFF"})
        e.write_json(local_output / "REMEDIATION_STATE.json", result)
        return 124
    except Exception as exc:
        result.update(
            {
                "end_time_utc": e.now_utc(),
                "status": "TOOL_FAILURE",
                "failure_type": type(exc).__name__,
                "failure_message": str(exc),
            }
        )
        e.write_json(local_output / "REMEDIATION_STATE.json", result)
        print(f"GREEN_V33_ACTIVITY_REMEDIATION_FAILURE: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--runtime-state", type=Path, required=True)
    parser.add_argument("--original-result", type=Path, required=True)
    parser.add_argument(
        "--new-remediation",
        action="store_true",
        help="Preserve the earlier remediation and emit a newly numbered result.",
    )
    args = parser.parse_args()
    if time.time() >= e.load_deadline(args.runtime_state)[1]:
        return 124
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
