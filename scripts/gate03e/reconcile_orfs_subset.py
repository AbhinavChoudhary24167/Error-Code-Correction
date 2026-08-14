#!/usr/bin/env python3
"""Hash and compare only the execution-relevant ORFS file subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def describe_path(root: Path, path: Path, entries: dict[str, dict[str, Any]]) -> None:
    relative = path.relative_to(root).as_posix()
    if path.is_symlink():
        target = os.readlink(path)
        entries[relative] = {
            "kind": "symlink",
            "target": target,
            "sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
        }
        return
    if path.is_file():
        entries[relative] = {
            "kind": "file",
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        return
    if path.is_dir():
        for child in sorted(path.iterdir(), key=lambda candidate: candidate.name):
            describe_path(root, child, entries)


def load_scope(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def build_manifest(root: Path, scope_path: Path, origin: str) -> dict[str, Any]:
    scope, scope_sha256 = load_scope(scope_path)
    root = root.resolve()
    entries: dict[str, dict[str, Any]] = {}
    missing_selections: list[str] = []
    for relative in scope["selected_paths"]:
        selected = root / relative
        if not selected.exists() and not selected.is_symlink():
            missing_selections.append(relative)
            continue
        describe_path(root, selected, entries)
    return {
        "schema_version": 1,
        "origin": origin,
        "scope_sha256": scope_sha256,
        "selected_paths": scope["selected_paths"],
        "missing_selected_paths": sorted(missing_selections),
        "top_level_entries": sorted(item.name for item in root.iterdir()),
        "entries": dict(sorted(entries.items())),
    }


def compare_manifests(source: dict[str, Any], container: dict[str, Any]) -> dict[str, Any]:
    if source["scope_sha256"] != container["scope_sha256"]:
        raise SystemExit("source and container manifests use different scope definitions")
    source_entries = source["entries"]
    container_entries = container["entries"]
    source_paths = set(source_entries)
    container_paths = set(container_entries)
    shared_paths = sorted(source_paths & container_paths)
    identical: list[str] = []
    mismatched: list[dict[str, Any]] = []
    for path in shared_paths:
        if source_entries[path] == container_entries[path]:
            identical.append(path)
        else:
            mismatched.append(
                {
                    "path": path,
                    "source": source_entries[path],
                    "container": container_entries[path],
                }
            )

    selected_top_levels = {
        item.split("/", 1)[0] for item in source["selected_paths"]
    }
    source_top = set(source["top_level_entries"]) - selected_top_levels
    container_top = set(container["top_level_entries"]) - selected_top_levels
    missing = sorted(source_paths - container_paths)
    additional = sorted(container_paths - source_paths)
    passed = not (
        source["missing_selected_paths"]
        or container["missing_selected_paths"]
        or missing
        or mismatched
    )
    return {
        "schema_version": 1,
        "scope_sha256": source["scope_sha256"],
        "byte_identity_pass": passed,
        "byte_identical_reconciled_files": identical,
        "files_missing_from_container": missing,
        "additional_container_files": additional,
        "mismatched_execution_relevant_files": mismatched,
        "missing_selected_paths": {
            "source": source["missing_selected_paths"],
            "container": container["missing_selected_paths"],
        },
        "outside_subset_top_level_population": {
            "shared_names_not_compared": sorted(source_top & container_top),
            "source_only_names_not_compared": sorted(source_top - container_top),
            "container_only_names_not_compared": sorted(container_top - source_top),
            "identity_rule": "Recorded only; the immutable OCI digest identifies the complete container.",
        },
        "counts": {
            "byte_identical": len(identical),
            "missing_from_container": len(missing),
            "additional_in_container": len(additional),
            "mismatched": len(mismatched),
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("--root", type=Path, required=True)
    manifest_parser.add_argument("--scope", type=Path, required=True)
    manifest_parser.add_argument("--origin", required=True)
    manifest_parser.add_argument("--output", type=Path, required=True)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--source", type=Path, required=True)
    compare_parser.add_argument("--container", type=Path, required=True)
    compare_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "manifest":
        write_json(args.output, build_manifest(args.root, args.scope, args.origin))
        return 0

    source = json.loads(args.source.read_text(encoding="utf-8"))
    container = json.loads(args.container.read_text(encoding="utf-8"))
    comparison = compare_manifests(source, container)
    write_json(args.output, comparison)
    print(json.dumps(comparison["counts"], sort_keys=True))
    return 0 if comparison["byte_identity_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
