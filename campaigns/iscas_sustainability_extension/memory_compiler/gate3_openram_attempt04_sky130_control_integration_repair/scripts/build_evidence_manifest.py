#!/usr/bin/env python3
"""Build the Attempt04 evidence manifest without hashing the manifest itself."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
OUTPUT = CAMPAIGN / "ATTEMPT04_EVIDENCE_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


rows = []
for path in sorted(CAMPAIGN.rglob("*"), key=lambda item: item.as_posix()):
    if not path.is_file() or path == OUTPUT:
        continue
    rows.append(
        {
            "path": path.relative_to(CAMPAIGN).as_posix(),
            "byte_size": path.stat().st_size,
            "sha256": sha256(path),
        }
    )

payload = {
    "campaign": "gate3_openram_attempt04_sky130_control_integration_repair",
    "algorithm": "sha256",
    "manifest_scope": "all Attempt04 repository files except this manifest",
    "external_work_root": "/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt04_sky130_control_integration_repair",
    "external_work_archived_under": "raw/",
    "file_count": len(rows),
    "byte_count": sum(row["byte_size"] for row in rows),
    "files": rows,
}
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
