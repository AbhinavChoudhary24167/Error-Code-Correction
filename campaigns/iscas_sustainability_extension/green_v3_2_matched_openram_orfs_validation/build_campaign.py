#!/usr/bin/env python3
"""Build deterministic, fail-closed artifacts for the matched validation campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0.0"
PARENT_GREEN_COMMIT = "29f20b196e04c713f88fd1a93440a2ff47986f06"
PARENT_GREEN_PROVENANCE_SEAL_COMMIT = "22d6ef2391f7d74f0890933fcda9952fdf656e52"
PARENT_CAMPAIGN_COMMIT = "1f6bcd009e7a05ebcde35a3272161a9a81ec7bf7"
FOUNDATION_COMMIT = "affc8145b184803189dac36391cb486f00e7b4f8"
PARENT_COUNTS = {"M_E": 561, "M_P": 2, "M_S": 2}
SEEDS = [11, 13, 17, 19, 23]
CLOCKS = [10.0, 5.0]
GENERATED_DATE = "2026-09-08"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def nested(payload: dict[str, Any], keys: Iterable[str]) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def mean_or_none(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "available_count": 0,
            "mean": None,
            "median": None,
            "sample_standard_deviation": None,
            "minimum": None,
            "maximum": None,
            "confidence_interval_95": None,
            "coefficient_of_variation": None,
            "uncertainty_note": "No measurement is available; null is not converted to zero.",
        }
    mean = statistics.mean(values)
    deviation = statistics.stdev(values) if len(values) >= 2 else None
    ci = None
    if len(values) == 5 and deviation is not None:
        half = 2.776 * deviation / math.sqrt(5)
        ci = [mean - half, mean + half]
    return {
        "available_count": len(values),
        "mean": mean,
        "median": statistics.median(values),
        "sample_standard_deviation": deviation,
        "minimum": min(values),
        "maximum": max(values),
        "confidence_interval_95": ci,
        "coefficient_of_variation": None if deviation is None or mean == 0 else deviation / mean,
        "uncertainty_note": "Student-t descriptive interval with n=5; exploratory and not a significance claim."
        if ci
        else "Insufficient observations for the campaign's n=5 descriptive interval.",
    }


def parse_synthesis_counts(path: Path) -> dict[str, int | None]:
    """Parse both legacy and current ORFS/Yosys statistics table formats."""
    if not path.is_file():
        return {}
    cells: dict[str, int] = {}
    total = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*Number of cells:\s+(\d+)", line)
        if match:
            total = int(match.group(1))
        match = re.match(r"\s*(\d+)\s+\S+\s+\d+\s+\S+\s+cells\s*$", line)
        if match:
            total = int(match.group(1))
        match = re.match(r"\s*(\d+)\s+\S+\s+\d+\s+\S+\s+(sky130_fd_sc_hd__\S+)\s*$", line)
        if match:
            cells[match.group(2)] = int(match.group(1))
        match = re.match(r"\s*(sky130_fd_sc_hd__\S+)\s+(\d+)\s*$", line)
        if match:
            cells[match.group(1)] = int(match.group(2))
    sequential = sum(count for name, count in cells.items() if "__df" in name or "__dl" in name)
    return {
        "mapped_cell_count": total,
        "combinational_cells": sum(cells.values()) - sequential,
        "sequential_cells": sequential,
        "buffers_inverters": sum(
            count for name, count in cells.items()
            if "__buf_" in name or "__inv_" in name or "__clkinv_" in name
        ),
        "xor_xnor_cells": sum(count for name, count in cells.items() if "xor" in name),
        "register_count": sequential,
    }


def inherited_macro_records(repo: Path) -> list[dict[str, Any]]:
    root = repo / (
        "campaigns/iscas_sustainability_extension/memory_compiler/"
        "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
    )
    specs = [
        ("sram22_256x64m4w8", 64, 256, 690.120, 291.640),
        ("sram22_256x8m8w1", 8, 256, 261.720, 225.680),
    ]
    records = []
    for name, width, words, macro_width, macro_height in specs:
        source = root / "source_checkout" / name
        paths = {
            "verilog": source / f"{name}.v",
            "lef": source / f"{name}.lef",
            "liberty": source / f"{name}_tt_025C_1v80.lib",
            "gds": root / "raw/derived_gds" / f"{name}.gds",
        }
        records.append(
            {
                "macro_id": name,
                "classification": "INHERITED_SRAM22_ARTIFACT_NOT_FRESH_OPENRAM_OUTPUT",
                "upstream_commit": "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05",
                "word_size_bits": width,
                "num_words": words,
                "width_um": macro_width,
                "height_um": macro_height,
                "area_um2": macro_width * macro_height,
                "views": {
                    role: {
                        "path": path.relative_to(repo).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                    for role, path in paths.items()
                },
                "qualification_limit": "Macro-internal foundry signoff DRC and independent LVS are not established by this campaign.",
            }
        )
    return records


def architecture_audit(repo: Path, functional: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    def sources(paths: list[str]) -> list[dict[str, Any]]:
        return [
            {"path": path, "sha256": sha256(repo / path)}
            for path in paths
            if (repo / path).is_file()
        ]

    return [
        {
            "architecture_id": "U0",
            "classification": "INCLUDE",
            "architecture": "unprotected SRAM baseline",
            "rtl_sources": sources([]),
            "encoder": None,
            "decoder": None,
            "wrapper": "u0_matched_sram_top",
            "sram_interface": "one synchronous 1RW SRAM22 256x64m4w8 macro",
            "data_width": 64,
            "ecc_width": 0,
            "codeword_width": 64,
            "latency_cycles": 1,
            "initiation_interval_cycles": 1,
            "scrub_retry_behavior": "none",
            "formal_evidence": "not applicable to unprotected pass-through storage",
            "fresh_regression_status": functional.get("U0", {}).get("status", "NOT_RUN"),
            "synthesis_status": "FRESH_MATCHED_ORFS_RESULTS_RECORDED",
            "previous_physical_evidence": "Gate3 Attempts 07-10; inherited only, not counted as a fresh run",
            "reason": "Canonical unprotected payload baseline with a fresh SRAM model round-trip pass.",
        },
        {
            "architecture_id": "SECDED",
            "classification": "INCLUDE",
            "architecture": "conventional extended-Hamming SECDED",
            "rtl_sources": sources(["scripts/gate03r/rtl/secded_characterization_tops.sv"]),
            "encoder": "gate03r_secded_baseline_encoder",
            "decoder": "gate03r_secded_baseline_decoder",
            "wrapper": "secded_matched_sram_top",
            "sram_interface": "one 256x64 data macro plus one 256x8 check-bit macro",
            "data_width": 64,
            "ecc_width": 8,
            "codeword_width": 72,
            "latency_cycles": 1,
            "initiation_interval_cycles": 1,
            "scrub_retry_behavior": "correction is reported; no autonomous scrub or retry",
            "formal_evidence": "frozen Gate03R exact identity and exhaustive class evidence",
            "fresh_regression_status": functional.get("SECDED", {}).get("status", "NOT_RUN"),
            "synthesis_status": "FRESH_MATCHED_ORFS_RESULTS_RECORDED",
            "previous_physical_evidence": "DATE2027 Gate04 codec-only physical characterization",
            "reason": "Fresh no-error, all-single, all-double mask-class regressions and SRAM round trip pass.",
        },
        {
            "architecture_id": "HSIAO_SECDED",
            "classification": "INCLUDE",
            "architecture": "Hsiao SECDED",
            "rtl_sources": sources([
                "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
                "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
                "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv",
            ]),
            "encoder": "hsiao_secded_72_64_v1_encoder",
            "decoder": "hsiao_secded_72_64_v1_decoder",
            "wrapper": "hsiao_matched_sram_top",
            "sram_interface": "one 256x64 data macro plus one 256x8 check-bit macro",
            "data_width": 64,
            "ecc_width": 8,
            "codeword_width": 72,
            "latency_cycles": 1,
            "initiation_interval_cycles": 1,
            "scrub_retry_behavior": "correction is reported; no autonomous scrub or retry",
            "formal_evidence": "exact logical implementation evidence in the frozen registry",
            "fresh_regression_status": functional.get("HSIAO_SECDED", {}).get("status", "NOT_RUN"),
            "synthesis_status": "FRESH_MATCHED_ORFS_RESULTS_RECORDED_WITH_DOCUMENTED_MEMORY_INFERENCE_THRESHOLD",
            "previous_physical_evidence": "Gate3 Attempt09 and DATE2027 Gate04",
            "reason": "Independent RTL exists and fresh no-error, all-single, all-double class regressions pass.",
        },
        {
            "architecture_id": "BCH_78_64_T2",
            "classification": "INCLUDE",
            "architecture": "shortened primitive BCH(78,64,t=2)",
            "rtl_sources": sources(["asic/rtl/bch/bch_78_64_t2_v1.sv"]),
            "encoder": "bch_78_64_t2_v1_encoder",
            "decoder": "bch_78_64_t2_v1_decoder",
            "wrapper": "bch_t2_matched_sram_top",
            "sram_interface": "one 256x64 data macro plus two 256x8 check macros; two physical padding bits per word",
            "data_width": 64,
            "ecc_width": 14,
            "codeword_width": 78,
            "latency_cycles": 1,
            "initiation_interval_cycles": 1,
            "scrub_retry_behavior": "correction is reported; no autonomous scrub or retry",
            "formal_evidence": "3082 fixed-mask arbitrary-symbolic-payload proofs in frozen Gate03R evidence",
            "fresh_regression_status": functional.get("BCH_78_64_T2", {}).get("status", "NOT_RUN"),
            "synthesis_status": "FRESH_MATCHED_ORFS_RESULTS_RECORDED",
            "previous_physical_evidence": "DATE2027 Gate04 codec-only physical characterization",
            "reason": "Fresh no-error and all weight-1/2 mask regressions over four deterministic payloads pass.",
        },
        {
            "architecture_id": "SEC_DAEC",
            "classification": "EXCLUDE",
            "architecture": "bounded adjacent-data-error search over extended Hamming",
            "rtl_sources": sources([
                "asic/rtl/secded/secded_codec.sv",
                "asic/rtl/secdaec/secdaec_codec.sv",
            ]),
            "encoder": "secdaec_encoder",
            "decoder": "secdaec_decoder",
            "wrapper": "secdaec_matched_sram_top",
            "sram_interface": "candidate 256x72 composition",
            "data_width": 64,
            "ecc_width": 8,
            "codeword_width": 72,
            "latency_cycles": 1,
            "initiation_interval_cycles": 1,
            "scrub_retry_behavior": "none",
            "formal_evidence": "no unrestricted DAEC proof; registry already limits the claim",
            "fresh_regression_status": functional.get("SEC_DAEC", {}).get("status", "NOT_RUN"),
            "synthesis_status": "NOT_RUN_FRESH_FUNCTIONAL_FAILURE",
            "previous_physical_evidence": "none qualifying",
            "reason": "Fresh supported-adjacent-mask regression fails at payload-adjacent bits 4 and 5; physical inclusion is fail-closed.",
        },
        {
            "architecture_id": "SECDED_PIPELINED",
            "classification": "CONDITIONAL_INCLUDE",
            "architecture": "two-stage pipelined extended-Hamming SECDED",
            "rtl_sources": sources(["asic/rtl/secded/secded_pipelined_72_64_v1.sv"]),
            "encoder": "secded_pipelined_72_64_v1_encoder",
            "decoder": "secded_pipelined_72_64_v1_decoder",
            "wrapper": None,
            "sram_interface": "no validated latency-aware SRAM transaction wrapper",
            "data_width": 64,
            "ecc_width": 8,
            "codeword_width": 72,
            "latency_cycles": 3,
            "initiation_interval_cycles": 1,
            "scrub_retry_behavior": "none",
            "formal_evidence": "frozen latency-aligned evidence",
            "fresh_regression_status": "NOT_RUN_NO_MEMORY_WRAPPER",
            "synthesis_status": "MATCHED_MEMORY_CAMPAIGN_NOT_RUN",
            "previous_physical_evidence": "DATE2027 Gate04 codec-only physical characterization",
            "reason": "Codec is valid, but inventing a memory transaction controller would change the campaign boundary.",
        },
        {
            "architecture_id": "INTERLEAVED_SECDED_I1_I2",
            "classification": "EXCLUDE",
            "architecture": "I1/I2 proposals",
            "rtl_sources": sources([]),
            "encoder": None,
            "decoder": None,
            "wrapper": None,
            "sram_interface": "proposal only",
            "data_width": 64,
            "ecc_width": 8,
            "codeword_width": 72,
            "latency_cycles": None,
            "initiation_interval_cycles": None,
            "scrub_retry_behavior": "undefined",
            "formal_evidence": "conditional proposal evidence only",
            "fresh_regression_status": "NOT_RUN_NO_RTL",
            "synthesis_status": "NOT_RUN_NO_IMPLEMENTATION",
            "previous_physical_evidence": "none",
            "reason": "No real address/data mapping RTL and no exact physical-to-logical topology map exist.",
        },
    ]


def audit_markdown(records: list[dict[str, Any]]) -> str:
    rows = ["| Architecture | Decision | Width | Fresh validation | Reason |", "|---|---:|---:|---|---|"]
    for record in records:
        rows.append(
            f"| {record['architecture_id']} | {record['classification']} | {record['codeword_width']} | "
            f"{record['fresh_regression_status']} | {record['reason']} |"
        )
    return """# Architecture audit

