#!/usr/bin/env python3
"""Freeze attempt 03 for only Gate-1 points missing after attempt 02."""

from __future__ import annotations

import json
from pathlib import Path

from gate1_common import write_csv, write_json


SCRIPT = Path(__file__).resolve()
ACTIVITY = SCRIPT.parent
SOURCE_CONTRACT = ACTIVITY / "gate1_contract.json"
OUTPUT_CONTRACT = ACTIVITY / "gate1_attempt03_contract.json"
OUTPUT_MATRIX = ACTIVITY / "gate1_attempt03_job_matrix.csv"
ATTEMPT02 = Path("/var/lib/green-ecc-iscas-sustainability/gate1_activity_power_attempt02")
ATTEMPT03 = Path("/var/lib/green-ecc-iscas-sustainability/gate1_activity_power_attempt03")

COMPLETED_ATTEMPT02 = (
    "secded_comb-seed-11",
    "secded_comb-seed-13",
    "secded_comb-seed-17",
    "secded_comb-seed-19",
    "secded_comb-seed-23",
    "secded_pipe-seed-11",
    "secded_pipe-seed-13",
    "secded_pipe-seed-17",
)


def main() -> int:
    if ATTEMPT03.exists():
        raise SystemExit(f"refusing to overwrite existing attempt-03 evidence: {ATTEMPT03}")
    source = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    by_id = {run["run_id"]: run for run in source["runs"]}
    if set(COMPLETED_ATTEMPT02) - by_id.keys():
        raise SystemExit("attempt-02 completed set is outside the frozen Gate-1 matrix")
    for run_id in COMPLETED_ATTEMPT02:
        root = ATTEMPT02 / "runs" / run_id
        for label in ("W1", "W2"):
            report = root / "power" / f"{label}.power.rpt"
            if not report.is_file() or report.stat().st_size == 0:
                raise SystemExit(f"attempt-02 report is not complete: {report}")
        log = (root / "container.log").read_text(encoding="utf-8", errors="replace")
        if "GATE1_ACTIVITY_POWER_PASS" not in log:
            raise SystemExit(f"attempt-02 OpenROAD completion marker absent: {run_id}")

    missing_runs = [run for run in source["runs"] if run["run_id"] not in COMPLETED_ATTEMPT02]
    contract = dict(source)
    contract.update(
        {
            "state": "FROZEN_BEFORE_EXECUTION",
            "execution_attempt": 3,
            "output_root": str(ATTEMPT03),
            "campaign_total_power_point_count": 40,
            "new_power_point_count": len(missing_runs) * 2,
            "container_invocation_count": len(missing_runs),
            "admitted_attempt02_runs": list(COMPLETED_ATTEMPT02),
            "preserved_predecessor": {
                "path": str(ATTEMPT02),
                "classification": "OPENROAD_REPORTS_COMPLETE_VALIDATOR_FALSE_FAILURE_AND_RUNNER_INTERRUPTION",
                "completed_openroad_run_count": len(COMPLETED_ATTEMPT02),
                "completed_scientific_power_point_count": len(COMPLETED_ATTEMPT02) * 2,
                "rerun_in_attempt03": False,
            },
            "runs": missing_runs,
        }
    )
    write_json(OUTPUT_CONTRACT, contract)
    rows = []
    for run in missing_runs:
        for trace in run["traces"]:
            rows.append(
                {
                    "run_id": run["run_id"],
                    "hardware_identity": run["hardware_identity"],
                    "architecture": run["architecture"],
                    "seed": run["seed"],
                    "activity_class": trace["activity_class"],
                    "odb_path": run["physical_artifacts"]["odb"]["path"],
                    "sdc_path": run["physical_artifacts"]["sdc"]["path"],
                    "spef_path": run["physical_artifacts"]["spef"]["path"],
                    "vcd_path": trace["path"],
                    "output_path": ATTEMPT03 / "runs" / run["run_id"] / "power",
                }
            )
    write_csv(
        OUTPUT_MATRIX,
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
        rows,
    )
    print(
        f"GATE1_ATTEMPT03_PREPARE_PASS missing_points={len(rows)} "
        f"preserved_points={len(COMPLETED_ATTEMPT02) * 2}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
