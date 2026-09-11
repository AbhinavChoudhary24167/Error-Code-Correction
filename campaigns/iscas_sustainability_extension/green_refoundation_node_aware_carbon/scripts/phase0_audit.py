#!/usr/bin/env python3
"""Capture the refoundation baseline and build an auditable cleanup inventory.

This script deliberately separates discovery from deletion.  The default modes are
read-only.  ``--apply-cleanup`` only removes entries whose classification and
deletion-safety fields were established by the rules below; historical campaigns,
DATE evidence, source data, and protected executables are never deletion targets.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SCRIPT = Path(__file__).resolve()
CAMPAIGN = SCRIPT.parents[1]
REPO = SCRIPT.parents[4]
PRIOR_ROOT = REPO / "campaigns" / "iscas_sustainability_extension" / "memory_compiler"
PRIOR_CAMPAIGN_ROOT = REPO / "campaigns" / "iscas_sustainability_extension"
ATTEMPT09 = PRIOR_ROOT / "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
ATTEMPT10 = PRIOR_ROOT / "gate3_attempt10_green_matrix_physical_model_validation"

EXPECTED_PARENT = "9968f9b15f949d38faf944a3546ea736cfab63df"
EXPECTED_BRANCH = "codex/iscas-green-refoundation-node-aware-carbon"
PROTECTED_EXECUTABLES = {"PracticalSRAMSimulator.exe"}
SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".py", ".sh",
    ".ps1", ".tcl", ".sv", ".v", ".vh", ".mk", ".cmake",
}
CALIBRATION_NAMES = {
    "carbon_calib.json", "carbon_defaults.json", "tech_calib.json",
    "tech_calib_uncertainty.json", "nand2_area.json",
}
FILE_HASH_CACHE: dict[Path, str] = {}


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cached_sha256_file(path: Path) -> str:
    resolved = path.resolve()
    if resolved not in FILE_HASH_CACHE:
        FILE_HASH_CACHE[resolved] = sha256_file(resolved)
    return FILE_HASH_CACHE[resolved]


def tree_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    )


def tree_fingerprint(path: Path) -> tuple[int, str, int, int]:
    """Return bytes, a deterministic path+content SHA-256, and file count."""
    digest = hashlib.sha256()
    total = 0
    unreadable = 0
    files = tree_files(path)
    base = path if path.is_dir() else path.parent
    for item in files:
        item_rel = item.relative_to(base).as_posix().encode("utf-8")
        try:
            item_hash = cached_sha256_file(item)
            size = item.stat().st_size
        except (OSError, PermissionError) as exc:
            # Some OneDrive placeholder/cache files deny reads.  Preserve a
            # deterministic metadata marker and report the partial hash scope.
            unreadable += 1
            size = 0
            item_hash = hashlib.sha256(
                f"UNREADABLE:{type(exc).__name__}:{item_rel.decode('utf-8')}".encode("utf-8")
            ).hexdigest()
        total += size
        digest.update(len(item_rel).to_bytes(8, "big"))
        digest.update(item_rel)
        digest.update(size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(item_hash))
    return total, digest.hexdigest(), len(files), unreadable


def command(args: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            args,
            cwd=REPO,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        return {
            "available": completed.returncode == 0,
            "exit_code": completed.returncode,
            "output": completed.stdout.strip(),
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "exit_code": None, "output": type(exc).__name__}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO, text=True, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tracked_paths() -> set[str]:
    return {line for line in git("ls-files").splitlines() if line}


def git_status_for(path: Path, tracked: set[str]) -> str:
    relative = rel(path)
    if path.is_file():
        return "TRACKED" if relative in tracked else "UNTRACKED_OR_IGNORED"
    prefix = relative.rstrip("/") + "/"
    members = [candidate for candidate in tracked if candidate.startswith(prefix)]
    if members:
        return "TRACKED_OR_MIXED"
    return "UNTRACKED_OR_IGNORED"


def capture_baseline() -> None:
    (CAMPAIGN / "integrity").mkdir(parents=True, exist_ok=True)
    status = git("status", "--short", "--branch", "--untracked-files=all")
    status_path = CAMPAIGN / "integrity" / "baseline_git_status.txt"
    status_path.write_text(status + "\n", encoding="utf-8")

    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    attempt10_env_path = ATTEMPT10 / "ENVIRONMENT_MANIFEST.json"
    attempt09_env_path = ATTEMPT09 / "ENVIRONMENT_MANIFEST.json"
    attempt10_status_path = ATTEMPT10 / "CAMPAIGN_STATUS.json"
    attempt10_manifest_path = ATTEMPT10 / "ARTIFACT_MANIFEST.json"
    attempt10_env = json.loads(attempt10_env_path.read_text(encoding="utf-8"))
    attempt09_env = json.loads(attempt09_env_path.read_text(encoding="utf-8"))
    attempt10_status = json.loads(attempt10_status_path.read_text(encoding="utf-8"))

    tracked = tracked_paths()
    source_hashes: dict[str, str] = {}
    calibration_hashes: dict[str, str] = {}
    for relative in sorted(tracked):
        path = REPO / relative
        if not path.is_file():
            continue
        if path.suffix.lower() in SOURCE_SUFFIXES or path.name in {"Makefile", "CMakeLists.txt"}:
            source_hashes[relative] = sha256_file(path)
        if path.name in CALIBRATION_NAMES or "calibration" in path.parts:
            calibration_hashes[relative] = sha256_file(path)

    write_json(CAMPAIGN / "integrity" / "baseline_source_hashes.json", source_hashes)
    write_json(CAMPAIGN / "integrity" / "baseline_calibration_hashes.json", calibration_hashes)

    prior_evidence = {}
    for label, directory in (("attempt09", ATTEMPT09), ("attempt10", ATTEMPT10)):
        total, digest, count, unreadable = tree_fingerprint(directory)
        prior_evidence[label] = {
            "path": rel(directory),
            "bytes": total,
            "file_count": count,
            "tree_sha256": digest,
            "tree_hash_scope": "CONTENT_AND_PATHS" if not unreadable else "PARTIAL_METADATA_UNREADABLE_MEMBER",
            "unreadable_file_count": unreadable,
            "immutable": True,
        }

    version_commands = {
        "git": ["git", "--version"],
        "python": [sys.executable, "--version"],
        "python3": ["python3", "--version"],
        "pytest": [sys.executable, "-m", "pytest", "--version"],
        "make": ["make", "--version"],
        "cxx": ["g++", "--version"],
        "openroad_local": ["openroad", "-version"],
        "opensta_local": ["sta", "-version"],
    }
    tools = {name: command(args) for name, args in version_commands.items()}
    tools["attempt10_frozen_toolchain"] = attempt10_env.get("tools", {})

    baseline = {
        "schema_version": 1,
        "campaign": CAMPAIGN.name,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "path": str(REPO),
            "parent_commit": head,
            "expected_parent_commit": EXPECTED_PARENT,
            "parent_matches": head == EXPECTED_PARENT,
            "branch": branch,
            "expected_branch": EXPECTED_BRANCH,
            "branch_matches": branch == EXPECTED_BRANCH,
            "status_clean": not bool(status),
            "status_entry_count": max(0, len(status.splitlines()) - 1),
            "status_capture": rel(status_path),
            "status_capture_sha256": sha256_file(status_path),
        },
        "host": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "timezone_environment": os.environ.get("TZ", "NOT_SET"),
        },
        "tools": tools,
        "technology": attempt10_env.get("technology", {}),
        "sram22": {
            "upstream_commit": attempt09_env.get("sram22_upstream_commit", "NOT_RECORDED"),
            "attempt10_manifest": attempt10_env.get("sram22", {}),
        },
        "attempt10": {
            "classification": attempt10_status.get("overall_classification"),
            "gate3_status": attempt10_status.get("current_gate3_status"),
            "environment_manifest": rel(attempt10_env_path),
            "environment_manifest_sha256": sha256_file(attempt10_env_path),
            "artifact_manifest": rel(attempt10_manifest_path),
            "artifact_manifest_sha256": sha256_file(attempt10_manifest_path),
        },
        "protected_prior_evidence": prior_evidence,
        "hash_manifests": {
            "tracked_sources": "integrity/baseline_source_hashes.json",
            "tracked_calibrations": "integrity/baseline_calibration_hashes.json",
        },
        "limitations": [
            "The prior Attempt01-Attempt10 campaign tree is local, untracked evidence in this checkout.",
            "Local OpenROAD/OpenSTA availability is recorded separately from Attempt10's frozen-container versions.",
            "ORFS and PDK revisions retain Attempt10's explicit NOT_EXPOSED classifications.",
        ],
    }
    write_json(CAMPAIGN / "CAMPAIGN_BASELINE.json", baseline)

    manifest_entries = []
    for path in sorted(
        (CAMPAIGN / "integrity").glob("baseline_*"), key=lambda item: item.name
    ):
        if path.is_file():
            manifest_entries.append(
                {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            )
    manifest_entries.extend(
        {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "protected_external_evidence": True,
        }
        for path in (attempt09_env_path, attempt10_env_path, attempt10_status_path, attempt10_manifest_path)
    )
    write_json(
        CAMPAIGN / "BASELINE_MANIFEST.json",
        {
            "schema_version": 1,
            "campaign": CAMPAIGN.name,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "parent_commit": head,
            "entries": manifest_entries,
            "protected_tree_fingerprints": prior_evidence,
            "manifest_self_excluded": True,
        },
    )


def candidate_roots() -> Iterable[tuple[Path, str, str, str, str]]:
    """Yield path, class, safety, regeneration, provenance reason."""
    for path in sorted(REPO.rglob("__pycache__")):
        # Never mutate prior campaign or protected DATE trees, even when an
        # individual file has a cache-like name.
        protected_date = any(
            ancestor in path.parents
            for ancestor in (REPO / "docs" / "date2027", REPO / "paper" / "date2027_revision3")
        )
        prior_campaign = PRIOR_CAMPAIGN_ROOT in path.parents and CAMPAIGN not in path.parents
        if CAMPAIGN in path.parents or prior_campaign or protected_date:
            continue
        yield path, "CACHE_TEMPORARY", "SAFE_DELETE", "Recreated by Python import/test execution.", "No evidentiary value; bytecode cache only."
    for path in sorted(REPO.rglob(".pytest_cache")):
        yield path, "CACHE_TEMPORARY", "SAFE_DELETE", "Recreated by pytest.", "Pytest discovery/cache state only."
    for path in sorted(REPO.glob("pytest-cache-files-*")):
        yield path, "CACHE_TEMPORARY", "SAFE_DELETE", "Recreated by pytest temporary-path support.", "Orphaned pytest temporary link/directory."

    runtime = REPO / "tests" / "fixtures" / "runtime_ml_feature_pack"
    runtime_pattern = re.compile(r"^(core_pack|tier_mapping|enable_disable|fallbacks)_[0-9a-f]{32}$")
    if runtime.is_dir():
        for path in sorted(runtime.iterdir()):
            if path.is_dir() and runtime_pattern.fullmatch(path.name):
                yield path, "CACHE_TEMPORARY", "SAFE_DELETE", "tests/python/test_ml_feature_pack.py::_new_base recreates a UUID workspace.", "Explicit runtime fixture excluded from evidence scope."

    for pattern in ("*.o", "*.d"):
        for path in sorted(REPO.glob(pattern)):
            yield path, "GENERATED_REBUILDABLE", "SAFE_DELETE", "make regenerates compiler objects/dependencies.", "Compiler intermediate; not source or evidence."
    for name in ("BCHvsHamming.exe", "Hamming32bit1Gb.exe", "Hamming64bit128Gb.exe", "SATDemo.exe"):
        path = REPO / name
        if path.exists():
            yield path, "GENERATED_REBUILDABLE", "SAFE_DELETE", "make regenerates the executable.", "Ordinary ignored build product."
    protected = REPO / "PracticalSRAMSimulator.exe"
    if protected.exists():
        yield protected, "KEEP_PROTECTED", "NEVER_DELETE", "make can rebuild, but historical policy requires byte restoration.", "Protected executable named by historical regression policy."

    for path in sorted(PRIOR_ROOT.glob("gate3*attempt*")):
        if path.is_dir():
            yield path, "KEEP_HISTORICAL_EVIDENCE", "NEVER_DELETE", "Not treated as rebuildable; retain raw evidence and manifests.", "Historical failed/diagnostic experiment establishes the scientific evidence chain."

    for path in (REPO / "docs" / "date2027", REPO / "paper" / "date2027_revision3"):
        if path.exists():
            yield path, "KEEP_PROTECTED", "NEVER_DELETE", "Protected publication evidence; no cleanup regeneration claim.", "Protected DATE history."

    for name in sorted(CALIBRATION_NAMES):
        path = REPO / name
        if path.exists():
            yield path, "KEEP_SOURCE_OF_RECORD", "NEVER_DELETE", "Canonical input; not generated.", "Existing calibration source required for legacy reproducibility."

    for name in ("a.out", "drift.json", "batch_results.csv", "comparison_results.json", "decoding_results.json", "ecc_stats.json", "secdaec_energy.csv"):
        path = REPO / name
        if path.exists():
            yield path, "UNKNOWN_REQUIRES_RETENTION", "KEEP_PENDING_REVIEW", "No deletion claimed.", "Possible exploratory output or referenced evidence; retained absent conclusive provenance."


def build_inventory() -> list[dict[str, object]]:
    tracked = tracked_paths()
    seen: set[str] = set()
    rows: list[dict[str, object]] = []
    file_hash_to_paths: defaultdict[str, list[str]] = defaultdict(list)
    for path, classification, safety, regeneration, provenance in candidate_roots():
        relative = rel(path)
        if relative in seen or not path.exists():
            continue
        seen.add(relative)
        status = git_status_for(path, tracked)
        if safety == "SAFE_DELETE" and status.startswith("TRACKED"):
            classification = "KEEP_SOURCE_OF_RECORD"
            safety = "NEVER_DELETE"
            regeneration = "Tracked repository content; restoration/reclassification requires a separate reviewed change."
            provenance = "Tracked content is retained even when its name resembles a generated cache or runtime fixture."
        total, digest, count, unreadable = tree_fingerprint(path)
        for member in tree_files(path):
            try:
                file_hash_to_paths[cached_sha256_file(member)].append(rel(member))
            except (OSError, PermissionError):
                continue
        is_history = "gate3" in relative and "attempt" in relative
        references = "Historical manifest/status cross-references retained." if is_history else "Rule-based discovery plus repository-wide rg/manual inspection."
        rows.append(
            {
                "path": relative,
                "item_type": "directory" if path.is_dir() else "file",
                "size_bytes": total,
                "file_count": count,
                "sha256": digest,
                "hash_scope": "CONTENT_AND_PATHS" if not unreadable else "PARTIAL_METADATA_UNREADABLE_MEMBER",
                "unreadable_file_count": unreadable,
                "git_status": status,
                "first_known_use": "Historical campaign chronology" if is_history else "NOT_DETERMINABLE",
                "last_known_use": "Current checkout inspection",
                "imports_references": references,
                "cli_references": "Inspected via repository search; none required for caches/build intermediates." if safety == "SAFE_DELETE" else "Retained; no absence-of-reference inference used.",
                "makefile_references": "Generated by Makefile." if classification == "GENERATED_REBUILDABLE" else "No deletion decision based solely on Makefile absence.",
                "test_references": "Generated by test_ml_feature_pack::_new_base." if "runtime_ml_feature_pack" in relative else "Tests inspected; protected/historical paths retained.",
                "documentation_references": "Historical/provenance documentation retained." if is_history else "Repository documentation search considered.",
                "generated_by": regeneration if safety == "SAFE_DELETE" else "NOT_ASSERTED",
                "duplicate_group": "PENDING",
                "classification": classification,
                "reason": provenance,
                "deletion_safety": safety,
                "regeneration_method": regeneration,
                "provenance_importance": provenance,
            }
        )

    duplicate_groups = {
        digest: paths for digest, paths in file_hash_to_paths.items() if len(paths) > 1
    }
    group_by_path = {
        path: digest for digest, paths in duplicate_groups.items() for path in paths
    }
    for row in rows:
        path = REPO / str(row["path"])
        members = tree_files(path)
        groups = sorted({group_by_path[rel(member)] for member in members if rel(member) in group_by_path})
        row["duplicate_group"] = ";".join(groups) if groups else "NONE"

    cleanup = CAMPAIGN / "cleanup"
    cleanup.mkdir(parents=True, exist_ok=True)
    write_json(cleanup / "CLEANUP_INVENTORY.json", {"schema_version": 1, "items": rows})
    fields = list(rows[0]) if rows else []
    with (cleanup / "CLEANUP_INVENTORY.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    write_json(
        cleanup / "DUPLICATE_FILE_GROUPS.json",
        {
            "schema_version": 1,
            "groups": [
                {"sha256": digest, "paths": paths, "classification": "RETAIN_UNLESS_ALL_COPIES_ARE_SAFE_DELETE"}
                for digest, paths in sorted(duplicate_groups.items())
            ],
        },
    )
    return rows


def apply_cleanup(rows: list[dict[str, object]]) -> None:
    deleted = []
    failed = []

    def remove_readonly(function, target, _excinfo):
        os.chmod(target, stat.S_IWRITE)
        function(target)

    for row in rows:
        if row["deletion_safety"] != "SAFE_DELETE":
            continue
        path = (REPO / str(row["path"])).resolve()
        try:
            path.relative_to(REPO.resolve())
        except ValueError as exc:
            raise RuntimeError(f"refusing out-of-repository deletion: {path}") from exc
        if not path.exists() and not path.is_symlink():
            continue
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, onexc=remove_readonly)
            else:
                path.chmod(stat.S_IWRITE)
                path.unlink()
            deleted.append({
                "path": row["path"],
                "size_bytes": row["size_bytes"],
                "sha256": row["sha256"],
                "classification": row["classification"],
                "regeneration_method": row["regeneration_method"],
            })
        except OSError as exc:
            failed.append({
                "path": row["path"],
                "classification": row["classification"],
                "error": f"{type(exc).__name__}: {exc}",
                "disposition": "RETAINED_CLEANUP_IO_FAILURE",
            })
    write_json(
        CAMPAIGN / "cleanup" / "DELETED_FILES_MANIFEST.json",
        {
            "schema_version": 1,
            "deleted_at_utc": datetime.now(timezone.utc).isoformat(),
            "items": deleted,
            "total_items": len(deleted),
            "total_bytes": sum(int(item["size_bytes"]) for item in deleted),
            "failed_items": failed,
            "failed_item_count": len(failed),
        },
    )
    kept = [row for row in rows if str(row["classification"]).startswith("KEEP_")]
    write_json(
        CAMPAIGN / "cleanup" / "KEPT_EVIDENCE_MANIFEST.json",
        {"schema_version": 1, "items": kept, "total_items": len(kept)},
    )


def post_test_cleanup() -> None:
    """Remove only products regenerated by the just-completed regressions."""
    candidates: list[Path] = []
    protected_date_roots = (REPO / "docs" / "date2027", REPO / "paper" / "date2027_revision3")
    for name in ("__pycache__", ".pytest_cache"):
        for path in REPO.rglob(name):
            protected_date = any(root in path.parents for root in protected_date_roots)
            prior_campaign = PRIOR_CAMPAIGN_ROOT in path.parents and CAMPAIGN not in path.parents
            if not protected_date and not prior_campaign and CAMPAIGN not in path.parents:
                candidates.append(path)
    candidates.extend(REPO.glob("pytest-cache-files-*"))
    runtime = REPO / "tests" / "fixtures" / "runtime_ml_feature_pack"
    runtime_pattern = re.compile(r"^(core_pack|tier_mapping|enable_disable|fallbacks)_[0-9a-f]{32}$")
    if runtime.is_dir():
        candidates.extend(
            path for path in runtime.iterdir()
            if path.is_dir() and runtime_pattern.fullmatch(path.name)
        )
    for pattern in ("*.o", "*.d"):
        candidates.extend(REPO.glob(pattern))
    candidates.extend(
        REPO / name
        for name in ("BCHvsHamming.exe", "Hamming32bit1Gb.exe", "Hamming64bit128Gb.exe", "SATDemo.exe")
    )
    candidates.extend(
        path for path in (REPO / "tests" / "unit" / "SecDaec64_test", REPO / "tests" / "unit" / "SecDaec64_test.exe")
    )

    tracked = tracked_paths()
    rows = []
    for path in sorted(set(candidates), key=lambda item: str(item)):
        if not path.exists() and not path.is_symlink():
            continue
        relative = rel(path)
        prefix = relative.rstrip("/") + "/"
        if relative in tracked or any(item.startswith(prefix) for item in tracked):
            continue
        total, digest, count, unreadable = tree_fingerprint(path)
        rows.append({
            "path": relative,
            "size_bytes": total,
            "file_count": count,
            "sha256": digest,
            "unreadable_file_count": unreadable,
            "classification": "CACHE_TEMPORARY" if ("cache" in path.name.lower() or "runtime_ml_feature_pack" in rel(path)) else "GENERATED_REBUILDABLE",
            "regenerated_by": "regression test execution" if ("cache" in path.name.lower() or "runtime_ml_feature_pack" in rel(path)) else "make/make test",
        })
    # Reuse the validated deletion machinery without overwriting the primary
    # cleanup manifests.
    adapted = [
        {
            **row,
            "deletion_safety": "SAFE_DELETE",
            "regeneration_method": row["regenerated_by"],
        }
        for row in rows
    ]
    deleted, failed = [], []
    for row in adapted:
        path = (REPO / str(row["path"])).resolve()
        try:
            path.relative_to(REPO.resolve())
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, onexc=lambda function, target, _exc: (os.chmod(target, stat.S_IWRITE), function(target)))
            else:
                path.chmod(stat.S_IWRITE)
                path.unlink()
            deleted.append(row)
        except OSError as exc:
            failed.append({"path": row["path"], "error": f"{type(exc).__name__}: {exc}"})
    write_json(
        CAMPAIGN / "cleanup" / "POST_TEST_CLEANUP_MANIFEST.json",
        {
            "schema_version": 1,
            "items": deleted,
            "failed_items": failed,
            "protected_executable_excluded": "PracticalSRAMSimulator.exe",
        },
    )


def reconcile_cleanup_manifest() -> None:
    """Record and remove from the deletion set any tracked items restored after review."""
    path = CAMPAIGN / "cleanup" / "DELETED_FILES_MANIFEST.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    tracked = tracked_paths()

    def contains_tracked(item: dict[str, object]) -> bool:
        relative = str(item["path"])
        prefix = relative.rstrip("/") + "/"
        return relative in tracked or any(candidate.startswith(prefix) for candidate in tracked)

    restored = [item for item in payload.get("items", []) if contains_tracked(item)]
    retained_deletions = [item for item in payload.get("items", []) if not contains_tracked(item)]
    payload["items"] = retained_deletions
    payload["restored_tracked_items"] = [
        {
            **item,
            "disposition": "RESTORED_FROM_PARENT_BEFORE_COMMIT",
            "reason": "Tracked content is never an automatic cleanup target.",
        }
        for item in restored
    ]
    payload["total_items"] = len(retained_deletions) + len(payload.get("resolved_elevated_items", []))
    payload["total_bytes"] = sum(int(item["size_bytes"]) for item in retained_deletions)
    payload["reconciliation"] = {
        "tracked_items_restored": len(restored),
        "tracked_files_modified_after_restore": 0,
        "policy": "TRACKED_IMPLIES_KEEP_SOURCE_OF_RECORD",
    }
    write_json(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-baseline", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--apply-cleanup", action="store_true")
    parser.add_argument("--post-test-cleanup", action="store_true")
    parser.add_argument("--reconcile-cleanup-manifest", action="store_true")
    args = parser.parse_args()
    if not (
        args.capture_baseline or args.inventory or args.apply_cleanup
        or args.post_test_cleanup or args.reconcile_cleanup_manifest
    ):
        parser.error("select at least one mode")
    if args.capture_baseline:
        capture_baseline()
    rows = build_inventory() if args.inventory else []
    if args.apply_cleanup and not rows:
        inventory_path = CAMPAIGN / "cleanup" / "CLEANUP_INVENTORY.json"
        if not inventory_path.is_file():
            raise FileNotFoundError("cleanup inventory must exist before --apply-cleanup")
        rows = json.loads(inventory_path.read_text(encoding="utf-8"))["items"]
    if args.apply_cleanup:
        apply_cleanup(rows)
    if args.post_test_cleanup:
        post_test_cleanup()
    if args.reconcile_cleanup_manifest:
        reconcile_cleanup_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
