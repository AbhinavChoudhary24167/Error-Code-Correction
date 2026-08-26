#!/usr/bin/env python3
"""Create Gate 03E-R preflight manifests without creating fresh-run directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


IMAGE_DIGEST = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
ORFS_COMMIT = "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
ORFS_TREE = "2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a"
OFFICIAL_MAKE = "make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk"
DEADLINE = "2026-08-17T11:59:59Z"
FLOW_TOOLS = ("openroad", "yosys", "klayout", "make", "python3")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    records: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        records.append(f"{path.relative_to(root).as_posix()}\0{path.stat().st_size}\0{sha256(path)}\n")
    return hashlib.sha256("".join(records).encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def container_tool_hashes() -> list[dict[str, str]]:
    """Resolve and hash every executable that directly drives the frozen flow."""
    script = """
set -euo pipefail
cd /OpenROAD-flow-scripts
source ./env.sh >/dev/null
for tool in openroad yosys klayout make python3; do
  path="$(command -v "$tool")"
  digest="$(sha256sum "$path" | awk '{print $1}')"
  printf '%s|%s|%s\\n' "$tool" "$path" "$digest"
done
"""
    output = subprocess.check_output(
        [
            "docker", "run", "--rm", "--platform", "linux/amd64",
            "--entrypoint", "/bin/bash", f"openroad/orfs@{IMAGE_DIGEST}",
            "-lc", script,
        ],
        text=True,
    )
    records: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        name, path, digest = line.split("|", 2)
        records.append({"name": name, "path": path, "sha256": digest})
    if tuple(row["name"] for row in records) != FLOW_TOOLS:
        raise SystemExit(f"unexpected flow-tool inventory: {records}")
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--v1-root", type=Path, default=Path("/var/lib/green-ecc-gate03e"))
    parser.add_argument("--external-root", type=Path, default=Path("/var/lib/green-ecc-gate03er"))
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    v1 = args.v1_root.resolve()
    external = args.external_root
    if external.exists():
        raise SystemExit(f"refusing to reuse Gate 03E-R root: {external}")
    if datetime.now(timezone.utc) > datetime(2026, 8, 17, 11, 59, 59, tzinfo=timezone.utc):
        raise SystemExit("Gate 03E-R deadline already expired")
    preflight = external / "preflight"
    preflight.mkdir(parents=True)

    required = [
        v1 / "policy/reproducibility_policy_v1.json",
        v1 / "policy/reproducibility.py",
        v1 / "runs/gcd-run-comparison.json",
        v1 / "runs/gcd-run-01-inventory.json",
        v1 / "runs/gcd-run-02-inventory.json",
        v1 / "reconciliation/execution-subset-comparison.json",
        v1 / "reconciliation/container-execution-subset.json",
        v1 / "reconciliation/source-execution-subset.json",
        v1 / "collateral/sky130hd-collateral-manifest.json",
        v1 / "source/complete-checkout-files.sha256",
        v1 / "source/git-submodules.txt",
        v1 / "image/docker-image-inspect.json",
        v1 / "image/pinned-container-health.log",
        v1 / "commands/command-manifest.json",
        v1 / "commands/command-manifest-amendment-01.json",
        v1 / "mapping/mapping-validation.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing preserved input(s): " + ", ".join(missing))

    execution_comparison = json.loads((v1 / "reconciliation/execution-subset-comparison.json").read_text())
    execution_manifest = json.loads((v1 / "reconciliation/container-execution-subset.json").read_text())
    execution_entries = execution_manifest.get("entries", {})
    if execution_comparison.get("counts") != {
        "additional_in_container": 0,
        "byte_identical": 169,
        "mismatched": 0,
        "missing_from_container": 0,
    } or len(execution_entries) != 169:
        raise SystemExit("the preserved 169-file reconciled execution subset is no longer exact")

    design_paths = (
        "flow/designs/src/gcd/gcd.v",
        "flow/designs/sky130hd/gcd/config.mk",
        "flow/designs/sky130hd/gcd/constraint.sdc",
    )
    if any(path not in execution_entries for path in design_paths):
        raise SystemExit("GCD RTL/config/SDC missing from execution manifest")
    collateral_entries = {
        path: value for path, value in execution_entries.items()
        if path.startswith("flow/platforms/sky130hd/") or path == "flow/platforms/sky130hs/rcx_patterns.rules"
    }
    source_root = v1 / "source/OpenROAD-flow-scripts"
    submodule_status = subprocess.check_output(
        ["git", "-C", str(source_root), "submodule", "status", "--recursive"], text=True
    )
    command_bytes = ("\n".join([
        "source /OpenROAD-flow-scripts/env.sh",
        "export LEC_CHECK=0",
        "export WORK_HOME=<fresh run root>",
        "cd /OpenROAD-flow-scripts/flow",
        OFFICIAL_MAKE,
    ]) + "\n").encode("utf-8")
    implementation_paths = [
        repo / "scripts/gate03er/reproducibility_policy_v2.json",
        repo / "scripts/gate03er/producer_catalog_v2.json",
        repo / "scripts/gate03er/reproducibility.py",
        repo / "scripts/gate03er/run_gcd_fresh.sh",
    ]
    if any(not path.is_file() for path in implementation_paths):
        raise SystemExit("Gate 03E-R implementation input is missing")

    input_manifest = {
        "schema_version": 1,
        "gate": "03E-R",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "oci_image": f"openroad/orfs@{IMAGE_DIGEST}",
        "oci_image_id": IMAGE_DIGEST,
        "orfs_source_root": str(v1 / "source/OpenROAD-flow-scripts"),
        "orfs_commit": ORFS_COMMIT,
        "orfs_tree": ORFS_TREE,
        "orfs_submodule_status": submodule_status,
        "orfs_submodule_status_sha256": hashlib.sha256(submodule_status.encode()).hexdigest(),
        "execution_subset_expected_count": 169,
        "execution_subset_scope_sha256": execution_comparison["scope_sha256"],
        "execution_subset_entries": execution_entries,
        "gcd_design_inputs": {path: execution_entries[path] for path in design_paths},
        "sky130hd_collateral_entries": collateral_entries,
        "flow_tool_binaries": container_tool_hashes(),
        "effective_environment_and_command": command_bytes.decode("utf-8").splitlines(),
        "effective_environment_and_command_sha256": hashlib.sha256(command_bytes).hexdigest(),
        "gate03er_implementation_files": [
            {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in implementation_paths
        ],
        "files": [
            {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)} for path in required
        ],
    }
    write_json(preflight / "immutable-input-manifest.json", input_manifest)

    protected_repo = [
        "docs/date2027/rigour_gate_01",
        "docs/date2027/rigour_gate_02",
        "docs/date2027/rigour_gate_03",
        "docs/date2027/rigour_gate_03r",
        "docs/date2027/rigour_gate_03e",
        "scripts/gate03e",
        "asic/rtl",
        "green_ecc_physical_simulation/registry",
    ]
    protected = {
        "schema_version": 1,
        "repo_head": "ceae4ad9b5a3ba612596fb7ac1a93dd144114409",
        "repo_trees": {
            relative: tree_hash(repo / relative) for relative in protected_repo
        },
        "external_trees": {
            "gcd-run-01": tree_hash(v1 / "runs/gcd-run-01"),
            "gcd-run-02": tree_hash(v1 / "runs/gcd-run-02"),
        },
        "v1_anchor_hashes": {
            "policy": "258694f328084c3fb92dec24e07b3b40d261037d5b1bd8d32b119684211d0b9a",
            "comparator": "9038cd174ccfd5c62d64908c6df9416f2ff542d58daa44faf3f9d6e5527d3a92",
            "comparison": "655a0b7f6aadde7fcf0c45266e9f80fbf77f2635badd7bcee11a0d737c447628",
        },
        "gate03r_verdict": (repo / "docs/date2027/rigour_gate_03r/GATE_03R_VERDICT.txt").read_text().strip(),
    }
    write_json(preflight / "protected-baseline.json", protected)

    command = {
        "schema_version": 1,
        "gate": "03E-R",
        "deadline_utc": DEADLINE,
        "policy_must_be_frozen_before_run_directories": True,
        "image": f"openroad/orfs@{IMAGE_DIGEST}",
        "effective_environment": [
            "source /OpenROAD-flow-scripts/env.sh",
            "export LEC_CHECK=0",
            "export WORK_HOME=<fresh run root>",
            "cd /OpenROAD-flow-scripts/flow",
        ],
        "official_make_invocation": OFFICIAL_MAKE,
        "runs": [
            {"id": 3, "host_root": "/var/lib/green-ecc-gate03er/runs/gcd-run-03", "container_root": "/gate03er-run-03"},
            {"id": 4, "host_root": "/var/lib/green-ecc-gate03er/runs/gcd-run-04", "container_root": "/gate03er-run-04"},
        ],
        "run_order": "sequential",
        "reuse_or_delete_existing_run": False,
    }
    write_json(preflight / "command-manifest.json", command)
    print(json.dumps({"status": "PASS", "external_root": str(external), "run_directories_created": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
