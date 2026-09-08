#!/usr/bin/env python3
"""Run and preserve the repository and campaign-local regression commands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
REPO = CAMPAIGN.parents[3]
OUT = CAMPAIGN / "raw" / "regression"
OUT.mkdir(parents=True, exist_ok=True)

commands = [
    (
        "campaign_local_tests",
        ["python3", "-m", "pytest", "-q", str(CAMPAIGN / "tests")],
    ),
    ("make", ["make"]),
    ("make_test", ["make", "test"]),
    ("full_pytest", ["python3", "-m", "pytest", "-q"]),
]

results = []
for name, command in commands:
    completed = subprocess.run(
        command,
        cwd=REPO,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log = OUT / f"{name}.log"
    log.write_text(
        f"command: {' '.join(command)}\nexit_code: {completed.returncode}\n{completed.stdout}",
        encoding="utf-8",
    )
    print(f"{name}: exit_code={completed.returncode} log={log.relative_to(CAMPAIGN)}")
    results.append(
        {
            "name": name,
            "command": command,
            "exit_code": completed.returncode,
            "log": log.relative_to(CAMPAIGN).as_posix(),
        }
    )

(OUT / "regression_command_results.json").write_text(
    json.dumps({"commands": results}, indent=2) + "\n", encoding="utf-8"
)
