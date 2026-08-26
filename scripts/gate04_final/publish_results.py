#!/usr/bin/env python3
"""Publish the sealed external Gate 04 qualification bundle into the repository."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


SOURCE = Path("/var/lib/green-ecc-date2027-gate04-final-confirmatory-02/qualification")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    destination = args.repo.resolve() / "docs/date2027/rigour_gate_04_final"
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted(SOURCE.iterdir()):
        if not source.is_file():
            continue
        target = destination / source.name
        if target.exists() and target.name in {
            "GATE04_FINAL_ECC_SET.json",
            "GATE04_INFRASTRUCTURE_INCIDENT.md",
            "GATE04_POWER_ACTIVITY_AUDIT.json",
            "GATE04_POWER_PRECISION_ADJUDICATION.md",
        } and sha256(target) != sha256(source):
            raise SystemExit(f"prospective input changed during qualification: {target.name}")
        shutil.copyfile(source, target)
        target.chmod(0o644)
    for line in (destination / "GATE04_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        target = destination / relative.removeprefix("./")
        if not target.is_file() or sha256(target) != expected:
            raise SystemExit(f"published qualification hash mismatch: {relative}")
    print(f"GATE04_QUALIFICATION_PUBLISHED files={len(list(SOURCE.iterdir()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
