#!/usr/bin/env python3
"""Summarize required regressions and enforce the known-failure boundary."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
LOGS = HERE / "integrity" / "regression"
EXPECTED = [
    "tests/python/test_gate03_artifacts.py::test_gate01_gate02_immutable_authorized_scope_and_binary_verdict",
    "tests/python/test_gate03e_artifacts.py::test_gate03e_artifact_validator",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name: str) -> str:
    return (LOGS / name).read_text(encoding="utf-8", errors="replace")


def code(name: str) -> int:
    return int(read(name).strip())


def count(pattern: str, text: str) -> int:
    matches = re.findall(pattern, text)
    return int(matches[-1]) if matches else 0


def failed_node_ids(text: str) -> list[str]:
    names = re.findall(r"FAILED\s+([^\s]+)", text)
    return sorted(set(name.replace("\\", "/") for name in names))


def main() -> int:
    make_log = read("make.log")
    make_test = read("make_test.log")
    full = read("python3_pytest.log")
    campaign = read("campaign_pytest.log")
    before = read("PracticalSRAMSimulator.before.sha256").strip().lower()
    after_build = read("PracticalSRAMSimulator.after.sha256").strip().lower()
    restored = read("PracticalSRAMSimulator.restored.sha256").strip().lower()
    expected = sorted(EXPECTED)
    make_test_failures = failed_node_ids(make_test)
    full_failures = failed_node_ids(full)
    assertions = {
        "make_passed": code("make.exit_code.txt") == 0,
        "make_test_has_exact_historical_failures": make_test_failures == expected,
        "full_pytest_has_exact_historical_failures": full_failures == expected,
        "campaign_tests_passed": code("campaign_pytest.exit_code.txt") == 0 and "28 passed" in campaign,
        "protected_executable_restored": before == restored == "99fbb17b7a9bc4296d6a044e5edc496f131def71e532062b563a776ab31e06ef",
    }
    document = {
        "schema_version": 1,
        "classification": "EXPECTED_FROZEN_VALIDATOR_FAILURES_ONLY" if all(assertions.values()) else "NEW_REGRESSION_DETECTED",
        "no_new_regression": all(assertions.values()),
        "assertions": assertions,
        "commands": [
            {"command": "make", "exit_code": code("make.exit_code.txt"), "passed": code("make.exit_code.txt") == 0, "log": "integrity/regression/make.log", "log_sha256": sha256(LOGS / "make.log")},
            {"command": "make test", "exit_code": code("make_test.exit_code.txt"), "passed": False, "passed_tests": count(r"(\d+) passed", make_test), "failed_tests": count(r"(\d+) failed", make_test), "failure_node_ids": make_test_failures, "failure_disposition": "EXPECTED_FROZEN_WORKING_TREE_SCOPE_VALIDATORS", "log": "integrity/regression/make_test.log", "log_sha256": sha256(LOGS / "make_test.log")},
            {"command": "python3 -m pytest -q", "exit_code": code("python3_pytest.exit_code.txt"), "passed": False, "passed_tests": count(r"(\d+) passed", full), "failed_tests": count(r"(\d+) failed", full), "failure_node_ids": full_failures, "failure_disposition": "EXPECTED_FROZEN_WORKING_TREE_SCOPE_VALIDATORS", "log": "integrity/regression/python3_pytest.log", "log_sha256": sha256(LOGS / "python3_pytest.log")},
            {"command": "python -m pytest -q campaigns/.../gate3_attempt10.../tests", "exit_code": code("campaign_pytest.exit_code.txt"), "passed": code("campaign_pytest.exit_code.txt") == 0, "passed_tests": count(r"(\d+) passed", campaign), "failed_tests": count(r"(\d+) failed", campaign), "log": "integrity/regression/campaign_pytest.log", "log_sha256": sha256(LOGS / "campaign_pytest.log")},
        ],
        "expected_historical_failures": EXPECTED,
        "failure_cause": "The frozen DATE validators reject the already-untracked campaigns/iscas_sustainability_extension scope. They do not report a functional product regression.",
        "protected_executable": {"path": "PracticalSRAMSimulator.exe", "sha256_before": before, "sha256_after_make": after_build, "sha256_after_restore": restored, "restored_to_exact_baseline": before == restored},
    }
    output = HERE / "integrity" / "REGRESSION_STATUS.json"
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"classification": document["classification"], "assertions": assertions}))
    return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
