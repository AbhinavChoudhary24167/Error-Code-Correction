#!/usr/bin/env python3
"""Execute one immutable breadth-remediation ORFS run and joined power run."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-breadth-remediation")
POLICY = ROOT / "policy"
SNAPSHOT = POLICY / "repo_snapshot"
CAMPAIGN = Path("campaigns/date_2027_breadth_remediation")
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
            raise SystemExit(f"frozen breadth policy mismatch: {relative}")


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
        raise SystemExit("usage: run_physical_characterization.py RUN_ID")
    verify_policy()
    contract_path = SNAPSHOT / CAMPAIGN / "physical/contract_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    run_id = sys.argv[1]
    matches = [row for row in contract["runs"] if row["run_id"] == run_id]
    if len(matches) != 1:
        raise SystemExit(f"run id is not in the frozen breadth matrix: {run_id}")
    record = matches[0]
    architecture = contract["architectures"][record["architecture"]]
    seed = int(record["seed"])
    workstream = record["workstream"]
    run_root = ROOT / "runs" / workstream / run_id
    if run_root.exists():
        raise SystemExit(f"refusing to overwrite immutable breadth run: {run_root}")
    run_root.mkdir()

    config = f"/breadth-repo/{architecture['config']}"
    period = float(architecture["clock_period_ns"])
    abc_period = int(architecture["abc_clock_period_ps"])
    common_env = (
        f"LEC_CHECK=0 NUM_CORES=1 WORK_HOME=/breadth-run CLOCK_PERIOD={period:.1f} "
        f"GPL_RANDOM_SEED={seed} GRT_SEED={seed} OR_SEED={seed}"
    )
    physical_script = (
        "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; "
        f"export {common_env}; cd /OpenROAD-flow-scripts/flow; "
        f"make ABC_CLOCK_PERIOD_IN_PS={abc_period} DESIGN_CONFIG={config}"
    )
    docker_command = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--volume", f"{run_root}:/breadth-run",
        "--volume", f"{SNAPSHOT}:/breadth-repo:ro",
        "--entrypoint", "/bin/bash", IMAGE, "-lc", physical_script,
    ]
    config_path = SNAPSHOT / architecture["config"]
    sdc_path = SNAPSHOT / CAMPAIGN / "configs/ecc.sdc"
    source_hashes = {source: sha256(SNAPSHOT / source) for source in architecture["sources"]}
    environment = {
        "ABC_CLOCK_PERIOD_IN_PS": str(abc_period),
        "CLOCK_PERIOD": f"{period:.1f}",
        "GPL_RANDOM_SEED": str(seed),
        "GRT_SEED": str(seed),
        "OR_SEED": str(seed),
        "LEC_CHECK": "0",
        "NUM_CORES": "1",
        "DESIGN_CONFIG": config,
        "DESIGN_NAME": architecture["design_top"],
        "RUN_ID": run_id,
        "WORKSTREAM": workstream,
        "IMPLEMENTATION_ID": architecture["implementation_id"],
        "CONTAINER_IMAGE": IMAGE,
        "BASELINE_COMMIT": contract["baseline_commit"],
        "CONTRACT_SHA256": sha256(contract_path),
        "CONFIG_SHA256": sha256(config_path),
        "SDC_SHA256": sha256(sdc_path),
        "SOURCE_HASHES": source_hashes,
    }
    write_json(run_root / "effective-run-environment.json", environment)
    (run_root / "physical-command.txt").write_text(" ".join(docker_command) + "\n", encoding="utf-8", newline="\n")

    start = utc_now()
    physical_status = 1
    physical_failure = ""
    with (run_root / "container.log").open("w", encoding="utf-8", newline="\n") as log:
        try:
            completed = subprocess.run(
                docker_command, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=7200, check=False
            )
            physical_status = completed.returncode
        except subprocess.TimeoutExpired:
            physical_status = 124
            physical_failure = "official ORFS flow exceeded the predeclared two-hour safety timeout"

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
    reports = (logs / "6_report.json", logs / "5_1_grt.json", logs / "5_2_route.json")
    for report in reports:
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

    setup_slack = None
    hold_slack = None
    setup_violations = None
    hold_violations = None
    target_feasible = False
    if physical_status == 0:
        finish = json.loads((logs / "6_report.json").read_text(encoding="utf-8"))
        setup_slack = float(finish["finish__timing__setup__ws"])
        hold_slack = float(finish["finish__timing__hold__ws"])
        setup_violations = int(finish["finish__timing__drv__setup_violation_count"])
        hold_violations = int(finish["finish__timing__drv__hold_violation_count"])
        target_feasible = (
            setup_slack >= 0 and setup_violations == 0
            and hold_slack >= 0 and hold_violations == 0
        )

    power_status = "NOT_RUN_TARGET_INFEASIBLE"
    power_failure = ""
    power_label = f"{record['architecture']}-no_error"
    if physical_status != 0:
        power_status = "NOT_RUN_PHYSICAL_FAILURE"
    elif target_feasible:
        power_root = run_root / "power"
        power_root.mkdir()
        vcd = f"/breadth-policy/traces/{architecture['power_trace_file']}"
        power_script = (
            "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; "
            f"export {common_env} BREADTH_POWER_DIR=/breadth-run/power "
            f"BREADTH_POWER_LABEL={power_label} BREADTH_POWER_VCD={vcd}; "
            "cd /OpenROAD-flow-scripts/flow; "
            f"make ABC_CLOCK_PERIOD_IN_PS={abc_period} DESIGN_CONFIG={config} "
            "RUN_SCRIPT=/breadth-repo/campaigns/date_2027_breadth_remediation/physical/power.tcl "
            "RUN_LOG_NAME_STEM=breadth_power run"
        )
        power_command = [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "--volume", f"{run_root}:/breadth-run",
            "--volume", f"{SNAPSHOT}:/breadth-repo:ro",
            "--volume", f"{POLICY}:/breadth-policy:ro",
            "--entrypoint", "/bin/bash", IMAGE, "-lc", power_script,
        ]
        (run_root / "power-command.txt").write_text(" ".join(power_command) + "\n", encoding="utf-8", newline="\n")
        with (run_root / "power-container.log").open("w", encoding="utf-8", newline="\n") as log:
            try:
                completed = subprocess.run(
                    power_command, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=600, check=False
                )
                power_status = "ACTIVITY_POWER_PASS_FULL_PRECISION_TEXT" if completed.returncode == 0 else "POWER_FAIL"
                if completed.returncode != 0:
                    power_failure = f"activity power exited {completed.returncode}"
            except subprocess.TimeoutExpired:
                power_status, power_failure = "POWER_FAIL", "activity power exceeded ten minutes"
        if power_status.startswith("ACTIVITY_POWER_PASS") and not (power_root / f"{power_label}.power.rpt").is_file():
            power_status, power_failure = "POWER_FAIL", "missing full-precision power report"

    metadata = {
        "schema_version": 1,
        "run_id": run_id,
        "workstream": workstream,
        "architecture": record["architecture"],
        "implementation_id": architecture["implementation_id"],
        "design_top": top,
        "config": architecture["config"],
        "clock_period_ns": period,
        "abc_clock_period_ps": abc_period,
        "physical_seed": seed,
        "start_time_utc": start,
        "end_time_utc": utc_now(),
        "physical_exit_status": physical_status,
        "physical_failure_reason": physical_failure,
        "routing_complete": physical_status == 0,
        "setup_slack_ns": setup_slack,
        "hold_slack_ns": hold_slack,
        "setup_violation_count": setup_violations,
        "hold_violation_count": hold_violations,
        "target_feasible": target_feasible,
        "power_status": power_status,
        "power_failure_reason": power_failure,
        "power_label": power_label,
        "trace_file": architecture["power_trace_file"],
        "replacement_attempt": False,
        "source_hashes": source_hashes,
        "config_sha256": sha256(config_path),
        "sdc_sha256": sha256(sdc_path),
        "contract_sha256": sha256(contract_path),
        "container_image": IMAGE,
        "baseline_commit": contract["baseline_commit"],
    }
    write_json(run_root / "run-metadata.json", metadata)
    inventory = []
    for path in sorted(item for item in run_root.rglob("*") if item.is_file() and item.name != "raw-artifacts.sha256"):
        inventory.append(f"{sha256(path)}  {path.relative_to(run_root).as_posix()}")
    (run_root / "raw-artifacts.sha256").write_text("\n".join(inventory) + "\n", encoding="utf-8", newline="\n")
    immutable_tree(run_root)
    if physical_status != 0:
        print(
            f"BREADTH_PHYSICAL_RUN_FAIL run={run_id} status={physical_status} reason={physical_failure}",
            file=sys.stderr,
            flush=True,
        )
        return physical_status
    print(
        f"BREADTH_PHYSICAL_RUN_PASS run={run_id} seed={seed} target_feasible={target_feasible} power={power_status}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