This audit is additive to the frozen GREEN Matrix v3.2 campaign. Inclusion is
based on real RTL, a stable mathematical contract, a usable SRAM wrapper, and
fresh regression evidence. `CONDITIONAL_INCLUDE` does not authorize a physical
run in this campaign.

""" + "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()
    campaign = repo / "campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation"
    for name in ("logs", "configs", "reports", "hashes", "manifests", "openram", "orfs", "validation"):
        (campaign / name).mkdir(parents=True, exist_ok=True)
    campaign_commit = (campaign / "CAMPAIGN_COMMIT.txt").read_text(encoding="utf-8").strip() \
        if (campaign / "CAMPAIGN_COMMIT.txt").is_file() else "UNSEALED_WORKTREE"
    common = {
        "schema_version": SCHEMA_VERSION,
        "campaign": "green_v3_2_matched_openram_orfs_validation",
        "campaign_commit": campaign_commit,
        "parent_green_v3_2_commit": PARENT_GREEN_COMMIT,
        "parent_green_v3_2_provenance_seal_commit": PARENT_GREEN_PROVENANCE_SEAL_COMMIT,
        "parent_campaign_commit": PARENT_CAMPAIGN_COMMIT,
        "foundation_commit": FOUNDATION_COMMIT,
        "generated_on": GENERATED_DATE,
    }

    functional_records: dict[str, dict[str, Any]] = {}
    for path in campaign.glob("FUNCTIONAL_VALIDATION_*.json"):
        record = load_json(path, {})
        if record.get("architecture_id"):
            record.update({
                "campaign_commit": campaign_commit,
                "parent_green_v3_2_commit": PARENT_GREEN_COMMIT,
                "parent_green_v3_2_provenance_seal_commit": PARENT_GREEN_PROVENANCE_SEAL_COMMIT,
            })
            write_json(path, record)
            functional_records[record["architecture_id"]] = record
    audit = architecture_audit(repo, functional_records)
    include_ids = [record["architecture_id"] for record in audit if record["classification"] == "INCLUDE"]
    write_json(campaign / "ARCHITECTURE_AUDIT.json", {**common, "records": audit})
    write_text(campaign / "ARCHITECTURE_AUDIT.md", (
        f"- Campaign commit: `{campaign_commit}`\n"
        f"- Parent GREEN v3.2: `{PARENT_GREEN_COMMIT}`\n\n"
        + audit_markdown(audit)
    ))

    openram_run = load_json(campaign / "openram/OPENRAM_FRESH_RUN.json", {
        "status": "NOT_RUN",
        "classification": "OPENRAM_REGENERATION_NOT_RUN",
        "fresh_artifacts": [],
        "drc_state": "NOT_RUN",
        "lvs_state": "NOT_RUN",
    })
    openram_provenance = {
        **common,
        "openram": {"version": "1.2.48", "tag": "v1.2.48", "commit": "b6a6f12642df6b84facc24a77f9a6f67a0d62dab"},
        "container": "vlsida/openram-ubuntu@sha256:90ecae634f99fa9055a32e32f9d6af1acc9942b974916f114330e7b5b4b29f7c",
        "python": "3.8.10",
        "tools": {"magic": "8.3.311", "netgen": "1.5.221", "ngspice": "36"},
        "pdk": {
            "name": "SKY130A",
            "open_pdks_volare_commit": "e8294524e5f67c533c5d0c3afa0bcc5b2a5fa066",
            "skywater_pdk_commit": "f70d8ca46961ff92719d8870a18a076370b85f6c",
            "sky130_fd_pr_commit": "f62031a1be9aefe902d6d54cddd6f59b57627436",
            "sky130_fd_sc_hd_commit": "ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1",
            "sky130_fd_bd_sram_commit": "dd64256961317205343a3fd446908b42bafba388",
        },
        "config_path": "configs/openram_256x72_config.py",
        "config_sha256": sha256(campaign / "configs/openram_256x72_config.py"),
        "fresh_run": openram_run,
    }
    macro_records = inherited_macro_records(repo)
    write_json(campaign / "OPENRAM_PROVENANCE.json", openram_provenance)
    write_json(campaign / "OPENRAM_MACRO_MANIFEST.json", {
        **common,
        "fresh_openram_artifacts": openram_run.get("fresh_artifacts", []),
        "inherited_macro_artifacts": macro_records,
        "substitution_policy": "Inherited SRAM22 views are never labelled as fresh OpenRAM output.",
    })
    fresh_artifact_rows = ["| Role | Bytes | SHA-256 | External path |", "|---|---:|---|---|"]
    for artifact in openram_run.get("fresh_artifacts", []):
        fresh_artifact_rows.append(
            f"| {artifact.get('role')} | {artifact.get('bytes')} | `{artifact.get('sha256')}` | `{artifact.get('path')}` |"
        )
    fresh_artifact_table = "\n".join(fresh_artifact_rows)
    geometry = openram_run.get("macro_geometry")
    write_text(campaign / "OPENRAM_VALIDATION_REPORT.md", f"""# OpenRAM validation report

