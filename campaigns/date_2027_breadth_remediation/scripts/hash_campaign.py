#!/usr/bin/env python3
"""Write a deterministic SHA-256 inventory for repository-resident campaign evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
OUTPUT = CAMPAIGN / "FINAL_campaign_inventory.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite campaign inventory: {OUTPUT}")
    paths = sorted(
        path
        for path in CAMPAIGN.rglob("*")
        if path.is_file()
        and path != OUTPUT
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )
    OUTPUT.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(CAMPAIGN).as_posix()}\n" for path in paths),
        encoding="utf-8",
        newline="\n",
    )
    print(f"CAMPAIGN_INVENTORY_WRITTEN files={len(paths)} path={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

