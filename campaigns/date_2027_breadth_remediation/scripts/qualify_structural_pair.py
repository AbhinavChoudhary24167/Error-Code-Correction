#!/usr/bin/env python3
"""Prospectively qualify and synthesize the additive Hsiao structural pair."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path


IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
CAMPAIGN = Path("campaigns/date_2027_breadth_remediation")
SYNDROME = Path("green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv")
ENCODER = Path("green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv")
BASELINE_DECODER = Path("green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv")
BASELINE_BOUNDARY = Path("scripts/revision2/rtl/rev2_hsiao_boundary.sv")
NEW_DECODER = CAMPAIGN / "rtl/hsiao_secded_72_64_v3_hierarchical_decoder.sv"
NEW_BOUNDARY = CAMPAIGN / "rtl/breadth_hsiao_hierarchical_boundary.sv"
CORE_MITER = CAMPAIGN / "formal/hsiao_structural_exact_miter.sv"
BOUNDARY_MITER = CAMPAIGN / "formal/hsiao_boundary_exact_miter.sv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def check_plan_freeze(repo: Path) -> None:
    freeze = repo / CAMPAIGN / "00_plan_freeze.sha256"
    for line in freeze.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = repo / CAMPAIGN / relative.strip()
        if sha256(path) != expected:
            raise SystemExit(f"frozen prospective plan changed: {relative}")


def check_historical_inventory(repo: Path) -> None:
    inventory = repo / CAMPAIGN / "00_baseline_inventory.sha256"
    expected: dict[str, str] = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        digest, key = line.split(maxsplit=1)
        expected[key.strip()] = digest
    for relative in (SYNDROME, ENCODER, BASELINE_DECODER, BASELINE_BOUNDARY):
        key = f"repository/{relative.as_posix()}"
        if key not in expected or sha256(repo / relative) != expected[key]:
            raise SystemExit(f"protected Revision-2 source changed: {relative}")


def check_new_columns(repo: Path) -> None:
    spec = json.loads((repo / "docs/date2027/revision2/REV2_HSIAO_IDENTITY_SPEC.json").read_text(encoding="utf-8"))
    expected = [int(value, 16) for value in spec["parity_check_matrix"]["columns_hex_in_storage_order"]]
    text = (repo / NEW_DECODER).read_text(encoding="utf-8")
    matches = re.findall(
        r"column_match\[(\d+)\]\s*=\s*high_match\[(\d+)\]\s*&\s*low_match\[(\d+)\]",
        text,
    )
    actual: list[int | None] = [None] * 72
    for index, high, low in matches:
        actual[int(index)] = (int(high) << 4) | int(low)
    if actual != expected:
        raise SystemExit("hierarchical decoder columns do not match the frozen H matrix")


def docker_yosys(repo: Path, script: str, timeout: int = 900) -> tuple[subprocess.CompletedProcess[str], float]:
    command = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--volume", f"{repo}:/repo:ro",
        "--entrypoint", "/bin/bash", IMAGE, "-lc",
        f"source /OpenROAD-flow-scripts/env.sh; yosys -p \"{script}\"",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=timeout,
    )
    return completed, time.monotonic() - started


def docker_version() -> str:
    return subprocess.check_output(
        [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "--entrypoint", "/bin/bash", IMAGE, "-lc",
            "source /OpenROAD-flow-scripts/env.sh; yosys -V",
        ],
        text=True,
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = repo / CAMPAIGN / "formal/results"
    if out.exists():
        raise SystemExit(f"refusing to overwrite structural qualification: {out}")
    out.mkdir(parents=True)

    check_plan_freeze(repo)
    check_historical_inventory(repo)
    check_new_columns(repo)

    core_sources = " ".join(
        f"/repo/{path.as_posix()}" for path in (SYNDROME, BASELINE_DECODER, NEW_DECODER, CORE_MITER)
    )
    core_script = (
        f"read_verilog -sv {core_sources}; "
        "prep -top breadth_hsiao_structural_exact_miter -flatten; "
        "memory_map; opt; "
        "sat -verify -prove mismatch 0 -show-inputs -show-outputs"
    )
    core, core_runtime = docker_yosys(repo, core_script)
    core_log = out / "A_decoder_exact_equivalence.log"
    core_log.write_text(core.stdout, encoding="utf-8", newline="\n")
    core_pass = core.returncode == 0 and "SAT proof finished - no model found: SUCCESS" in core.stdout

    boundary_sources = " ".join(
        f"/repo/{path.as_posix()}"
        for path in (
            ENCODER, SYNDROME, BASELINE_DECODER, NEW_DECODER,
            BASELINE_BOUNDARY, NEW_BOUNDARY, BOUNDARY_MITER,
        )
    )
    boundary_script = (
        f"read_verilog -sv {boundary_sources}; "
        "prep -top breadth_hsiao_boundary_exact_miter -flatten; "
        "memory_map; opt; "
        "sat -verify -seq 6 -tempinduct -set-init-zero -prove mismatch 0 "
        "-show-inputs -show-outputs"
    )
    boundary, boundary_runtime = docker_yosys(repo, boundary_script)
    boundary_log = out / "A_boundary_exact_equivalence.log"
    boundary_log.write_text(boundary.stdout, encoding="utf-8", newline="\n")
    boundary_pass = boundary.returncode == 0 and "Induction step proven: SUCCESS" in boundary.stdout

    source_paths = (SYNDROME, ENCODER, BASELINE_DECODER, BASELINE_BOUNDARY, NEW_DECODER, NEW_BOUNDARY, CORE_MITER, BOUNDARY_MITER)
    formal_pass = core_pass and boundary_pass
    status = "PASS" if formal_pass else "FAIL"
    payload = {
        "schema_version": 1,
        "formal_status": status,
        "hard_gate": "STRUCTURAL_PAIR_FORMAL_GATE",
        "tool": docker_version(),
        "container_image": IMAGE,
        "completed_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "baseline_implementation_id": "hsiao-algorithmic-combinational-72-64-rev2-v1",
        "new_implementation_id": "hsiao-hierarchical-nibble-decode-combinational-72-64-breadth-v1",
        "latency_alignment_cycles": 0,
        "expected_request_latency_cycles": 1,
        "expected_initiation_interval_cycles": 1,
        "proofs": {
            "decoder_arbitrary_word": {
                "status": "PASS" if core_pass else "FAIL",
                "command": core_script,
                "runtime_seconds": core_runtime,
                "constraints": "none; arbitrary 72-bit received word",
                "assumptions": "none",
                "log": str(core_log.relative_to(repo).as_posix()),
                "proof_log_sha256": sha256(core_log),
            },
            "registered_boundary": {
                "status": "PASS" if boundary_pass else "FAIL",
                "command": boundary_script,
                "runtime_seconds": boundary_runtime,
                "constraints": "equal zero initial state; arbitrary reset, valid, encoder payload, and decoder word sequences",
                "assumptions": "common clock step; no temporal output alignment",
                "log": str(boundary_log.relative_to(repo).as_posix()),
                "proof_log_sha256": sha256(boundary_log),
            },
        },
        "source_files": [
            {"path": path.as_posix(), "bytes": (repo / path).stat().st_size, "sha256": sha256(repo / path)}
            for path in source_paths
        ],
        "baseline_decoder_sha256": sha256(repo / BASELINE_DECODER),
        "new_decoder_sha256": sha256(repo / NEW_DECODER),
        "physical_authorized": formal_pass,
    }
    write_json(out / "A_formal_qualification.json", payload)
    (out / "STRUCTURAL_PAIR_FORMAL_GATE.txt").write_text(
        f"STRUCTURAL_PAIR_FORMAL_GATE = {status}\n", encoding="utf-8", newline="\n"
    )
    print(f"STRUCTURAL_PAIR_FORMAL_GATE = {status}")
    return 0 if formal_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
