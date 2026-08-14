#!/usr/bin/env python3
"""Mechanical validator for the Gate 03R evidence and failure verdict."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from green_ecc_phy.registry import EccRegistry


DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
REQUIRED = (
    "GATE_03R_REPORT.md",
    "EXACT_IDENTITY_FREEZE.json",
    "H2_ARCHITECTURE_CONTRACT.md",
    "BCH_78_64_T2_CONTRACT.md",
    "RTL_LINEAGE_MATRIX.csv",
    "ENCODER_PROOF_MATRIX.csv",
    "DECODER_PROOF_MATRIX.csv",
    "FORMAL_PROOF_INDEX.csv",
    "COUNTEREXAMPLES.jsonl",
    "TOOLCHAIN_FREEZE.json",
    "ORFS_SMOKE_RESULTS.csv",
    "GATE_03_REENTRY_MANIFEST.json",
    "baseline/command_manifest.json",
    "baseline/environment_manifest.json",
    "RAW_LOG_INDEX.csv",
)


def load_json(relative: str) -> dict[str, Any]:
    return json.loads((DOC / relative).read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (DOC / relative).is_file():
            errors.append(f"missing required artifact: {relative}")

    verdict = (DOC / "GATE_03R_VERDICT.txt").read_text(encoding="ascii").strip()
    if verdict != "REMEDIATION_FAILED":
        errors.append(f"unexpected verdict: {verdict}")
    reentry = load_json("GATE_03_REENTRY_MANIFEST.json")
    if reentry.get("gate03r_verdict") != verdict:
        errors.append("re-entry manifest verdict differs")
    if reentry.get("authorization", {}).get("complete_gate03_reentry_authorized") is not False:
        errors.append("failed Gate 03R must not authorize re-entry")

    frozen = load_json("FROZEN_GATE_HASH_CHECK.json")
    for relative, result in frozen.get("gates", {}).items():
        if result.get("status") != "PASS":
            errors.append(f"frozen gate hash failed: {relative}")
        diff = subprocess.run(
            ["git", "diff", "--quiet", reentry["freeze_commit"], "--", relative],
            cwd=ROOT,
            check=False,
        )
        if diff.returncode != 0:
            errors.append(f"previous gate changed after freeze: {relative}")

    with (DOC / "FORMAL_PROOF_INDEX.csv").open(encoding="utf-8", newline="") as stream:
        proofs = list(csv.DictReader(stream))
    bch = [row for row in proofs if row["family"] == "BCH_78_64_T2"]
    if len(bch) != 3082:
        errors.append(f"BCH proof count {len(bch)} != 3082")
    counts = {weight: sum(row["mask_weight"] == str(weight) for row in bch) for weight in (0, 1, 2)}
    if counts != {0: 1, 1: 78, 2: 3003}:
        errors.append(f"BCH proof weight counts are wrong: {counts}")
    for row in proofs:
        if row["status"] != "PASS":
            errors.append(f"failed indexed proof: {row['job_id']}")
        if not row["command"] or not row["result"]:
            errors.append(f"proof command/result absent: {row['job_id']}")
    counterexamples = (DOC / "COUNTEREXAMPLES.jsonl").read_text(encoding="utf-8").splitlines()
    if counterexamples:
        errors.append(f"unexpected counterexamples: {len(counterexamples)}")

    identity = load_json("BCH_IDENTITY_RECONSTRUCTION.json")
    if identity.get("matrix_sha256") != "d518cab40c77da302afecab0e8199f3f0c4e0b2c095660d5d0df8a1e2dae4e89":
        errors.append("BCH identity hash mismatch")
    if identity.get("bounded_locator_entries") != 3081 or identity.get("bounded_locator_collisions"):
        errors.append("BCH bounded locator identity mismatch")
    characterization = load_json("BCH_WEIGHT3_CHARACTERIZATION.json")
    if characterization.get("zero_payload_weight3_masks_examined") != 76076:
        errors.append("weight-3 characterization count mismatch")
    if characterization.get("claim_scope") != "characterization_only_no_weight3_correction_claim":
        errors.append("weight-3 claim scope mismatch")

    default_registry = ROOT / "green_ecc_physical_simulation" / "registry" / "registry.json"
    overlay_registry = ROOT / "green_ecc_physical_simulation" / "registry" / "registry_gate03r.json"
    default = EccRegistry.load(default_registry, repo_root=ROOT)
    overlay = EccRegistry.load(overlay_registry, repo_root=ROOT)
    if len(default.implementations) != 17 or len(overlay.implementations) != 19:
        errors.append("default/overlay implementation counts changed")
    expected_added = {
        "secded-rtl-pipelined-72-64-v1",
        "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
    }
    if set(overlay.implementations) - set(default.implementations) != expected_added:
        errors.append("registry overlay additions differ")
    default_diff = subprocess.run(
        ["git", "diff", "--quiet", reentry["freeze_commit"], "--", "green_ecc_physical_simulation/registry/registry.json"],
        cwd=ROOT,
        check=False,
    )
    if default_diff.returncode != 0:
        errors.append("default registry bytes changed")

    for relative in (
        "asic/rtl/bch/bch_78_64_t2_v1.sv",
        "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
        "scripts/gate03r/rtl/gate03r_characterization_wrappers.sv",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        port_blocks = "\n".join(re.findall(r"module\s+\w+\s*\((.*?)\);", text, re.DOTALL))
        if re.search(r"\b(?:inject|fault|error_mask)_?\w*\b", port_blocks, re.IGNORECASE):
            errors.append(f"fault-injection port entered production boundary: {relative}")
    bch_rtl = (ROOT / "asic/rtl/bch/bch_78_64_t2_v1.sv").read_text(encoding="utf-8")
    if "always_ff" in bch_rtl:
        errors.append("BCH production core was pipelined")
    if "codeword_o = {work[13:0], data_i}" not in bch_rtl:
        errors.append("BCH canonical output mapping absent")

    synthesis = load_json("SYNTHESIS_AND_STRUCTURE_RESULTS.json")
    if any(job.get("status") != "PASS" for job in synthesis.get("jobs", {}).values()):
        errors.append("generic synthesis job failed")
    if synthesis.get("h2_generic_status") != "PASS":
        errors.append("generic H2 structure distinction failed")
    if synthesis.get("sky130hd_mapping", {}).get("status") != "BLOCKED_PINNED_ORFS_ENVIRONMENT_UNAVAILABLE":
        errors.append("SKY130HD mapping blocker was not retained")
    rtl_simulation = load_json("RTL_SIMULATION_RESULTS.json")
    if rtl_simulation.get("status") != "PASS" or rtl_simulation.get("passing_simulator") != "Verilator":
        errors.append("compiled RTL smoke did not pass with Verilator")

    toolchain = load_json("TOOLCHAIN_FREEZE.json")
    if toolchain.get("orfs", {}).get("required_image") != (
        "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
    ):
        errors.append("pinned ORFS digest changed")
    if toolchain.get("orfs", {}).get("substitution_performed") is not False:
        errors.append("ORFS substitution recorded")
    smoke = list(csv.DictReader((DOC / "ORFS_SMOKE_RESULTS.csv").open(encoding="utf-8", newline="")))
    if len(smoke) != 1 or smoke[0]["status"] != "BLOCKED_PINNED_ENVIRONMENT_UNAVAILABLE":
        errors.append("ORFS smoke blocker mismatch")
    if smoke[0]["final_gds"] != "ABSENT":
        errors.append("nonexistent GDS was claimed")

    with (DOC / "RAW_LOG_INDEX.csv").open(encoding="utf-8", newline="") as stream:
        raw_rows = list(csv.DictReader(stream))
    for row in raw_rows:
        path = DOC / row["path"]
        if not path.is_file():
            errors.append(f"raw log identity mismatch: {row['path']}")
        elif not row["path"].startswith("baseline/regression/") and (
            hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]
        ):
            errors.append(f"raw log identity mismatch: {row['path']}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "verdict": "REMEDIATION_FAILED"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
