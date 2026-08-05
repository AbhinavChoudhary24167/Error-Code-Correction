from __future__ import annotations

import json
from pathlib import Path
import shutil

from green_ecc_phy.hashing import (
    RAW_BYTES_SHA256_V1,
    SCIENTIFIC_CONTENT_SHA256_V1,
    canonical_scientific_text_bytes,
    file_sha256,
    scientific_file_identity,
    scientific_file_sha256,
)
from green_ecc_phy.registry import EccRegistry


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "green_ecc_physical_simulation" / "registry"


def _write(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_lf_crlf_and_cr_have_one_scientific_identity(tmp_path: Path) -> None:
    lf = _write(tmp_path / "lf.py", b"x = 1\ny = 2\n")
    crlf = _write(tmp_path / "crlf.py", b"x = 1\r\ny = 2\r\n")
    cr = _write(tmp_path / "cr.py", b"x = 1\ry = 2\r")
    identities = {scientific_file_sha256(path) for path in (lf, crlf, cr)}
    assert len(identities) == 1


def test_non_line_ending_character_change_changes_identity(tmp_path: Path) -> None:
    left = _write(tmp_path / "left.py", b"value = 1\n")
    right = _write(tmp_path / "right.py", b"value = 2\n")
    assert scientific_file_sha256(left) != scientific_file_sha256(right)


def test_matrix_bit_change_changes_identity(tmp_path: Path) -> None:
    left = _write(tmp_path / "left.json", b'{"H":[[1,0],[0,1]]}\n')
    right = _write(tmp_path / "right.json", b'{"H":[[1,1],[0,1]]}\n')
    assert scientific_file_sha256(left) != scientific_file_sha256(right)


def test_polynomial_coefficient_change_changes_identity(tmp_path: Path) -> None:
    left = _write(tmp_path / "left.txt", b"g(x)=x^6+x+1\n")
    right = _write(tmp_path / "right.txt", b"g(x)=x^6+x^2+1\n")
    assert scientific_file_sha256(left) != scientific_file_sha256(right)


def test_python_indentation_change_changes_identity(tmp_path: Path) -> None:
    left = _write(tmp_path / "left.py", b"if ok:\n    run()\n")
    right = _write(tmp_path / "right.py", b"if ok:\n\trun()\n")
    assert scientific_file_sha256(left) != scientific_file_sha256(right)


def test_binary_inputs_remain_raw_byte_sensitive(tmp_path: Path) -> None:
    lf = _write(tmp_path / "payload.bin", b"\x00\r\n\xff")
    cr = _write(tmp_path / "other.bin", b"\x00\n\xff")
    left = scientific_file_identity(lf)
    right = scientific_file_identity(cr)
    assert left["scheme"] == right["scheme"] == RAW_BYTES_SHA256_V1
    assert left["sha256"] == file_sha256(lf)
    assert left["sha256"] != right["sha256"]


def _declared_sources() -> set[str]:
    sources: set[str] = set()
    for directory in ("codes", "implementations", "architectures"):
        for path in sorted((REGISTRY / directory).glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            sources.update(map(str, payload.get("source_files", [])))
            sources.update(map(str, payload.get("source_hashes", {})))
            sources.update(map(str, payload.get("content_hashes", {}).get("source_files", {})))
    return sources


def _emulated_checkout(tmp_path: Path, newline: bytes) -> Path:
    root = tmp_path / ("checkout-" + ("lf" if newline == b"\n" else "crlf"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(REGISTRY, root / "green_ecc_physical_simulation" / "registry")
    for raw in sorted(_declared_sources()):
        source = ROOT / raw
        destination = root / raw
        payload = source.read_bytes()
        identity = scientific_file_identity(source, scheme=SCIENTIFIC_CONTENT_SHA256_V1)
        if identity["scheme"] != RAW_BYTES_SHA256_V1:
            payload = canonical_scientific_text_bytes(payload).replace(b"\n", newline)
        _write(destination, payload)
    return root


def test_registry_loads_from_emulated_lf_checkout(tmp_path: Path) -> None:
    root = _emulated_checkout(tmp_path, b"\n")
    registry = EccRegistry.builtin(root)
    assert (len(registry.codes), len(registry.implementations)) == (15, 17)


def test_registry_loads_from_emulated_crlf_checkout(tmp_path: Path) -> None:
    root = _emulated_checkout(tmp_path, b"\r\n")
    registry = EccRegistry.builtin(root)
    assert (len(registry.codes), len(registry.implementations)) == (15, 17)


def test_existing_expected_content_identities_still_bind_same_content() -> None:
    config = json.loads((REGISTRY / "registry.json").read_text(encoding="utf-8"))
    assert config["scientific_source_hash_scheme"] == SCIENTIFIC_CONTENT_SHA256_V1
    registry = EccRegistry.builtin(ROOT)
    for directory in ("codes", "implementations"):
        for path in sorted((REGISTRY / directory).glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            expected = (
                payload["content_hashes"]["source_files"]
                if directory == "codes"
                else payload["source_hashes"]
            )
            for raw, digest in expected.items():
                assert registry.source_hash_matches(raw, ROOT / raw, digest)


def test_legacy_registry_scheme_remains_raw(tmp_path: Path) -> None:
    registry = EccRegistry(
        repo_root=ROOT,
        registry_path=tmp_path / "registry-without-scheme.json",
    )
    assert registry.source_hash_scheme == RAW_BYTES_SHA256_V1
    lf = _write(tmp_path / "legacy.py", b"x = 1\n")
    crlf = _write(tmp_path / "legacy-crlf.py", b"x = 1\r\n")
    assert scientific_file_sha256(lf, scheme=registry.source_hash_scheme) != scientific_file_sha256(
        crlf, scheme=registry.source_hash_scheme
    )
