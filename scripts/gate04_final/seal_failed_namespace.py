#!/usr/bin/env python3
"""Inventory and seal the excluded Gate 04 infrastructure-failure namespace."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path


FAILED_ROOT = Path("/var/lib/green-ecc-date2027-gate04-final")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def seal_tree(root: Path) -> None:
    for path in (item for item in root.rglob("*") if item.is_file()):
        path.chmod(0o444)
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


def main() -> int:
    if os.geteuid() != 0:
        raise SystemExit("run as root inside Ubuntu WSL2")
    root = FAILED_ROOT
    if not root.is_dir() or (root / "INFRASTRUCTURE_FAILURE.json").exists():
        raise SystemExit("failed namespace is absent or already sealed")
    attempts = {
        "secded-comb-final-01": {
            "classification": "INFRASTRUCTURE_POSTPROCESSING_FAILURE_EXCLUDED",
            "cause": "Python NameError: metadata literal false was used instead of False after physical and power commands",
            "physical_artifacts_present": True,
            "three_power_reports_present": True,
            "scientific_results_adjudicated": False,
            "replacement_justified": True,
        },
        "secded-pipe-final-01": {
            "classification": "INFRASTRUCTURE_INTERRUPTED_PARTIAL_ATTEMPT_EXCLUDED",
            "cause": "matrix intentionally interrupted after the deterministic postprocessing defect was discovered",
            "physical_artifacts_present": False,
            "three_power_reports_present": False,
            "scientific_results_adjudicated": False,
            "replacement_justified": True,
        },
    }
    for run_id, record in attempts.items():
        run_root = root / "runs" / run_id
        if not run_root.is_dir():
            raise SystemExit(f"expected failed attempt directory missing: {run_id}")
        write_json(run_root / "INFRASTRUCTURE_ATTEMPT.json", {"schema_version": 1, "run_id": run_id, **record})
        inventory = []
        for path in sorted(item for item in run_root.rglob("*") if item.is_file() and item.name != "raw-artifacts.sha256"):
            inventory.append(f"{sha256(path)}  {path.relative_to(run_root).as_posix()}")
        (run_root / "raw-artifacts.sha256").write_text("\n".join(inventory) + "\n", encoding="utf-8", newline="\n")
        seal_tree(run_root)

    write_json(
        root / "INFRASTRUCTURE_FAILURE.json",
        {
            "schema_version": 1,
            "namespace_status": "EXCLUDED_WHOLE_NAMESPACE_INFRASTRUCTURE_FAILURE",
            "sealed_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "cause": "frozen runner metadata boolean NameError",
            "scientific_metrics_used": False,
            "attempts": attempts,
            "replacement_policy": "one clean replacement is justified for each affected run because no scientific input changes",
        },
    )
    top_inventory = [
        f"{sha256(root / 'policy/frozen-bundle.sha256')}  policy/frozen-bundle.sha256",
        f"{sha256(root / 'runs/secded-comb-final-01/raw-artifacts.sha256')}  runs/secded-comb-final-01/raw-artifacts.sha256",
        f"{sha256(root / 'runs/secded-pipe-final-01/raw-artifacts.sha256')}  runs/secded-pipe-final-01/raw-artifacts.sha256",
        f"{sha256(root / 'INFRASTRUCTURE_FAILURE.json')}  INFRASTRUCTURE_FAILURE.json",
    ]
    (root / "FAILED_NAMESPACE.sha256").write_text("\n".join(top_inventory) + "\n", encoding="utf-8", newline="\n")
    (root / "runs").chmod(0o555)
    seal_tree(root)
    print("GATE04_FAILED_NAMESPACE_SEALED attempts=2 scientific_results_used=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
