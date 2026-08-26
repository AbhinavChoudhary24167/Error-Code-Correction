#!/usr/bin/env python3
"""Create Gate 03E-S preflight evidence without creating fresh-run directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


OCI_INDEX = "sha256:68d42e5c92a7193a9cf9a331a429250e47d42e16883366af2107022f7dafff74"
OCI_MANIFEST = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
OCI_CONFIG = "sha256:ab3a3006003431cd7189a82567df3e6deb0d0aae66aa42a0bdf56d2751447c08"
ORFS_COMMIT = "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
ORFS_TREE = "2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a"
OFFICIAL_MAKE = "make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk"
DEADLINE = datetime(2026, 8, 17, 11, 59, 59, tzinfo=timezone.utc)
FLOW_TOOLS = ("openroad", "yosys", "klayout", "make", "python3")
STARTING_BRANCH = "main"
STARTING_HEAD = "ceae4ad9b5a3ba612596fb7ac1a93dd144114409"
LEGACY_BEFORE = {
    "scripts/gate03e/validate_artifacts.py": "54e645385a56ab5fd6a5b5c7e4f5b73be6632dd953ece21ee0a70fa8c9450299",
    "tests/python/test_gate03_artifacts.py": "ece77a9c427e8cb7f6f064c0ccd9e46f924cdeff55bd9a14afece89fbaac7c4b",
}


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


def tree_record(root: Path) -> dict[str, object]:
    files = [item for item in root.rglob("*") if item.is_file()]
    return {
        "path": str(root),
        "file_count": len(files),
        "size_bytes": sum(item.stat().st_size for item in files),
        "tree_sha256": tree_hash(root),
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def command_output(command: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True, encoding="utf-8").strip()


def container_tool_records() -> list[dict[str, str]]:
    script = """
set -euo pipefail
cd /OpenROAD-flow-scripts
source ./env.sh >/dev/null
for tool in openroad yosys klayout make python3; do
  path="$(command -v "$tool")"
  digest="$(sha256sum "$path" | awk '{print $1}')"
  version="$($tool --version 2>&1 | head -1 || true)"
  printf '%s|%s|%s|%s\n' "$tool" "$path" "$digest" "$version"
