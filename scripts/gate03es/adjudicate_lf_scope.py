#!/usr/bin/env python3
"""Validate the Gate 03E-S source delta in an isolated LF-only checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


LEGACY_EDITS = (
    "scripts/gate03e/validate_artifacts.py",
    "tests/python/test_gate03_artifacts.py",
)
ADDITIVE_DIRECTORIES = (
    "docs/date2027/rigour_gate_03er",
    "scripts/gate03er",
    "docs/date2027/rigour_gate_03es",
    "scripts/gate03es",
)
ADDITIVE_FILES = ("tests/python/test_gate03er_reproducibility.py",)


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


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True, encoding="utf-8").strip()


def candidate_relpaths(source: Path) -> list[str]:
    paths: list[str] = []
    for relative in (*LEGACY_EDITS, *ADDITIVE_FILES):
        if (source / relative).is_file():
            paths.append(relative)
    for relative in ADDITIVE_DIRECTORIES:
        root = source / relative
        if root.is_dir():
            paths.extend(
                path.relative_to(source).as_posix()
                for path in root.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
            )
    tests = source / "tests/python"
    if tests.is_dir():
        paths.extend(path.relative_to(source).as_posix() for path in tests.glob("test_gate03es_*.py"))
    return sorted(set(paths))


def copy_candidates(source: Path, checkout: Path, candidates: list[str]) -> None:
    for relative in candidates:
        destination = checkout / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)


def adjudicate(source: Path, baseline_path: Path, v1_root: Path, v2_root: Path) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    candidates = candidate_relpaths(source)
    with tempfile.TemporaryDirectory(prefix="gate03es-lf-scope-") as temporary:
        checkout = Path(temporary) / "checkout"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-checkout", "--no-hardlinks", str(source), str(checkout)],
            check=True,
        )
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=checkout, check=True)
        subprocess.run(["git", "config", "core.eol", "lf"], cwd=checkout, check=True)
        subprocess.run(
            ["git", "checkout", "--quiet", "-B", baseline["starting_branch"], f"origin/{baseline['starting_branch']}"],
            cwd=checkout,
            check=True,
        )
        copy_candidates(source, checkout, candidates)

        lf_baseline = json.loads(json.dumps(baseline))
        lf_hash_basis: dict[str, str] = {}
        for relative in lf_baseline["repo_trees"]:
            tracked = bool(git(checkout, "ls-tree", "-r", "--name-only", "HEAD", "--", relative))
            if tracked:
                value = tree_hash(checkout / relative)
                lf_baseline["repo_trees"][relative] = value
                lf_hash_basis[relative] = "starting HEAD Git blobs materialized with core.autocrlf=false"
            else:
                lf_hash_basis[relative] = "recorded Gate 03E-S starting hash for pre-existing untracked evidence"
        temporary_baseline = Path(temporary) / "lf-baseline.json"
        temporary_baseline.write_text(json.dumps(lf_baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        command = [
            sys.executable,
            str(checkout / "scripts/gate03es/validate_scope.py"),
            "--repo-root",
            str(checkout),
            "--baseline",
            str(temporary_baseline),
            "--v1-root",
            str(v1_root),
            "--v2-root",
            str(v2_root),
        ]
        completed = subprocess.run(command, cwd=checkout, text=True, encoding="utf-8", capture_output=True)
        try:
            validation = json.loads(completed.stdout)
        except json.JSONDecodeError:
            validation = {"status": "FAIL", "errors": ["scope validator emitted non-JSON output"]}
        status = git(checkout, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
        return {
            "schema_version": 1,
            "adjudication": "gate03es-isolated-lf-scope-validation",
            "physical_flow_executed": False,
            "temporary_checkout_removed_on_exit": True,
            "source_head": git(source, "rev-parse", "HEAD"),
            "isolated_head": git(checkout, "rev-parse", "HEAD"),
            "isolated_branch": git(checkout, "branch", "--show-current"),
            "isolated_git_config": {
                "core.autocrlf": git(checkout, "config", "--get", "core.autocrlf"),
                "core.eol": git(checkout, "config", "--get", "core.eol"),
            },
            "candidate_delta_policy": (
                "Copy only the two authorized compatibility edits, the pre-existing Gate 03E-R delta, "
                "and additive Gate 03E-S paths. Build/test products are not source-delta candidates."
            ),
            "candidate_paths": candidates,
            "isolated_status_rows": status,
            "lf_protected_hashes": lf_baseline["repo_trees"],
            "lf_protected_hash_basis": lf_hash_basis,
            "validator_exit_status": completed.returncode,
            "validator_stderr": completed.stderr,
            "validator_result": validation,
            "summary": {
                "candidate_path_count": len(candidates),
                "isolated_status_row_count": len(status),
                "validator_status": validation.get("status"),
                "pass": completed.returncode == 0 and validation.get("status") == "PASS",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--v1-root", type=Path, default=Path("/var/lib/green-ecc-gate03e"))
    parser.add_argument("--v2-root", type=Path, default=Path("/var/lib/green-ecc-gate03er"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = adjudicate(
        args.source_repo.resolve(), args.baseline.resolve(), args.v1_root.resolve(), args.v2_root.resolve()
    )
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if result["summary"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
