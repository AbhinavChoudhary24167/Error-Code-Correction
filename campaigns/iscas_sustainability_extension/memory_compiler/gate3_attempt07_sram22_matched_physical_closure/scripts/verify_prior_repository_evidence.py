#!/usr/bin/env python3
"""Freshly rehash repository-resident evidence from Attempts01--06."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT.parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(label: str, manifest_path: Path, root: Path, field: str) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = []
    for row in manifest[field]:
        path = root / row["path"]
        actual = sha256(path) if path.is_file() else None
        checks.append(
            {
                "path": row["path"],
                "expected_sha256": row["sha256"],
                "actual_sha256": actual,
                "status": (
                    "PASS"
                    if actual == row["sha256"]
                    else ("MISSING" if actual is None else "CHANGED")
                ),
            }
        )
    return {
        "label": label,
        "manifest": manifest_path.relative_to(MEMORY).as_posix(),
        "file_count": len(checks),
        "status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
        "failures": [row for row in checks if row["status"] != "PASS"],
    }


campaigns = [
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
    verify(
        "Attempt05 repository evidence",
        MEMORY / "gate3_openram_attempt05_sky130_primitive_view_materialization_qualification" / "ATTEMPT05_EVIDENCE_MANIFEST.json",
        MEMORY / "gate3_openram_attempt05_sky130_primitive_view_materialization_qualification",
        "files",
    ),
    verify(
        "Attempt06 repository evidence",
        MEMORY / "gate3_attempt06_replacement_sram_backend_qualification" / "ATTEMPT06_EVIDENCE_MANIFEST.json",
        MEMORY / "gate3_attempt06_replacement_sram_backend_qualification",
        "files",
    ),
]
payload = {
    "schema_version": 1,
    "algorithm": "sha256",
    "scope": "repository-resident files listed by preserved Attempts01--06 manifests",
    "status": "PASS" if all(row["status"] == "PASS" for row in campaigns) else "FAIL",
    "campaigns": campaigns,
    "external_attempt02_attempt03": {
        "status": "NOT_REVERIFIED",
        "reason": (
            "Historical external trees are not promoted; this check covers only "
            "repository-resident evidence registered by prior manifests."
        ),
    },
}
target = ROOT / "raw" / "integrity" / "prior_campaign_repository_verification.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "status": payload["status"],
            "campaigns": [
                {"label": row["label"], "status": row["status"], "files": row["file_count"]}
                for row in campaigns
            ],
        }
    )
)
raise SystemExit(0 if payload["status"] == "PASS" else 1)
