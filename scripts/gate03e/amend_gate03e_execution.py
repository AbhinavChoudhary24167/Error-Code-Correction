#!/usr/bin/env python3
"""Append an execution amendment for the pinned Kepler AVX-512 incompatibility."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


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
    output = commands / "command-manifest-amendment-01.json"
    if output.exists():
        raise SystemExit("execution amendment already exists")
    attempt = external / "attempts/gcd-native-lec-avx512-failure-01"
    if not attempt.is_dir() or (external / "runs/gcd-run-01").exists():
        raise SystemExit("failed attempt was not preserved or clean run-1 path is not empty")
    evidence_files = [
        external / "image/kepler-illegal-instruction-analysis.log",
        external / "image/kepler-direct-smoke.log",
        external / "image/kepler-direct-smoke.exit-status",
        external / "attempts/gcd-native-lec-avx512-failure-01-inventory.json",
    ]
    amendment = {
        "schema_version": 1,
        "amends": {
            "path": "command-manifest.json",
            "sha256": sha256(commands / "command-manifest.json"),
        },
        "reason": "The pinned Kepler libnaja_python.so executes unconditional AVX-512VL while this AMD Ryzen 7 7735HS WSL2 host exposes AVX2 and no AVX-512; direct startup exits 132 (SIGILL).",
        "failed_attempt_preserved_at": "/var/lib/green-ecc-gate03e/attempts/gcd-native-lec-avx512-failure-01",
        "compatibility_setting": {
            "name": "LEC_CHECK",
            "value": "0",
            "pinned_documented_default": 0,
            "source": "flow/scripts/variables.yaml",
            "scope": "Disable only the optional post-repair CTS formal equivalence check opportunistically enabled by flow/settings.mk when Kepler is present.",
        },
        "unchanged_controls": {
            "official_make_invocation": "make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk",
            "default_goal_and_stage_chain": True,
            "orfs_image_digest": "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e",
            "design_config_rtl_and_platform_bytes": True,
            "frozen_reproducibility_policy": True,
            "acceptance_outputs": True,
        },
        "effective_environment_before_make": [
            "source /OpenROAD-flow-scripts/env.sh",
            "export LEC_CHECK=0",
            "export WORK_HOME=<one of the two predeclared run roots>",
            "cd /OpenROAD-flow-scripts/flow",
        ],
        "effective_runner_sha256": sha256(repo / "scripts/gate03e/run_gcd_smoke.sh"),
        "evidence_sha256": {
            path.relative_to(external).as_posix(): sha256(path) for path in evidence_files
        },
    }
    output.write_text(json.dumps(amendment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256(output)
    (commands / "command-manifest-amendment-01.sha256").write_text(
        f"{digest}  command-manifest-amendment-01.json\n", encoding="ascii"
    )
    print(json.dumps({"amendment_sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
