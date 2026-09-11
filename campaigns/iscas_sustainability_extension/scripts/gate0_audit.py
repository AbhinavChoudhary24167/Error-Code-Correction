#!/usr/bin/env python3
"""Reconstruct and protect the immutable DATE baseline for Gate 0.

This script is deliberately read-only with respect to every prior campaign.  It
creates files only below ``campaigns/iscas_sustainability_extension`` and can
later verify the protected repository and external evidence trees.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent
REPO = CAMPAIGN.parents[1]
DEFAULT_BASELINE_COMMIT = "9968f9b15f949d38faf944a3546ea736cfab63df"
PHYSICAL_EVIDENCE_COMMIT = "b51291442bbd04346dac939dea6ba7d532b9c5c4"
EXTERNAL_ROOTS = {
    "date2027_revision2_raw": Path("/var/lib/green-ecc-date2027-revision2"),
    "date2027_breadth_raw": Path("/var/lib/green-ecc-date2027-breadth-remediation"),
}

REV2_RUNS = REPO / "docs/date2027/revision2/results/REV2_RUN_RESULTS.csv"
REV2_EFFECTS = REPO / "docs/date2027/revision2/results/REV2_SECDED_PAIRED_SEED_EFFECTS.json"
A_RUNS = CAMPAIGN.parent / "date_2027_breadth_remediation/analysis/A_structural_pair_per_seed.csv"
B_RUNS = CAMPAIGN.parent / "date_2027_breadth_remediation/analysis/B_power_components_per_seed.csv"
C_RUNS = CAMPAIGN.parent / "date_2027_breadth_remediation/analysis/C_5ns_per_seed.csv"
A_SUMMARY = CAMPAIGN.parent / "date_2027_breadth_remediation/analysis/A_structural_pair_summary.json"
B_SUMMARY = CAMPAIGN.parent / "date_2027_breadth_remediation/analysis/B_power_components_summary.json"
C_SUMMARY = CAMPAIGN.parent / "date_2027_breadth_remediation/analysis/C_5ns_summary.json"
TRACE_MANIFEST = REPO / "docs/date2027/rigour_gate_03f/ACTIVITY_TRACE_MANIFEST.json"


IDENTITIES = {
    "secded_comb": {
        "code_id": "extended-hamming-secded-72-64-v1",
        "guarantee": "all W1 corrected; all W2 detected",
        "sources": [
            "scripts/gate03r/rtl/secded_characterization_tops.sv",
            "scripts/gate04/rtl/gate04_boundaries.sv",
        ],
        "formal": [
            "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json",
            "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md",
        ],
        "trace_family": "conventional_secded",
    },
    "secded_pipe": {
        "code_id": "extended-hamming-secded-72-64-v1",
        "guarantee": "all W1 corrected; all W2 detected",
        "sources": [
            "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
            "scripts/gate03r/rtl/secded_characterization_tops.sv",
            "scripts/gate04/rtl/gate04_boundaries.sv",
        ],
        "formal": [
            "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json",
            "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md",
        ],
        "trace_family": "conventional_secded",
    },
    "hsiao_algorithmic": {
        "code_id": "hsiao-secded-72-64-v1",
        "guarantee": "all W1 corrected; all W2 detected",
        "sources": [
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv",
            "scripts/revision2/rtl/rev2_hsiao_boundary.sv",
        ],
        "formal": [
            "docs/date2027/revision2/REV2_HSIAO_QUALIFICATION.json",
            "docs/date2027/revision2/REV2_HSIAO_EXACT_IDENTITY.log",
        ],
        "trace_family": "hsiao",
    },
    "bch78": {
        "code_id": "shortened-bch-78-64-t2-v1",
        "guarantee": "all W0/W1/W2 corrected; W3 characterized without guarantee",
        "sources": [
            "asic/rtl/bch/bch_78_64_t2_v1.sv",
            "scripts/gate04/rtl/gate04_boundaries.sv",
        ],
        "formal": [
            "docs/date2027/rigour_gate_03r/EXACT_PROOF_SUMMARY.json",
            "docs/date2027/rigour_gate_03r/FORMAL_PROOF_INDEX.csv",
            "docs/date2027/rigour_gate_03r/BCH_78_64_T2_CONTRACT.md",
        ],
        "trace_family": "bch78",
    },
    "A_hsiao_flat": {
        "alias": "hsiao_algorithmic",
    },
    "A_hsiao_hierarchical": {
        "code_id": "hsiao-secded-72-64-v1",
        "guarantee": "all W1 corrected; all W2 detected",
        "sources": [
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
            "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
            "campaigns/date_2027_breadth_remediation/rtl/hsiao_secded_72_64_v3_hierarchical_decoder.sv",
            "campaigns/date_2027_breadth_remediation/rtl/breadth_hsiao_hierarchical_boundary.sv",
        ],
        "formal": [
            "campaigns/date_2027_breadth_remediation/formal/results/A_formal_qualification.json",
            "campaigns/date_2027_breadth_remediation/formal/results/A_decoder_exact_equivalence.log",
            "campaigns/date_2027_breadth_remediation/formal/results/A_boundary_exact_equivalence.log",
        ],
        "trace_family": "hsiao",
    },
    "C_secded_comb": {"alias": "secded_comb"},
    "C_secded_pipe": {"alias": "secded_pipe"},
}


RESULT_FIELDS = [
    "campaign",
    "run_id",
    "architecture",
    "implementation_id",
    "code_id",
    "protection_guarantee",
    "rtl_sha256",
    "rtl_sources_json",
    "formal_status",
    "formal_evidence",
    "physical_target",
    "technology",
    "corner",
    "voltage_v",
    "temperature_c",
    "seed",
    "clock_period_ns",
    "latency_cycles",
    "initiation_interval_cycles",
    "activity_class",
    "useful_operations",
    "trace_sha256",
    "activity_power_status",
    "routing_complete",
    "target_feasible",
    "characterization_status",
    "hold_status",
    "setup_violation_count",
    "standard_cell_instance_area_um2",
    "cell_count",
    "sequential_cell_count",
    "signed_worst_setup_slack_ns",
    "slack_derived_frequency_mhz",
    "detailed_route_wirelength_um",
    "via_count",
    "internal_power_w",
    "switching_power_w",
    "leakage_power_w",
    "total_power_w",
    "energy_per_useful_op_pj",
    "final_odb_sha256",
    "final_netlist_sha256",
    "final_sdc_sha256",
    "final_spef_sha256",
    "power_report_sha256",
    "raw_artifacts_manifest_sha256",
    "raw_artifact_root",
    "source_record",
]


def run(command: list[str], *, cwd: Path = REPO) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_hash(items: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path, value in sorted(items.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_load(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def clean(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str) and value.strip().lower() in {"", "none", "null"}:
        return ""
    return value


def identity(key: str) -> dict[str, Any]:
    record = IDENTITIES[key]
    if "alias" in record:
        return identity(str(record["alias"]))
    return record


def trace_lookup() -> dict[tuple[str, str], dict[str, Any]]:
    payload = json_load(TRACE_MANIFEST)
    return {(row["family"], row["trace_class"]): row for row in payload["traces"]}


def source_hashes(key: str, supplied: str = "") -> dict[str, str]:
    selected = identity(key)
    parsed = json.loads(supplied) if supplied else {}
    result: dict[str, str] = {}
    for relative in selected["sources"]:
        result[relative] = parsed.get(relative) or sha256(REPO / relative)
    return result


def git_tree_paths(commit: str) -> list[str]:
    raw = subprocess.run(
        ["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", "-z", commit],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return [part.decode("utf-8") for part in raw.split(b"\0") if part]


def hash_tree(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        raise FileNotFoundError(f"external evidence root is missing: {root}")
    rows = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda p: p.as_posix()):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return rows


def qualified_rev2_tree(root: Path) -> list[dict[str, Any]]:
    """Verify Revision-2 using its qualified manifest and return its rows.

    Reading this particular ext4 tree through Python has caused a host WSL
    interop failure.  The campaign's original GNU sha256sum verifier remains
    reliable, so use that exact byte-verification method without a large
    stdout pipe.
    """
    source = CAMPAIGN.parent / "date_2027_breadth_remediation/00_baseline_inventory.sha256"
    expected: list[tuple[str, str]] = []
    prefix = "external-rev2/"
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, key = line.split(maxsplit=1)
        key = key.strip()
        if key.startswith(prefix):
            expected.append((digest, key.removeprefix(prefix)))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n") as stream:
        for digest, relative in expected:
            stream.write(f"{digest}  {relative}\n")
        stream.flush()
        completed = subprocess.run(
            ["sha256sum", "--status", "-c", stream.name],
            cwd=root,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError("Revision-2 raw evidence differs from its qualified SHA-256 manifest")
    rows = []
    for digest, relative in expected:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"qualified Revision-2 file is missing: {path}")
        rows.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest})
    return rows


def external_cache_path(cache_dir: Path, label: str) -> Path:
    return cache_dir / f"{label}.json"


def write_external_cache(cache_dir: Path, label: str) -> dict[str, Any]:
    root = EXTERNAL_ROOTS[label]
    rows = qualified_rev2_tree(root) if label == "date2027_revision2_raw" else hash_tree(root)
    payload = {
        "label": label,
        "root": root.as_posix(),
        "file_count": len(rows),
        "tree_sha256": aggregate_hash({row["path"]: row["sha256"] for row in rows}),
        "verification_method": (
            "qualified campaign sha256sum --status -c manifest"
            if label == "date2027_revision2_raw"
            else "fresh Python SHA-256 read of every regular file"
        ),
        "files": rows,
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    external_cache_path(cache_dir, label).write_text(
        json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return payload


def make_integrity_manifest(commit: str, cache_dir: Path | None = None) -> dict[str, Any]:
    print("gate0-manifest: validating commit", file=sys.stderr, flush=True)
    if run(["git", "rev-parse", commit]).strip() != commit:
        raise RuntimeError(f"baseline commit does not resolve exactly: {commit}")
    repository_rows = []
    print("gate0-manifest: hashing repository tree", file=sys.stderr, flush=True)
    for relative in git_tree_paths(commit):
        path = REPO / relative
        if not path.is_file():
            raise FileNotFoundError(f"tracked baseline file is missing: {relative}")
        repository_rows.append(
            {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    external = {}
    for label, root in EXTERNAL_ROOTS.items():
        print(f"gate0-manifest: verifying {label}", file=sys.stderr, flush=True)
        if cache_dir is not None and external_cache_path(cache_dir, label).is_file():
            cached = json_load(external_cache_path(cache_dir, label))
            if cached["label"] != label or cached["root"] != root.as_posix():
                raise RuntimeError(f"invalid external cache identity for {label}")
            external[label] = {key: value for key, value in cached.items() if key != "label"}
            rows = external[label]["files"]
        else:
            rows = qualified_rev2_tree(root) if label == "date2027_revision2_raw" else hash_tree(root)
            external[label] = {
                "root": root.as_posix(),
                "file_count": len(rows),
                "tree_sha256": aggregate_hash({row["path"]: row["sha256"] for row in rows}),
                "verification_method": (
                    "qualified campaign sha256sum --status -c manifest"
                    if label == "date2027_revision2_raw"
                    else "fresh Python SHA-256 read of every regular file"
                ),
                "files": rows,
            }
        print(f"gate0-manifest: verified {label} ({len(rows)} files)", file=sys.stderr, flush=True)
    return {
        "schema_version": 1,
        "algorithm": "sha256-raw-bytes",
        "gate": "GATE_0_BASELINE_AUDIT",
        "status": "BASELINE_PROTECTED",
        "baseline_commit": commit,
        "physical_evidence_commit": PHYSICAL_EVIDENCE_COMMIT,
        "repository": {
            "root": str(REPO),
            "file_count": len(repository_rows),
            "tree_sha256": aggregate_hash(
                {row["path"]: row["sha256"] for row in repository_rows}
            ),
            "files": repository_rows,
        },
        "external_evidence": external,
    }


def verify_integrity(
    manifest: dict[str, Any], scopes: set[str] | None = None
) -> dict[str, Any]:
    changed: list[str] = []
    missing: list[str] = []
    added: list[str] = []
    selected = scopes or {"repository", *manifest["external_evidence"]}
    if "repository" in selected:
        print("gate0-verify: repository", file=sys.stderr, flush=True)
        for row in manifest["repository"]["files"]:
            path = REPO / row["path"]
            if not path.is_file():
                missing.append(f"repository/{row['path']}")
            elif sha256(path) != row["sha256"]:
                changed.append(f"repository/{row['path']}")
    for label, payload in manifest["external_evidence"].items():
        if label not in selected:
            continue
        print(f"gate0-verify: {label}", file=sys.stderr, flush=True)
        root = Path(payload["root"])
        expected_paths = {row["path"] for row in payload["files"]}
        current_paths = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        }
        missing.extend(f"{label}/{relative}" for relative in sorted(expected_paths - current_paths))
        added.extend(f"{label}/{relative}" for relative in sorted(current_paths - expected_paths))
        if label == "date2027_breadth_raw":
            for row in payload["files"]:
                path = root / row["path"]
                if path.is_file() and sha256(path) != row["sha256"]:
                    changed.append(f"{label}/{row['path']}")
        else:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n") as stream:
                for row in payload["files"]:
                    stream.write(f"{row['sha256']}  {row['path']}\n")
                stream.flush()
                completed = subprocess.run(
                    ["sha256sum", "--status", "-c", stream.name],
                    cwd=root,
                    check=False,
                )
            if completed.returncode != 0 and not missing:
                changed.append(f"{label}/<one-or-more-byte-mismatches>")
        print(f"gate0-verify: {label} complete", file=sys.stderr, flush=True)
    return {
        "status": "PASS" if not changed and not missing and not added else "FAIL",
        "changed": changed,
        "missing": missing,
        "added": added,
        "scopes": sorted(selected),
        "protected_file_count": (
            manifest["repository"]["file_count"] if "repository" in selected else 0
        )
        + sum(
            item["file_count"]
            for label, item in manifest["external_evidence"].items()
            if label in selected
        ),
    }


def raw_manifest_fields(root: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    runs_root = root / "runs"
    if not runs_root.is_dir():
        return result
    for manifest_path in runs_root.glob("*/raw-artifacts.sha256"):
        run_id = manifest_path.parent.name
        entries: dict[str, str] = {}
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, relative = line.split(None, 1)
            entries[relative.strip()] = digest
        def suffix(*values: str) -> str:
            for relative, digest in entries.items():
                if any(relative.endswith(value) for value in values):
                    return digest
            return ""
        result[run_id] = {
            "final_odb_sha256": suffix("/6_final.odb"),
            "final_netlist_sha256": suffix("/6_final.v"),
            "final_sdc_sha256": suffix("/6_final.sdc"),
            "final_spef_sha256": suffix("/6_final.spef"),
            "power_report_sha256": suffix(".power.rpt"),
            "raw_artifacts_manifest_sha256": sha256(manifest_path),
        }
    return result


def common_result(
    *,
    campaign: str,
    row: dict[str, str],
    architecture_key: str,
    clock_period_ns: str,
    activity_status: str,
    supplied_source_hashes: str = "",
) -> dict[str, Any]:
    selected = identity(architecture_key)
    hashes = source_hashes(architecture_key, supplied_source_hashes)
    traces = trace_lookup()
    trace = traces[(selected["trace_family"], "no_error")]
    return {
        "campaign": campaign,
        "run_id": row["run_id"],
        "architecture": row["architecture"],
        "implementation_id": row["implementation_id"],
        "code_id": selected["code_id"],
        "protection_guarantee": selected["guarantee"],
        "rtl_sha256": aggregate_hash(hashes),
        "rtl_sources_json": json.dumps(hashes, sort_keys=True, separators=(",", ":")),
        "formal_status": "PASS",
        "formal_evidence": ";".join(selected["formal"]),
        "physical_target": f"sky130hd_tt_025C_1v80_{float(clock_period_ns):g}ns",
        "technology": "SKY130HD",
        "corner": "tt_025C_1v80",
        "voltage_v": "1.8",
        "temperature_c": "25",
        "seed": row["seed"],
        "clock_period_ns": clock_period_ns,
        "latency_cycles": row["latency_cycles"],
        "initiation_interval_cycles": row["initiation_interval_cycles"],
        "activity_class": "A0_clean_no_error",
        "useful_operations": trace["useful_operations"],
        "trace_sha256": trace["compressed_sha256"],
        "activity_power_status": activity_status,
    }


def reconstruct_results() -> list[dict[str, Any]]:
    external = raw_manifest_fields(EXTERNAL_ROOTS["date2027_revision2_raw"])
    results: list[dict[str, Any]] = []
    for row in csv_load(REV2_RUNS):
        base = common_result(
            campaign="date2027_revision2",
            row=row,
            architecture_key=row["architecture"],
            clock_period_ns="10.0",
            activity_status=row["power_status"],
        )
        base.update(
            {
                "routing_complete": row["routing_complete"],
                "target_feasible": str(row["timing_feasibility"] == "MEETS_10NS"),
                "characterization_status": row["characterization_status"],
                "hold_status": row["hold_status"],
                "setup_violation_count": row["setup_violation_count"],
                "standard_cell_instance_area_um2": row["standard_cell_instance_area_um2"],
                "cell_count": row["cell_count"],
                "sequential_cell_count": row["sequential_cell_count"],
                "signed_worst_setup_slack_ns": row["signed_worst_setup_slack_ns"],
                "slack_derived_frequency_mhz": row["slack_derived_frequency_mhz"],
                "detailed_route_wirelength_um": row["detailed_route_wirelength_um"],
                "via_count": row["via_count"],
                "internal_power_w": clean(row["internal_power_w"]),
                "switching_power_w": clean(row["switching_power_w"]),
                "leakage_power_w": clean(row["leakage_power_w"]),
                "total_power_w": clean(row["total_power_w"]),
                "energy_per_useful_op_pj": clean(
                    row["achievable_no_error_energy_pj_per_operation"]
                ),
                **external.get(row["run_id"], {}),
                "raw_artifact_root": f"/var/lib/green-ecc-date2027-revision2/runs/{row['run_id']}",
                "source_record": "docs/date2027/revision2/results/REV2_RUN_RESULTS.csv",
            }
        )
        if row["architecture"] == "bch78":
            base["activity_power_status"] = "TRACE_AVAILABLE_POWER_NOT_RUN_TIMING_INELIGIBLE"
        results.append(base)

    for source, campaign, root_name in (
        (A_RUNS, "date2027_breadth_structural_10ns", "A"),
        (C_RUNS, "date2027_breadth_condition_5ns", "C"),
    ):
        for row in csv_load(source):
            key = row["architecture"]
            base = common_result(
                campaign=campaign,
                row=row,
                architecture_key=key,
                clock_period_ns=row["clock_period_ns"],
                activity_status=row["power_status"],
                supplied_source_hashes=row["source_hashes_json"],
            )
            base.update(
                {
                    "routing_complete": row["routing_complete"],
                    "target_feasible": row["target_feasible"],
                    "characterization_status": row["characterization_status"],
                    "hold_status": row["hold_status"],
                    "setup_violation_count": row["setup_violation_count"],
                    "standard_cell_instance_area_um2": row["standard_cell_instance_area_um2"],
                    "cell_count": row["cell_count"],
                    "sequential_cell_count": row["sequential_cell_count"],
                    "signed_worst_setup_slack_ns": row["signed_worst_setup_slack_ns"],
                    "slack_derived_frequency_mhz": row["slack_derived_frequency_mhz"],
                    "detailed_route_wirelength_um": row["detailed_route_wirelength_um"],
                    "via_count": row["via_count"],
                    "internal_power_w": clean(row["internal_power_w"]),
                    "switching_power_w": clean(row["switching_power_w"]),
                    "leakage_power_w": clean(row["leakage_power_w"]),
                    "total_power_w": clean(row["total_power_w"]),
                    "energy_per_useful_op_pj": clean(row["energy_per_op_pj"]),
                    "final_odb_sha256": row["final_odb_sha256"],
                    "final_netlist_sha256": row["final_netlist_sha256"],
                    "final_sdc_sha256": row["final_sdc_sha256"],
                    "final_spef_sha256": row["final_spef_sha256"],
                    "power_report_sha256": row["power_report_sha256"],
                    "raw_artifacts_manifest_sha256": row["raw_artifacts_manifest_sha256"],
                    "raw_artifact_root": (
                        "/var/lib/green-ecc-date2027-breadth-remediation/runs/"
                        f"{root_name}/{row['run_id']}"
                    ),
                    "source_record": source.relative_to(REPO).as_posix(),
                }
            )
            results.append(base)
    return results


def paired_effect(
    rows: Iterable[dict[str, Any]],
    *,
    reference: str,
    candidate: str,
    field: str,
) -> dict[str, Any]:
    grouped: dict[int, dict[str, float]] = {}
    for row in rows:
        if row["architecture"] not in {reference, candidate}:
            continue
        value = clean(row[field])
        if value == "":
            continue
        grouped.setdefault(int(row["seed"]), {})[row["architecture"]] = float(value)
    values: dict[str, float] = {}
    for seed, pair in sorted(grouped.items()):
        if set(pair) != {reference, candidate}:
            continue
        values[str(seed)] = (pair[candidate] - pair[reference]) / pair[reference] * 100.0
    ordered = list(values.values())
    return {
        "formula": f"({candidate} - {reference}) / {reference} * 100 percent",
        "values_by_seed": values,
        "count": len(ordered),
        "mean": statistics.fmean(ordered),
        "minimum": min(ordered),
        "maximum": max(ordered),
        "sample_standard_deviation": statistics.stdev(ordered),
    }


def nested(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for key in path.split("."):
        value = value[key]
    return value


def reconstruction_checks(results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rev2_rows = [row for row in results if row["campaign"] == "date2027_revision2"]
    a_rows = [row for row in results if row["campaign"] == "date2027_breadth_structural_10ns"]
    c_rows = [row for row in results if row["campaign"] == "date2027_breadth_condition_5ns"]
    b_rows = csv_load(B_RUNS)
    computed = {
        "secded_10ns_area_percent": paired_effect(
            rev2_rows, reference="secded_comb", candidate="secded_pipe", field="standard_cell_instance_area_um2"
        ),
        "secded_10ns_timing_percent": paired_effect(
            rev2_rows, reference="secded_comb", candidate="secded_pipe", field="slack_derived_frequency_mhz"
        ),
        "secded_10ns_energy_percent": paired_effect(
            rev2_rows, reference="secded_comb", candidate="secded_pipe", field="energy_per_useful_op_pj"
        ),
        "hsiao_10ns_area_percent": paired_effect(
            a_rows, reference="A_hsiao_flat", candidate="A_hsiao_hierarchical", field="standard_cell_instance_area_um2"
        ),
        "hsiao_10ns_timing_percent": paired_effect(
            a_rows, reference="A_hsiao_flat", candidate="A_hsiao_hierarchical", field="slack_derived_frequency_mhz"
        ),
        "hsiao_10ns_energy_percent": paired_effect(
            a_rows, reference="A_hsiao_flat", candidate="A_hsiao_hierarchical", field="energy_per_useful_op_pj"
        ),
        "secded_5ns_area_percent": paired_effect(
            c_rows, reference="C_secded_comb", candidate="C_secded_pipe", field="standard_cell_instance_area_um2"
        ),
        "secded_5ns_timing_percent": paired_effect(
            c_rows, reference="C_secded_comb", candidate="C_secded_pipe", field="slack_derived_frequency_mhz"
        ),
        "secded_5ns_energy_percent": paired_effect(
            c_rows, reference="C_secded_comb", candidate="C_secded_pipe", field="energy_per_useful_op_pj"
        ),
        "secded_10ns_internal_power_percent": paired_effect(
            b_rows, reference="secded_comb", candidate="secded_pipe", field="internal_power_w"
        ),
        "secded_10ns_switching_power_percent": paired_effect(
            b_rows, reference="secded_comb", candidate="secded_pipe", field="switching_power_w"
        ),
        "secded_10ns_leakage_power_percent": paired_effect(
            b_rows, reference="secded_comb", candidate="secded_pipe", field="leakage_power_w"
        ),
        "secded_10ns_total_power_percent": paired_effect(
            b_rows, reference="secded_comb", candidate="secded_pipe", field="total_power_w"
        ),
    }
    source_values = {
        "secded_10ns_area_percent": nested(json_load(REV2_EFFECTS), "effects.area_percent.summary.mean"),
        "secded_10ns_timing_percent": nested(json_load(REV2_EFFECTS), "effects.slack_derived_frequency_percent.summary.mean"),
        "secded_10ns_energy_percent": nested(json_load(REV2_EFFECTS), "effects.achievable_energy_percent.summary.mean"),
        "hsiao_10ns_area_percent": nested(json_load(A_SUMMARY), "paired_effects.standard_cell_instance_area_um2.percent_effect.mean"),
        "hsiao_10ns_timing_percent": nested(json_load(A_SUMMARY), "paired_effects.slack_derived_frequency_mhz.percent_effect.mean"),
        "hsiao_10ns_energy_percent": nested(json_load(A_SUMMARY), "paired_effects.energy_per_op_pj.percent_effect.mean"),
        "secded_5ns_area_percent": nested(json_load(C_SUMMARY), "within_5ns_paired_effects.standard_cell_instance_area_um2.percent_effect.mean"),
        "secded_5ns_timing_percent": nested(json_load(C_SUMMARY), "within_5ns_paired_effects.slack_derived_frequency_mhz.percent_effect.mean"),
        "secded_5ns_energy_percent": nested(json_load(C_SUMMARY), "within_5ns_paired_effects.energy_per_op_pj.percent_effect.mean"),
        "secded_10ns_internal_power_percent": nested(json_load(B_SUMMARY), "paired_effects.internal_power_w.percent_effect.mean"),
        "secded_10ns_switching_power_percent": nested(json_load(B_SUMMARY), "paired_effects.switching_power_w.percent_effect.mean"),
        "secded_10ns_leakage_power_percent": nested(json_load(B_SUMMARY), "paired_effects.leakage_power_w.percent_effect.mean"),
        "secded_10ns_total_power_percent": nested(json_load(B_SUMMARY), "paired_effects.total_power_w.percent_effect.mean"),
    }
    prompt_approx = {
        "secded_10ns_area_percent": 37.2,
        "secded_10ns_timing_percent": 46.6,
        "secded_10ns_energy_percent": -23.4,
        "hsiao_10ns_area_percent": -0.564,
        "hsiao_10ns_timing_percent": 2.656,
        "hsiao_10ns_energy_percent": 1.328,
        "secded_5ns_area_percent": 36.7,
        "secded_5ns_timing_percent": 68.6,
        "secded_5ns_energy_percent": -19.3,
        "secded_10ns_internal_power_percent": 6.77,
        "secded_10ns_switching_power_percent": -49.48,
        "secded_10ns_leakage_power_percent": 34.43,
        "secded_10ns_total_power_percent": -23.4,
    }
    checks = []
    for name, value in computed.items():
        actual = value["mean"]
        source = float(source_values[name])
        exact_error = abs(actual - source)
        prompt_error = abs(actual - prompt_approx[name])
        checks.append(
            {
                "claim": name,
                "reconstructed_mean_percent": actual,
                "qualified_source_mean_percent": source,
                "source_absolute_error": exact_error,
                "source_tolerance": 1e-9,
                "prompt_reported_approx_percent": prompt_approx[name],
                "prompt_absolute_error": prompt_error,
                "prompt_approx_tolerance": 0.15,
                "status": "PASS" if exact_error <= 1e-9 and prompt_error <= 0.15 else "FAIL",
            }
        )
    return checks, computed


def evidence_sources() -> list[dict[str, Any]]:
    paths = [
        REV2_RUNS,
        REV2_EFFECTS,
        A_RUNS,
        B_RUNS,
        C_RUNS,
        A_SUMMARY,
        B_SUMMARY,
        C_SUMMARY,
        TRACE_MANIFEST,
        REPO / "campaigns/date_2027_breadth_remediation/physical/contract_v1.json",
        REPO / "paper/date2027_revision3/data/claim_registry.json",
        REPO / "campaigns/date_2027_breadth_remediation/FINAL_baseline_integrity_check.json",
    ]
    return [
        {
            "path": path.relative_to(REPO).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in paths
    ]


def write_results(rows: list[dict[str, Any]]) -> None:
    target = CAMPAIGN / "baseline_results.csv"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_provenance(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    checks, computed = reconstruction_checks(rows)
    traces = json_load(TRACE_MANIFEST)["traces"]
    payload = {
        "schema_version": 1,
        "gate": "GATE_0_BASELINE_AUDIT",
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "baseline": {
            "final_date_revision3_commit": DEFAULT_BASELINE_COMMIT,
            "physical_evidence_freeze_commit": PHYSICAL_EVIDENCE_COMMIT,
            "branch": "codex/ecc-lifecycle-sustainability",
            "tracked_file_count": manifest["repository"]["file_count"],
            "protected_file_count": manifest["repository"]["file_count"]
            + sum(item["file_count"] for item in manifest["external_evidence"].values()),
        },
        "physical_environment": {
            "container_image": "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e",
            "orfs_commit": "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2",
            "openroad_commit": "ab6fd26351dc449e69059684dc6aa9ae9046eb36",
            "platform": "sky130hd",
            "corner": "tt_025C_1v80",
            "voltage_v": 1.8,
            "temperature_c": 25,
            "matched_seeds": [11, 13, 17, 19, 23],
        },
        "result_record_count": len(rows),
        "evidence_sources": evidence_sources(),
        "reconstruction_checks": checks,
        "reconstructed_effects": computed,
        "activity_evidence": {
            "trace_count": len(traces),
            "traces": traces,
            "post_route_power_measured_classes": ["no_error"],
            "available_but_not_power_measured_classes": ["single_error", "double_error"],
            "useful_operations_per_trace": 100000,
            "interpretation": (
                "W1/W2 deterministic primary-input traces exist and are integrity protected, "
                "but qualified post-route power was run only for W0/no-error traffic."
            ),
        },
        "sram_infrastructure": {
            "synthesizable_array_model": "asic/common/sram_core.sv",
            "ecc_array_wrappers": [
                "asic/secded/sram_secded_top.sv",
                "asic/secdaec/sram_secdaec_top.sv",
                "asic/taec/sram_taec_top.sv",
                "asic/bch/sram_bch_top.sv",
                "asic/polar/sram_polar_64_32_top.sv",
                "asic/polar/sram_polar_64_48_top.sv",
                "asic/polar/sram_polar_128_96_top.sv",
                "asic/rtl/sram/sram_wrappers.sv",
            ],
            "software_proxy": [
                "PracticalSRAMSimulator.cpp",
                "sram_workflow.py",
                "sram_ecc_benchmark.py",
                "ml/sram_advisory.py",
            ],
            "openram_installed": False,
            "openram_repository_infrastructure": False,
            "sram_macro_lef_gds_liberty_spice_views_present": False,
            "physical_to_logical_bit_mapping_present": False,
            "logical_intra_word_placement_candidates_present": True,
            "logical_intra_word_placement_source": "codeforge/placement_policy.py",
            "physical_cross_codeword_bit_interleaving_model_present": False,
            "qualification_note": (
                "The existing even/odd placement library permutes logical columns within one "
                "codeword and uses a displacement proxy. It is not a macro-cell coordinate map "
                "and cannot model one physical burst becoming events in several codewords."
            ),
        },
        "integrity_manifest": "campaigns/iscas_sustainability_extension/baseline_integrity_manifest.json",
    }
    (CAMPAIGN / "baseline_provenance.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-commit", default=DEFAULT_BASELINE_COMMIT)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument(
        "--verify-scope",
        action="append",
        choices=["repository", *sorted(EXTERNAL_ROOTS)],
    )
    parser.add_argument("--emit-tree-json", type=Path)
    parser.add_argument("--emit-run-fields-json", type=Path)
    parser.add_argument("--cache-external", choices=sorted(EXTERNAL_ROOTS))
    parser.add_argument("--external-cache-dir", type=Path)
    args = parser.parse_args()

    if args.emit_tree_json:
        print(json.dumps(hash_tree(args.emit_tree_json), sort_keys=True))
        return 0
    if args.emit_run_fields_json:
        print(json.dumps(raw_manifest_fields(args.emit_run_fields_json), sort_keys=True))
        return 0
    if args.cache_external:
        if args.external_cache_dir is None:
            parser.error("--cache-external requires --external-cache-dir")
        payload = write_external_cache(args.external_cache_dir, args.cache_external)
        print(json.dumps({"label": args.cache_external, "file_count": payload["file_count"]}, sort_keys=True))
        return 0

    manifest_path = CAMPAIGN / "baseline_integrity_manifest.json"
    if args.manifest_only:
        if manifest_path.exists():
            raise SystemExit(f"refusing to overwrite protected baseline manifest: {manifest_path}")
        payload = make_integrity_manifest(args.baseline_commit, args.external_cache_dir)
        print("gate0-manifest: serializing protected manifest", file=sys.stderr, flush=True)
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print("gate0-manifest: write complete", file=sys.stderr, flush=True)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "repository_files": payload["repository"]["file_count"],
                    "external_files": {
                        key: value["file_count"] for key, value in payload["external_evidence"].items()
                    },
                },
                sort_keys=True,
            )
        )
        return 0

    if not manifest_path.is_file():
        raise SystemExit("baseline integrity manifest is missing; run --manifest-only first")
    manifest = json_load(manifest_path)

    if args.verify:
        result = verify_integrity(manifest, set(args.verify_scope) if args.verify_scope else None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1

    if args.generate:
        results = reconstruct_results()
        write_results(results)
        provenance = write_provenance(results, manifest)
        print(
            json.dumps(
                {
                    "status": provenance["status"],
                    "result_records": len(results),
                    "reconstruction_checks": len(provenance["reconstruction_checks"]),
                },
                sort_keys=True,
            )
        )
        return 0 if provenance["status"] == "PASS" else 1

    parser.error("select one of --manifest-only, --generate, or --verify")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
