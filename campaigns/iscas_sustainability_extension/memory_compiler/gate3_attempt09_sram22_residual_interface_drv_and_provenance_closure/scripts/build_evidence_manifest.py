#!/usr/bin/env python3
"""Build Attempt09's non-self-referential SHA-256 evidence manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ATTEMPT09_EVIDENCE_MANIFEST.json"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


files = []
for path in sorted((path for path in ROOT.rglob("*") if path.is_file()), key=lambda path: path.as_posix()):
    if path == TARGET or ".git" in path.parts or "__pycache__" in path.parts or ".pytest_cache" in path.parts or path.suffix == ".pyc":
        continue
    files.append({"path": path.relative_to(ROOT).as_posix(), "byte_size": path.stat().st_size, "sha256": digest(path)})

payload = {
    "schema_version": 1,
    "campaign": ROOT.name,
    "algorithm": "sha256-raw-bytes",
    "manifest_scope": "all campaign files except this manifest, nested Git metadata, and transient Python caches",
    "file_count": len(files),
    "byte_count": sum(row["byte_size"] for row in files),
    "files": files,
}
TARGET.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"file_count": payload["file_count"], "byte_count": payload["byte_count"]}))