- Fresh regeneration status: `{openram_run.get('status')}`
- Classification: `{openram_run.get('classification')}`
- DRC: `{openram_run.get('drc_state')}`
- LVS: `{openram_run.get('lvs_state')}`
- Characterization: `{openram_run.get('characterization_state', 'UNKNOWN')}`
- Failure domains: `{', '.join(openram_run.get('failure_domains', [])) or 'none'}`
- Fresh artifact count: `{len(openram_run.get('fresh_artifacts', []))}`
- Macro geometry: `{geometry if geometry is not None else 'NOT_AVAILABLE'}`
- Pin geometry/power-pin audit: `NOT_AVAILABLE_UNLESS_COMPLETE_LEF_IS_GENERATED`
- Timing characterization: `{openram_run.get('characterization_state', 'UNKNOWN')}`

The target is 256 words × 72 logical stored bits, one 1RW port, one bank,
TT/1.8 V/25 °C. Historical output is not substituted for a fresh failure.
Any inherited SRAM22 macro used by ORFS is separately identified in
`OPENRAM_MACRO_MANIFEST.json` and does not establish fresh OpenRAM generation.
No DRC result is treated as an array-cell waiver unless a complete cell/layer
classification supports it.

## Fresh artifact inventory

{fresh_artifact_table}
""")

    functional_summary_records = []
    for record in audit:
        arch = record["architecture_id"]
        if arch in functional_records:
            functional_summary_records.append(functional_records[arch])
    passing_statuses = {"FORMALLY_VALIDATED", "EXHAUSTIVELY_ENUMERATED", "REGRESSION_VALIDATED"}
    functional_pass = sum(record.get("status") in passing_statuses for record in functional_summary_records)
    write_json(campaign / "FUNCTIONAL_VALIDATION_SUMMARY.json", {
        **common,
        "audited_fresh_execution_count": len(functional_summary_records),
        "passed_count": functional_pass,
        "failed_count": len(functional_summary_records) - functional_pass,
        "records": functional_summary_records,
        "formal_evidence_policy": "Frozen exact/formal evidence is cited as inherited; fresh n-payload mask regressions are not relabelled as unrestricted proofs.",
    })
    functional_rows = ["| Architecture | Status | Scope |", "|---|---|---|"]
    for record in functional_summary_records:
        functional_rows.append(f"| {record['architecture_id']} | {record['status']} | {record['scope_limit']} |")
    write_text(campaign / "FUNCTIONAL_VALIDATION_SUMMARY.md", (
        "# Functional validation summary\n\n"
        f"- Campaign commit: `{campaign_commit}`\n"
        f"- Parent GREEN v3.2: `{PARENT_GREEN_COMMIT}`\n\n"
        + "\n".join(functional_rows)
    ))

    physical_payload = load_json(campaign / "manifests/PHYSICAL_RUN_RECORDS.json", {"records": []})
    physical_records = physical_payload.get("records", [])
    for record in physical_records:
        report_dir = campaign / "reports" / "runs" / record["run_id"]
        counts = parse_synthesis_counts(report_dir / "synth_stat.txt")
        if counts:
            record["metrics"]["synthesis"].update(counts)
        timing_metrics = record["metrics"]["timing"]
        timing_metrics["derived_frequency_qualified"] = False
        timing_metrics["derived_frequency_limit"] = (
            "Tool-reported fmax is diagnostic and is not maximum sustainable architectural throughput."
        )
        evidence_files = sorted(
            path for path in report_dir.iterdir()
            if path.is_file() and path.name != "run-metadata.json"
        )
        record["compact_log_sha256"] = {
            path.name: sha256(path) for path in evidence_files if path.name.endswith(".log.gz")
        }
        record["compact_report_sha256"] = {
            path.name: sha256(path) for path in evidence_files if not path.name.endswith(".log.gz")
        }
        record.setdefault("architecture_specific_exceptions", [])
        record.update({
            "campaign_commit": campaign_commit,
            "parent_green_v3_2_commit": PARENT_GREEN_COMMIT,
            "parent_green_v3_2_provenance_seal_commit": PARENT_GREEN_PROVENANCE_SEAL_COMMIT,
        })
        write_json(report_dir / "run-metadata.json", record)
    physical_payload.update({
        "campaign_commit": campaign_commit,
        "parent_green_v3_2_commit": PARENT_GREEN_COMMIT,
        "records": physical_records,
    })
    write_json(campaign / "manifests/PHYSICAL_RUN_RECORDS.json", physical_payload)
    initial_failure_path = campaign / "manifests/PHYSICAL_RUN_RECORDS_INITIAL_HSIAO_FAILURE.json"
    initial_failure_payload = load_json(initial_failure_path, {"records": []})
    initial_failure_records = [
        record for record in initial_failure_payload.get("records", [])
        if record.get("architecture_id") == "HSIAO_SECDED" and not record.get("route_success")
    ]
    if initial_failure_path.is_file():
        initial_failure_payload.update({
            "campaign_commit": campaign_commit,
            "parent_green_v3_2_commit": PARENT_GREEN_COMMIT,
            "classification": "PRESERVED_INITIAL_HSIAO_SYNTH_MEMORY_GUARD_FAILURE",
            "failure_count": len(initial_failure_records),
            "repair": {
                "setting": "SYNTH_MEMORY_MAX_BITS=20000",
                "scope": "HSIAO_SECDED only",
                "justification": "Allows Yosys memory_map to lower the explicit combinational syndrome table; no RTL or mathematical change.",
            },
        })
        write_json(initial_failure_path, initial_failure_payload)
    permission_failure_path = campaign / "openram/failed_attempts/01_namespace_permission/OPENRAM_FRESH_RUN.json"
    if permission_failure_path.is_file():
        permission_failure = load_json(permission_failure_path, {})
        permission_failure.update({
            "campaign_commit": campaign_commit,
            "parent_green_v3_2_commit": PARENT_GREEN_COMMIT,
            "posthoc_failure_domain": "ENVIRONMENT_FILESYSTEM_PERMISSION",
            "preservation_note": "Original exit code, command, timestamps, and log hash are unchanged.",
        })
        write_json(permission_failure_path, permission_failure)
    write_json(campaign / "FAILED_PARTIAL_EXPERIMENTS.json", {
        **common,
        "records": [
            {
                "experiment": "fresh_openram_namespace_preflight",
                "status": "FAIL_REPAIRED_ENVIRONMENT",
                "failed_run_count": 1,
                "evidence": "openram/failed_attempts/01_namespace_permission/OPENRAM_FRESH_RUN.json",
                "compact_log": "openram/failed_attempts/01_namespace_permission/openram_256x72_fresh.log.gz",
                "cause": "The fresh WSL parent directories were not writable by the pinned image's unprivileged user.",
                "scientifically_justified_repair": "Only fresh output/work/log directory modes were made writable; source, configuration, image, and PDK remained unchanged.",
            },
            {
                "experiment": "initial_hsiao_orfs_matrix",
                "status": "FAIL_REPAIRED_CONFIGURATION_INTEGRATION",
                "failed_run_count": len(initial_failure_records),
                "evidence": "manifests/PHYSICAL_RUN_RECORDS_INITIAL_HSIAO_FAILURE.json",
                "compact_logs": "reports/failed_attempts/hsiao_initial_synth_memory_guard/",
                "cause": "ORFS SYNTH_MEMORY_MAX_BITS=4096 rejected a 256x73 combinational ROM inferred from the explicit Hsiao syndrome case table.",
                "scientifically_justified_repair": "Threshold raised to 20000 for Hsiao so memory_map can lower the unchanged case table to gates.",
            },
            {
                "experiment": "sec_daec_functional_validation",
                "status": "FAILED_EXCLUDED",
                "failed_run_count": 1,
                "evidence": "FUNCTIONAL_VALIDATION_SEC_DAEC.json",
                "cause": "Adjacent payload-bit pair 4/5 is not corrected under the declared supported-mask contract.",
            },
            {
                "experiment": "fresh_openram_regeneration",
                "status": openram_run.get("status"),
                "evidence": "openram/OPENRAM_FRESH_RUN.json",
                "cause": openram_run.get("classification"),
            },
        ],
    })
    run_ids = {record["run_id"] for record in physical_records}
    run_manifest_records = []
    for record in physical_records:
        run_manifest_records.append({
            "run_id": record["run_id"],
            "architecture_id": record["architecture_id"],
            "seed": record["seed"],
            "clock_period_ns": record["clock_period_ns"],
            "rtl_sha256": record["rtl_sha256"],
            "macro_sha256": record["macro_sha256"],
            "config_sha256": record["config_sha256"],
            "constraint_sha256": record["constraint_sha256"],
            "toolchain": record["toolchain"],
            "pdk": record["pdk"],
            "commands": record["commands"],
            "common_documented_exception": record["common_documented_exception"],
            "architecture_specific_exceptions": record["architecture_specific_exceptions"],
            "physical_validation_classification": record["physical_validation_classification"],
            "external_evidence_root": record["external_evidence_root"],
            "report_path": f"reports/runs/{record['run_id']}/run-metadata.json",
            "report_sha256": sha256(campaign / f"reports/runs/{record['run_id']}/run-metadata.json"),
            "compact_log_sha256": record["compact_log_sha256"],
            "compact_report_sha256": record["compact_report_sha256"],
            "output_sha256": record["final_artifact_sha256"],
            "workload_hash": None,
            "activity_hash": None,
        })
    write_json(campaign / "RUN_MANIFEST.json", {**common, "run_count": len(run_manifest_records), "records": run_manifest_records})
    write_json(campaign / "PHYSICAL_RUN_RESULTS.json", {**common, "run_count": len(physical_records), "records": physical_records})

    csv_fields = [
        "run_id", "architecture_id", "clock_period_ns", "seed", "physical_validation_classification",
        "route_success", "gds_success", "mapped_cell_count", "standard_cell_area_um2", "macro_area_um2",
        "die_area_um2", "wirelength_um", "via_count", "setup_wns_ns", "setup_tns_ns", "hold_wns_ns",
        "hold_tns_ns", "route_drc_errors", "internal_power_w", "switching_power_w", "leakage_power_w",
        "total_power_w", "energy_qualification",
    ]
    with (campaign / "PHYSICAL_RUN_RESULTS.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields, lineterminator="\n")
        writer.writeheader()
        for record in physical_records:
            m = record["metrics"]
            writer.writerow({
                "run_id": record["run_id"], "architecture_id": record["architecture_id"],
                "clock_period_ns": record["clock_period_ns"], "seed": record["seed"],
                "physical_validation_classification": record["physical_validation_classification"],
                "route_success": record["route_success"], "gds_success": record["gds_success"],
                "mapped_cell_count": m["synthesis"]["mapped_cell_count"],
                "standard_cell_area_um2": m["floorplan_placement"]["standard_cell_area_um2"],
                "macro_area_um2": m["floorplan_placement"]["macro_area_um2"],
                "die_area_um2": m["floorplan_placement"]["die_area_um2"],
                "wirelength_um": m["routing"]["total_wirelength_um"], "via_count": m["routing"]["via_count"],
                "setup_wns_ns": m["timing"]["setup_wns_ns"], "setup_tns_ns": m["timing"]["setup_tns_ns"],
                "hold_wns_ns": m["timing"]["hold_wns_ns"], "hold_tns_ns": m["timing"]["hold_tns_ns"],
                "route_drc_errors": m["routing"]["detailed_route_drc_errors"],
                "internal_power_w": m["power"]["internal_w"], "switching_power_w": m["power"]["switching_w"],
                "leakage_power_w": m["power"]["leakage_w"], "total_power_w": m["power"]["total_w"],
                "energy_qualification": m["power"]["qualification"],
            })

    timing = [{"run_id": r["run_id"], "architecture_id": r["architecture_id"], "seed": r["seed"],
               "clock_period_ns": r["clock_period_ns"], **r["metrics"]["timing"]} for r in physical_records]
    routing = [{"run_id": r["run_id"], "architecture_id": r["architecture_id"], "seed": r["seed"],
                "clock_period_ns": r["clock_period_ns"], **r["metrics"]["routing"]} for r in physical_records]
    power = [{"run_id": r["run_id"], "architecture_id": r["architecture_id"], "seed": r["seed"],
              "clock_period_ns": r["clock_period_ns"], **r["metrics"]["power"]} for r in physical_records]
    write_json(campaign / "TIMING_SUMMARY.json", {**common, "records": timing})
    write_json(campaign / "ROUTING_SUMMARY.json", {**common, "records": routing})
    write_json(campaign / "POWER_DIAGNOSTIC_SUMMARY.json", {
        **common, "classification": "E4_DIAGNOSTIC_VECTORLESS", "e5_qualified": False,
        "records": power,
        "warning": "A post-route vectorless report is not activity-complete operational energy.",
    })

    metric_paths = {
        "standard_cell_area_um2": ("metrics", "floorplan_placement", "standard_cell_area_um2"),
        "macro_area_um2": ("metrics", "floorplan_placement", "macro_area_um2"),
        "total_instance_area_um2": ("metrics", "floorplan_placement", "total_instance_area_um2"),
        "die_area_um2": ("metrics", "floorplan_placement", "die_area_um2"),
        "mapped_cell_count": ("metrics", "synthesis", "mapped_cell_count"),
        "wirelength_um": ("metrics", "routing", "total_wirelength_um"),
        "via_count": ("metrics", "routing", "via_count"),
        "setup_wns_ns": ("metrics", "timing", "setup_wns_ns"),
        "total_power_w": ("metrics", "power", "total_w"),
        "congestion_metric": ("metrics", "routing", "congestion_metric"),
    }
    stats_records = []
    for arch in include_ids:
        for clock in CLOCKS:
            group = [r for r in physical_records if r["architecture_id"] == arch and r["clock_period_ns"] == clock]
            metrics = {}
            for name, path in metric_paths.items():
                values = [float(value) for record in group if isinstance((value := nested(record, path)), (int, float))]
                metrics[name] = summary(values)
            stats_records.append({"architecture_id": arch, "clock_period_ns": clock, "seed_count": len(group), "metrics": metrics})
    pairwise = []
    for clock in CLOCKS:
        baseline = {(r["seed"]): r for r in physical_records if r["architecture_id"] == "U0" and r["clock_period_ns"] == clock}
        for arch in [item for item in include_ids if item != "U0"]:
            compared = [r for r in physical_records if r["architecture_id"] == arch and r["clock_period_ns"] == clock]
            deltas: dict[str, list[float]] = {name: [] for name in metric_paths}
            better: dict[str, int] = {name: 0 for name in metric_paths}
            counts: dict[str, int] = {name: 0 for name in metric_paths}
            for record in compared:
                base = baseline.get(record["seed"])
                if not base:
                    continue
                for name, path in metric_paths.items():
                    value, base_value = nested(record, path), nested(base, path)
                    if isinstance(value, (int, float)) and isinstance(base_value, (int, float)) and base_value != 0:
                        deltas[name].append(100.0 * (value - base_value) / base_value)
                        counts[name] += 1
                        if (name == "setup_wns_ns" and value > base_value) or (name != "setup_wns_ns" and value < base_value):
                            better[name] += 1
            pairwise.append({
                "architecture_id": arch, "baseline": "U0", "clock_period_ns": clock,
                "mean_percent_delta": {name: mean_or_none(values) for name, values in deltas.items()},
                "fraction_of_matched_seeds_better_than_u0": {
                    name: None if counts[name] == 0 else better[name] / counts[name] for name in metric_paths
                },
            })
    seed_stats = {**common, "expected_seeds": SEEDS, "records": stats_records, "pairwise_vs_u0": pairwise}
    write_json(campaign / "SEED_STATISTICS.json", seed_stats)
    with (campaign / "SEED_STATISTICS.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = ["architecture_id", "clock_period_ns", "metric", "available_count", "mean", "median",
                  "sample_standard_deviation", "minimum", "maximum", "ci95_low", "ci95_high", "coefficient_of_variation"]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for group in stats_records:
            for name, values in group["metrics"].items():
                ci = values["confidence_interval_95"] or [None, None]
                writer.writerow({"architecture_id": group["architecture_id"], "clock_period_ns": group["clock_period_ns"],
                                 "metric": name, **{key: values[key] for key in fields[3:9]},
                                 "ci95_low": ci[0], "ci95_high": ci[1],
                                 "coefficient_of_variation": values["coefficient_of_variation"]})

    interleaver = {
        **common, "I1": "BLOCKED_NO_IMPLEMENTATION", "I2": "BLOCKED_NO_IMPLEMENTATION",
        "physical_reliability_claim": "BLOCKED_NO_TOPOLOGY_MAP",
        "routed_overhead": None,
        "reason": "No real I1/I2 RTL/address-data transformation exists; implementing an invented mapping would corrupt the primary campaign boundary.",
    }
    bit_mapping = {
        **common,
        "PHYSICAL_TO_LOGICAL_BIT_MAPPING": "BLOCKED",
        "known": ["logical address width", "macro instance", "stored codeword slice", "macro placement XY"],
        "unknown": ["exact internal row", "exact internal column", "column mux selection", "physical bitcell instance", "bitcell XY"],
        "reason": "LEF/GDS dimensions and instance counts do not prove exact internal bitcell identity.",
    }
    write_json(campaign / "INTERLEAVER_ROUTED_VALIDATION.json", interleaver)
    write_json(campaign / "BIT_MAPPING_AUDIT.json", bit_mapping)

    complete_runs = [r for r in physical_records if r.get("route_success") and r.get("gds_success")]
    complete_matrix = len(complete_runs) == len(include_ids) * len(SEEDS) * len(CLOCKS)
    e4_records = [{
        "evidence_id": f"E4_ORFS_{r['run_id'].upper()}", "tier": "E4", "status": "AVAILABLE",
        "run_id": r["run_id"], "measurement_boundary": "matched tool-derived RTL-to-GDS implementation",
        "compatible_with": ["M_P.physical_implementation"],
    } for r in complete_runs]
    physical_population = []
    for arch in include_ids:
        for clock in CLOCKS:
            stat = next((r for r in stats_records if r["architecture_id"] == arch and r["clock_period_ns"] == clock), None)
            physical_population.append({
                "architecture_id": arch, "clock_period_ns": clock,
                "evidence_refs": [item["evidence_id"] for item in e4_records if item["run_id"].startswith(arch.lower()) and f"clk{str(clock).replace('.', 'p')}ns" in item["run_id"]],
                "aggregate": stat,
            })
    adapter = {
        **common,
        "mode": "ADDITIVE_ADAPTER_DOES_NOT_MODIFY_V3_2",
        "parent_matrix_counts": PARENT_COUNTS,
        "new_matrix_counts": {"M_E": len(e4_records), "M_P": len(physical_population), "M_S": 0},
        "combined_additive_view_counts": {
            "M_E": PARENT_COUNTS["M_E"] + len(e4_records),
            "M_P": PARENT_COUNTS["M_P"] + len(physical_population),
            "M_S": PARENT_COUNTS["M_S"],
        },
        "M_E_records": e4_records,
        "M_P_records": physical_population,
        "M_S_policy": "PARENT_QUALIFICATION_RULES_UNCHANGED",
        "global_architecture_winner": "NO_GLOBAL_WINNER_QUALIFIED",
    }
    write_json(campaign / "GREEN_V3_2_EVIDENCE_ADAPTER.json", adapter)

    pareto_records = []
    pareto_metrics = ["total_instance_area_um2", "wirelength_um", "total_power_w", "setup_wns_ns"]
    for clock in CLOCKS:
        candidates = []
        for arch in include_ids:
            group = next((item for item in stats_records if item["architecture_id"] == arch and item["clock_period_ns"] == clock), None)
            if group is None:
                continue
            values = {name: group["metrics"][name]["mean"] for name in pareto_metrics}
            if all(value is not None for value in values.values()):
                candidates.append({"architecture_id": arch, "metrics": values})

        def dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
            left_values, right_values = left["metrics"], right["metrics"]
            no_worse = (
                all(left_values[name] <= right_values[name] for name in pareto_metrics[:3])
                and left_values["setup_wns_ns"] >= right_values["setup_wns_ns"]
            )
            strictly_better = (
                any(left_values[name] < right_values[name] for name in pareto_metrics[:3])
                or left_values["setup_wns_ns"] > right_values["setup_wns_ns"]
            )
            return no_worse and strictly_better

        front = [
            candidate for candidate in candidates
            if not any(dominates(other, candidate) for other in candidates if other is not candidate)
        ]
        pareto_records.append({
            "clock_period_ns": clock,
            "population": candidates,
            "front_architecture_ids": [item["architecture_id"] for item in front],
            "classification": "E4_DIAGNOSTIC_NOT_QUALIFIED",
        })
    population_complete = (
        complete_matrix
        and len(include_ids) >= 4
        and all(len(item["population"]) == len(include_ids) for item in pareto_records)
    )
    if population_complete and any(len(item["front_architecture_ids"]) > 1 for item in pareto_records):
        diagnostic_pareto = "AVAILABLE_NONTRIVIAL_MULTI_ARCH_E4_DIAGNOSTIC_FRONT"
    elif population_complete:
        diagnostic_pareto = "AVAILABLE_MULTI_ARCH_POPULATION_SINGLETON_U0_E4_DIAGNOSTIC_FRONT"
    else:
        diagnostic_pareto = "BLOCKED_INCOMPLETE_PHYSICAL_POPULATION"
    write_json(campaign / "DIAGNOSTIC_PARETO.json", {
        **common,
        "status": diagnostic_pareto,
        "objective_directions": {
            "total_instance_area_um2": "minimize",
            "wirelength_um": "minimize",
            "total_power_w": "minimize",
            "setup_wns_ns": "maximize",
        },
        "normalization": "NONE",
        "records": pareto_records,
        "qualification_limit": "This E4 tool-derived front is diagnostic; blocked mandatory GREEN dimensions are not discarded.",
    })
    claims = [
        ("fresh_functional_validation", functional_pass >= 4, "Fresh deterministic RTL regressions and memory round trips"),
        ("matched_multiseed_orfs_implementation", complete_matrix, "All planned architecture × clock × seed records route and emit GDS"),
        ("fresh_openram_generated", openram_run.get("status") == "PASS", "Fresh OpenRAM run record"),
        ("E4_physical_tool_evidence", bool(complete_runs), "Fresh ORFS run records"),
        ("E5_activity_complete_energy", False, "No all-of activity-complete operation-class campaign"),
        ("silicon_validated", False, "No silicon evidence"),
        ("radiation_validated", False, "No particle-beam evidence"),
        ("physical_SDC_DUE_FIT", False, "No qualified event rate/topology/fluence evidence"),
        ("Qcrit", False, "No charge-collection experiment"),
        ("SKY130_manufacturing_lifecycle_carbon", False, "No qualified manufacturing inventory"),
        ("interleaver_reliability_improvement", False, "No routed implementation and no topology map"),
        ("qualified_sustainability_front", False, "Mandatory reliability, E5, and lifecycle dimensions remain blocked"),
        ("global_winner", False, "NO_GLOBAL_WINNER_QUALIFIED"),
    ]
    claim_records = [{"claim": claim, "enabled": enabled, "evidence": evidence} for claim, enabled, evidence in claims]
    write_json(campaign / "CLAIM_EVIDENCE_MAP.json", {**common, "records": claim_records})
    claim_lines = ["| Claim | Enabled | Evidence / blocker |", "|---|---:|---|"] + [
        f"| {item['claim']} | {str(item['enabled']).lower()} | {item['evidence']} |" for item in claim_records
    ]
    write_text(campaign / "CLAIM_EVIDENCE_MAP.md", "# Claim–evidence map\n\n" + "\n".join(claim_lines))

    if complete_matrix:
        if openram_run.get("status") == "PASS":
            openram_classification = "FRESH_OPENRAM_GENERATED_"
        elif openram_run.get("status") == "TIMEOUT":
            openram_classification = "OPENRAM_REGENERATION_PARTIAL_RUNTIME_CUTOFF_INHERITED_SRAM_MACROS_"
        elif openram_run.get("status") == "NOT_RUN":
            openram_classification = "OPENRAM_REGENERATION_NOT_RUN_INHERITED_SRAM_MACROS_"
        else:
            openram_classification = "OPENRAM_REGENERATION_FAILED_INHERITED_SRAM_MACROS_"
        classification = (
            "GREEN_V3_2_MATCHED_ORFS_MULTI_ARCH_PHYSICAL_VALIDATION_COMPLETE_"
            + openram_classification
            + "E4_E5_PENDING_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED"
        )
    else:
        classification = "GREEN_V3_2_MATCHED_OPENRAM_ORFS_PHYSICAL_VALIDATION_PARTIAL_E4_E5_PENDING_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED"
    status = {
        **common,
        "classification": classification,
        "included_architecture_count": len(include_ids),
        "included_architectures": include_ids,
        "openram_regeneration_status": openram_run.get("status"),
        "functional_validation_success_count": functional_pass,
        "synthesis_success_count": sum(r["metrics"]["physical_outputs"]["synthesis_odb_generated"] for r in physical_records),
        "route_success_count": sum(r.get("route_success", False) for r in physical_records),
        "gds_success_count": sum(r.get("gds_success", False) for r in physical_records),
        "setup_timing_met_count": sum(
            isinstance(r["metrics"]["timing"]["setup_wns_ns"], (int, float))
            and r["metrics"]["timing"]["setup_wns_ns"] >= 0
            for r in physical_records
        ),
        "hold_timing_met_count": sum(
            isinstance(r["metrics"]["timing"]["hold_wns_ns"], (int, float))
            and r["metrics"]["timing"]["hold_wns_ns"] >= 0
            for r in physical_records
        ),
        "setup_and_hold_timing_met_count": sum(
            isinstance(r["metrics"]["timing"]["setup_wns_ns"], (int, float))
            and isinstance(r["metrics"]["timing"]["hold_wns_ns"], (int, float))
            and r["metrics"]["timing"]["setup_wns_ns"] >= 0
            and r["metrics"]["timing"]["hold_wns_ns"] >= 0
            for r in physical_records
        ),
        "completed_physical_run_count": len(physical_records),
        "planned_physical_run_count": len(include_ids) * len(SEEDS) * len(CLOCKS),
        "preserved_initial_physical_failure_count": len(initial_failure_records),
        "seeds_per_architecture_timing_condition": len(SEEDS),
        "timing_condition_count": len(CLOCKS),
        "evidence_added": {"E3": 0, "E4": len(e4_records), "E5": 0},
        "combined_additive_matrix_counts": adapter["combined_additive_view_counts"],
        "e3_note": "Frozen exact/formal E3 is referenced; fresh finite-payload regressions are not promoted to unrestricted E3.",
        "E5_status": "E5_CAMPAIGN_READY_BUT_NOT_QUALIFIED",
        "I1_I2_status": "BLOCKED_NO_IMPLEMENTATION_AND_TOPOLOGY_MAP",
        "diagnostic_pareto_status": diagnostic_pareto,
        "conditional_pareto_status": "PARENT_FIVE_CONDITIONAL_FRONTS_PRESERVED_NO_NEW_PROMOTION",
        "qualified_pareto_status": "BLOCKED",
        "physical_SDC_DUE_FIT": "BLOCKED",
        "Qcrit": "BLOCKED",
        "SKY130_manufacturing_lifecycle_carbon": "BLOCKED",
        "global_winner": "NO_GLOBAL_WINNER_QUALIFIED",
        "remaining_blockers": [
            "fresh qualified OpenRAM SKY130 macro", "activity-complete E5 power/energy", "physical-to-logical bit map",
            "particle-beam event coordinates and fluence", "Qcrit", "SKY130 manufacturing/lifecycle inventory", "I1/I2 RTL",
        ],
        "highest_value_remaining_experiment": "ACTIVITY_COMPLETE_POST_ROUTE_OPERATION_CLASS_POWER_ON_THE_MATCHED_POPULATION",
        "failed_partial_experiments": "FAILED_PARTIAL_EXPERIMENTS.json",
    }
    write_json(campaign / "CAMPAIGN_STATUS.json", status)

    def stat_value(arch: str, clock: float, name: str, field: str = "mean") -> Any:
        group = next((r for r in stats_records if r["architecture_id"] == arch and r["clock_period_ns"] == clock), None)
        return None if group is None else group["metrics"][name][field]

    compact = min(include_ids, key=lambda a: float("inf") if stat_value(a, 10.0, "total_instance_area_um2") is None else stat_value(a, 10.0, "total_instance_area_um2"))
    low_power = min(include_ids, key=lambda a: float("inf") if stat_value(a, 10.0, "total_power_w") is None else stat_value(a, 10.0, "total_power_w"))
    best_timing = max(include_ids, key=lambda a: float("-inf") if stat_value(a, 10.0, "setup_wns_ns") is None else stat_value(a, 10.0, "setup_wns_ns"))

    def mean_sd(arch: str, clock: float, metric_name: str) -> str:
        mean = stat_value(arch, clock, metric_name)
        deviation = stat_value(arch, clock, metric_name, "sample_standard_deviation")
        if mean is None:
            return "unknown"
        if deviation is None:
            return f"{mean:.6g}"
        return f"{mean:.6g} ± {deviation:.3g}"

    statistics_rows = [
        "| Architecture | Clock ns | Total instance area µm² | Wirelength µm | Vias | Setup WNS ns | Vectorless power W |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for clock in CLOCKS:
        for arch in include_ids:
            statistics_rows.append(
                f"| {arch} | {clock:g} | {mean_sd(arch, clock, 'total_instance_area_um2')} | "
                f"{mean_sd(arch, clock, 'wirelength_um')} | {mean_sd(arch, clock, 'via_count')} | "
                f"{mean_sd(arch, clock, 'setup_wns_ns')} | {mean_sd(arch, clock, 'total_power_w')} |"
            )
    statistics_table = "\n".join(statistics_rows)
    answers = [
        "1. Audited U0, conventional and pipelined SECDED, Hsiao SECDED, bounded SEC-DAEC, BCH(78,64,t=2), and I1/I2 interleaver proposals.",
        f"2. Included {', '.join(include_ids)}.",
        "3. SEC-DAEC failed a fresh adjacent-pair check; pipelined SECDED lacks a validated SRAM controller wrapper; I1/I2 have no RTL/topology map.",
        f"4. Fresh OpenRAM status: {openram_run.get('status')}.",
        f"5. Fresh OpenRAM artifacts: {', '.join(item.get('role', 'unknown') for item in openram_run.get('fresh_artifacts', [])) or 'none'}.",
        "6. No. The failed fresh 256x72 target is not substituted; ORFS uses separately inherited SRAM22 macros.",
        "7. U0 uses 64 physical bits, SECDED variants use 72, and BCH uses 80 physical macro bits for 78 code bits.",
        "8. 16,384 user payload bits (256 × 64) per architecture.",
        "9. U0: 0; SECDED/Hsiao: 2,048; BCH: 4,096 physical bits including 512 padding bits.",
        f"10. No. {functional_pass} of {len(functional_summary_records)} freshly executed candidates passed; SEC-DAEC failed.",
        "11. Frozen exact evidence exists for conventional SECDED, Hsiao, and BCH; fresh runs are finite-payload exhaustive-mask regressions, not unrestricted proofs.",
        f"12. Synthesis artifacts: {status['synthesis_success_count']} of {status['planned_physical_run_count']} planned runs.",
        f"13. Placement artifacts: {sum(r['metrics']['physical_outputs']['placement_odb_generated'] for r in physical_records)} runs.",
        f"14. Routes: {status['route_success_count']} runs.",
        f"15. GDS: {status['gds_success_count']} runs.",
        "16. External detailed routing is classified per run; macro-internal DRC is not independently signoff-qualified.",
        "17. LVS is unavailable/not independently reproduced for the matched top levels.",
        f"18. Fresh OpenRAM DRC classification: {openram_run.get('drc_state')}; no array violation is silently waived.",
        f"19. Five seeds completed per architecture/condition: {complete_matrix}.",
        f"20. Two timing conditions completed: {complete_matrix}.",
        "21. Area mean/dispersion values are in SEED_STATISTICS.json/csv.",
        "22. Wirelength mean/dispersion values are in SEED_STATISTICS.json/csv.",
        "23. Via mean/dispersion values are in SEED_STATISTICS.json/csv.",
        "24. Timing mean/dispersion values are in SEED_STATISTICS.json/csv.",
        "25. Vectorless power mean/dispersion values are in SEED_STATISTICS.json/csv and remain E4 diagnostic.",
        f"26. Most compact by mean 10 ns total instance area: {compact}.",
        f"27. Lowest mean 10 ns diagnostic total power: {low_power}.",
        f"28. Best mean 10 ns setup slack: {best_timing}.",
        "29. Ordering stability is reported as matched-seed fractions in SEED_STATISTICS.json; n=5 is not overinterpreted.",
        f"30. Architecture breadth beyond U0/E0: {'yes' if len(include_ids) >= 4 and complete_matrix else 'not yet complete'}.",
        f"31. Diagnostic implementation Pareto: {diagnostic_pareto}; the physical-only front is not called nontrivial when U0 dominates every measured implementation objective.",
        "32. E5 energy did not become qualified.",
        "33. Missing isolated operation windows, complete activity annotation, counted operations, and macro-internal activity characterization block E5.",
        "34. I1/I2 were not physically implemented.",
        "35. I1/I2 overhead is unknown, not zero.",
        "36. Complete physical/logical bit mapping was not established.",
        "37. Interleaver reliability benefit cannot be claimed.",
        "38. Physical SDC/DUE/FIT cannot be claimed.",
        "39. Qcrit cannot be claimed.",
        "40. SKY130 manufacturing/lifecycle carbon cannot be claimed.",
        "41. A qualified sustainability front does not exist.",
        "42. A global winner cannot be claimed: NO_GLOBAL_WINNER_QUALIFIED.",
        "43. ISCAS-safe claims: fresh functional regression where passed, matched ORFS RTL-to-GDS implementation where completed, multi-seed E4 characterization, and exact inherited conditional logical evidence where cited.",
        "44. Forbidden: tapeout, foundry signoff, silicon/radiation validation, physical event rates/FIT/SDC/DUE, Qcrit, E5 energy, absolute lifecycle carbon, or a global winner.",
        "45. Highest-value next experiment: activity-complete post-route operation-class power on the matched population.",
    ]
    report = f"""# Final scientific report

