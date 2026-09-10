#!/usr/bin/env python3
"""Write the final package provenance manifest after all validation outputs exist."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
MANIFEST = ROOT / "PROVENANCE_MANIFEST.json"
DIGEST = ROOT / "PROVENANCE_MANIFEST.sha256"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    excluded = {MANIFEST.resolve(), DIGEST.resolve()}
    files = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
        if path.resolve() in excluded:
            continue
        files.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    obj = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository_head_at_generation": head,
        "sealed_scientific_input_commit": "8cf245ac6ac8cb9b010c073d439f04eb204d48a1",
        "manifest_self_exclusion": ["PROVENANCE_MANIFEST.json", "PROVENANCE_MANIFEST.sha256"],
        "artifact_count": len(files),
        "artifacts": files,
    }
    MANIFEST.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    DIGEST.write_text(f"{sha256(MANIFEST)}  PROVENANCE_MANIFEST.json\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "artifact_count": len(files), "manifest_sha256": sha256(MANIFEST)}, indent=2))


if __name__ == "__main__":
    main()
