#!/usr/bin/env python3
"""Freeze the additive breadth-remediation physical campaign before routing."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


DEFAULT_ROOT = Path("/var/lib/green-ecc-date2027-breadth-remediation")
REV2_ROOT = Path("/var/lib/green-ecc-date2027-revision2")
CAMPAIGN = Path("campaigns/date_2027_breadth_remediation")
IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def freeze_manifest(root: Path) -> None:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "frozen-bundle.sha256"):
        rows.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "frozen-bundle.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def make_read_only(root: Path) -> None:
    for path in (item for item in root.rglob("*") if item.is_file()):
        path.chmod(0o444)
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


def check_plan_freeze(repo: Path) -> None:
    for line in (repo / CAMPAIGN / "00_plan_freeze.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        if sha256(repo / CAMPAIGN / relative.strip()) != expected:
            raise SystemExit(f"frozen prospective plan changed: {relative}")


def check_physical_freeze(repo: Path) -> None:
    freeze = repo / CAMPAIGN / "00_physical_contract_freeze.sha256"
    for line in freeze.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        if sha256(repo / CAMPAIGN / relative.strip()) != expected:
            raise SystemExit(f"frozen physical contract input changed: {relative}")


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
        raise SystemExit(f"refusing to overwrite breadth campaign root: {root}")

    check_plan_freeze(repo)
    check_physical_freeze(repo)
    formal = json.loads((repo / CAMPAIGN / "formal/results/A_formal_qualification.json").read_text(encoding="utf-8"))
    synthesis = json.loads((repo / CAMPAIGN / "synthesis/A_synthesis_structural_comparison.json").read_text(encoding="utf-8"))
    if formal["formal_status"] != "PASS" or not formal["physical_authorized"]:
        raise SystemExit("formal gate does not authorize structural routing")
    if synthesis["status"] != "PASS":
        raise SystemExit("mapped synthesis did not establish structural distinctness")

    contract_path = repo / CAMPAIGN / "physical/contract_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["common_flow"]["seeds"] != [11, 13, 17, 19, 23]:
        raise SystemExit("seed set is not the predeclared five-seed set")
    for relative, expected in contract["source_hashes"].items():
        if sha256(repo / relative) != expected:
            raise SystemExit(f"source identity mismatch before physical freeze: {relative}")
    for workstream, expected_architectures in (
        ("A", {"A_hsiao_flat", "A_hsiao_hierarchical"}),
        ("C", {"C_secded_comb", "C_secded_pipe"}),
    ):
        records = [row for row in contract["runs"] if row["workstream"] == workstream]
        pairs = {(row["architecture"], int(row["seed"])) for row in records}
        expected = {(architecture, seed) for architecture in expected_architectures for seed in (11, 13, 17, 19, 23)}
        if len(records) != 10 or pairs != expected:
            raise SystemExit(f"workstream {workstream} is not the frozen 2x5 matrix")

    image = json.loads(subprocess.check_output(["docker", "image", "inspect", IMAGE], text=True))[0]
    if image["Id"] != IMAGE.split("@", 1)[1]:
        raise SystemExit("local ORFS image does not match the frozen digest")

    policy = root / "policy"
    snapshot = policy / "repo_snapshot"
    traces = policy / "traces"
    (root / "runs/A").mkdir(parents=True)
    (root / "runs/C").mkdir(parents=True)
    snapshot.mkdir(parents=True)
    traces.mkdir()

    snapshot_paths = {
        path.relative_to(repo).as_posix()
        for path in (repo / CAMPAIGN).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    snapshot_paths.update(contract["source_hashes"])
    snapshot_records = []
    for relative in sorted(snapshot_paths):
        source = repo / relative
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        snapshot_records.append({"path": relative, "bytes": destination.stat().st_size, "sha256": sha256(destination)})

    old_trace_manifest = json.loads((REV2_ROOT / "policy/traces/TRACE_MANIFEST.json").read_text(encoding="utf-8"))
    hsiao_record = next(
        row for row in old_trace_manifest["traces"]
        if row["family"] == "hsiao" and row["trace_class"] == "no_error" and float(row["clock_period_ns"]) == 10.0
    )
    hsiao_source = REV2_ROOT / "policy/traces" / hsiao_record["file"]
    if sha256(hsiao_source) != hsiao_record["compressed_sha256"]:
        raise SystemExit("immutable Revision-2 Hsiao trace hash mismatch")
    shutil.copy2(hsiao_source, traces / hsiao_source.name)
    hsiao_record = dict(hsiao_record) | {
        "provenance": "byte-exact copy of immutable Revision-2 primary-input trace",
        "source_path": str(hsiao_source),
    }

    five_trace = traces / "conventional_secded-5ns-no_error.vcd.gz"
    five_record_path = traces / "conventional_secded-5ns-no_error.record.json"
    subprocess.run(
        [
            "python3",
            str(snapshot / CAMPAIGN / "scripts/generate_5ns_trace.py"),
            "--out", str(five_trace),
            "--record", str(five_record_path),
        ],
        check=True,
    )
    five_record = json.loads(five_record_path.read_text(encoding="utf-8"))
    write_json(
        traces / "TRACE_MANIFEST.json",
        {
            "schema_version": 1,
            "campaign": "DATE 2027 breadth remediation",
            "traces": [hsiao_record, five_record],
        },
    )

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, text=True
    )
    frozen_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": 1,
        "state": "BREADTH_PHYSICAL_CAMPAIGN_FROZEN_BEFORE_EXECUTION",
        "frozen_at_utc": frozen_at,
        "evidence_root": str(root),
        "baseline_commit": contract["baseline_commit"],
        "git_commit_at_freeze": head,
        "worktree_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "snapshot_file_count": len(snapshot_records),
        "snapshot_files": snapshot_records,
        "contract_sha256": sha256(contract_path),
        "plan_freeze_sha256": sha256(repo / CAMPAIGN / "00_plan_freeze.sha256"),
        "formal_qualification_sha256": sha256(repo / CAMPAIGN / "formal/results/A_formal_qualification.json"),
        "synthesis_comparison_sha256": sha256(repo / CAMPAIGN / "synthesis/A_synthesis_structural_comparison.json"),
        "trace_manifest_sha256": sha256(traces / "TRACE_MANIFEST.json"),
        "container_image": IMAGE,
        "exact_commands": {
            "workstream_A": f"python3 {snapshot / CAMPAIGN / 'scripts/run_physical_matrix.py'} --workstream A",
            "workstream_C": f"python3 {snapshot / CAMPAIGN / 'scripts/run_physical_matrix.py'} --workstream C",
        },
    }
    write_json(policy / "CAMPAIGN_MANIFEST.json", manifest)
    (policy / "repository-status-at-freeze.txt").write_text(status, encoding="utf-8", newline="\n")
    freeze_manifest(policy)
    make_read_only(policy)
    print(f"BREADTH_PHYSICAL_CAMPAIGN_FROZEN root={root} runs=20")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