done
"""
    output = command_output([
        "docker", "run", "--rm", "--platform", "linux/amd64", "--entrypoint", "/bin/bash",
        f"openroad/orfs@{OCI_MANIFEST}", "-lc", script,
    ])
    records = []
    for line in output.splitlines():
        tool, path, digest, version = line.split("|", 3)
        records.append({"name": tool, "path": path, "sha256": digest, "version": version})
    if tuple(row["name"] for row in records) != FLOW_TOOLS:
        raise SystemExit(f"unexpected tool inventory: {records}")
    return records


def verify_oci(registry: Path) -> dict[str, object]:
    paths = {
        "index": registry / "tag-index.raw.json",
        "manifest": registry / "amd64-manifest.raw.json",
        "configuration": registry / "amd64-config.raw.json",
    }
    observed = {key: f"sha256:{sha256(path)}" for key, path in paths.items()}
    expected = {"index": OCI_INDEX, "manifest": OCI_MANIFEST, "configuration": OCI_CONFIG}
    if observed != expected:
        raise SystemExit(f"OCI raw-document identity mismatch: {observed}")
    index = json.loads(paths["index"].read_text())
    manifest = json.loads(paths["manifest"].read_text())
    amd64 = [
        row for row in index.get("manifests", [])
        if row.get("platform", {}).get("os") == "linux" and row.get("platform", {}).get("architecture") == "amd64"
    ]
    if len(amd64) != 1 or amd64[0].get("digest") != OCI_MANIFEST:
        raise SystemExit("OCI index does not select the expected unique linux/amd64 manifest")
    if manifest.get("config", {}).get("digest") != OCI_CONFIG:
        raise SystemExit("OCI manifest does not reference the expected configuration")
    inspect = json.loads(command_output(["docker", "image", "inspect", f"openroad/orfs@{OCI_MANIFEST}"]))[0]
    if inspect.get("Descriptor", {}).get("digest") != OCI_MANIFEST or inspect.get("Os") != "linux" or inspect.get("Architecture") != "amd64":
        raise SystemExit("local pinned image descriptor/platform mismatch")
    return {
        "index_digest": OCI_INDEX,
        "linux_amd64_manifest_digest": OCI_MANIFEST,
        "configuration_digest": OCI_CONFIG,
        "identities_are_distinct": len({OCI_INDEX, OCI_MANIFEST, OCI_CONFIG}) == 3,
        "raw_documents": [
            {"role": role, "path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for role, path in paths.items()
        ],
        "local_descriptor_digest": inspect["Descriptor"]["digest"],
        "platform": {"os": inspect["Os"], "architecture": inspect["Architecture"]},
    }


def verify_execution_subset(v1: Path) -> tuple[dict[str, object], dict[str, object]]:
    comparison = json.loads((v1 / "reconciliation/execution-subset-comparison.json").read_text())
    manifest = json.loads((v1 / "reconciliation/container-execution-subset.json").read_text())
    entries = manifest.get("entries", {})
    if comparison.get("counts") != {
        "additional_in_container": 0, "byte_identical": 169, "mismatched": 0, "missing_from_container": 0,
    } or len(entries) != 169:
        raise SystemExit("the preserved 169-file reconciled execution subset is not exact")
    source = v1 / "source/OpenROAD-flow-scripts"
    failures = []
    for relative, record in entries.items():
        path = source / relative
        if record["kind"] == "file":
            if not path.is_file() or path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
                failures.append(relative)
        elif record["kind"] == "symlink":
            if not path.is_symlink() or os.readlink(path) != record["target"] or hashlib.sha256(record["target"].encode()).hexdigest() != record["sha256"]:
                failures.append(relative)
        else:
            failures.append(relative)
    if failures:
        raise SystemExit(f"execution subset source mismatch: {failures}")
    return comparison, entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--v1-root", type=Path, default=Path("/var/lib/green-ecc-gate03e"))
    parser.add_argument("--v2-root", type=Path, default=Path("/var/lib/green-ecc-gate03er"))
    parser.add_argument("--external-root", type=Path, default=Path("/var/lib/green-ecc-gate03es"))
    args = parser.parse_args()
    repo, v1, v2, external = args.repo_root.resolve(), args.v1_root.resolve(), args.v2_root.resolve(), args.external_root
    if external.exists():
        entries = sorted(path.name for path in external.iterdir())
        if not entries or any(not name.startswith("preflight-attempt-") for name in entries):
            raise SystemExit(f"refusing to reuse Gate 03E-S root: {external}")
    if datetime.now(timezone.utc) > DEADLINE:
        raise SystemExit("Gate 03E-S deadline already expired")
    if command_output(["git", "branch", "--show-current"], repo) != STARTING_BRANCH or command_output(["git", "rev-parse", "HEAD"], repo) != STARTING_HEAD:
        raise SystemExit("starting branch or HEAD changed")
    preflight = external / "preflight"
    preflight.mkdir(parents=True)

    required = [
        v1 / "policy/reproducibility_policy_v1.json",
        v1 / "policy/reproducibility.py",
        v1 / "runs/gcd-run-comparison.json",
        v1 / "reconciliation/execution-subset-comparison.json",
        v1 / "reconciliation/container-execution-subset.json",
        v1 / "collateral/sky130hd-collateral-manifest.json",
        v1 / "source/git-submodules.txt",
        v1 / "commands/command-manifest.json",
        v2 / "policy/frozen-bundle.json",
        v2 / "runs/gcd-run-03-inventory.json",
        v2 / "runs/gcd-run-04-inventory.json",
        repo / "docs/date2027/rigour_gate_03er/GATE_03ER_REPORT.md",
        repo / "docs/date2027/rigour_gate_03er/GATE_03ER_VERDICT.txt",
        repo / "docs/date2027/rigour_gate_03er/FRESH_RUN_COMPARISON.json",
    ]
    if any(not path.is_file() for path in required):
        raise SystemExit("required preserved Gate 03E/03E-R input is missing")

    comparison, entries = verify_execution_subset(v1)
    oci = verify_oci(v1 / "registry")
    source_root = v1 / "source/OpenROAD-flow-scripts"
    if command_output(["git", "rev-parse", "HEAD"], source_root) != ORFS_COMMIT or command_output(["git", "rev-parse", "HEAD^{tree}"], source_root) != ORFS_TREE:
        raise SystemExit("ORFS commit/tree mismatch")
    if command_output(["git", "status", "--porcelain"], source_root):
        raise SystemExit("ORFS source checkout is dirty")
    submodules = command_output(["git", "submodule", "status", "--recursive"], source_root)

    gate03er_report = (repo / "docs/date2027/rigour_gate_03er/GATE_03ER_REPORT.md").read_text()
    gate03er_comparison = json.loads((repo / "docs/date2027/rigour_gate_03er/FRESH_RUN_COMPARISON.json").read_text())
    scientific_rows = [
        row for key in ("semantic_artifact_comparisons", "technology_xml_comparisons", "mapped_master_histograms", "metric_comparisons")
        for row in gate03er_comparison[key]
    ]
    adjudication = {
        "gate03er_verdict": (repo / "docs/date2027/rigour_gate_03er/GATE_03ER_VERDICT.txt").read_text().strip(),
        "report_sha256": sha256(repo / "docs/date2027/rigour_gate_03er/GATE_03ER_REPORT.md"),
        "comparison_sha256": sha256(repo / "docs/date2027/rigour_gate_03er/FRESH_RUN_COMPARISON.json"),
        "scientific_comparison_rows": len(scientific_rows),
        "scientific_comparisons_all_pass": bool(scientific_rows) and all(row["pass"] for row in scientific_rows),
        "only_comparison_failure": gate03er_comparison["failures"],
        "report_consistent": (
            "Semantic physical outputs, technology XML, stage ODBs, mapped masters, and all frozen QoR rules passed" in gate03er_report
            and "run-metadata.json" in gate03er_report
            and "legacy Gate 03/03E scope validators" in gate03er_report
        ),
        "formal_pass_claim_prohibited": True,
    }
    if adjudication["gate03er_verdict"] != "ENVIRONMENT_ENABLEMENT_FAILED" or not adjudication["scientific_comparisons_all_pass"] or not adjudication["report_consistent"]:
        raise SystemExit("Gate 03E-R preservation/adjudication failed")

    implementation_paths = [
        repo / path for path in (
            "scripts/gate03es/__init__.py",
            "scripts/gate03es/reproducibility_policy_v3.json",
            "scripts/gate03es/producer_catalog_v3.json",
            "scripts/gate03es/qor_metric_schema_v3.json",
            "scripts/gate03es/reproducibility.py",
            "scripts/gate03es/odb_semantic_export.py",
            "scripts/gate03es/scope_compatibility.py",
            "scripts/gate03es/run_gcd_fresh.sh",
            "scripts/gate03es/prepare_gate03es.py",
            "scripts/gate03es/finalize_gate03es.py",
            "scripts/gate03es/validate_gate03es.py",
            "scripts/gate03es/validate_scope.py",
            "scripts/gate03e/validate_artifacts.py",
            "tests/python/test_gate03_artifacts.py",
            "tests/python/test_gate03es_reproducibility.py",
        )
    ]
    if any(not path.is_file() for path in implementation_paths):
        raise SystemExit("Gate 03E-S implementation input is missing")

    design_paths = (
        "flow/designs/src/gcd/gcd.v", "flow/designs/sky130hd/gcd/config.mk", "flow/designs/sky130hd/gcd/constraint.sdc",
    )
    collateral_entries = {
        path: record for path, record in entries.items()
        if path.startswith("flow/platforms/sky130hd/") or path == "flow/platforms/sky130hs/rcx_patterns.rules"
    }
    immutable = {
        "schema_version": 3,
        "gate": "03E-S",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "oci_identity": oci,
        "orfs_source_root": str(source_root),
        "orfs_commit": ORFS_COMMIT,
        "orfs_tree": ORFS_TREE,
        "orfs_submodule_status": submodules,
        "orfs_submodule_status_sha256": hashlib.sha256(submodules.encode()).hexdigest(),
        "execution_subset_expected_count": 169,
        "execution_subset_scope_sha256": comparison["scope_sha256"],
        "execution_subset_entries": entries,
        "gcd_design_inputs": {path: entries[path] for path in design_paths},
        "sky130hd_collateral_entries": collateral_entries,
        "flow_tool_binaries": container_tool_records(),
        "effective_environment": {"LEC_CHECK": "0", "NUM_CORES": "1", "thread_count": 1},
        "official_make_invocation": OFFICIAL_MAKE,
        "gate03es_implementation_files": [
            {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)} for path in implementation_paths
        ],
        "files": [{"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)} for path in required],
    }
    write_json(preflight / "immutable-input-manifest.json", immutable)
    write_json(preflight / "gate03er-adjudication.json", adjudication)

    protected_repo = [
        "docs/date2027/rigour_gate_01", "docs/date2027/rigour_gate_02", "docs/date2027/rigour_gate_03",
        "docs/date2027/rigour_gate_03r", "docs/date2027/rigour_gate_03e", "docs/date2027/rigour_gate_03er",
        "asic/rtl", "green_ecc_physical_simulation/registry",
    ]
    protected = {
        "schema_version": 3,
        "starting_branch": STARTING_BRANCH,
        "starting_head": STARTING_HEAD,
        "starting_tracked_changes": [],
        "starting_untracked_scope": ["docs/date2027/rigour_gate_03er/", "scripts/gate03er/", "tests/python/test_gate03er_reproducibility.py"],
        "repo_trees": {relative: tree_hash(repo / relative) for relative in protected_repo},
        "external_trees": {
            "gate03e": tree_record(v1),
            "gate03er": tree_record(v2),
        },
        "legacy_validator_changes": [
            {
                "path": relative,
                "before_sha256": before,
                "after_sha256": sha256(repo / relative),
                "rationale": "minimum path-scope compatibility adapter for explicitly registered additive gate directories; historical evidence hashing remains unchanged",
            }
            for relative, before in LEGACY_BEFORE.items()
        ],
        "gate03er_adjudication": adjudication,
    }
    write_json(preflight / "protected-baseline.json", protected)

    command_manifest = {
        "schema_version": 3,
        "gate": "03E-S",
        "deadline_utc": "2026-08-17T11:59:59Z",
        "image_index_digest": OCI_INDEX,
        "image_linux_amd64_manifest_digest": OCI_MANIFEST,
        "image_configuration_digest": OCI_CONFIG,
        "effective_environment": [
            "source /OpenROAD-flow-scripts/env.sh", "export LEC_CHECK=0", "export NUM_CORES=1",
            "export WORK_HOME=<fresh run root>", "cd /OpenROAD-flow-scripts/flow",
        ],
        "official_make_invocation": OFFICIAL_MAKE,
        "postprocess": "complete semantic export for every stage ODB using the frozen exporter under the same pinned image",
        "runs": [
            {"id": 5, "label": "gcd-run-05", "host_root": "/var/lib/green-ecc-gate03es/runs/gcd-run-05", "container_root": "/gate03es-run-05"},
            {"id": 6, "label": "gcd-run-06", "host_root": "/var/lib/green-ecc-gate03es/runs/gcd-run-06", "container_root": "/gate03es-run-06"},
        ],
        "run_order": "sequential",
        "reuse_delete_or_retry_existing_run": False,
    }
    write_json(preflight / "command-manifest.json", command_manifest)
    print(json.dumps({"status": "PASS", "external_root": str(external), "run_directories_created": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
