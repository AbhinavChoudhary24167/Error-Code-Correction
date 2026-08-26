from pathlib import Path

from scripts.gate03es.adjudicate_historical_bytes import sha256_bytes, tree_hash


def test_tree_hash_is_sensitive_to_raw_line_endings(tmp_path: Path) -> None:
    source = tmp_path / "file.txt"
    source.write_bytes(b"one\ntwo\n")
    lf_hash = tree_hash(tmp_path)
    source.write_bytes(b"one\r\ntwo\r\n")

    assert tree_hash(tmp_path) != lf_hash


def test_sha256_bytes_is_raw(tmp_path: Path) -> None:
    assert sha256_bytes(b"one\n") != sha256_bytes(b"one\r\n")
