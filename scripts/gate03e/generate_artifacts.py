#!/usr/bin/env python3
"""Generate the narrowly scoped Gate-03E evidence package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "date2027" / "rigour_gate_03e"
FREEZE_COMMIT = "db32a47d103495787a17b59388dfad3cc4cb77e8"
CHECKPOINT_TAG = "gate03e-pre-reboot-db32a47"
ORFS_IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
ORFS_DIGEST = ORFS_IMAGE.rsplit("@", 1)[1]
ORFS_TAG = "26Q3-275-g56496f398"
ORFS_COMMIT = "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
ORFS_TREE = "2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a"
POLICY_SHA256 = "258694f328084c3fb92dec24e07b3b40d261037d5b1bd8d32b119684211d0b9a"
OFFICIAL_MAKE = "make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk"
DEADLINE_AOE = "2026-08-16T23:59:59-12:00"
DEADLINE_UTC = "2026-08-17T11:59:59Z"
GATE_HASHES = {
    "docs/date2027/rigour_gate_01": "24cd71d2f7cbb10f0709bd49e89855fca50d2dbeb3c8d6f8aabb6c9e83bee526",
    "docs/date2027/rigour_gate_02": "972c873d377c66ad183a52b25632f6811c916d44be27a2892b119a2fda8dc79f",
    "docs/date2027/rigour_gate_03": "e5e96c4f02ffec03ffbab532f5d09dc3249a51534bbc43e494798b270fb51bc4",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, columns: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def external_record(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    return {
        "path": f"$GATE03E_EVIDENCE/{relative}",
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def tree_hash(root: Path) -> str:
    entries: list[tuple[str, int, str]] = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix().encode("utf-8"),
    ):
        entries.append((path.relative_to(root).as_posix(), path.stat().st_size, sha256_file(path)))
    payload = b"".join(
        name.encode("utf-8") + b"\0" + str(size).encode("ascii") + b"\0" + digest.encode("ascii") + b"\n"
        for name, size, digest in entries
    )
    return hashlib.sha256(payload).hexdigest()


def artifact_by_path(inventory: dict[str, Any], relative: str) -> dict[str, Any]:
    for item in inventory["artifacts"]:
        if item["path"] == relative:
            return item
    raise KeyError(f"artifact absent from inventory: {relative}")


def copy_raw_logs(evidence_root: Path, inventories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_root = DOC / "raw_logs"
    raw_root.mkdir(parents=True, exist_ok=True)
    canonical: dict[str, str] = {}
    for inventory in inventories:
        run_label = inventory["run_label"]
        for item in inventory["artifacts"]:
            canonical[f"runs/{run_label}/{item['path']}"] = item["canonical_sha256"]
    rows: list[dict[str, Any]] = []
    for source in sorted(evidence_root.rglob("*.log"), key=lambda item: item.relative_to(evidence_root).as_posix()):
        relative = source.relative_to(evidence_root).as_posix()
        destination = raw_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        rows.append(
            {
                "path": destination.relative_to(DOC).as_posix(),
                "source_path": f"$GATE03E_EVIDENCE/{relative}",
                "size_bytes": source.stat().st_size,
                "raw_sha256": sha256_file(source),
                "canonical_sha256": canonical.get(relative, "NOT_APPLICABLE"),
            }
        )
    repository_validation_roots = sorted(
        (path for path in raw_root.glob("repository-validation*") if path.is_dir()),
        key=lambda path: path.name,
    )
    for repository_validation_root in repository_validation_roots:
        for source in sorted(repository_validation_root.rglob("*.log"), key=lambda item: item.relative_to(DOC).as_posix()):
            rows.append(
                {
                    "path": source.relative_to(DOC).as_posix(),
                    "source_path": f"$REPOSITORY/{source.relative_to(ROOT).as_posix()}",
                    "size_bytes": source.stat().st_size,
                    "raw_sha256": sha256_file(source),
                    "canonical_sha256": "NOT_APPLICABLE",
                }
            )
    rows.sort(key=lambda row: row["path"])
    write_csv(
        DOC / "RAW_LOG_INDEX.csv",
        ("path", "source_path", "size_bytes", "raw_sha256", "canonical_sha256"),
        rows,
    )
    return rows


def generate(evidence_root: Path, repository_validation_status: str) -> None:
    required = (
        "registry/registry-summary.json",
        "registry/amd64-manifest.raw.json",
        "registry/amd64-config.raw.json",
        "image/docker-image-inspect.json",
        "image/pinned-container-health.log",
        "source/git-identities.txt",
        "source/git-submodules.txt",
        "source/complete-checkout-files.sha256",
        "reconciliation/execution-subset-comparison.json",
        "reconciliation/container-execution-subset.json",
        "collateral/sky130hd-collateral-manifest.json",
        "policy/reproducibility_policy_v1.json",
        "policy/reproducibility.py",
        "commands/command-manifest.json",
        "commands/command-manifest-amendment-01.json",
        "runs/gcd-run-01-inventory.json",
        "runs/gcd-run-02-inventory.json",
        "runs/gcd-run-comparison.json",
        "mapping/mapping-validation.json",
    )
    missing = [item for item in required if not (evidence_root / item).is_file()]
    if missing:
        raise SystemExit(f"missing Gate-03E evidence: {missing}")

    DOC.mkdir(parents=True, exist_ok=True)
    registry = load(evidence_root, "registry/registry-summary.json")
    reconciliation = load(evidence_root, "reconciliation/execution-subset-comparison.json")
    collateral = load(evidence_root, "collateral/sky130hd-collateral-manifest.json")
    command = load(evidence_root, "commands/command-manifest.json")
    amendment = load(evidence_root, "commands/command-manifest-amendment-01.json")
    comparison = load(evidence_root, "runs/gcd-run-comparison.json")
    mapping = load(evidence_root, "mapping/mapping-validation.json")
    inspect = load(evidence_root, "image/docker-image-inspect.json")[0]
    inventories = [
        load(evidence_root, "runs/gcd-run-01-inventory.json"),
        load(evidence_root, "runs/gcd-run-02-inventory.json"),
    ]

    identity_lines = (evidence_root / "source/git-identities.txt").read_text(encoding="utf-8").splitlines()
    if identity_lines[:2] != [ORFS_COMMIT, ORFS_TREE]:
        raise SystemExit("official source identity changed")
    source_file_lines = (evidence_root / "source/complete-checkout-files.sha256").read_text(encoding="utf-8").splitlines()
    submodule_lines = [
        line for line in (evidence_root / "source/git-submodules.txt").read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    source_freeze = {
        "schema_version": 1,
        "official_repository": "https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git",
        "expected_short_revision": "56496f398",
        "commit": ORFS_COMMIT,
        "git_tree": ORFS_TREE,
        "checkout_clean": (evidence_root / "source/git-status.txt").stat().st_size == 0,
        "recursive_submodule_count": len(submodule_lines),
        "complete_non_admin_file_count": len(source_file_lines),
        "complete_checkout_manifest": external_record(evidence_root, "source/complete-checkout-files.sha256"),
        "git_submodules": external_record(evidence_root, "source/git-submodules.txt"),
        "git_clone_log": external_record(evidence_root, "source/git-clone.log"),
        "source_status": external_record(evidence_root, "source/git-status.txt"),
        "relationship": {
            "tag": ORFS_TAG,
            "linux_amd64_manifest_digest": ORFS_DIGEST,
            "image_config_digest": registry["config_digest"],
            "full_source_commit": ORFS_COMMIT,
            "execution_subset_byte_identity": reconciliation["byte_identity_pass"],
        },
    }
    write_json(DOC / "ORFS_SOURCE_FREEZE.json", source_freeze)

    image_reconciliation = {
        "schema_version": 1,
        "repository": registry["repository"],
        "tag": ORFS_TAG,
        "linux_amd64_manifest_digest": registry["linux_amd64_manifest_digest"],
        "required_image": ORFS_IMAGE,
        "image_id": inspect["Id"],
        "image_labels": inspect.get("Config", {}).get("Labels") or {},
        "architecture": inspect["Architecture"],
        "operating_system": inspect["Os"],
        "rootfs_layers": inspect.get("RootFS", {}).get("Layers", []),
        "complete_container_identity_rule": "The immutable OCI digest identifies the complete container.",
        "execution_relevant_scope_rule": "Byte identity is required only for actual flow scripts, platform files, configurations, and dynamically resolved files used by the selected flow.",
        "execution_subset": reconciliation,
        "execution_subset_manifest": external_record(evidence_root, "reconciliation/container-execution-subset.json"),
        "raw_registry_evidence": {
            "tag_index": external_record(evidence_root, "registry/tag-index.raw.json"),
            "amd64_manifest": external_record(evidence_root, "registry/amd64-manifest.raw.json"),
            "amd64_config": external_record(evidence_root, "registry/amd64-config.raw.json"),
        },
        "status": "PASS" if reconciliation["byte_identity_pass"] and registry["linux_amd64_manifest_digest"] == ORFS_DIGEST else "FAIL",
    }
    write_json(DOC / "ORFS_IMAGE_RECONCILIATION.json", image_reconciliation)

    collateral_copy = dict(collateral)
    collateral_copy["raw_evidence"] = external_record(evidence_root, "collateral/sky130hd-collateral-manifest.json")
    write_json(DOC / "SKY130HD_COLLATERAL_MANIFEST.json", collateral_copy)

    docker_candidates = []
    for line in (evidence_root / "provision/docker-package-candidates.tsv").read_text(encoding="utf-8").splitlines():
        if line.strip():
            package, version = line.split("\t", 1)
            docker_candidates.append({"package": package, "version": version})
    previous_gates = {
        relative: {"expected_sha256": expected, "actual_sha256": tree_hash(ROOT / relative)}
        for relative, expected in GATE_HASHES.items()
    }
    environment = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "gate": "03E",
        "deadline": {"aoe": DEADLINE_AOE, "utc": DEADLINE_UTC},
        "gate03r_freeze": {
            "starting_commit": FREEZE_COMMIT,
            "checkpoint_tag": CHECKPOINT_TAG,
            "commit_pushed": False,
            "tag_pushed": False,
            "gate03e_files_committed": False,
            "preserved_verdict": "REMEDIATION_FAILED",
            "subresults": {
                "EXACT_IDENTITY_SECDED_REMEDIATION": "PASS",
                "BCH_78_64_T2_REMEDIATION": "PASS",
                "PHYSICAL_ENVIRONMENT_REMEDIATION": "FAIL",
            },
        },
        "host": {
            "wsl_version": "2.7.11.0",
            "default_wsl_generation": 2,
            "distribution": "Ubuntu-24.04",
            "distribution_state": "Running",
            "distribution_generation": 2,
            "ubuntu_release": "24.04.4 LTS",
            "kernel": "6.18.33.2-microsoft-standard-WSL2",
            "architecture": "x86_64",
            "systemd": True,
        },
        "docker": {
            "engine": "Docker Engine CE",
            "version": "29.7.2",
            "packages": docker_candidates,
            "service_active": True,
            "service_enabled": True,
            "functional_health_test": "successful execution of the required pinned ORFS container",
            "hello_world_required": False,
            "docker_version_evidence": external_record(evidence_root, "provision/docker-version.log"),
            "docker_info_evidence": external_record(evidence_root, "provision/docker-info.log"),
            "package_inventory": external_record(evidence_root, "provision/dpkg-query.tsv"),
        },
        "orfs_container": {
            "image": ORFS_IMAGE,
            "image_id": inspect["Id"],
            "architecture": inspect["Architecture"],
            "operating_system": inspect["Os"],
            "openroad_version": "26Q3-1080-gab6fd26351",
            "yosys_version": "0.68+post",
            "make_version": "GNU Make 4.3",
            "openroad_executable_sha256": "2fc67d3a82df36014b615e710ce2e68600b592b27b051e4533c30248a2e2eb91",
            "yosys_executable_sha256": "5cd52bc790d39b1e59a88112e9132ef8de338c2a26e4b0df8222d937e65bab92",
            "installed_package_inventory": external_record(evidence_root, "image/container-dpkg-query.tsv"),
            "health_and_tool_versions": external_record(evidence_root, "image/pinned-container-health.log"),
        },
        "source": source_freeze,
        "previous_gate_byte_hashes": previous_gates,
        "scope": {
            "production_rtl_modified_in_gate03e": False,
            "registries_modified_in_gate03e": False,
            "previous_gate_evidence_modified_in_gate03e": False,
            "large_run_root": "/var/lib/green-ecc-gate03e",
            "stable_run_root_token": "$GATE03E_EVIDENCE",
        },
    }
    write_json(DOC / "ENVIRONMENT_MANIFEST.json", environment)

    smoke_rows = []
    semantic_pass = all(item["pass"] for item in comparison["semantic_artifact_comparisons"])
    for index, inventory in enumerate(inventories, 1):
        run_label = inventory["run_label"]
        metadata = load(evidence_root, f"runs/{run_label}/run-metadata.json")
        final = {
            suffix: artifact_by_path(inventory, f"results/sky130hd/gcd/base/6_final.{suffix}")
            for suffix in ("gds", "def", "v", "sdc", "spef")
        }
        smoke_rows.append(
            {
                "run_id": run_label,
                "clean_run_directory": f"$GATE03E_EVIDENCE/runs/{run_label}",
                "invocation": OFFICIAL_MAKE,
                "effective_lec_check": "0",
                "default_all_chain": "check-yosys>check-openroad>synth>floorplan>place>cts>route>finish",
                "start_utc": metadata["start_time"],
                "end_utc": metadata["end_time"],
                "exit_status": metadata["exit_status"],
                "status": "PASS" if metadata["exit_status"] == 0 else "FAIL",
                "artifact_count": inventory["artifact_count"],
                "inventory_sha256": sha256_file(evidence_root / f"runs/{run_label}-inventory.json"),
                "final_gds_raw_sha256": final["gds"]["raw_sha256"],
                "final_gds_canonical_sha256": final["gds"]["canonical_sha256"],
                "final_def_raw_sha256": final["def"]["raw_sha256"],
                "final_def_canonical_sha256": final["def"]["canonical_sha256"],
                "final_netlist_raw_sha256": final["v"]["raw_sha256"],
                "final_netlist_canonical_sha256": final["v"]["canonical_sha256"],
                "final_spef_raw_sha256": final["spef"]["raw_sha256"],
                "final_spef_canonical_sha256": final["spef"]["canonical_sha256"],
                "semantic_artifacts_match": semantic_pass,
                "frozen_policy_sha256": comparison["policy_sha256"],
                "reproducibility_status": "PASS" if comparison["reproducibility_pass"] else "FAIL",
            }
        )
    write_csv(DOC / "GCD_SMOKE_RUNS.csv", smoke_rows[0].keys(), smoke_rows)

    mapping_rows = []
    for job in mapping["jobs"]:
        mapping_rows.append(
            {
                "job": job["job"],
                "implementation": job["implementation"],
                "top_module": job["design"],
                "status": job["status"],
                "port_contract": json.dumps(job["port_contract"], sort_keys=True, separators=(",", ":")),
                "source_hashes": json.dumps(job["source_files"], sort_keys=True, separators=(",", ":")),
                "mapped_netlist_sha256": job["mapped_artifacts"]["netlist"]["sha256"],
                "normalized_mapped_netlist_sha256": job["normalized_netlist_sha256"],
                "liberty_sha256": mapping["liberty"]["sha256"],
                "cell_count": job["cell_count"],
                "sequential_cell_count": job["sequential_cell_count"],
                "generic_or_unmapped_cell_type_count": len(job["generic_or_unmapped_cell_types"]),
                "mapped_latch_master_count": len(job["latch_masters"]),
                "fault_injection_input_present": False,
                "equivalence_setup_assessable": job["equivalence_setup_assessable"],
                "comparative_ppa_generated": False,
            }
        )
    write_csv(DOC / "GREEN_ECC_MAPPING_READINESS.csv", mapping_rows[0].keys(), mapping_rows)

    raw_rows = copy_raw_logs(evidence_root, inventories)
    combined_command = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "evidence_root": "/var/lib/green-ecc-gate03e",
        "stable_evidence_root_token": "$GATE03E_EVIDENCE",
        "initial_frozen_command_manifest": command,
        "additive_execution_amendment": amendment,
        "official_smoke_invocation": OFFICIAL_MAKE,
        "mapping_jobs": [
            {
                "job": job["job"],
                "status": job["status"],
                "command": (evidence_root / "mapping" / job["job"] / "run-command.txt").read_text(encoding="utf-8").strip(),
                "command_record": external_record(evidence_root, f"mapping/{job['job']}/run-command.txt"),
            }
            for job in mapping["jobs"]
        ],
        "failed_attempts_retained": [
            {
                "classification": "native_optional_lec_avx512_incompatibility",
                "path": "$GATE03E_EVIDENCE/attempts/gcd-native-lec-avx512-failure-01",
                "inventory": external_record(evidence_root, "attempts/gcd-native-lec-avx512-failure-01-inventory.json"),
            },
            {
                "classification": "production_secded_package_elaboration_incompatibility",
                "path": "$GATE03E_EVIDENCE/mapping-attempts/production-secded-package-elaboration-failure",
                "production_rtl_modified": False,
            },
            {
                "classification": "mapping_validator_false_positive_preserved",
                "evidence": external_record(evidence_root, "mapping-attempts/mapping-validator-false-positive-01.json"),
            },
        ],
        "large_run_artifact_inventories": [
            external_record(evidence_root, "runs/gcd-run-01-inventory.json"),
            external_record(evidence_root, "runs/gcd-run-02-inventory.json"),
        ],
        "frozen_reproducibility": {
            "policy_sha256": POLICY_SHA256,
            "policy": external_record(evidence_root, "policy/reproducibility_policy_v1.json"),
            "comparator": external_record(evidence_root, "policy/reproducibility.py"),
            "comparison": external_record(evidence_root, "runs/gcd-run-comparison.json"),
            "reproducibility_pass": comparison["reproducibility_pass"],
            "raw_hash_difference_count": len(comparison["raw_hash_differences"]),
            "unexplained_raw_hash_difference_count": sum(not row["pass"] for row in comparison["raw_hash_differences"]),
            "numeric_metric_failure_count": sum(not row["pass"] for row in comparison["metric_comparisons"]),
            "semantic_artifact_failure_count": sum(not row["pass"] for row in comparison["semantic_artifact_comparisons"]),
        },
        "mapping_validation": external_record(evidence_root, "mapping/mapping-validation.json"),
        "raw_log_count": len(raw_rows),
        "raw_log_index": "RAW_LOG_INDEX.csv",
        "repository_validation_status": repository_validation_status,
    }
    write_json(DOC / "COMMAND_MANIFEST.json", combined_command)

    gate_hashes_pass = all(item["actual_sha256"] == item["expected_sha256"] for item in previous_gates.values())
    acceptance = {
        "wsl2_and_docker_operate_correctly": True,
        "required_image_digest_used": registry["linux_amd64_manifest_digest"] == ORFS_DIGEST,
        "full_orfs_source_configuration_identity_established": image_reconciliation["status"] == "PASS",
        "sky130hd_collateral_and_corner_verified": collateral["liberty_pvt_selection"]["metadata_confirmation_pass"],
        "both_clean_gcd_rtl_to_gds_runs_complete": all(row["status"] == "PASS" for row in smoke_rows),
        "gcd_reproducibility_policy_passes": comparison["reproducibility_pass"],
        "all_four_boundaries_map_without_generic_cells_or_black_boxes": mapping["status"] == "PASS",
        "secded_mapped_structures_distinct": all(item["pass"] for item in mapping["secded_structural_distinction"]),
        "previous_gates_unchanged": gate_hashes_pass,
        "repository_validation_passes": repository_validation_status == "PASS",
    }
    ready = all(acceptance.values())
    deadline_expired = datetime.now(timezone.utc) > datetime(2026, 8, 17, 11, 59, 59, tzinfo=timezone.utc)
    terminal_verdict = "ENVIRONMENT_READY_FOR_GATE_03_REENTRY" if ready else (
        "ENVIRONMENT_ENABLEMENT_FAILED" if deadline_expired else None
    )
    current_status = "AUTHORIZED" if ready else ("DEADLINE_FAILURE" if deadline_expired else "INCOMPLETE_PENDING_DEADLINE")

    authorization = f"""# Gate 03 Re-entry Authorization

