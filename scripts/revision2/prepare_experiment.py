#!/usr/bin/env python3
"""Freeze the complete Revision-2 source and policy bundle before execution."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


DEFAULT_ROOT = Path("/var/lib/green-ecc-date2027-revision2")
AUTHORITATIVE_ROOT = Path("/var/lib/green-ecc-date2027-final")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def verify_manifest(root: Path, manifest: Path) -> None:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = root / relative.strip()
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"authoritative policy mismatch: {relative}")


def copy_snapshot(repo: Path, snapshot: Path, paths: set[str]) -> list[dict[str, object]]:
    records = []
    for relative in sorted(paths):
        source = repo / relative
        if not source.is_file():
            raise SystemExit(f"missing Revision-2 freeze input: {relative}")
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        destination.chmod(0o444)
        records.append({"path": relative, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
    return records


def freeze_hash_manifest(policy: Path) -> None:
    rows = []
    for path in sorted(item for item in policy.rglob("*") if item.is_file()):
        if path.name != "frozen-bundle.sha256":
            rows.append(f"{sha256(path)}  {path.relative_to(policy).as_posix()}")
    (policy / "frozen-bundle.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run as root inside Ubuntu WSL2")

    repo = args.repo.resolve()
    root = args.evidence_root
    if root.exists():
        raise SystemExit(f"refusing to overwrite Revision-2 evidence root: {root}")

    contract_path = repo / "scripts/revision2/contract_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    protocol = (repo / "docs/date2027/revision2/REV2_MULTI_SEED_PROTOCOL.md").read_text(encoding="utf-8")
    if "FROZEN_BEFORE_EXECUTION" not in protocol:
        raise SystemExit("Revision-2 protocol is not frozen")
    qualification = json.loads((repo / "docs/date2027/revision2/REV2_HSIAO_QUALIFICATION.json").read_text(encoding="utf-8"))
    rtl_freeze = json.loads((repo / "docs/date2027/revision2/REV2_HSIAO_RTL_FREEZE.json").read_text(encoding="utf-8"))
    if qualification["verdict"] != "HSIAO_EXACT_IDENTITY_PASS" or not qualification["ppa_authorized"]:
        raise SystemExit("Hsiao is not authorized for Revision-2 PPA")
    if rtl_freeze["state"] != "REV2_HSIAO_RTL_FROZEN_BEFORE_PHYSICAL_EXECUTION":
        raise SystemExit("Hsiao RTL freeze is not valid")

    seeds = contract["flow"]["seeds"]
    if seeds != [11, 13, 17, 19, 23]:
        raise SystemExit("frozen seed set changed")
    expected_pairs = {(architecture, seed) for architecture in contract["architectures"] for seed in seeds}
    actual_pairs = {(run["architecture"], run["seed"]) for run in contract["runs"]}
    if actual_pairs != expected_pairs or len(contract["runs"]) != 20:
        raise SystemExit("Revision-2 matrix is not the frozen 4x5 design")

    for relative, expected in contract["source_hashes"].items():
        path = repo / relative
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"frozen RTL/boundary hash mismatch: {relative}")
    freeze_sources = {item["path"]: item["sha256"] for item in rtl_freeze["source_files"]}
    for relative in (
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v2_algorithmic_decoder.sv",
        "scripts/revision2/rtl/rev2_hsiao_boundary.sv",
    ):
        if sha256(repo / relative) != freeze_sources[relative]:
            raise SystemExit(f"post-qualification Hsiao source change: {relative}")

    gate03f_policy = AUTHORITATIVE_ROOT / "policy"
    verify_manifest(gate03f_policy, gate03f_policy / "frozen-bundle.sha256")
    environment_path = gate03f_policy / "DATE_FINAL_PHYSICAL_ENVIRONMENT.json"
    if sha256(environment_path) != contract["gate03f_environment_manifest_sha256"]:
        raise SystemExit("authoritative Gate-03F environment mismatch")

    image = contract["technology"]["container_image"]
    image_inspect = json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]
    if image_inspect["Id"] != image.split("@", 1)[1]:
        raise SystemExit("local Docker image does not match the frozen digest")

    policy = root / "policy"
    snapshot = policy / "repo_snapshot"
    traces = policy / "traces"
    authoritative = policy / "authoritative_gate03f"
    runs = root / "runs"
    snapshot.mkdir(parents=True)
    traces.mkdir()
    authoritative.mkdir()
    runs.mkdir()

    snapshot_paths = {
        path.relative_to(repo).as_posix()
        for path in (repo / "scripts/revision2").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    snapshot_paths.update(contract["source_hashes"])
    snapshot_paths.update(
        path.relative_to(repo).as_posix()
        for path in (repo / "docs/date2027/revision2").iterdir()
        if path.is_file()
    )
    source_records = copy_snapshot(repo, snapshot, snapshot_paths)

    gate03f_trace_root = gate03f_policy / "traces"
    for source in sorted(gate03f_trace_root.iterdir()):
        if source.is_file():
            shutil.copy2(source, traces / source.name)
    for name in ("DATE_FINAL_PHYSICAL_ENVIRONMENT.json", "IMMUTABLE_INPUT_MANIFEST.json", "frozen-bundle.sha256"):
        shutil.copy2(gate03f_policy / name, authoritative / name)

    trace_manifest = json.loads((traces / "TRACE_MANIFEST.json").read_text(encoding="utf-8"))
    if sha256(traces / "TRACE_MANIFEST.json") != contract["power"]["trace_manifest_sha256"]:
        raise SystemExit("copied trace manifest changed")
    needed = {(family, "no_error") for family in ("conventional_secded", "hsiao")}
    records_by_key = {(row["family"], row["trace_class"]): row for row in trace_manifest["traces"]}
    for key in needed:
        row = records_by_key[key]
        if sha256(traces / row["file"]) != row["compressed_sha256"]:
            raise SystemExit(f"copied trace hash mismatch: {row['file']}")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, text=True)
    (policy / "repository-status-at-freeze.txt").write_text(status, encoding="utf-8", newline="\n")
    frozen_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": 1,
        "state": "REV2_EXPERIMENT_FROZEN_BEFORE_EXECUTION",
        "frozen_at_utc": frozen_at,
        "evidence_root": str(root),
        "contract": contract,
        "authoritative_gate03f_environment_sha256": sha256(environment_path),
        "authoritative_gate03f_policy_sha256": sha256(gate03f_policy / "frozen-bundle.sha256"),
        "hsiao_qualification": qualification,
        "repository": {
            "git_commit": head,
            "worktree_status_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
            "snapshot_file_count": len(source_records),
            "snapshot_files": source_records,
        },
        "trace_manifest_sha256": sha256(traces / "TRACE_MANIFEST.json"),
        "exact_commands": {
            "prepare": f"python3 scripts/revision2/prepare_experiment.py --repo {repo}",
            "matrix": f"python3 {root}/policy/repo_snapshot/scripts/revision2/run_matrix.py",
            "analysis": f"python3 {root}/policy/repo_snapshot/scripts/revision2/analyze_results.py",
        },
    }
    write_json(policy / "REV2_EXPERIMENT_MANIFEST.json", manifest)
    write_json(
        policy / "REV2_IMMUTABLE_INPUT_MANIFEST.json",
        {
            "schema_version": 1,
            "algorithm": "sha256-raw-bytes",
            "repository_snapshot": source_records,
            "trace_manifest_sha256": sha256(traces / "TRACE_MANIFEST.json"),
            "authoritative_environment_manifest_sha256": sha256(environment_path),
        },
    )
    freeze_hash_manifest(policy)
    for path in (item for item in policy.rglob("*") if item.is_file()):
        path.chmod(0o444)
    for path in sorted((item for item in policy.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o555)
    policy.chmod(0o555)
    print(f"REV2_EXPERIMENT_FROZEN root={root} runs=20 seeds={','.join(map(str, seeds))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
