#!/usr/bin/env python3
"""Standalone mechanical validator for the frozen Gate-03 artifact set."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gate03.constants import (
    ELIGIBLE_IMPLEMENTATIONS, EVIDENCE_ENUMS, EVIDENCE_HEADER, EXCLUDED_IMPLEMENTATIONS,
    PPA_HEADER, RAW_REPORT_HEADER, RTL_MATRIX_HEADER, SENTINEL_HEADER, SENTINELS, STAGES,
)

OUT = ROOT / "docs" / "date2027" / "rigour_gate_03"


def rows(name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (OUT / name).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> list[str]:
    errors: list[str] = []
    schemas = {
        "RTL_TO_IMPLEMENTATION_MATRIX.csv": RTL_MATRIX_HEADER,
        "PPA_FEASIBILITY_MATRIX.csv": PPA_HEADER,
        "SENTINEL_RUNS.csv": SENTINEL_HEADER,
        "RAW_REPORT_INDEX.csv": RAW_REPORT_HEADER,
        "EVIDENCE_CLASSIFICATION.csv": EVIDENCE_HEADER,
    }
    parsed = {}
    for name, expected in schemas.items():
        actual, data = rows(name)
        parsed[name] = data
        if actual != list(expected): errors.append(f"header mismatch: {name}")

    rtl = parsed["RTL_TO_IMPLEMENTATION_MATRIX.csv"]
    if {row["implementation_id"] for row in rtl if row["eligibility"] == "ELIGIBLE"} != set(ELIGIBLE_IMPLEMENTATIONS):
        errors.append("eligible implementation set mismatch")
    if {row["implementation_id"] for row in rtl if row["eligibility"] == "EXCLUDED"} != set(EXCLUDED_IMPLEMENTATIONS):
        errors.append("excluded implementation set mismatch")

    ppa = {row["implementation_id"]: row for row in parsed["PPA_FEASIBILITY_MATRIX.csv"]}
    conventional = ppa["secded-rtl-combinational-72-64-v1"]
    hsiao = ppa["hsiao-generated-combinational-72-64-v1"]
    if conventional["mathematical_code_id"] == hsiao["mathematical_code_id"]:
        errors.append("H2 identity was incorrectly merged")
    if {conventional["h2_status"], hsiao["h2_status"]} != {"UNTESTABLE_IDENTITY_MISMATCH"}:
        errors.append("H2 mismatch status absent")
    for row in ppa.values():
        if row["primary_activity_id"] != "normal-clean-random-v1":
            errors.append(f"non-clean primary activity: {row['implementation_id']}")
        if "verification-stress-v1" in row["primary_activity_id"]:
            errors.append("stress trace populated primary power")

    sentinel = parsed["SENTINEL_RUNS.csv"]
    keys = [(r["run_id"], r["implementation_id"], r["stage"], r["attempt"]) for r in sentinel]
    if len(keys) != len(set(keys)): errors.append("duplicate sentinel-stage key")
    for repeat in (1, 2):
        for identifier in SENTINELS:
            found = {r["stage"] for r in sentinel if r["repeat_index"] == str(repeat) and r["implementation_id"] == identifier}
            if found != set(STAGES): errors.append(f"missing stages: repeat={repeat} id={identifier}")
    bch = [r for r in sentinel if r["implementation_id"] == "shortened-bch-78-64-t2-v1-reference-decoder"]
    if any(r["status"] != "PASS_FROZEN_IDENTITY_COPIED_EXACTLY" and r["status"] != "BLOCKED_MISSING_VALID_RTL" for r in bch):
        errors.append("BCH blocked-stage coverage mismatch")

    for row in parsed["EVIDENCE_CLASSIFICATION.csv"]:
        if row["classification"] not in EVIDENCE_ENUMS:
            errors.append(f"bad evidence enum: {row['classification']}")
    for row in parsed["RAW_REPORT_INDEX.csv"]:
        if row["retained_in_git"] == "true":
            path = ROOT / row["path"]
            if not path.is_file() or sha256(path) != row["sha256"]:
                errors.append(f"raw report hash mismatch: {row['raw_report_id']}")

    workload = json.loads((OUT / "baseline" / "workload_contract.json").read_text(encoding="utf-8"))
    if workload["verification_stress_may_populate_primary_power"] is not False:
        errors.append("verification stress primary-power guard disabled")
    audit = json.loads((OUT / "baseline" / "bch_rtl_acceptance_audit.json").read_text(encoding="utf-8"))
    if audit["decoder_acceptance"]["required_mask_cases"] != 3082 or audit["accepted_rtl"]:
        errors.append("BCH exact-proof contract mismatch")

    wrapper_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "scripts" / "gate03" / "rtl").glob("*.sv"))
    for forbidden in ("error_mask_i", "fault_mask", "testbench_mask", "syndrome injection"):
        if forbidden.lower() in wrapper_text.lower(): errors.append(f"synthesized wrapper contains {forbidden}")
    if re.search(r"assign\s+\w+\s*=.*\^", wrapper_text):
        errors.append("synthesized wrapper contains injection XOR assignment")

    environment = json.loads((OUT / "baseline" / "environment_manifest.json").read_text(encoding="utf-8"))
    if not environment["gate01"]["byte_identical"] or not environment["gate02"]["byte_identical"]:
        errors.append("Gate-01/Gate-02 byte identity failed")
    decision = (OUT / "BINARY_NO_GO_DECISION.md").read_text(encoding="utf-8")
    verdicts = re.findall(r"(?m)^(?:GO_TO_GATE_04|NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE)$", decision)
    if verdicts != ["NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE"]:
        errors.append("binary verdict is not exactly one permitted token")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print("Gate-03 artifacts validate")