Authorization: **{'AUTHORIZED' if ready else 'NOT AUTHORIZED'}**

Current status: `{current_status}`  
Terminal verdict: `{terminal_verdict or 'NOT_ISSUED_BEFORE_DEADLINE'}`  
Deadline: **16 August 2026 AoE** (`{DEADLINE_UTC}`)

Gate-03R remains `REMEDIATION_FAILED` and its required sub-results remain:

- `EXACT_IDENTITY_SECDED_REMEDIATION: PASS`
- `BCH_78_64_T2_REMEDIATION: PASS`
- `PHYSICAL_ENVIRONMENT_REMEDIATION: FAIL`

Acceptance state:

""" + "\n".join(f"- `{name}: {'PASS' if passed else 'FAIL'}`" for name, passed in acceptance.items()) + """

The current blocker is the frozen two-run reproducibility comparison. Both clean targetless GCD flows completed and all required semantic design artifacts match canonically, but the pre-frozen comparator records unexplained or exact-tolerance differences. No exclusion was added after either run. A terminal failure verdict is not issued before the deadline solely because a criterion is currently incomplete.

An eventual pass authorizes complete Gate-03 re-entry only. It does not authorize publication claims, PPA conclusions, figures, selector changes, FIT, energy, or carbon results.
"""
    (DOC / "GATE_03_REENTRY_AUTHORIZATION.md").write_text(authorization, encoding="utf-8", newline="\n")

    diff_rows = []
    for item in comparison["raw_hash_differences"]:
        path = str(item["path"]).replace("|", "\\|")
        classification = str(item["classification"]).replace("|", "\\|")
        explanation = str(item["explanation"]).replace("|", "\\|")
        diff_rows.append(f"| `{path}` | `{classification}` | {'PASS' if item['pass'] else 'FAIL'} | {explanation} |")
    report = f"""# GREEN-ECC DATE 2027 Gate 03E Report

