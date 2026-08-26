#!/usr/bin/env python3
"""Execute exactly the seven frozen Gate 03F runs once, in matrix order."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-final")
POLICY = ROOT / "policy"
SNAPSHOT = POLICY / "repo_snapshot"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    contract = json.loads((SNAPSHOT / "scripts/gate03f/contract_v1.json").read_text(encoding="utf-8"))
    runs = contract["qualification_runs"]
    if len(runs) != 7 or len({item["run_id"] for item in runs}) != 7:
        raise SystemExit("frozen qualification matrix is not exactly seven unique runs")
    existing = [item["run_id"] for item in runs if (ROOT / "runs" / item["run_id"]).exists()]
    if existing:
        raise SystemExit(f"refusing to rerun existing immutable qualification directories: {existing}")

    runner = SNAPSHOT / "scripts/gate03f/run_qualification.py"
    started = utc_now()
    results = []
    for item in runs:
        completed = subprocess.run([sys.executable, str(runner), item["run_id"]], check=False)
        results.append({"run_id": item["run_id"], "exit_status": completed.returncode})
    completed_at = utc_now()
    payload = {
        "schema_version": 1,
        "expected_run_count": 7,
        "actual_run_count": len(results),
        "started_at_utc": started,
        "completed_at_utc": completed_at,
        "runs": results,
        "all_physical_runs_passed": all(item["exit_status"] == 0 for item in results),
    }
    (ROOT / "MATRIX_EXECUTION.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if not payload["all_physical_runs_passed"]:
        print("GATE03F_MATRIX_FAIL", file=sys.stderr)
        return 1
    print("GATE03F_MATRIX_PASS runs=7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
