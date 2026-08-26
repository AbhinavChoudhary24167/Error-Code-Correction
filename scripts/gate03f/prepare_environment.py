#!/usr/bin/env python3
"""Create the one-shot, result-blind DATE-final physical environment freeze."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


DEFAULT_EVIDENCE_ROOT = Path("/var/lib/green-ecc-date2027-final")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(args: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, encoding="utf-8").strip()


def docker_shell(image: str, script: str) -> str:
    return run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "--entrypoint",
            "/bin/bash",
            image,
            "-lc",
            script,
        ]
    )


def snapshot_inputs(repo: Path, snapshot: Path) -> list[dict[str, object]]:
    paths = {
        path.relative_to(repo).as_posix()
        for path in (repo / "scripts" / "gate03f").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    paths.update(
        {
            "asic/rtl/bch/bch_78_64_t2_v1.sv",
            "docs/date2027/rigour_gate_02/CANONICAL_CODE_SPECS.json",
            "scripts/gate03r/rtl/secded_characterization_tops.sv",
            "scripts/gate04/generate_traces.py",
            "scripts/gate04/rtl/gate04_boundaries.sv",
        }
    )
    missing = [relative for relative in sorted(paths) if not (repo / relative).is_file()]
    if missing:
        raise SystemExit(f"freeze inputs missing: {missing}")

    records: list[dict[str, object]] = []
    for relative in sorted(paths):
        source = repo / relative
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        destination.chmod(0o444)
        records.append(
            {
                "path": relative,
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            }
        )
    return records


def image_file_hashes(image: str, paths: list[str]) -> dict[str, str]:
    output = docker_shell(image, "set -e; sha256sum " + " ".join(paths))
    records: dict[str, str] = {}
    for line in output.splitlines():
        digest, path = line.split(maxsplit=1)
        records[path] = digest
    if set(records) != set(paths):
        raise SystemExit("container file hash inventory is incomplete")
    return records


def freeze_hash_manifest(policy: Path) -> None:
    records: list[str] = []
    for path in sorted(item for item in policy.rglob("*") if item.is_file()):
        if path.name == "frozen-bundle.sha256":
            continue
        records.append(f"{sha256(path)}  {path.relative_to(policy).as_posix()}")
    (policy / "frozen-bundle.sha256").write_text(
        "\n".join(records) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    args = parser.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("run as root inside the Ubuntu WSL2 distro")
    repo = args.repo.resolve()
    root = args.evidence_root
    if root.exists():
        raise SystemExit(f"refusing to overwrite existing DATE-final root: {root}")

    contract_path = repo / "scripts/gate03f/contract_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    image = contract["technology"]["container_image"]
    digest = contract["technology"]["container_image_digest"]

    image_inspect = json.loads(run(["docker", "image", "inspect", image]))[0]
    if image_inspect["Id"] != digest or image not in image_inspect.get("RepoDigests", []):
        raise SystemExit("local Docker object does not match the frozen image digest")

    policy = root / "policy"
    snapshot = policy / "repo_snapshot"
    runs = root / "runs"
    policy.mkdir(parents=True)
    snapshot.mkdir()
    runs.mkdir()

    source_records = snapshot_inputs(repo, snapshot)
    snapshot_contract = snapshot / "scripts/gate03f/contract_v1.json"

    repository_head = run(["git", "rev-parse", "HEAD"], cwd=repo)
    repository_status = run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo
    )
    (policy / "repository-status-at-freeze.txt").write_text(
        repository_status + ("\n" if repository_status else ""),
        encoding="utf-8",
        newline="\n",
    )

    trace_dir = policy / "traces"
    subprocess.run(
        [
            "python3",
            str(snapshot / "scripts/gate04/generate_traces.py"),
            "--out",
            str(trace_dir),
            "--contract",
            str(snapshot_contract),
        ],
        check=True,
        cwd=snapshot,
    )
    trace_manifest = json.loads((trace_dir / "TRACE_MANIFEST.json").read_text(encoding="utf-8"))
    if len(trace_manifest["traces"]) != 9:
        raise SystemExit("DATE-final activity generator did not produce exactly nine 10 ns traces")

    platform_paths = [
        "/OpenROAD-flow-scripts/flow/platforms/sky130hd/config.mk",
        contract["technology"]["technology_lef"]["path"],
        contract["technology"]["standard_cell_lef"]["path"],
        contract["technology"]["liberty"]["path"],
        contract["technology"]["set_rc_tcl"]["path"],
    ]
    seed_paths = [
        "/OpenROAD-flow-scripts/flow/scripts/global_place.tcl",
        "/OpenROAD-flow-scripts/flow/scripts/global_place_skip_io.tcl",
        "/OpenROAD-flow-scripts/flow/scripts/global_route.tcl",
        "/OpenROAD-flow-scripts/flow/scripts/detail_route.tcl",
        "/OpenROAD-flow-scripts/flow/scripts/variables.json",
        "/OpenROAD-flow-scripts/flow/scripts/variables.yaml",
    ]
    gcd_rtl = "/OpenROAD-flow-scripts/flow/designs/src/gcd/gcd.v"
    container_hashes = image_file_hashes(image, platform_paths + seed_paths + [gcd_rtl])
    for key in ("technology_lef", "standard_cell_lef", "liberty", "set_rc_tcl"):
        expected = contract["technology"][key]
        if container_hashes[expected["path"]] != expected["sha256"]:
            raise SystemExit(f"pinned image {key} hash mismatch")
    if container_hashes[gcd_rtl] != "5009f224876d39e5e77e59ee1528cb0d2a03697251f0971b77cf3e8b0426dd3e":
        raise SystemExit("pinned image GCD RTL hash mismatch")

    versions = docker_shell(
        image,
        "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null; "
        "openroad -version; yosys -V; klayout -v",
    ).splitlines()
    if contract["technology"]["openroad_version"] not in versions[0]:
        raise SystemExit("OpenROAD version does not match the frozen contract")

    seed_proof = docker_shell(
        image,
        "set -e; grep -HnE 'GPL_RANDOM_SEED|GRT_SEED|OR_SEED|random_seed|or_seed' "
        + " ".join(seed_paths),
    )
    for variable in contract["flow"]["seed_environment_variables"]:
        if variable not in seed_proof:
            raise SystemExit(f"seed variable not found in pinned ORFS source: {variable}")
    (policy / "seed-control-source-proof.txt").write_text(
        seed_proof + "\n", encoding="utf-8", newline="\n"
    )

    docker_version = json.loads(run(["docker", "version", "--format", "{{json .}}"] ))
    os_release = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            os_release[key] = value.strip('"')

    environment = {
        "schema_version": 1,
        "gate": contract["gate"],
        "state": "DATE_FINAL_PHYSICAL_ENVIRONMENT_FROZEN",
        "frozen_before_qualification": True,
        "frozen_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "evidence_root": str(root),
        "repository": {
            "git_commit": repository_head,
            "worktree_status_sha256": hashlib.sha256(repository_status.encode("utf-8")).hexdigest(),
            "snapshot_file_count": len(source_records),
            "snapshot_files": source_records,
        },
        "docker": {
            "reference": image,
            "image_id": image_inspect["Id"],
            "repo_digests": image_inspect.get("RepoDigests", []),
            "created": image_inspect["Created"],
            "architecture": image_inspect["Architecture"],
            "os": image_inspect["Os"],
            "client_version": docker_version["Client"]["Version"],
            "server_version": docker_version["Server"]["Version"],
        },
        "host_execution": {
            "wsl_distribution": os.environ.get("WSL_DISTRO_NAME", "UNKNOWN"),
            "kernel": run(["uname", "-srmo"]),
            "distribution": os_release.get("PRETTY_NAME", "UNKNOWN"),
        },
        "orfs": {
            "git_commit": contract["technology"]["orfs_git_commit"],
            "git_tree": contract["technology"]["orfs_git_tree"],
            "identity_basis": "executing image bytes previously reconciled to this ORFS source revision; image digest is the primary execution identity",
        },
        "tools": {
            "openroad_git_commit": contract["technology"]["openroad_git_commit"],
            "openroad_version": versions[0],
            "openroad_binary_sha256": contract["technology"]["openroad_binary_sha256"],
            "yosys_version": versions[1],
            "klayout_version": versions[2],
        },
        "platform": {
            "name": contract["technology"]["platform"],
            "corner": contract["technology"]["corner"],
            "files": [
                {"path": path, "sha256": container_hashes[path]} for path in platform_paths
            ],
        },
        "gcd_rtl": {"path": gcd_rtl, "sha256": container_hashes[gcd_rtl]},
        "seed_control": {
            "fixed_seed": contract["flow"]["physical_seed"],
            "available_variables": contract["flow"]["seed_environment_variables"],
            "source_files": [
                {"path": path, "sha256": container_hashes[path]} for path in seed_paths
            ],
        },
        "flow": contract["flow"],
        "qualification_runs": contract["qualification_runs"],
        "statistics": contract["statistics"],
        "power": {
            **contract["power"],
            "trace_manifest_sha256": sha256(trace_dir / "TRACE_MANIFEST.json"),
            "trace_count": len(trace_manifest["traces"]),
        },
        "exact_commands": {
            "freeze": f"python3 scripts/gate03f/prepare_environment.py --repo {repo}",
            "per_run": "python3 /var/lib/green-ecc-date2027-final/policy/repo_snapshot/scripts/gate03f/run_qualification.py RUN_ID",
            "matrix": "python3 /var/lib/green-ecc-date2027-final/policy/repo_snapshot/scripts/gate03f/run_matrix.py",
            "analysis": "python3 /var/lib/green-ecc-date2027-final/policy/repo_snapshot/scripts/gate03f/analyze_qualification.py --logical-validation PASS",
            "physical_container": "source /OpenROAD-flow-scripts/env.sh; export LEC_CHECK=0 NUM_CORES=1 WORK_HOME=/date-final-run CLOCK_PERIOD=10.0 GPL_RANDOM_SEED=11 GRT_SEED=11 OR_SEED=11; cd /OpenROAD-flow-scripts/flow; make ABC_CLOCK_PERIOD_IN_PS=10000 DESIGN_CONFIG=/date-final-repo/scripts/gate03f/configs/CONFIG",
        },
    }
    write_json(policy / "DATE_FINAL_PHYSICAL_ENVIRONMENT.json", environment)
    write_json(
        policy / "IMMUTABLE_INPUT_MANIFEST.json",
        {
            "schema_version": 1,
            "algorithm": "sha256-raw-bytes",
            "repository_snapshot": source_records,
            "container_files": [
                {"path": path, "sha256": digest_value}
                for path, digest_value in sorted(container_hashes.items())
            ],
            "activity_trace_manifest_sha256": sha256(trace_dir / "TRACE_MANIFEST.json"),
        },
    )
    freeze_hash_manifest(policy)

    for path in (item for item in policy.rglob("*") if item.is_file()):
        path.chmod(0o444)
    for path in sorted((item for item in policy.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o555)
    policy.chmod(0o555)
    print(
        "DATE_FINAL_PHYSICAL_ENVIRONMENT_FROZEN "
        f"root={root} runs={len(contract['qualification_runs'])} traces={len(trace_manifest['traces'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
