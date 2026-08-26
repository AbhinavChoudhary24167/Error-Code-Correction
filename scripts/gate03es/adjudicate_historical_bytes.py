#!/usr/bin/env python3
"""Verify Gate 03E-S historical bytes without working-tree status heuristics."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(f"{path.relative_to(root).as_posix()}\0{path.stat().st_size}\0{sha256(path)}\n")
    return sha256_bytes("".join(rows).encode())


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def head_entries(repo: Path, prefix: str) -> dict[str, str]:
    raw = git(repo, "ls-tree", "-r", "-z", "HEAD", "--", prefix)
    result: dict[str, str] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        _mode, object_type, oid = metadata.decode().split()
        if object_type == "blob":
            result[encoded_path.decode()] = oid
    return result


def index_entries(repo: Path, prefix: str) -> dict[str, str]:
    raw = git(repo, "ls-files", "--stage", "-z", "--", prefix)
    result: dict[str, str] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        _mode, oid, stage = metadata.decode().split()
        if stage == "0":
            result[encoded_path.decode()] = oid
    return result


def blob_tree_hash(repo: Path, prefix: str, entries: dict[str, str]) -> str:
    rows = []
    base = prefix.rstrip("/") + "/"
    for path, oid in sorted(entries.items()):
        data = git(repo, "cat-file", "blob", oid)
        relative = path[len(base) :] if path.startswith(base) else path
        rows.append(f"{relative}\0{len(data)}\0{sha256_bytes(data)}\n")
    return sha256_bytes("".join(rows).encode())


def compare_repo_tree(repo: Path, prefix: str, expected: str) -> dict[str, Any]:
    head = head_entries(repo, prefix)
    index = index_entries(repo, prefix)
    rows: list[dict[str, Any]] = []
    for path in sorted(set(head) | set(index)):
        head_oid, index_oid = head.get(path), index.get(path)
        blob = git(repo, "cat-file", "blob", head_oid) if head_oid else b""
        working_path = repo / path
        working = working_path.read_bytes() if working_path.is_file() else b""
        raw_equal = head_oid is not None and working == blob
        eol_only = not raw_equal and working.replace(b"\r\n", b"\n") == blob
        rows.append(
            {
                "path": path,
                "head_blob_oid": head_oid,
                "index_blob_oid": index_oid,
                "head_index_equal": head_oid == index_oid and head_oid is not None,
                "git_blob_sha256": sha256_bytes(blob) if head_oid else None,
                "working_file_sha256": sha256_bytes(working) if working_path.is_file() else None,
                "working_bytes_equal_git_blob": raw_equal,
                "checkout_crlf_only_difference": eol_only,
            }
        )
    actual = tree_hash(repo / prefix)
    non_eol_differences = [
        row for row in rows if not row["working_bytes_equal_git_blob"] and not row["checkout_crlf_only_difference"]
    ]
    return {
        "path": prefix,
        "recorded_working_tree_sha256": expected,
        "current_working_tree_sha256": actual,
        "working_tree_matches_recorded_sha256": actual == expected,
        "git_blob_tree_sha256": blob_tree_hash(repo, prefix, head),
        "file_count": len(rows),
        "head_index_object_matches": sum(row["head_index_equal"] for row in rows),
        "head_index_object_mismatches": sum(not row["head_index_equal"] for row in rows),
        "working_bytes_equal_git_blob": sum(row["working_bytes_equal_git_blob"] for row in rows),
        "checkout_crlf_only_differences": sum(row["checkout_crlf_only_difference"] for row in rows),
        "non_eol_working_blob_differences": len(non_eol_differences),
        "pass": (
            actual == expected
            and all(row["head_index_equal"] for row in rows)
            and not non_eol_differences
        ),
        "files": rows,
    }


def adjudicate(repo: Path, baseline_path: Path, v1_root: Path, v2_root: Path) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    head = git(repo, "rev-parse", "HEAD").decode().strip()
    tracked_rows = []
    untracked_rows = []
    for prefix, expected in baseline["repo_trees"].items():
        if head_entries(repo, prefix):
            tracked_rows.append(compare_repo_tree(repo, prefix, expected))
        else:
            actual = tree_hash(repo / prefix)
            untracked_rows.append(
                {
                    "path": prefix,
                    "basis": "pre-existing untracked evidence at Gate 03E-S start",
                    "recorded_working_tree_sha256": expected,
                    "current_working_tree_sha256": actual,
                    "pass": actual == expected,
                }
            )
    external_rows = []
    for key, root in (("gate03e", v1_root), ("gate03er", v2_root)):
        expected = baseline["external_trees"][key]["tree_sha256"]
        actual = tree_hash(root)
        external_rows.append(
            {
                "path": str(root),
                "recorded_tree_sha256": expected,
                "current_tree_sha256": actual,
                "pass": actual == expected,
            }
        )
    passed = (
        head == baseline["starting_head"]
        and all(row["pass"] for row in tracked_rows)
        and all(row["pass"] for row in untracked_rows)
        and all(row["pass"] for row in external_rows)
    )
    return {
        "schema_version": 1,
        "adjudication": "gate03es-historical-raw-byte-verification",
        "read_only_source_evidence": True,
        "starting_head": baseline["starting_head"],
        "current_head": head,
        "head_unchanged": head == baseline["starting_head"],
        "interpretation": {
            "git_object_identity": "HEAD blob OIDs are compared directly with index blob OIDs; working-tree filters are bypassed.",
            "recorded_byte_identity": "Current raw working-tree SHA-256 aggregates are compared with the Gate 03E-S starting aggregates.",
            "checkout_eol": "A working file may differ from its Git blob only when CRLF-to-LF normalization reproduces the blob exactly.",
        },
        "tracked_repository_trees": tracked_rows,
        "preexisting_untracked_repository_trees": untracked_rows,
        "external_prior_evidence_trees": external_rows,
        "summary": {
            "tracked_files": sum(row["file_count"] for row in tracked_rows),
            "head_index_object_mismatches": sum(row["head_index_object_mismatches"] for row in tracked_rows),
            "working_bytes_equal_git_blob": sum(row["working_bytes_equal_git_blob"] for row in tracked_rows),
            "checkout_crlf_only_differences": sum(row["checkout_crlf_only_differences"] for row in tracked_rows),
            "non_eol_working_blob_differences": sum(row["non_eol_working_blob_differences"] for row in tracked_rows),
            "recorded_tree_hash_failures": sum(not row["working_tree_matches_recorded_sha256"] for row in tracked_rows)
            + sum(not row["pass"] for row in untracked_rows)
            + sum(not row["pass"] for row in external_rows),
            "pass": passed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--v1-root", type=Path, default=Path("/var/lib/green-ecc-gate03e"))
    parser.add_argument("--v2-root", type=Path, default=Path("/var/lib/green-ecc-gate03er"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = adjudicate(
        args.repo_root.resolve(), args.baseline.resolve(), args.v1_root.resolve(), args.v2_root.resolve()
    )
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if result["summary"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
