#!/usr/bin/env python3
"""Execute one immutable Revision-2 physical seed run."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-revision2")
POLICY = ROOT / "policy"
SNAPSHOT = POLICY / "repo_snapshot"
IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_policy() -> None:
    for line in (POLICY / "frozen-bundle.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = POLICY / relative.strip()
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"frozen Revision-2 policy mismatch: {relative}")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def immutable_tree(root: Path) -> None:
    for path in (item for item in root.rglob("*") if item.is_file()):
        path.chmod(0o444)
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


def main() -> int:
    if os.geteuid() != 0:
        raise SystemExit("run as root inside Ubuntu WSL2")
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_characterization.py RUN_ID")
    verify_policy()
    contract = json.loads((SNAPSHOT / "scripts/revision2/contract_v1.json").read_text(encoding="utf-8"))
    run_id = sys.argv[1]
    matches = [item for item in contract["runs"] if item["run_id"] == run_id]
    if len(matches) != 1:
        raise SystemExit(f"run id is not in the frozen Revision-2 matrix: {run_id}")
    record = matches[0]
    architecture = contract["architectures"][record["architecture"]]
    seed = int(record["seed"])
    run_root = ROOT / "runs" / run_id
    if run_root.exists():
        raise SystemExit(f"refusing to overwrite immutable Revision-2 run: {run_root}")
    run_root.mkdir()

    config = f"/rev2-repo/scripts/revision2/configs/{architecture['config']}"
    common_env = (
        "LEC_CHECK=0 NUM_CORES=1 WORK_HOME=/rev2-run CLOCK_PERIOD=10.0 "
        f"GPL_RANDOM_SEED={seed} GRT_SEED={seed} OR_SEED={seed}"
    )
    physical_script = (
        "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; "
        f"export {common_env}; cd /OpenROAD-flow-scripts/flow; "
        f"make ABC_CLOCK_PERIOD_IN_PS=10000 DESIGN_CONFIG={config}"
    )
    docker_command = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--volume", f"{run_root}:/rev2-run",
        "--volume", f"{SNAPSHOT}:/rev2-repo:ro",
        "--entrypoint", "/bin/bash", IMAGE, "-lc", physical_script,
    ]
    write_json(
        run_root / "effective-run-environment.json",
        {
            "ABC_CLOCK_PERIOD_IN_PS": "10000",
            "CLOCK_PERIOD": "10.0",
            "GPL_RANDOM_SEED": str(seed),
            "GRT_SEED": str(seed),
            "OR_SEED": str(seed),
            "LEC_CHECK": "0",
            "NUM_CORES": "1",
            "DESIGN_CONFIG": config,
            "DESIGN_NAME": architecture["design_top"],
            "RUN_ID": run_id,
            "IMPLEMENTATION_ID": architecture["implementation_id"],
        },
    )
    (run_root / "physical-command.txt").write_text(" ".join(docker_command) + "\n", encoding="utf-8", newline="\n")

    start = utc_now()
    physical_status = 1
    physical_failure = ""
    with (run_root / "container.log").open("w", encoding="utf-8", newline="\n") as log:
        try:
            completed = subprocess.run(docker_command, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=7200, check=False)
            physical_status = completed.returncode
        except subprocess.TimeoutExpired:
            physical_status = 124
            physical_failure = "official ORFS flow exceeded the frozen two-hour safety timeout"

    top = architecture["design_top"]
    results = run_root / f"results/sky130hd/{top}/base"
    logs = run_root / f"logs/sky130hd/{top}/base"
    required = [
        "1_synth.odb", "2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_route.odb",
        "6_final.odb", "6_final.v", "6_final.sdc", "6_final.def", "6_final.gds", "6_final.spef",
    ]
    if physical_status == 0:
        missing = [name for name in required if not (results / name).is_file() or (results / name).stat().st_size == 0]
        if missing:
            physical_status, physical_failure = 91, f"missing required final artifacts: {missing}"
    for report in (logs / "6_report.json", logs / "5_1_grt.json", logs / "5_2_route.json"):
        if physical_status == 0 and (not report.is_file() or report.stat().st_size == 0):
            physical_status, physical_failure = 92, f"missing machine-readable report: {report.name}"
    if physical_status == 0:
        route = json.loads((logs / "5_2_route.json").read_text(encoding="utf-8"))
        if route.get("detailedroute__route__drc_errors") != 0 or route.get("detailedroute__flow__errors__count") != 0:
            physical_status, physical_failure = 93, "detailed routing did not finish with zero DRC and flow errors"
    if physical_status == 0:
        module_types = []
        for line in (results / "6_final.v").read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"^\s*([^/\s][^\s]*)\s+(?:\\[^\s]+|[A-Za-z_][^\s(]*)\s*\($", line)
            if match:
                module_types.append(match.group(1).lstrip("\\"))
        generic = sorted({cell for cell in module_types if cell.startswith("$_") or cell.startswith("$")})
        if generic:
            physical_status, physical_failure = 94, f"generic cells remain in final netlist: {generic[:10]}"

    timing_feasible = False
    if physical_status == 0:
        finish = json.loads((logs / "6_report.json").read_text(encoding="utf-8"))
        timing_feasible = (
            float(finish["finish__timing__setup__ws"]) >= 0
            and int(finish["finish__timing__drv__setup_violation_count"]) == 0
        )

    power_required = record["architecture"] in contract["power"]["required_for_architectures"]
    power_conditional = record["architecture"] in contract["power"]["conditional_timing_feasible_architectures"]
    run_power = physical_status == 0 and (power_required or (power_conditional and timing_feasible))
    power_status = "NOT_REQUIRED_BY_PROTOCOL"
    power_failure = ""
    if physical_status != 0:
        power_status = "NOT_RUN_PHYSICAL_FAILURE"
    elif power_conditional and not timing_feasible:
        power_status = "NOT_RUN_TARGET_TIMING_INFEASIBLE"
    elif run_power:
        power_root = run_root / "power"
        power_root.mkdir()
        family = architecture["power_family"]
        label = f"{family}-no_error"
        vcd = f"/rev2-policy/traces/{family}-10ns-no_error.vcd.gz"
        power_script = (
            "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; "
            f"export {common_env} REV2_POWER_DIR=/rev2-run/power "
            f"REV2_POWER_LABEL={label} REV2_POWER_VCD={vcd}; "
            "cd /OpenROAD-flow-scripts/flow; "
            f"make ABC_CLOCK_PERIOD_IN_PS=10000 DESIGN_CONFIG={config} "
            "RUN_SCRIPT=/rev2-repo/scripts/revision2/power.tcl RUN_LOG_NAME_STEM=rev2_power run"
        )
        power_command = [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "--volume", f"{run_root}:/rev2-run",
            "--volume", f"{SNAPSHOT}:/rev2-repo:ro",
            "--volume", f"{POLICY}:/rev2-policy:ro",
            "--entrypoint", "/bin/bash", IMAGE, "-lc", power_script,
        ]
        (run_root / "power-command.txt").write_text(" ".join(power_command) + "\n", encoding="utf-8", newline="\n")
        with (run_root / "power-container.log").open("w", encoding="utf-8", newline="\n") as log:
            try:
                completed = subprocess.run(power_command, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=600, check=False)
                power_status = "ACTIVITY_POWER_PASS_FULL_PRECISION_TEXT" if completed.returncode == 0 else "POWER_DEFERRED"
                if completed.returncode != 0:
                    power_failure = f"activity power exited {completed.returncode}"
            except subprocess.TimeoutExpired:
                power_status, power_failure = "POWER_DEFERRED", "activity power exceeded the frozen ten-minute timeout"
        if power_status.startswith("ACTIVITY_POWER_PASS") and not (power_root / f"{label}.power.rpt").is_file():
            power_status, power_failure = "POWER_DEFERRED", "missing 12-digit no-error power report"

    metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "architecture": record["architecture"],
        "implementation_id": architecture["implementation_id"],
        "design_top": top,
        "config": architecture["config"],
        "clock_period_ns": 10.0,
        "physical_seed": seed,
        "start_time_utc": start,
        "end_time_utc": utc_now(),
        "physical_exit_status": physical_status,
        "physical_failure_reason": physical_failure,
        "routing_complete": physical_status == 0,
        "timing_feasible": timing_feasible,
        "power_status": power_status,
        "power_failure_reason": power_failure,
        "replacement_attempt": False,
    }
    write_json(run_root / "run-metadata.json", metadata)
    inventory = []
    for path in sorted(item for item in run_root.rglob("*") if item.is_file() and item.name != "raw-artifacts.sha256"):
        inventory.append(f"{sha256(path)}  {path.relative_to(run_root).as_posix()}")
    (run_root / "raw-artifacts.sha256").write_text("\n".join(inventory) + "\n", encoding="utf-8", newline="\n")
    immutable_tree(run_root)
    if physical_status != 0:
        print(f"REV2_PHYSICAL_RUN_FAIL run={run_id} status={physical_status} reason={physical_failure}", file=sys.stderr, flush=True)
        return physical_status
    print(f"REV2_PHYSICAL_RUN_PASS run={run_id} seed={seed} timing_feasible={timing_feasible} power={power_status}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