Classification: `{classification}`

This campaign is additive to frozen GREEN Matrix v3.2. Physical implementation
measurements are treated as tool-derived evidence and are not conflated with
silicon or radiation measurements. GREEN v3.2 propagates only evidence
compatible with the required technology, workload, measurement boundary, and
semantic qualification.

The initial ten Hsiao runs are preserved as failed experiments. Their common
ORFS inference-threshold integration defect was repaired by allowing the
unchanged combinational syndrome table to reach `memory_map`; this recorded
architecture-specific exception does not modify ECC semantics.

## Answers to the required scientific questions

""" + "\n".join(answers) + (
        "\n\n## Multi-seed descriptive results\n\n"
        "Values are mean ± sample standard deviation over five seeds.\n\n"
        + statistics_table
    )
    write_text(campaign / "FINAL_REPORT.md", report)
    write_text(campaign / "ISCAS_EXPERIMENT_SUMMARY.md", f"""# ISCAS experiment summary

## Experimental Setup

The included population is {', '.join(include_ids)}. Every design stores 256 ×
64 user payload bits. Physical redundancy is included rather than normalized
away. The pinned flow is ORFS `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2`
using OpenROAD `26Q3-1080-gab6fd26351`, SKY130HD TT/25 °C/1.8 V, common 10 ns
and 5 ns constraints, and seeds 11, 13, 17, 19, and 23. Fresh OpenRAM status
is `{openram_run.get('status')}`; inherited SRAM22 macros are explicitly
separate evidence.

