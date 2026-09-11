#!/usr/bin/env python3
"""Populate the audited matched SECDED/Hsiao queue without resetting the deadline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CAMPAIGN_REL = Path("campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5")


def wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[13, 17, 19, 23])
    args = parser.parse_args()
    repo = args.repo.resolve()
    campaign = repo / CAMPAIGN_REL
    executor = wsl_path(campaign / "scripts/execute_e5_job.py")
    state = wsl_path(campaign / "RUNTIME_STATE.json")
    repo_wsl = wsl_path(repo)
    jobs = []
    priority = 100
    for seed in args.seeds:
        for architecture, run_name in (
            ("SECDED", "secded"),
            ("HSIAO_SECDED", "hsiao_secded"),
        ):
            run_id = f"{run_name}_clk10p0ns_seed{seed}"
            jobs.append(
                {
                    "architecture_id": architecture,
                    "clock_period_ns": 10.0,
                    "command": [
                        "wsl.exe",
                        "python3",
                        executor,
                        "--repo",
                        repo_wsl,
                        "--runtime-state",
                        state,
                        "--external-root",
                        "/var/lib/green-ecc-v33-activity-complete-e5",
                        "--architecture",
                        architecture,
                        "--clock-ns",
                        "10.0",
                        "--seed",
                        str(seed),
                    ],
                    "completion_artifact": (campaign / f"fresh_runs/{run_id}/RESULT.json").as_posix(),
                    "cwd": repo.as_posix(),
                    "job_id": f"{run_id}_e5",
                    "log_path": (campaign / f"logs/{run_id}_e5.log").as_posix(),
                    "priority": priority,
                    "seed": seed,
                }
            )
            priority += 10
    payload = {
        "budget_scope": "ENTIRE_CAMPAIGN",
        "campaign_budget_seconds": 54000,
        "jobs": jobs,
        "per_run_timeout_seconds": None,
        "priority_policy": [
            "A: 10ns U0/SECDED/HSIAO seeds 11,13,17,19,23",
            "B: 10ns BCH diagnostic",
            "C: 5ns sensitivity population",
        ],
        "queue_state": "EXPANDED_MATCHED_SEEDS_13_17_19_23_READY_AFTER_SEED11",
        "schema_version": 1,
    }
    (campaign / "CAMPAIGN_QUEUE.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
