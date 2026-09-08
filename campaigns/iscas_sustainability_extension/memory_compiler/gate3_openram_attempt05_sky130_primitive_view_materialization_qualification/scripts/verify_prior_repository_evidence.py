#!/usr/bin/env python3
"""Freshly rehash repository-resident evidence from the prior campaigns."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT.parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(label, manifest_path, root, field):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest[field]
    checks = []
    for row in rows:
        path = root / row["path"]
        actual = sha256(path) if path.is_file() else None
        checks.append({
            "path": row["path"],
            "expected_sha256": row["sha256"],
            "actual_sha256": actual,
            "status": "PASS" if actual == row["sha256"] else ("MISSING" if actual is None else "CHANGED"),
        })
    return {
        "label": label,
        "manifest": str(manifest_path.relative_to(MEMORY)).replace("\\", "/"),
        "file_count": len(checks),
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "failures": [row for row in checks if row["status"] != "PASS"],
    }


results = [
    verify(
        "Attempt01/Attempt02 repository evidence",
        MEMORY / "GATE2_GATE3_EVIDENCE_MANIFEST.json",
        MEMORY,
        "files",
    ),
    verify(
        "Attempt03 repository evidence",
        MEMORY / "gate3_openram_attempt03_target_diagnosis" / "ATTEMPT03_EVIDENCE_MANIFEST.json",
        MEMORY / "gate3_openram_attempt03_target_diagnosis",
        "artifacts",
    ),
    verify(
        "Attempt04 repository evidence",
        MEMORY / "gate3_openram_attempt04_sky130_control_integration_repair" / "ATTEMPT04_EVIDENCE_MANIFEST.json",
        MEMORY / "gate3_openram_attempt04_sky130_control_integration_repair",
        "files",
    ),
]
payload = {
    "algorithm": "sha256",
    "scope": "repository-resident files listed by preserved manifests",
    "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
    "campaigns": results,
    "external_attempt02_attempt03": {
        "status": "NOT_REVERIFIED",
        "reason": "Original Ubuntu-24.04 VHDX remains inaccessible due documented ERROR_SHARING_VIOLATION; historical results were not promoted to current PASS."
    }
}
target = ROOT / "raw" / "integrity" / "prior_campaign_repository_verification.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": payload["status"], "campaigns": [{"label": r["label"], "status": r["status"], "files": r["file_count"]} for r in results]}))
