"""Canonical provenance and file hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


RAW_BYTES_SHA256_V1 = "sha256-raw-bytes-v1"
SCIENTIFIC_CONTENT_SHA256_V1 = "scientific-content-sha256-v1"
TEXT_LF_SHA256_V1 = "sha256-text-lf-v1"

# Deliberately conservative: only declared scientific sources with a known
# textual suffix receive newline canonicalisation.  Everything else remains a
# raw byte stream, including a binary file that happens to contain CR or LF.
SCIENTIFIC_TEXT_SUFFIXES = frozenset(
    {
        ".c", ".cc", ".cpp", ".h", ".hh", ".hpp",
        ".json", ".md", ".py", ".sv", ".svh", ".txt", ".v", ".vh",
        ".yaml", ".yml",
    }
)
SCIENTIFIC_TEXT_FILENAMES = frozenset({"Makefile"})


def canonical_hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_declared_scientific_text(path: Path) -> bool:
    """Classify a declared source without attempting to decode its bytes."""

    return path.name in SCIENTIFIC_TEXT_FILENAMES or path.suffix.lower() in SCIENTIFIC_TEXT_SUFFIXES


def canonical_scientific_text_bytes(payload: bytes) -> bytes:
    """Canonicalise line endings only; all other bytes remain significant."""

    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def scientific_file_identity(
    path: Path,
    *,
    scheme: str = SCIENTIFIC_CONTENT_SHA256_V1,
) -> dict[str, str]:
    """Return an explicit versioned identity for a declared scientific source."""

    if scheme == RAW_BYTES_SHA256_V1:
        return {"scheme": RAW_BYTES_SHA256_V1, "sha256": file_sha256(path)}
    if scheme != SCIENTIFIC_CONTENT_SHA256_V1:
        raise ValueError(f"unsupported scientific source hash scheme: {scheme}")
    if not is_declared_scientific_text(path):
        return {"scheme": RAW_BYTES_SHA256_V1, "sha256": file_sha256(path)}
    digest = hashlib.sha256(canonical_scientific_text_bytes(path.read_bytes())).hexdigest()
    return {"scheme": TEXT_LF_SHA256_V1, "sha256": digest}


def scientific_file_sha256(
    path: Path,
    *,
    scheme: str = SCIENTIFIC_CONTENT_SHA256_V1,
) -> str:
    return scientific_file_identity(path, scheme=scheme)["sha256"]


def scientific_hash_matches(
    path: Path,
    expected: str,
    *,
    scheme: str = SCIENTIFIC_CONTENT_SHA256_V1,
    legacy_canonical_sha256: str | None = None,
) -> bool:
    """Match a declared digest without treating arbitrary legacy bytes as content.

    ``legacy_canonical_sha256`` is accepted only when a registry separately
    binds its historical digest to that canonical content identity.
    """

    actual = scientific_file_sha256(path, scheme=scheme)
    return expected == actual or (
        legacy_canonical_sha256 is not None and actual == legacy_canonical_sha256
    )


def manifest_basis(payload: Mapping[str, Any]) -> dict[str, Any]:
    basis = {key: value for key, value in payload.items() if not str(key).startswith("_")}
    basis.pop("manifest_sha256", None)
    basis.pop("content_hashes", None)
    return basis


def manifest_sha256(payload: Mapping[str, Any]) -> str:
    return canonical_hash(manifest_basis(payload))
