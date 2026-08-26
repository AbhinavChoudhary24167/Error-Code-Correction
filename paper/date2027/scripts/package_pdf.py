#!/usr/bin/env python3
"""Copy the validated manuscript PDF to the stable submission path."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "paper" / "date2027" / "main.pdf"
DEST = ROOT / "output" / "pdf" / "date2027_submission.pdf"


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"missing compiled manuscript: {SOURCE}")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, DEST)
    print(DEST)


if __name__ == "__main__":
    main()

