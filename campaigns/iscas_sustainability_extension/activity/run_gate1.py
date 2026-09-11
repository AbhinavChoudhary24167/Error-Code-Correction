#!/usr/bin/env python3
"""Execute the frozen Gate-1 W1/W2 matrix against read-only DATE artifacts."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from gate1_common import parse_power_report, sha256, write_json


SCRIPT = Path(__file__).resolve()
ACTIVITY = SCRIPT.parent
DEFAULT_CONTRACT_PATH = ACTIVITY / "gate1_contract.json"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def immutable_tree(root: Path) -> None:
    for path in (item for item in root.rglob("*") if item.is_file()):
        path.chmod(0o444)
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


def verify_file(record: dict[str, str], label: str) -> None:
    path = Path(record["path"])
    if not path.is_file():
        raise SystemExit(f"missing frozen {label}: {path}")
    observed = sha256(path)
    if observed != record["sha256"]:
        raise SystemExit(f"frozen {label} hash mismatch: {path}: {observed} != {record['sha256']}")


def main() -> int:
    if os.name != "posix" or os.geteuid() != 0:
        raise SystemExit("run Gate 1 as root inside Ubuntu WSL2")
    if len(sys.argv) > 2:
        raise SystemExit("usage: run_gate1.py [CONTRACT_JSON]")
    contract_path = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else DEFAULT_CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["state"] != "FROZEN_BEFORE_EXECUTION":
        raise SystemExit("Gate-1 contract is not frozen before execution")
    output_root = Path(contract["output_root"])
    if output_root.exists():
        raise SystemExit(f"refusing to overwrite existing Gate-1 evidence: {output_root}")
    capacity_root = output_root.parents[1]
    usage = shutil.disk_usage(capacity_root)
    if usage.free < 100 * 1024**3:
        raise SystemExit(f"unsafe WSL capacity: only {usage.free} bytes free at {capacity_root}")

    for run in contract["runs"]:
        for name, artifact in run["physical_artifacts"].items():
            verify_file(artifact, f"{run['run_id']} {name}")
        for trace in run["traces"]:
            verify_file(trace, f"{run['run_id']} {trace['activity_class']} trace")

    output_root.mkdir(parents=True)
    policy_root = output_root / "policy"
    runs_root = output_root / "runs"
    policy_root.mkdir()
    runs_root.mkdir()
    shutil.copy2(contract_path, policy_root / "gate1_contract.json")
    shutil.copy2(ACTIVITY / "power.tcl", policy_root / "power.tcl")
    write_json(
        output_root / "execution-start.json",
        {
            "schema_version": 1,
            "started_at_utc": utc_now(),
            "free_bytes_before": usage.free,
            "total_bytes": usage.total,
            "contract_sha256": sha256(contract_path),
            "power_tcl_sha256": sha256(ACTIVITY / "power.tcl"),
        },
    )

    failed = 0
    total_start = time.monotonic()
    for ordinal, run in enumerate(contract["runs"], start=1):
        run_root = runs_root / run["run_id"]
        run_root.mkdir()
        power_root = run_root / "power"
        logs_root = run_root / "logs"
        reports_root = run_root / "reports"
        objects_root = run_root / "objects"
        for path in (power_root, logs_root, reports_root, objects_root):
            path.mkdir()

        source_root = Path(run["source_evidence_root"])
        snapshot = source_root / "policy/repo_snapshot"
        input_run = Path(run["input_run_root"])
        config_mount = "/rev2-repo" if run["source_kind"] == "revision2" else "/breadth-repo"
        config = f"{config_mount}/{run['config']}"
        trace_specs = ",".join(
            f"{trace['activity_class']}|/rev2-policy/traces/{Path(trace['path']).name}" for trace in run["traces"]
        )
        results_dir = f"/date-run/{run['results_relative_path']}"
        common_env = (
            "LEC_CHECK=0 NUM_CORES=1 WORK_HOME=/gate1-out CLOCK_PERIOD=10.0 "
            f"GPL_RANDOM_SEED={run['seed']} GRT_SEED={run['seed']} OR_SEED={run['seed']} "
            f"GATE1_POWER_DIR=/gate1-out/power GATE1_TRACE_SPECS='{trace_specs}'"
        )
        shell_script = (
            "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; "
            f"export {common_env}; cd /OpenROAD-flow-scripts/flow; "
            f"make ABC_CLOCK_PERIOD_IN_PS=10000 DESIGN_CONFIG={config} "
            f"RESULTS_DIR={results_dir} LOG_DIR=/gate1-out/logs "
            "REPORTS_DIR=/gate1-out/reports OBJECTS_DIR=/gate1-out/objects "
            "RUN_SCRIPT=/gate1-policy/power.tcl RUN_LOG_NAME_STEM=gate1_activity_power run"
        )
        command = [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "--volume",
            f"{input_run}:/date-run:ro",
            "--volume",
            f"{snapshot}:{config_mount}:ro",
            "--volume",
            "/var/lib/green-ecc-date2027-revision2/policy:/rev2-policy:ro",
            "--volume",
            f"{policy_root}:/gate1-policy:ro",
            "--volume",
            f"{run_root}:/gate1-out",
            "--entrypoint",
            "/bin/bash",
            contract["container_image"],
            "-lc",
            shell_script,
        ]
        (run_root / "command.json").write_text(
            json.dumps(command, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        start = time.monotonic()
        exit_code = 1
        failure = ""
        with (run_root / "container.log").open("w", encoding="utf-8", newline="\n") as log:
            try:
                completed = subprocess.run(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=600,
                    check=False,
                )
                exit_code = completed.returncode
                if exit_code:
                    failure = f"OpenROAD activity-power invocation exited {exit_code}"
            except subprocess.TimeoutExpired:
                exit_code = 124
                failure = "OpenROAD activity-power invocation exceeded 600 seconds"
        elapsed = time.monotonic() - start

        if exit_code == 0:
            for trace in run["traces"]:
                label = trace["activity_class"]
                required = [
                    power_root / f"{label}.power.rpt",
                    power_root / f"{label}.annotation.rpt",
                    power_root / f"{label}.annotated.rpt",
                    power_root / f"{label}.unannotated.rpt",
                ]
                missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
                if missing:
                    exit_code = 91
                    failure = f"missing required reports: {missing}"
                    break
                try:
                    parse_power_report(power_root / f"{label}.power.rpt")
                except ValueError as exc:
                    exit_code = 92
                    failure = str(exc)
                    break
        if exit_code:
            failed += 1

        metadata = {
            "schema_version": 1,
            "ordinal": ordinal,
            "run_id": run["run_id"],
            "hardware_identity": run["hardware_identity"],
            "architecture": run["architecture"],
            "seed": run["seed"],
            "target_ns": run["target_ns"],
            "activity_classes": [trace["activity_class"] for trace in run["traces"]],
            "evidence_origin": "SUSTAINABILITY_EXTENSION",
            "physical_inputs_read_only": True,
            "exit_code": exit_code,
            "status": "PASS" if exit_code == 0 else "FAIL",
            "failure_reason": failure,
            "elapsed_seconds": elapsed,
        }
        write_json(run_root / "run-metadata.json", metadata)
        inventory = []
        for path in sorted(item for item in run_root.rglob("*") if item.is_file() and item.name != "raw-artifacts.sha256"):
            inventory.append(f"{sha256(path)}  {path.relative_to(run_root).as_posix()}")
        (run_root / "raw-artifacts.sha256").write_text(
            "\n".join(inventory) + "\n", encoding="utf-8", newline="\n"
        )
        immutable_tree(run_root)
        print(
            f"GATE1_RUN_{metadata['status']} {ordinal}/{len(contract['runs'])} "
            f"run={run['run_id']} elapsed={elapsed:.3f}s",
            flush=True,
        )

    final_usage = shutil.disk_usage(capacity_root)
    write_json(
        output_root / "execution-summary.json",
        {
            "schema_version": 1,
            "completed_at_utc": utc_now(),
            "run_count": len(contract["runs"]),
            "new_power_point_count": contract["new_power_point_count"],
            "failed_run_count": failed,
            "status": "PASS" if failed == 0 else "FAIL",
            "elapsed_seconds": time.monotonic() - total_start,
            "free_bytes_after": final_usage.free,
            "bytes_consumed": usage.free - final_usage.free,
        },
    )
    if failed:
        print(f"GATE1_MATRIX_FAIL failed_runs={failed}", file=sys.stderr)
        return 1
    print(f"GATE1_MATRIX_PASS runs={len(contract['runs'])} points={contract['new_power_point_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
