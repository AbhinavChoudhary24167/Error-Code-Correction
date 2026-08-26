#!/usr/bin/env python3
"""Prospectively qualify and freeze the Revision-2 algorithmic Hsiao RTL."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path


IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
OLD_ENCODER = "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv"
OLD_SYNDROME = "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv"
OLD_DECODER = "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv"
NEW_DECODER = "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv"
MITER = "scripts/revision2/rtl/hsiao_exact_identity_miter.sv"
BOUNDARY = "scripts/revision2/rtl/rev2_hsiao_boundary.sv"
SPEC = "docs/date2027/revision2/REV2_HSIAO_IDENTITY_SPEC.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def docker_yosys(repo: Path, script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "--volume", f"{repo}:/repo:ro",
            "--entrypoint", "/bin/bash", IMAGE, "-lc",
            f"source /OpenROAD-flow-scripts/env.sh; yosys -p \"{script}\"",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=600,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = repo / "docs/date2027/revision2"
    spec = json.loads((repo / SPEC).read_text(encoding="utf-8"))

    historical_hashes = {
        OLD_ENCODER: "638b36ff3ab1ee31bb8e29b8d5ea064b5b36d1d7df7a3f2b96c52e305a31e036",
        OLD_SYNDROME: "5b232248546e1945ab5084b7f4850851bb62c6e54dc9c4fa00950e2a457590be",
        OLD_DECODER: "9f74648a861c0506bdd698ab53bb47f8f999eed2bdcc1f6e3c0cf548d9929bfb",
    }
    for relative, expected in historical_hashes.items():
        if sha256(repo / relative) != expected:
            raise SystemExit(f"historical qualified Hsiao source changed: {relative}")

    columns = [int(value, 16) for value in spec["parity_check_matrix"]["columns_hex_in_storage_order"]]
    if len(columns) != 72 or len(set(columns)) != 72 or 0 in columns or any(value.bit_count() % 2 == 0 for value in columns):
        raise SystemExit("frozen Hsiao column identity is invalid")

    rtl_text = (repo / NEW_DECODER).read_text(encoding="utf-8")
    assignments = re.findall(r"column_match\[(\d+)\]\s*=\s*\(syndrome\s*==\s*8'h([0-9a-fA-F]{2})\)", rtl_text)
    rtl_columns = [None] * 72
    for index_text, value_text in assignments:
        rtl_columns[int(index_text)] = int(value_text, 16)
    if rtl_columns != columns:
        raise SystemExit("algorithmic decoder columns do not match the frozen H matrix")
    if re.search(r"\bcase\b|\brom\b", re.sub(r"//.*", "", rtl_text), flags=re.IGNORECASE):
        raise SystemExit("algorithmic decoder contains a prohibited table/ROM construct")

    sources = " ".join(f"/repo/{path}" for path in (OLD_SYNDROME, OLD_DECODER, NEW_DECODER, MITER))
    equivalence_script = (
        f"read_verilog -sv {sources}; "
        "prep -top rev2_hsiao_exact_identity_miter -flatten; "
        "memory_map; opt; "
        "select -clear; select rev2_hsiao_exact_identity_miter; "
        "sat -verify -prove mismatch 0 -show-inputs -show-outputs"
    )
    equivalence = docker_yosys(repo, equivalence_script)
    (out / "REV2_HSIAO_EXACT_IDENTITY.log").write_text(equivalence.stdout, encoding="utf-8", newline="\n")
    exact_pass = equivalence.returncode == 0 and "SAT proof finished - no model found: SUCCESS" in equivalence.stdout

    structure_script = (
        f"read_verilog -sv /repo/{OLD_SYNDROME} /repo/{NEW_DECODER}; "
        "prep -top hsiao_secded_72_64_v2_algorithmic_decoder; "
        "memory_dff; memory_collect; "
        "select -assert-none t:$mem t:$mem_v2 t:$memrd t:$memwr; stat"
    )
    structure = docker_yosys(repo, structure_script)
    (out / "REV2_HSIAO_STRUCTURE.log").write_text(structure.stdout, encoding="utf-8", newline="\n")
    structure_pass = structure.returncode == 0 and "Assert `select' failed" not in structure.stdout

    verdict = "HSIAO_EXACT_IDENTITY_PASS" if exact_pass and structure_pass else "HSIAO_REV2_NOT_QUALIFIED"
    source_files = [OLD_ENCODER, OLD_SYNDROME, OLD_DECODER, NEW_DECODER, MITER, BOUNDARY, SPEC]
    freeze = {
        "schema_version": 1,
        "state": "REV2_HSIAO_RTL_FROZEN_BEFORE_PHYSICAL_EXECUTION" if verdict.endswith("PASS") else "REV2_HSIAO_NOT_FROZEN_FOR_PPA",
        "frozen_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "code_id": spec["code_id"],
        "hardware_implementation_id": "hsiao-algorithmic-combinational-72-64-rev2-v1",
        "latency_cycles": 1,
        "initiation_interval_cycles": 1,
        "source_files": [
            {"path": relative, "bytes": (repo / relative).stat().st_size, "sha256": sha256(repo / relative)}
            for relative in source_files
        ],
        "post_freeze_rtl_change_rule": "any change creates a new identity and invalidates all PPA",
    }
    qualification = {
        "schema_version": 1,
        "verdict": verdict,
        "code_id": spec["code_id"],
        "matrix_hash": spec["matrix_hash"],
        "equivalence": {
            "method": "Yosys exhaustive SAT over arbitrary 72-bit received word",
            "latency_alignment": "both decoder cores combinational; common registered boundary unchanged",
            "outputs_compared": ["data_out[63:0]", "correction_applied", "detected_uncorrectable"],
            "passed": exact_pass,
            "log": "REV2_HSIAO_EXACT_IDENTITY.log",
        },
        "structure": {
            "method": "post-process Yosys memory collection and assert no memory cell types",
            "passed": structure_pass,
            "large_table_inferred": False if structure_pass else None,
            "synthesis_memory_policy_changed": False,
            "log": "REV2_HSIAO_STRUCTURE.log",
        },
        "historical_evidence_transfer": "permitted for code-level W0/W1/W2/W3 semantics only" if exact_pass else "forbidden",
        "ppa_authorized": bool(exact_pass and structure_pass),
    }
    write_json(out / "REV2_HSIAO_RTL_FREEZE.json", freeze)
    write_json(out / "REV2_HSIAO_QUALIFICATION.json", qualification)
    print(verdict)
    return 0 if verdict == "HSIAO_EXACT_IDENTITY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
