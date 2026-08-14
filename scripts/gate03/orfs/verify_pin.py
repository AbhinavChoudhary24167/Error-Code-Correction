#!/usr/bin/env python3
"""Verify an immutable ORFS image/source pairing before any physical run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def tree_hash(root: Path, paths: list[str]) -> str:
    records = []
    for relative in paths:
        base = root / relative
        for path in sorted(base.rglob("*")) if base.is_dir() else [base]:
            if path.is_file():
                name = path.relative_to(root).as_posix()
                records.append((name, hashlib.sha256(path.read_bytes()).hexdigest()))
    data = "".join(f"{name}\0{digest}\n" for name, digest in sorted(records)).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="openroad/orfs@sha256:<64 hex>")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--image-metadata", type=Path, required=True,
                        help="JSON captured from the pinned image, including source_commit and content hashes")
    args = parser.parse_args()
    if not re.fullmatch(r"openroad/orfs@sha256:[0-9a-f]{64}", args.image):
        raise SystemExit("mutable or invalid ORFS image reference")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.source_root, text=True).strip()
    if head != args.expected_commit:
        raise SystemExit("ORFS source checkout does not match expected commit")
    metadata = json.loads(args.image_metadata.read_text(encoding="utf-8"))
    if metadata.get("source_commit") != head:
        raise SystemExit("image revision metadata does not match source checkout")
    hashes = {
        "flow": tree_hash(args.source_root, ["flow"]),
        "sky130hd": tree_hash(args.source_root, ["flow/platforms/sky130hd"]),
    }
    expected = metadata.get("source_hashes", {})
    if any(expected.get(key) != value for key, value in hashes.items()):
        raise SystemExit("image/source flow or platform hash mismatch")
    print(json.dumps({"image": args.image, "source_commit": head, "source_hashes": hashes,
                      "match_status": "PASS"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
