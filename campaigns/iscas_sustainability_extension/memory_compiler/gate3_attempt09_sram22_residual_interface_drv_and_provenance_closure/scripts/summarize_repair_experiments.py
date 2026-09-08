#!/usr/bin/env python3
"""Summarize every preserved Attempt09 interface-drive experiment."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "raw" / "repair_experiments"


def maximum(line: str) -> float:
    match = re.search(r"\^ ([\d.]+):([\d.]+) v ([\d.]+):([\d.]+)", line)
    if not match:
        raise ValueError(line)
    return max(float(value) for value in match.groups())


def main() -> None:
    records = []
    for path in sorted(EXP.glob("*.log")):
        text = path.read_text(encoding="utf-8", errors="replace")
        header = re.search(r"ATTEMPT09_EXPERIMENT design=(\S+) target=(\S+) cell=(\S+)(?: inputs=(\S+) output=(\S+))?", text)
        if not header:
            raise RuntimeError(f"experiment header not found in {path}")
        target = header.group(2)
        before_text, after_text = text.split("ATTEMPT09_AFTER", 1)[0], text.split("ATTEMPT09_AFTER", 1)[1]
        before_line = re.search(rf"^{re.escape(target)} \^ .+$", before_text, re.M)
        after_line = re.search(rf"^{re.escape(target)} \^ .+$", after_text, re.M)
        if not before_line or not after_line:
            raise RuntimeError(f"target slew not found in {path}")
        before, after = maximum(before_line.group(0)), maximum(after_line.group(0))
        records.append({
            "log": str(path.relative_to(ROOT)).replace("\\", "/"),
            "design": header.group(1).upper(),
            "target": target,
            "cell": header.group(3),
            "experiment_kind": "single stage" if header.group(4) else "phase-preserving two-stage",
            "before_slew_ns": before,
            "after_slew_ns": after,
            "required_slew_ns": 0.351,
            "improvement_ns": before - after,
            "closes_target_at_placement_estimate": after <= 0.351,
        })
    payload = {
        "schema_version": 1,
        "experiment_count": len(records),
        "nonpersistent_candidate_basis": "frozen Attempt08 canonical seed-11 ODB/SDC/SPEF with legal standard-cell insertion near the macro pin and placement-estimated parasitics",
        "production_constraints_or_liberty_changed": False,
        "records": records,
    }
    (EXP / "experiment_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
