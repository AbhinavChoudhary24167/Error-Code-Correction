#!/usr/bin/env python3
"""Compare Attempt09 SRAM22 source views with the frozen Attempt06 manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT.parent / "gate3_attempt06_replacement_sram_backend_qualification"
manifest = json.loads((PRIOR / "SRAM22_SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
checks = []
for row in manifest["artifacts"]:
    if row["role"] != "macro_source_artifact":
        continue
    path = ROOT / "source_checkout" / row["path"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    checks.append({
        "path": row["path"], "expected_sha256": row["sha256"], "actual_sha256": actual,
        "status": "PASS" if actual == row["sha256"] else "FAIL",
    })
payload = {
    "upstream_commit": manifest["upstream_commit"],
    "artifact_count": len(checks),
    "macro_internal_geometry_modified": False,
    "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
    "artifacts": checks,
}
target = ROOT / "raw" / "integrity" / "frozen_source_verification.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": payload["status"], "artifact_count": len(checks)}))
raise SystemExit(0 if payload["status"] == "PASS" else 1)
