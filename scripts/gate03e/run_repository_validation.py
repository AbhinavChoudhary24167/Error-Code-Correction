#!/usr/bin/env python3
"""Run and retain the required Gate-03E repository validation commands."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOG_ROOT = ROOT / "docs" / "date2027" / "rigour_gate_03e" / "raw_logs" / "repository-validation"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"required command is not available: {name}")
    return path


def run_job(job_id: str, command: list[str], timeout_seconds: int) -> dict[str, object]:
    log_path = LOG_ROOT / f"{job_id}.log"
    start = now()
    with log_path.open("wb") as log:
        log.write(("COMMAND=" + json.dumps(command) + "\nSTART_UTC=" + start + "\n").encode("utf-8"))
        log.flush()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
                check=False,
            )
            status = completed.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            status = 124
            timed_out = True
        end = now()
        log.write((f"\nEND_UTC={end}\nEXIT_STATUS={status}\nTIMED_OUT={str(timed_out).lower()}\n").encode("utf-8"))
    return {
        "job_id": job_id,
        "command": command,
        "start_utc": start,
        "end_utc": end,
        "exit_status": status,
        "timed_out": timed_out,
        "log": log_path.relative_to(ROOT).as_posix(),
    }


def main() -> int:
    if (LOG_ROOT / "summary.log").is_file():
        attempt = 1
        while (LOG_ROOT.parent / f"repository-validation-attempt-{attempt:02d}").exists():
            attempt += 1
        shutil.copytree(LOG_ROOT, LOG_ROOT.parent / f"repository-validation-attempt-{attempt:02d}")
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    python3 = tool("python3")
    make = tool("make")
    git = tool("git")
    jobs = [
        ("gate03r-validator", [python3, "scripts/gate03r/validate_artifacts.py"], 300),
        (
            "gate03e-focused-tests",
            [
                python3,
                "-m",
                "pytest",
                "-q",
                "tests/python/test_gate03e_artifacts.py",
                "tests/python/test_gate03e_mapping_validator.py",
                "tests/python/test_gate03e_reproducibility.py",
            ],
            600,
        ),
        ("make", [make], 1800),
        ("make-test", [make, "test"], 3600),
        ("python3-pytest-q", [python3, "-m", "pytest", "-q"], 3600),
        ("git-diff-check", [git, "diff", "--check"], 300),
        ("gate03e-artifact-scope-validator", [python3, "scripts/gate03e/validate_artifacts.py"], 300),
    ]
    results = [run_job(job_id, command, timeout_seconds) for job_id, command, timeout_seconds in jobs]
    passed = all(item["exit_status"] == 0 for item in results)
    summary = {
        "schema_version": 1,
        "status": "PASS" if passed else "FAIL",
        "jobs": results,
    }
    summary_path = LOG_ROOT / "summary.log"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    for item in results:
        print(f"{item['job_id']} exit={item['exit_status']} log={item['log']}")
    print(f"GATE03E_REPOSITORY_VALIDATION_{summary['status']}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