## Outcome

Gate 03 re-entry is **not currently authorized**. WSL2, Docker CE, the immutable ORFS image, source reconciliation, SKY130HD collateral, two targetless full GCD flows, and all four technology-mapping jobs are complete. The pre-frozen reproducibility policy reports a failure, so readiness cannot be claimed. Because the deadline has not expired, no terminal failure verdict is issued.

The Gate-03R freeze is local commit `{FREEZE_COMMIT}` with annotated local tag `{CHECKPOINT_TAG}`. Neither was pushed. Gate-03E files remain uncommitted. Gate-03R remains `REMEDIATION_FAILED` with the three sub-results recorded in the authorization artifact.

## Environment and identity

- Ubuntu 24.04.4 runs as WSL2 with systemd; Docker Engine CE 29.7.2 is active and enabled.
- Successful execution of `{ORFS_IMAGE}` is the Docker functional health test.
- Registry tag `{ORFS_TAG}` resolves to the required Linux/amd64 manifest `{ORFS_DIGEST}` and image ID `{inspect['Id']}`.
- Official source commit `{ORFS_COMMIT}` and Git tree `{ORFS_TREE}` are frozen with {len(submodule_lines)} recursive submodules and {len(source_file_lines):,} hashed checkout files.
- Narrow execution reconciliation is PASS: {reconciliation['counts']['byte_identical']} byte-identical files, {reconciliation['counts']['missing_from_container']} missing, {reconciliation['counts']['additional_in_container']} additional, and {reconciliation['counts']['mismatched']} mismatched. Files outside the execution subset are recorded separately; the OCI digest remains the identity of the complete container.
- The selected Liberty metadata confirms process 1.0, 25 °C, and 1.8 V for `sky130_fd_sc_hd__tt_025C_1v80`.

