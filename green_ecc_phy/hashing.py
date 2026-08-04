"""Canonical provenance and file hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def canonical_hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_basis(payload: Mapping[str, Any]) -> dict[str, Any]:
    basis = {key: value for key, value in payload.items() if not str(key).startswith("_")}
    basis.pop("manifest_sha256", None)
    basis.pop("content_hashes", None)
    return basis


def manifest_sha256(payload: Mapping[str, Any]) -> str:
    return canonical_hash(manifest_basis(payload))
