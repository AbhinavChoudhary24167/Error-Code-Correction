#!/usr/bin/env python3
"""Fail-closed final evidence validator for Gate 03E-S."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


READY = "ENVIRONMENT_READY_FOR_GATE_03_REENTRY"
FAILED = "ENVIRONMENT_ENABLEMENT_FAILED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, default=Path("/var/lib/green-ecc-gate03es"))
    args = parser.parse_args()
    repo, external = args.repo_root.resolve(), args.external_root
    docs, policy = repo / "docs/date2027/rigour_gate_03es", external / "policy"
    errors: list[str] = []

    required = (
        "GATE_03ES_REPORT.md", "GATE_03ES_VERDICT.txt", "ACCEPTANCE.json",
        "GATE_03ER_ADJUDICATION.json", "REPRODUCIBILITY_POLICY_V3.json",
        "PRODUCER_CATALOG_V3.json", "QOR_METRIC_SCHEMA_V3.json", "FROZEN_BUNDLE.json",
        "IMMUTABLE_INPUT_MANIFEST.json", "COMMAND_MANIFEST.json",
        "STARTING_STATE_AND_PROTECTED_BASELINE.json", "RUN_05_INVENTORY.json",
        "RUN_06_INVENTORY.json", "FRESH_RUN_COMPARISON.json",
        "PATH_SCOPE_REVALIDATION.json", "PRIOR_EVIDENCE_HASH_REVALIDATION.json",
        "REPOSITORY_COMMAND_RESULTS.json", "LEGACY_VALIDATOR_COMPATIBILITY_CHANGE.json",
        "EXTERNAL_ARTIFACT_INDEX.csv", "RAW_LOG_INDEX.csv", "EVIDENCE.sha256",
    )
    for name in required:
        if not (docs / name).is_file():
            errors.append(f"missing required artifact: {name}")
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1

    acceptance = json.loads((docs / "ACCEPTANCE.json").read_text())
    comparison = json.loads((docs / "FRESH_RUN_COMPARISON.json").read_text())
    adjudication = json.loads((docs / "GATE_03ER_ADJUDICATION.json").read_text())
    verdict = (docs / "GATE_03ES_VERDICT.txt").read_text().strip()
    condition_values = [value for key, value in acceptance.items() if key.endswith("_pass")]
    if verdict not in {READY, FAILED} or acceptance.get("verdict") != verdict:
        errors.append("unknown or inconsistent verdict token")
    if verdict == READY and any(value is not True for value in condition_values):
        errors.append("ready verdict has a failed acceptance condition")
    if verdict == FAILED and all(value is True for value in condition_values):
        errors.append("failure verdict has no failed acceptance condition")
    report = (docs / "GATE_03ES_REPORT.md").read_text()
    tokens = re.findall(r"(?m)^(?:ENVIRONMENT_READY_FOR_GATE_03_REENTRY|ENVIRONMENT_ENABLEMENT_FAILED)$", report)
    if tokens:
        errors.append("report contains a bare verdict token in addition to the verdict file")
    if "within-environment repeatability only" not in report or "independent reproducibility" not in report:
        errors.append("repeatability claim scope is missing")
    if adjudication.get("gate03er_verdict") != FAILED or not adjudication.get("scientific_comparisons_all_pass"):
        errors.append("Gate 03E-R was modified or reinterpreted")
    if comparison.get("run_metadata_validation", {}).get("pass") is not True:
        errors.append("run-metadata producer contract failed")
    if comparison.get("reproducibility_pass") is not True or comparison.get("failures") or comparison.get("unknown_metrics"):
        errors.append("fresh repeatability comparison failed")
    if not comparison.get("semantic_artifact_comparisons") or not all(row["pass"] for row in comparison["semantic_artifact_comparisons"]):
        errors.append("semantic/ODB comparison coverage failed")

    manifest = docs / "EVIDENCE.sha256"
    for line in manifest.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        path = docs / relative
        if not path.is_file() or sha256(path) != expected:
            errors.append(f"documentation evidence hash mismatch: {relative}")
    frozen = json.loads((policy / "frozen-bundle.json").read_text())
    for row in frozen["files"]:
        path = policy / row["name"]
        if not path.is_file() or sha256(path) != row["sha256"]:
            errors.append(f"frozen bundle mismatch: {row['name']}")
    for name, expected in (("RUN_05_INVENTORY.json", "gcd-run-05"), ("RUN_06_INVENTORY.json", "gcd-run-06")):
        if json.loads((docs / name).read_text()).get("run_label") != expected:
            errors.append(f"unexpected inventory label: {name}")

    print(json.dumps({"status": "PASS" if not errors else "FAIL", "verdict": verdict, "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