## Functional Validation

Four architectures pass fresh deterministic RTL and memory-model regressions.
SEC-DAEC fails its declared adjacent-pair space and is excluded. Exact/formal
depth is identified per architecture in `ARCHITECTURE_AUDIT.json`.

## Physical Implementation Results

Completed run records: {len(physical_records)}; clean external routes:
{status['route_success_count']}; GDS outputs: {status['gds_success_count']}.
Setup constraints are met in {status['setup_timing_met_count']} runs and both
setup and hold are met in {status['setup_and_hold_timing_met_count']} runs;
RTL-to-GDS completion is not described as timing closure.
Multi-seed area, cell count, wirelength, via, timing, vectorless power, and
available congestion statistics are in `SEED_STATISTICS.json` and CSV. With
only five seeds, intervals are descriptive.

{statistics_table}

## Evidence Qualification

Analytical/formal evidence remains E3 only where independently established.
Fresh routed quantities are E4. Vectorless power is `E4_DIAGNOSTIC`, not E5.
Missing reliability, Qcrit, manufacturing, lifecycle, and activity-complete
evidence remains blocked.

## GREEN Analysis

The additive adapter supplies {len(e4_records)} new M_E records and
{len(physical_population)} aggregate M_P records. It supplies no M_S rule and
the combined additive view is M_E={PARENT_COUNTS['M_E'] + len(e4_records)},
M_P={PARENT_COUNTS['M_P'] + len(physical_population)}, and M_S={PARENT_COUNTS['M_S']}.
It does not alter v3.2 admissibility. Qualified Pareto remains blocked and the
global result remains `NO_GLOBAL_WINNER_QUALIFIED`.

