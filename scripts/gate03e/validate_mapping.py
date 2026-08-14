#!/usr/bin/env python3
"""Validate the four bounded Gate-03E SKY130HD mapping jobs.

This validator deliberately reports structural readiness only.  It does not
publish comparative area, timing, power, or other PPA claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
VALIDATOR_VERSION = "gate03e-mapping-validator-v1"
ORFS_DIGEST = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
ORFS_COMMIT = "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
LIBERTY_RELATIVE = "flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"


PORT_SPECS: dict[str, dict[str, str]] = {
    "secded-combinational": {
        "input enc_data_i": "[63:0]",
        "output enc_codeword_o": "[71:0]",
        "input dec_codeword_i": "[71:0]",
        "output dec_data_o": "[63:0]",
        "output dec_corrected_codeword_o": "[71:0]",
        "output dec_detected_o": "scalar",
        "output dec_corrected_o": "scalar",
        "output dec_uncorrectable_o": "scalar",
    },
    "secded-pipelined": {
        "input clk_i": "scalar",
        "input enc_valid_i": "scalar",
        "input enc_data_i": "[63:0]",
        "output enc_valid_o": "scalar",
        "output enc_codeword_o": "[71:0]",
        "input dec_valid_i": "scalar",
        "input dec_codeword_i": "[71:0]",
        "output dec_valid_o": "scalar",
        "output dec_data_o": "[63:0]",
        "output dec_corrected_codeword_o": "[71:0]",
        "output dec_detected_o": "scalar",
        "output dec_corrected_o": "scalar",
        "output dec_uncorrectable_o": "scalar",
    },
    "bch-encoder": {
        "input data_i": "[63:0]",
        "output codeword_o": "[77:0]",
    },
    "bch-decoder": {
        "input codeword_i": "[77:0]",
        "output data_o": "[63:0]",
        "output corrected_codeword_o": "[77:0]",
        "output syndrome_o": "[27:0]",
        "output correction_mask_o": "[77:0]",
        "output err_detected_o": "scalar",
        "output err_corrected_o": "scalar",
        "output err_uncorrectable_o": "scalar",
    },
}


JOBS: dict[str, dict[str, Any]] = {
    "secded-combinational": {
        "design": "gate03e_secded_combinational_boundary",
        "sources": [
            "scripts/gate03r/rtl/secded_characterization_tops.sv",
            "scripts/gate03e/mapping/secded_package_free_boundary.sv",
        ],
        "sdc": "scripts/gate03e/mapping/combinational.sdc",
        "latency_cycles": {"encoder": 0, "decoder": 0},
        "implementation": "independent-channel SECDED boundary; Gate-03R exact-proven package-free implementation",
        "proof_reference": "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json",
        "sequential_required": False,
    },
    "secded-pipelined": {
        "design": "gate03e_secded_pipelined_boundary",
        "sources": [
            "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
            "scripts/gate03e/mapping/independent_channel_boundaries.sv",
        ],
        "sdc": "scripts/gate03e/mapping/pipelined.sdc",
        "latency_cycles": {"encoder": 2, "decoder": 2},
        "implementation": "independent-channel production pipelined SECDED boundary",
        "proof_reference": "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json",
        "sequential_required": True,
    },
    "bch-encoder": {
        "design": "bch_78_64_t2_v1_encoder",
        "sources": ["asic/rtl/bch/bch_78_64_t2_v1.sv"],
        "sdc": "scripts/gate03e/mapping/combinational.sdc",
        "latency_cycles": {"encoder": 0},
        "implementation": "exact BCH (78,64,t=2) encoder",
        "proof_reference": "docs/date2027/rigour_gate_03r/EXACT_PROOF_SUMMARY.json",
        "sequential_required": False,
    },
    "bch-decoder": {
        "design": "bch_78_64_t2_v1_decoder",
        "sources": ["asic/rtl/bch/bch_78_64_t2_v1.sv"],
        "sdc": "scripts/gate03e/mapping/combinational.sdc",
        "latency_cycles": {"decoder": 0},
        "implementation": "exact BCH (78,64,t=2) decoder",
        "proof_reference": "docs/date2027/rigour_gate_03r/EXACT_PROOF_SUMMARY.json",
        "sequential_required": False,
    },
}


DECLARATION_RE = re.compile(
    r"^\s*(input|output)\s+(?:wire\s+|reg\s+)?(?:(\[[^\]]+\])\s+)?(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*;",
    re.MULTILINE,
)
MODULE_RE = re.compile(r"^\s*module\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\(", re.MULTILINE)
INSTANCE_RE = re.compile(
    r"^\s*(\\\S+|[A-Za-z_$][A-Za-z0-9_$]*)\s+(\\\S+|[A-Za-z_$][A-Za-z0-9_$]*)\s*\(",
    re.MULTILINE,
)
INSTANCE_KEYWORDS = {"module", "input", "output", "wire", "reg", "assign", "endmodule"}
FAULT_PORT_RE = re.compile(r"(?:fault|inject|flip|error_mask|corrupt)", re.IGNORECASE)
SEQUENTIAL_MASTER_RE = re.compile(r"^sky130_fd_sc_hd__(?:s?df|edf)", re.IGNORECASE)
LATCH_MASTER_RE = re.compile(
    r"^sky130_fd_sc_hd__(?:dlr[bt][np]|dlx[bt][np]|lpflow_inputisolatch)",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path, base: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(base).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def source_artifact(path: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(repo_root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def parse_ports(text: str) -> dict[str, str]:
    ports: dict[str, str] = {}
    for direction, width, raw_name in DECLARATION_RE.findall(text):
        name = raw_name.lstrip("\\")
        ports[f"{direction} {name}"] = width or "scalar"
    return ports


def parse_cell_masters(text: str) -> Counter[str]:
    masters: Counter[str] = Counter()
    for cell_type, _instance in INSTANCE_RE.findall(text):
        cell_type = cell_type.lstrip("\\")
        if cell_type not in INSTANCE_KEYWORDS:
            masters[cell_type] += 1
    return masters


def normalized_netlist_sha256(text: str) -> str:
    lines: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("/*") or stripped.startswith("(*"):
            continue
        lines.append(" ".join(stripped.split()))
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def validate_job(
    job_name: str,
    config: dict[str, Any],
    repo_root: Path,
    mapping_root: Path,
    liberty_path: Path,
) -> dict[str, Any]:
    design = config["design"]
    job_root = mapping_root / job_name
    result_root = job_root / "results" / "sky130hd" / design / "base"
    log_root = job_root / "logs" / "sky130hd" / design / "base"
    netlist = result_root / "1_2_yosys.v"
    odb = result_root / "1_synth.odb"
    yosys_log = log_root / "1_2_yosys.log"
    synth_log = log_root / "1_synth.log"
    container_log = job_root / "container.log"
    run_metadata_path = job_root / "run-metadata.json"
    required_paths = [netlist, odb, yosys_log, synth_log, container_log, run_metadata_path, liberty_path]
    required_paths.extend(repo_root / item for item in config["sources"])
    required_paths.append(repo_root / config["sdc"])
    missing = [str(path) for path in required_paths if not path.is_file() or path.stat().st_size == 0]
    if missing:
        return {"job": job_name, "design": design, "status": "FAIL", "missing_or_empty": missing}

    checks: list[dict[str, Any]] = []
    metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
    checks.append({"name": "bounded_synthesis_exit_status", "pass": metadata.get("exit_status") == 0})
    checks.append({"name": "timeout_is_1200_seconds", "pass": metadata.get("timeout_seconds") == 1200})

    text = netlist.read_text(encoding="utf-8", errors="strict")
    modules = [item.lstrip("\\") for item in MODULE_RE.findall(text)]
    ports = parse_ports(text)
    expected_ports = PORT_SPECS[job_name]
    checks.append({"name": "single_exact_top_module", "pass": modules == [design], "actual": modules})
    checks.append({"name": "exact_port_contract", "pass": ports == expected_ports})

    masters = parse_cell_masters(text)
    generic_or_unmapped = sorted(master for master in masters if not master.startswith("sky130_fd_sc_hd__"))
    latch_masters = sorted(master for master in masters if LATCH_MASTER_RE.search(master))
    sequential_count = sum(count for master, count in masters.items() if SEQUENTIAL_MASTER_RE.search(master))
    sequential_ok = sequential_count > 0 if config["sequential_required"] else sequential_count == 0
    checks.append({"name": "mapped_cells_are_sky130hd_only", "pass": not generic_or_unmapped})
    checks.append({"name": "no_latches", "pass": not latch_masters})
    checks.append({"name": "sequential_structure_contract", "pass": sequential_ok})
    checks.append({"name": "no_fault_injection_ports", "pass": not any(FAULT_PORT_RE.search(key) for key in ports)})

    log_text = container_log.read_text(encoding="utf-8", errors="replace")
    fatal_log_lines = [
        line.strip()
        for line in log_text.splitlines()
        if re.search(r"(?:^|\s)(?:ERROR:|FATAL:)|unsupported construct", line, re.IGNORECASE)
    ]
    inferred_latch_warnings = [
        line.strip() for line in log_text.splitlines() if re.search(r"latch inferred", line, re.IGNORECASE)
    ]
    checks.append({"name": "no_fatal_log_markers", "pass": not fatal_log_lines})

    proof_path = repo_root / config["proof_reference"]
    checks.append({"name": "accepted_exact_proof_reference_present", "pass": proof_path.is_file()})
    checks.append({"name": "liberty_present", "pass": liberty_path.is_file()})

    source_manifest = [source_artifact(repo_root / item, repo_root) for item in config["sources"]]
    sdc_manifest = source_artifact(repo_root / config["sdc"], repo_root)
    passed = all(bool(check["pass"]) for check in checks)
    return {
        "job": job_name,
        "design": design,
        "implementation": config["implementation"],
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "port_contract": {"expected": expected_ports, "observed": ports, "latency_cycles": config["latency_cycles"]},
        "source_files": source_manifest,
        "sdc": sdc_manifest,
        "proof_reference": source_artifact(proof_path, repo_root) if proof_path.is_file() else {"path": config["proof_reference"], "missing": True},
        "mapped_artifacts": {
            "netlist": artifact(netlist, mapping_root),
            "synthesis_database": artifact(odb, mapping_root),
            "yosys_log": artifact(yosys_log, mapping_root),
            "synthesis_log": artifact(synth_log, mapping_root),
            "container_log": artifact(container_log, mapping_root),
            "run_metadata": artifact(run_metadata_path, mapping_root),
        },
        "normalized_netlist_sha256": normalized_netlist_sha256(text),
        "cell_count": sum(masters.values()),
        "cell_master_counts": dict(sorted(masters.items())),
        "sequential_cell_count": sequential_count,
        "latch_masters": latch_masters,
        "generic_or_unmapped_cell_types": generic_or_unmapped,
        "fatal_log_lines": fatal_log_lines,
        "inferred_latch_warnings": inferred_latch_warnings,
        "equivalence_setup_assessable": passed,
    }


def build_report(repo_root: Path, mapping_root: Path, source_root: Path) -> dict[str, Any]:
    liberty_path = source_root / LIBERTY_RELATIVE
    jobs = [validate_job(name, config, repo_root, mapping_root, liberty_path) for name, config in JOBS.items()]
    by_name = {job["job"]: job for job in jobs}
    comb = by_name["secded-combinational"]
    pipe = by_name["secded-pipelined"]
    distinct_checks = [
        {
            "name": "normalized_netlist_hashes_differ",
            "pass": comb.get("normalized_netlist_sha256") != pipe.get("normalized_netlist_sha256"),
        },
        {
            "name": "cell_master_histograms_differ",
            "pass": comb.get("cell_master_counts") != pipe.get("cell_master_counts"),
        },
        {
            "name": "pipeline_registers_preserved",
            "pass": comb.get("sequential_cell_count") == 0 and int(pipe.get("sequential_cell_count", 0)) > 0,
        },
    ]
    overall = all(job.get("status") == "PASS" for job in jobs) and all(item["pass"] for item in distinct_checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "structural mapping readiness only; no comparative PPA claims",
        "orfs_image_digest": ORFS_DIGEST,
        "orfs_source_commit": ORFS_COMMIT,
        "liberty": artifact(liberty_path, source_root) if liberty_path.is_file() else {"path": LIBERTY_RELATIVE, "missing": True},
        "jobs": jobs,
        "secded_structural_distinction": distinct_checks,
        "status": "PASS" if overall else "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--mapping-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args.repo_root.resolve(), args.mapping_root.resolve(), args.source_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"GATE03E_MAPPING_VALIDATION_{report['status']}")
    for job in report["jobs"]:
        print(f"{job['job']}={job['status']} cells={job.get('cell_count', 0)} sequential={job.get('sequential_cell_count', 0)}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
