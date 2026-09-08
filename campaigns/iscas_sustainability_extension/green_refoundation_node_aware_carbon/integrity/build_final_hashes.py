"""Build a self-excluding SHA-256 manifest for final campaign artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
OUTPUT = BASE / "integrity" / "FINAL_ARTIFACT_HASHES.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_paths(base: Path = BASE) -> list[Path]:
    return [
        path
        for path in sorted(base.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
        and path != base / "integrity" / "FINAL_ARTIFACT_HASHES.json"
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    ]


def build(base: Path = BASE) -> Path:
    output = base / "integrity" / "FINAL_ARTIFACT_HASHES.json"
    artifacts = [
        {
            "path": path.relative_to(base).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in artifact_paths(base)
    ]
    payload = {
        "schema_version": 1,
        "algorithm": "SHA-256",
        "root": "green_refoundation_node_aware_carbon",
        "self_exclusion": "integrity/FINAL_ARTIFACT_HASHES.json",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    return output


if __name__ == "__main__":
    build()