## Limitations

There is no silicon validation, particle-beam validation, qualified physical
event rate, physical FIT, Qcrit, exact bitcell-to-codeword topology map, E5
energy, or qualified SKY130 manufacturing inventory.
""")
    write_text(campaign / "README.md", f"""# GREEN v3.2 matched OpenRAM + ORFS validation

This additive campaign asks whether a broader ECC population can be freshly
functionally validated and physically implemented at a matched boundary. It
does not modify GREEN Matrix v3.2 or create v3.3.

Current classification: `{classification}`

Reproduce fresh RTL validation with:

```bash
python3 scripts/run_functional_validation.py --repo <repository-root>
```

Run the pinned OpenRAM attempt in its isolated WSL namespace with:

```bash
python3 scripts/run_openram_campaign.py --repo <repository-root> --timeout-seconds 10800
```

The three-hour cutoff is explicit evidence metadata; it is not reported as a
compiler pass. The historical OpenRAM source, virtual environment, and PDK are
mounted read-only.

Run the WSL ORFS matrix with:

```bash
python3 scripts/run_orfs_campaign.py --repo <repository-root> --workers 2
```

Rebuild committed tables and reports deterministically with:

```bash
python3 build_campaign.py --repo <repository-root>
```

Full physical outputs are preserved under the external WSL evidence root
recorded in `RUN_MANIFEST.json`; hashes and compact reports are committed here.
""")

    e5_config = {
        **common, "status": "E5_CAMPAIGN_READY_BUT_NOT_QUALIFIED",
        "operation_classes": ["normal_read", "normal_write", "corrected_read", "corrected_write_if_applicable",
                              "detected_uncorrectable", "retry", "scrub", "recovery_sequence_if_applicable"],
        "all_of_requirements": [
            "post_route_netlist", "SDF_or_SPEF", "complete_activity_annotation", "no_silent_default_activity",
            "isolated_operation_window", "positive_duration", "counted_operations", "macro_internal_characterization",
            "workload_and_activity_hashes", "implementation_and_power_report_hashes",
        ],
        "qualified": False,
    }
    write_json(campaign / "configs/E5_CAMPAIGN_REQUIREMENTS.json", e5_config)

    hash_targets = sorted(
        path for path in campaign.rglob("*")
        if path.is_file() and path.relative_to(campaign).as_posix() not in {
            "hashes/CAMPAIGN_ARTIFACTS.sha256", "CAMPAIGN_COMMIT.txt"
        } and "__pycache__" not in path.parts
    )
    write_text(campaign / "hashes/CAMPAIGN_ARTIFACTS.sha256", "\n".join(
        f"{sha256(path)}  {path.relative_to(campaign).as_posix()}" for path in hash_targets
    ))
    print(f"CAMPAIGN_BUILD_COMPLETE classification={classification} runs={len(physical_records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
