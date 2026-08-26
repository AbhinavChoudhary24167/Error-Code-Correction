#!/usr/bin/env python3
"""Validate exact additive path scope and immutable historical/external trees."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gate03es.scope_compatibility import is_registered_additive_path


LEGACY_EDIT_PATHS = {
    "scripts/gate03e/validate_artifacts.py",
    "tests/python/test_gate03_artifacts.py",
}


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
    return hashlib.sha256("".join(rows).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--v1-root", type=Path, default=Path("/var/lib/green-ecc-gate03e"))
    parser.add_argument("--v2-root", type=Path, default=Path("/var/lib/green-ecc-gate03er"))
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    baseline = json.loads(args.baseline.read_text())
    errors: list[str] = []

    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    if branch != baseline["starting_branch"] or head != baseline["starting_head"]:
        errors.append("starting branch or HEAD changed")

    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, text=True, encoding="utf-8"
    ).splitlines()
    status_rows = []
    for line in status:
        path = line[3:].replace("\\", "/")
        allowed = path in LEGACY_EDIT_PATHS or is_registered_additive_path(path)
        status_rows.append({"status": line[:2], "path": path, "allowed": allowed})
        if not allowed:
            errors.append(f"unauthorized repository path: {path}")

    repo_rows = []
    for relative, expected in baseline["repo_trees"].items():
        actual = tree_hash(repo / relative)
        row = {"path": relative, "expected": expected, "actual": actual, "pass": actual == expected}
        repo_rows.append(row)
        if not row["pass"]:
            errors.append(f"historical/protected repository tree changed: {relative}")

    external_rows = []
    for key, root in (("gate03e", args.v1_root), ("gate03er", args.v2_root)):
        expected = baseline["external_trees"][key]["tree_sha256"]
        actual = tree_hash(root)
        row = {"path": str(root), "expected": expected, "actual": actual, "pass": actual == expected}
        external_rows.append(row)
        if not row["pass"]:
            errors.append(f"prior external tree changed: {key}")

    legacy_rows = []
    for row in baseline["legacy_validator_changes"]:
        actual = sha256(repo / row["path"])
        valid = actual == row["after_sha256"] and row["before_sha256"] != row["after_sha256"]
        legacy_rows.append({**row, "actual_after_sha256": actual, "pass": valid})
        if not valid:
            errors.append(f"legacy validator compatibility edit changed: {row['path']}")

    result = {
        "schema_version": 3,
        "status": "PASS" if not errors else "FAIL",
        "starting_branch": branch,
        "starting_head": head,
        "status_rows": status_rows,
        "repository_tree_revalidation": repo_rows,
        "external_tree_revalidation": external_rows,
        "legacy_validator_change_revalidation": legacy_rows,
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
