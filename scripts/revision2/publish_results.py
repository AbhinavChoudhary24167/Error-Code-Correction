#!/usr/bin/env python3
"""Copy the immutable external Revision-2 qualification into the repository."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-revision2/qualification")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    destination = args.repo.resolve() / "docs/date2027/revision2/results"
    if destination.exists():
        raise SystemExit(f"refusing to overwrite published Revision-2 results: {destination}")
    for line in (ROOT / "REV2_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        source = ROOT / relative.strip().removeprefix("./")
        if sha256(source) != expected:
            raise SystemExit(f"external Revision-2 qualification mismatch: {source.name}")
    destination.mkdir(parents=True)
    for source in ROOT.iterdir():
        if source.is_file():
            shutil.copy2(source, destination / source.name)
    print(f"REV2_RESULTS_PUBLISHED files={len(list(destination.iterdir()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
