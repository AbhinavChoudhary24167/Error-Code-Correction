#!/usr/bin/env python3
"""Run the prioritized GREEN v3.3 queue under one campaign deadline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


CAMPAIGN = Path(__file__).resolve().parents[1]
REPO = CAMPAIGN.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from campaigns.iscas_sustainability_extension.green_v3_3_activity_complete_e5.campaign_runtime import (  # noqa: E402
    CAMPAIGN_BUDGET_SECONDS,
    CampaignController,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute all queued jobs under one persisted wall-clock campaign budget."
    )
    parser.add_argument("--queue", type=Path, default=CAMPAIGN / "CAMPAIGN_QUEUE.json")
    parser.add_argument("--runtime-state", type=Path, default=CAMPAIGN / "RUNTIME_STATE.json")
    parser.add_argument("--progress", type=Path, default=CAMPAIGN / "PROGRESS.md")
    parser.add_argument(
        "--campaign-budget-seconds", type=int, default=CAMPAIGN_BUDGET_SECONDS,
        help="Total budget shared by the entire campaign; it is not renewed per job.",
    )
    parser.add_argument("--launch-guard-seconds", type=float, default=300.0)
    args = parser.parse_args()
    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    if payload.get("budget_scope") != "ENTIRE_CAMPAIGN":
        parser.error("queue must declare budget_scope=ENTIRE_CAMPAIGN")
    jobs = sorted(payload["jobs"], key=lambda item: (item["priority"], item["job_id"]))
    if not jobs:
        parser.error(
            "the queue contains no audited executable jobs; refusing to start and consume the campaign clock"
        )
    controller = CampaignController(
        state_path=args.runtime_state,
        progress_path=args.progress,
        budget_seconds=args.campaign_budget_seconds,
        launch_guard_seconds=args.launch_guard_seconds,
    )
    state = controller.run(jobs)
    print(
        f"CAMPAIGN_FINISHED status={state['status']} "
        f"start={state['campaign_start_time_utc']} deadline={state['hard_deadline_utc']}"
    )
    return 0 if state["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
