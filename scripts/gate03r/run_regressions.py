#!/usr/bin/env python3
"""Run and retain the exact final Gate 03R regression commands."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
OUT = DOC / "baseline" / "regression"
COMMANDS = [
    ("git_diff_check", ["git", "diff", "--check"]),
    ("git_diff_cached_check", ["git", "diff", "--cached", "--check"]),
    ("gate03r_validator", ["python3", "scripts/gate03r/validate_artifacts.py"]),
    ("gate03r_focused_tests", ["python3", "-m", "pytest", "-q", "tests/python/test_gate03r_artifacts.py"]),
    ("make", ["make"]),
    ("make_test", ["make", "test"]),
    ("python3_pytest_q", ["python3", "-m", "pytest", "-q"]),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for command_id, command in COMMANDS:
        started = utc_now()
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
                check=False,
            )
            exit_code = result.returncode
            stdout, stderr = result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + "\nTIMEOUT_AFTER_900_SECONDS\n"
        ended = utc_now()
        transcript = (
            "command=" + subprocess.list2cmdline(command) + "\n"
            + f"start_utc={started}\nend_utc={ended}\nexit_code={exit_code}\n\nSTDOUT\n"
            + stdout + "\nSTDERR\n" + stderr
        )
        log = OUT / f"{command_id}.log"
        log.write_text(transcript, encoding="utf-8", newline="\n")
        rows.append(
            {
                "command_id": command_id,
                "command": command,
                "start_utc": started,
                "end_utc": ended,
                "exit_code": exit_code,
                "status": "PASS" if exit_code == 0 else "FAIL",
                "log": log.relative_to(DOC).as_posix(),
            }
        )
        print(f"{command_id}: {'PASS' if exit_code == 0 else 'FAIL'} ({exit_code})", flush=True)
    payload = {
        "schema_version": 1,
        "commands": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
    }
    (DOC / "REGRESSION_RESULTS.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
