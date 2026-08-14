#!/usr/bin/env python3
"""Create the pre-run Gate-03E command manifest and empty run parent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


IMAGE_DIGEST = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
SOURCE_COMMIT = "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
SOURCE_TREE = "2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a"
FREEZE_COMMIT = "db32a47d103495787a17b59388dfad3cc4cb77e8"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    external = args.external_root.resolve()
    repo = args.repo_root.resolve()
    commands = external / "commands"
    runs = external / "runs"
    if commands.exists() or runs.exists():
        raise SystemExit("commands or runs path already exists; refusing to reuse a physical-run directory")
    commands.mkdir(parents=True)
    runs.mkdir()
    frozen_bundle = json.loads((external / "policy/frozen-bundle.json").read_text())
    runner = repo / "scripts/gate03e/run_gcd_smoke.sh"
    scope = repo / "scripts/gate03e/orfs_execution_subset.json"
    manifest = {
        "schema_version": 1,
        "gate": "03E",
        "deadline": "2026-08-16 AoE",
        "gate03r_starting_commit": FREEZE_COMMIT,
        "checkpoint_tag": "gate03e-pre-reboot-db32a47",
        "push_authorized": False,
        "orfs": {
            "image": f"openroad/orfs@{IMAGE_DIGEST}",
            "oci_digest": IMAGE_DIGEST,
            "tag_evidence": "26Q3-275-g56496f398",
            "source_commit": SOURCE_COMMIT,
            "source_tree": SOURCE_TREE,
            "default_goal": "all",
            "default_dependency_chain": [
                "check-yosys", "check-openroad", "synth", "floorplan", "place",
                "cts", "route", "finish",
            ],
        },
        "official_make_invocation": "make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk",
        "environment_setup": "source /OpenROAD-flow-scripts/env.sh; export WORK_HOME=<run-root>; cd /OpenROAD-flow-scripts/flow",
        "runs": [
            {
                "id": 1,
                "host_root": "/var/lib/green-ecc-gate03e/runs/gcd-run-01",
                "container_root": "/gate03e-run-01",
            },
            {
                "id": 2,
                "host_root": "/var/lib/green-ecc-gate03e/runs/gcd-run-02",
                "container_root": "/gate03e-run-02",
            },
        ],
        "frozen_reproducibility_bundle": frozen_bundle["files"],
        "runner_sha256": sha256(runner),
        "execution_subset_sha256": sha256(scope),
        "reconciliation_evidence_sha256": sha256(
            external / "reconciliation/execution-subset-comparison.json"
        ),
        "collateral_manifest_sha256": sha256(
            external / "collateral/sky130hd-collateral-manifest.json"
        ),
    }
    manifest_path = commands / "command-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (commands / "command-manifest.sha256").write_text(
        f"{sha256(manifest_path)}  command-manifest.json\n", encoding="ascii"
    )
    print(json.dumps({"command_manifest_sha256": sha256(manifest_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
