#!/usr/bin/env python3
"""Run one predeclared 2x5 breadth-remediation physical matrix."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-breadth-remediation")
SNAPSHOT = ROOT / "policy/repo_snapshot"
CAMPAIGN = Path("campaigns/date_2027_breadth_remediation")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workstream", choices=("A", "C"), required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run as root inside Ubuntu WSL2")
    matrix_path = ROOT / f"MATRIX_{args.workstream}_EXECUTION.json"
    if matrix_path.exists():
        raise SystemExit(f"refusing duplicate matrix execution: {matrix_path}")
    contract = json.loads((SNAPSHOT / CAMPAIGN / "physical/contract_v1.json").read_text(encoding="utf-8"))
    records = [row for row in contract["runs"] if row["workstream"] == args.workstream]
    if len(records) != 10:
        raise SystemExit("frozen workstream matrix does not contain ten runs")
    started = now()
    outcomes = []
    for index, record in enumerate(records, start=1):
        print(
            f"BREADTH_RUN_START workstream={args.workstream} index={index}/10 "
            f"run={record['run_id']} architecture={record['architecture']} seed={record['seed']}",
            flush=True,
        )
        completed = subprocess.run(
            ["python3", str(SNAPSHOT / CAMPAIGN / "scripts/run_physical_characterization.py"), record["run_id"]],
            check=False,
        )
        outcomes.append(dict(record) | {"process_exit_status": completed.returncode})
    payload = {
        "schema_version": 1,
        "workstream": args.workstream,
        "started_at_utc": started,
        "completed_at_utc": now(),
        "planned_run_count": 10,
        "executed_run_count": len(outcomes),
        "replacement_attempt_count": 0,
        "outcomes": outcomes,
    }
    matrix_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    success = len(outcomes) == 10 and all(row["process_exit_status"] == 0 for row in outcomes)
    print(
        f"BREADTH_MATRIX_{args.workstream}_COMPLETE" if success else f"BREADTH_MATRIX_{args.workstream}_COMPLETE_WITH_FAILURES",
        flush=True,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
