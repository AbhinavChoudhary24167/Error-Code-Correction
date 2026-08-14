#!/usr/bin/env python3
"""Mechanical consistency and scope validator for Gate-03E artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "date2027" / "rigour_gate_03e"
FREEZE_COMMIT = "db32a47d103495787a17b59388dfad3cc4cb77e8"
ORFS_DIGEST = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
ORFS_COMMIT = "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
ORFS_TREE = "2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a"
POLICY_SHA256 = "258694f328084c3fb92dec24e07b3b40d261037d5b1bd8d32b119684211d0b9a"
OFFICIAL_MAKE = "make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk"
REQUIRED = (
    "GATE_03E_REPORT.md",
    "ENVIRONMENT_MANIFEST.json",
    "ORFS_IMAGE_RECONCILIATION.json",
    "ORFS_SOURCE_FREEZE.json",
    "SKY130HD_COLLATERAL_MANIFEST.json",
    "GCD_SMOKE_RUNS.csv",
    "GREEN_ECC_MAPPING_READINESS.csv",
    "GATE_03_REENTRY_AUTHORIZATION.md",
    "COMMAND_MANIFEST.json",
    "RAW_LOG_INDEX.csv",
)


def load_json(name: str) -> dict:
    return json.loads((DOC / name).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate() -> list[str]:
    errors: list[str] = []
    for name in REQUIRED:
        if not (DOC / name).is_file():
            errors.append(f"missing required artifact: {name}")
    if errors:
        return errors

    environment = load_json("ENVIRONMENT_MANIFEST.json")
    image = load_json("ORFS_IMAGE_RECONCILIATION.json")
    source = load_json("ORFS_SOURCE_FREEZE.json")
    collateral = load_json("SKY130HD_COLLATERAL_MANIFEST.json")
    command = load_json("COMMAND_MANIFEST.json")
    if environment["gate03r_freeze"]["starting_commit"] != FREEZE_COMMIT:
        errors.append("Gate-03R starting commit changed")
    if environment["gate03r_freeze"]["preserved_verdict"] != "REMEDIATION_FAILED":
        errors.append("Gate-03R verdict changed")
    expected_subresults = {
        "EXACT_IDENTITY_SECDED_REMEDIATION": "PASS",
        "BCH_78_64_T2_REMEDIATION": "PASS",
        "PHYSICAL_ENVIRONMENT_REMEDIATION": "FAIL",
    }
    if environment["gate03r_freeze"]["subresults"] != expected_subresults:
        errors.append("Gate-03R sub-results changed")
    if environment["gate03r_freeze"]["commit_pushed"] or environment["gate03r_freeze"]["tag_pushed"]:
        errors.append("local freeze commit or tag was described as pushed")
    if image["linux_amd64_manifest_digest"] != ORFS_DIGEST or image["status"] != "PASS":
        errors.append("pinned image digest/reconciliation failed")
    subset = image["execution_subset"]
    if subset["counts"] != {
        "additional_in_container": 0,
        "byte_identical": 169,
        "mismatched": 0,
        "missing_from_container": 0,
    }:
        errors.append("execution subset reconciliation counts changed")
    for key in ("additional_container_files", "files_missing_from_container", "mismatched_execution_relevant_files"):
        if subset[key]:
            errors.append(f"nonempty reconciliation failure list: {key}")
    if source["commit"] != ORFS_COMMIT or source["git_tree"] != ORFS_TREE or not source["checkout_clean"]:
        errors.append("official source freeze identity failed")
    pvt = collateral["liberty_pvt_selection"]
    nominal = pvt["nominal_conditions"]
    operating = pvt["operating_conditions"]
    if (
        not pvt["metadata_confirmation_pass"]
        or not pvt["selected_only_after_metadata_confirmation"]
        or nominal != {"process": 1.0, "temperature_c": 25.0, "voltage_v": 1.8}
        or operating["process"] != 1.0
        or operating["temperature_c"] != 25.0
        or operating["voltage_v"] != 1.8
    ):
        errors.append("SKY130HD Liberty PVT metadata mismatch")
    if command["frozen_reproducibility"]["policy_sha256"] != POLICY_SHA256:
        errors.append("reproducibility policy hash changed")
    if command["frozen_reproducibility"]["reproducibility_pass"] is not False:
        errors.append("known frozen-comparison failure was not retained")
    if command["frozen_reproducibility"]["semantic_artifact_failure_count"] != 0:
        errors.append("required semantic artifact comparison failed")

    with (DOC / "GCD_SMOKE_RUNS.csv").open(encoding="utf-8", newline="") as stream:
        smoke = list(csv.DictReader(stream))
    if len(smoke) != 2:
        errors.append(f"expected two GCD runs, found {len(smoke)}")
    for row in smoke:
        if row["invocation"] != OFFICIAL_MAKE or row["status"] != "PASS" or row["exit_status"] != "0":
            errors.append(f"official GCD run failed: {row.get('run_id')}")
        if row["artifact_count"] != "106" or row["semantic_artifacts_match"] != "True":
            errors.append(f"GCD artifact inventory mismatch: {row.get('run_id')}")
        if row["reproducibility_status"] != "FAIL":
            errors.append("frozen reproducibility failure was hidden")

    with (DOC / "GREEN_ECC_MAPPING_READINESS.csv").open(encoding="utf-8", newline="") as stream:
        mapping = list(csv.DictReader(stream))
    if {row["job"] for row in mapping} != {
        "secded-combinational", "secded-pipelined", "bch-encoder", "bch-decoder"
    }:
        errors.append("mapping job set changed")
    for row in mapping:
        if row["status"] != "PASS" or row["generic_or_unmapped_cell_type_count"] != "0":
            errors.append(f"mapping readiness failed: {row.get('job')}")
        if row["mapped_latch_master_count"] != "0" or row["fault_injection_input_present"] != "False":
            errors.append(f"mapped boundary structural violation: {row.get('job')}")
        if row["equivalence_setup_assessable"] != "True" or row["comparative_ppa_generated"] != "False":
            errors.append(f"mapping claim-scope violation: {row.get('job')}")
    pipeline = next((row for row in mapping if row["job"] == "secded-pipelined"), None)
    combinational = next((row for row in mapping if row["job"] == "secded-combinational"), None)
    if not pipeline or int(pipeline["sequential_cell_count"]) <= 0:
        errors.append("pipeline registers did not survive")
    if not combinational or combinational["sequential_cell_count"] != "0":
        errors.append("combinational SECDED unexpectedly contains registers")
    if pipeline and combinational and pipeline["normalized_mapped_netlist_sha256"] == combinational["normalized_mapped_netlist_sha256"]:
        errors.append("SECDED mapped structures are not distinct")

    authorization = (DOC / "GATE_03_REENTRY_AUTHORIZATION.md").read_text(encoding="utf-8")
    if "Authorization: **NOT AUTHORIZED**" not in authorization:
        errors.append("incomplete reproducibility result incorrectly authorizes re-entry")
    if "Terminal verdict: `NOT_ISSUED_BEFORE_DEADLINE`" not in authorization:
        errors.append("pre-deadline terminal verdict handling changed")

    with (DOC / "RAW_LOG_INDEX.csv").open(encoding="utf-8", newline="") as stream:
        raw_logs = list(csv.DictReader(stream))
    if len(raw_logs) != command["raw_log_count"]:
        errors.append("raw log count differs from command manifest")
    for row in raw_logs:
        path = DOC / row["path"]
        if not path.is_file() or path.stat().st_size != int(row["size_bytes"]):
            errors.append(f"raw log missing/size mismatch: {row['path']}")
        elif sha256_file(path) != row["raw_sha256"]:
            errors.append(f"raw log hash mismatch: {row['path']}")

    diff = subprocess.run(
        ["git", "diff", "--quiet", FREEZE_COMMIT, "--", "docs/date2027/rigour_gate_01", "docs/date2027/rigour_gate_02", "docs/date2027/rigour_gate_03", "docs/date2027/rigour_gate_03r"],
        cwd=ROOT,
        check=False,
    )
    if diff.returncode != 0:
        errors.append("previous gate evidence changed after Gate-03R freeze")
    changed = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT, text=True, encoding="utf-8"
    ).splitlines()
    allowed = (
        "scripts/gate03e/",
        "tests/python/test_gate03_artifacts.py",
        "tests/python/test_gate03e_",
        "docs/date2027/rigour_gate_03e/",
        "PracticalSRAMSimulator.exe",
        "drift.json",
        "tests/fixtures/runtime_ml_feature_pack/",
    )
    for line in changed:
        path = line[3:].replace("\\", "/")
        if not path.startswith(allowed):
            errors.append(f"working-tree scope violation: {path}")
    tracked_gate03e = subprocess.check_output(
        ["git", "ls-files", "--", "scripts/gate03e", "tests/python/test_gate03e_*", "docs/date2027/rigour_gate_03e"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).splitlines()
    if tracked_gate03e:
        errors.append("Gate-03E files must remain uncommitted")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "authorization": "NOT_AUTHORIZED_PENDING_DEADLINE"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
