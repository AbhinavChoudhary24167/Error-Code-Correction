#!/usr/bin/env python3
"""Summarize Attempt09 regression and integrity evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
LOGS = ROOT / "raw" / "regression"
EXPECTED = {
    "tests/python/test_gate03_artifacts.py::test_gate01_gate02_immutable_authorized_scope_and_binary_verdict",
    "tests/python/test_gate03e_artifacts.py::test_gate03e_artifact_validator",
}


def read(name: str) -> str:
    return (LOGS / name).read_text(encoding="utf-8", errors="replace")


def pytest_result(name: str, expected_frozen: bool) -> dict:
    text = read(name)
    failures = set(re.findall(r"^FAILED\s+(\S+)", text, re.M))
    passed_matches = re.findall(r"(\d+) passed", text)
    failed_matches = re.findall(r"(\d+) failed", text)
    passed = int(passed_matches[-1]) if passed_matches else 0
    failed = int(failed_matches[-1]) if failed_matches else len(failures)
    if not failures and failed == 0:
        status = "PASS"
        exit_code = 0
    elif expected_frozen and failures == EXPECTED:
        status = "EXPECTED_FROZEN_FAILURES_ONLY"
        exit_code = 2 if name == "make_test.log" else 1
    else:
        status = "NEW_REGRESSION"
        exit_code = 1
    return {"status": status, "exit_code": exit_code, "passed": passed, "failed": failed, "failure_nodeids": sorted(failures), "log": f"raw/regression/{name}"}


campaign = pytest_result("campaign_local_tests.log", False)
make_text = read("make.log")
make_status = "PASS" if "make: ***" not in make_text and "error:" not in make_text.lower() else "FAIL"
make = {"status": make_status, "exit_code": 0 if make_status == "PASS" else 1, "log": "raw/regression/make.log", "toolchain": "Windows GNU make / MSYS-compatible g++"}
make_test = pytest_result("make_test.log", True)
full = pytest_result("full_pytest.log", True)
protected_text = (ROOT / "raw" / "integrity" / "protected_date_final_verify.log").read_text(encoding="utf-8")
protected = json.loads(protected_text[protected_text.index("{"):])
prior = json.loads((ROOT / "raw" / "integrity" / "prior_campaign_repository_verification.json").read_text(encoding="utf-8"))
frozen = json.loads((ROOT / "raw" / "integrity" / "frozen_source_verification.json").read_text(encoding="utf-8"))
binary_hash = hashlib.sha256((REPO / "PracticalSRAMSimulator.exe").read_bytes()).hexdigest()
required_hash = "99fbb17b7a9bc4296d6a044e5edc496f131def71e532062b563a776ab31e06ef"
new_regressions = 0 if make["status"] == campaign["status"] == "PASS" and make_test["status"] == full["status"] == "EXPECTED_FROZEN_FAILURES_ONLY" else 1
payload = {
    "schema_version": 1,
    "overall_status": "PASS_WITH_EXPECTED_FROZEN_FAILURES" if new_regressions == 0 else "FAIL",
    "campaign_local_tests": campaign,
    "make": make,
    "make_test": make_test,
    "full_pytest": full,
    "expected_frozen_failure_nodeids": sorted(EXPECTED),
    "new_regression_count": new_regressions,
    "protected_date_baseline": {"status": protected["status"], "protected_file_count": protected["protected_file_count"], "added": protected["added"], "changed": protected["changed"], "missing": protected["missing"]},
    "prior_campaign_evidence": {"status": prior["status"], "campaign_count": len(prior["campaigns"])},
    "frozen_sram22_sources": {"status": frozen["status"], "artifact_count": frozen["artifact_count"], "upstream_commit": frozen["upstream_commit"]},
    "protected_binary": {"status": "RESTORED" if binary_hash == required_hash else "HASH_MISMATCH", "required_sha256": required_hash, "actual_sha256": binary_hash},
}
(ROOT / "REGRESSION_STATUS.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"overall_status": payload["overall_status"], "new_regression_count": new_regressions, "binary": payload["protected_binary"]["status"]}))
raise SystemExit(0 if new_regressions == 0 and payload["protected_binary"]["status"] == "RESTORED" else 1)
