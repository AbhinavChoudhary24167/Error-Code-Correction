#!/usr/bin/env python3
"""Carry an unchanged ORFS global-placement DB across a documented resize stop."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--design", required=True)
    args = parser.parse_args()

    if args.source.name != "3_3_place_gp.odb" or args.target.name != "3_4_place_resized.odb":
        raise SystemExit("refusing unexpected ORFS stage names")
    if not args.source.is_file():
        raise SystemExit(f"missing source database: {args.source}")

    args.target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, args.target)
    # Make the carried result newer than its prerequisite so Make can continue.
    args.target.touch()

    record = {
        "schema_version": 1,
        "design": args.design,
        "operation": "UNCHANGED_DATABASE_CARRY_FORWARD",
        "source_stage": "3_3_place_gp",
        "target_stage": "3_4_place_resized",
        "source_path": args.source.as_posix(),
        "target_path": args.target.as_posix(),
        "source_sha256": sha256(args.source),
        "target_sha256": sha256(args.target),
        "bytes_identical": args.source.read_bytes() == args.target.read_bytes(),
        "reason": "ORFS repair_design RSZ-0090: immutable SRAM22 rstb pin is 0.448 pF with 0.351 ns max_transition; pinned sky130hd best achievable is 0.467 ns",
        "qualification_effect": "resize optimization not credited; CTS, routing, extraction, and final reports must run from the unchanged global-placement DB",
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