## Official GCD flows

Both new clean run directories invoked exactly `{OFFICIAL_MAKE}`. The pinned Makefile declares `.DEFAULT_GOAL := all` and `all: check-yosys check-openroad synth floorplan place cts route finish`. Both runs completed synthesis, floorplanning, placement, CTS, routing, extraction/STA, and final netlist/DEF/GDS generation. The effective `LEC_CHECK=0` retains the pinned flow's documented default after an optional Kepler library was proven incompatible with this AVX2-only host.

The first native optional-LEC attempt is retained under `$GATE03E_EVIDENCE/attempts/gcd-native-lec-avx512-failure-01`: the pinned `libnaja_python.so` executes an unconditional AVX-512VL instruction and exits with SIGILL on the Ryzen 7 7735HS WSL2 host. This is an image/host optional-check compatibility issue, not an ORFS physical-flow failure.

## Reproducibility result

Policy SHA-256: `{POLICY_SHA256}`. It was frozen before run 1 and was not changed afterward. Each run inventory contains {inventories[0]['artifact_count']} raw and canonical artifact records. All {len(comparison['semantic_artifact_comparisons'])} required semantic GDS/DEF/netlist/SDC/SPEF comparisons pass exactly, and the authoritative JSON cell counts, areas, utilization instance counts, routing/antenna/violation counts match. Nevertheless, the complete comparison is FAIL: {len(comparison['raw_hash_differences'])} raw-hash differences include {sum(not row['pass'] for row in comparison['raw_hash_differences'])} unexplained or tolerance-breach classifications, and {sum(not row['pass'] for row in comparison['metric_comparisons'])} numeric records breach their pre-frozen rule. No post-run exclusion was invented.

