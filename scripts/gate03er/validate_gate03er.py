#!/usr/bin/env python3
"""Fail-closed final artifact and protected-scope validator for Gate 03E-R."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


READY = "ENVIRONMENT_READY_FOR_GATE_03_REENTRY"
FAILED = "ENVIRONMENT_ENABLEMENT_FAILED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, default=Path("/var/lib/green-ecc-gate03er"))
    args = parser.parse_args()
    docs = args.repo_root.resolve() / "docs/date2027/rigour_gate_03er"
    external = args.external_root
    errors: list[str] = []
    acceptance = json.loads((docs / "ACCEPTANCE.json").read_text())
    comparison = json.loads((docs / "FRESH_RUN_COMPARISON.json").read_text())
    mapping = json.loads((docs / "MAPPING_REVALIDATION.json").read_text())
    protected = json.loads((docs / "PROTECTED_SCOPE_REVALIDATION.json").read_text())
    adjudication = json.loads((docs / "REPRODUCIBILITY_ADJUDICATION.json").read_text())
    condition_values = [value for key, value in acceptance.items() if key.endswith("_pass")]
    if acceptance.get("verdict") == READY:
        if any(value is not True for value in condition_values):
            errors.append("ready verdict is inconsistent with failed acceptance conditions")
    elif acceptance.get("verdict") == FAILED:
        if all(value is True for value in condition_values):
            errors.append("failure verdict has no failed acceptance condition")
    else:
        errors.append("unknown verdict token")
    if not mapping.get("pass") or len(mapping.get("jobs", [])) != 4:
        errors.append("four-job mapping revalidation failed")
    if not protected.get("pass") or protected.get("gate03r_verdict") != "REMEDIATION_FAILED":
        errors.append("protected scope changed")
    if not adjudication.get("adjudication_pass") or len(adjudication.get("raw_difference_adjudications", [])) != 16 or len(adjudication.get("numeric_breach_adjudications", [])) != 29:
        errors.append("adjudication cardinality or result changed")
    manifest = docs / "EVIDENCE.sha256"
    for line in manifest.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        path = docs / relative
        if not path.is_file() or sha256(path) != expected:
            errors.append(f"documentation evidence hash mismatch: {relative}")
    frozen = json.loads((external / "policy/frozen-bundle.json").read_text())
    for row in frozen["files"]:
        path = external / "policy" / row["name"]
        if not path.is_file() or sha256(path) != row["sha256"]:
            errors.append(f"frozen bundle mismatch: {row['name']}")
    verdict = (docs / "GATE_03ER_VERDICT.txt").read_text().strip()
    if verdict != acceptance.get("verdict"):
        errors.append("verdict file disagrees with acceptance record")
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