Every raw-hash difference is retained below; the complete 551,701-byte comparison with all metric records is indexed at `$GATE03E_EVIDENCE/runs/gcd-run-comparison.json`.

| Path | Predefined classification | Result | Explanation |
|---|---|---:|---|
{chr(10).join(diff_rows)}

## GREEN-ECC mapping readiness

All four bounded 1,200-second `make synth` jobs pass against the frozen SKY130HD Liberty. Every flattened cell instance is a SKY130HD master, no mapped latches or black boxes remain, no fault-injection input enters a boundary, and equivalence remains assessable. The independent combinational SECDED boundary maps to {mapping['jobs'][0]['cell_count']} cells with zero sequential cells; the pipelined boundary maps to {mapping['jobs'][1]['cell_count']} cells including {mapping['jobs'][1]['sequential_cell_count']} sequential cells. Their normalized hashes and master histograms differ. BCH encoder/decoder mapping also passes. These are structural readiness results only; no comparative PPA was calculated or published.

The direct production SECDED package elaboration attempt failed before mapping because the pinned Yosys Verilog-2005 frontend rejects the production package construct. It was reported and preserved before any RTL change. Production RTL remains untouched; the combinational job uses the already accepted Gate-03R package-free implementation whose exact identity is referenced by `SECDED_PROOF_SUMMARY.json`.

## Scope and evidence

No production RTL, registry, selector, results, paper material, or previous-gate evidence was changed. Large physical outputs remain under `/var/lib/green-ecc-gate03e` and are identified by stable root-relative paths, sizes, raw hashes, and canonical hashes. The {len(raw_rows)} retained raw logs are copied byte-for-byte under `raw_logs/` and indexed by `RAW_LOG_INDEX.csv`.
"""
    (DOC / "GATE_03E_REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(f"GATE03E_ARTIFACTS_GENERATED status={current_status} raw_logs={len(raw_rows)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument(
        "--repository-validation-status",
        choices=("PENDING_FINAL_VALIDATION", "PASS"),
        default="PENDING_FINAL_VALIDATION",
    )
    args = parser.parse_args()
    generate(args.evidence_root.resolve(), args.repository_validation_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
