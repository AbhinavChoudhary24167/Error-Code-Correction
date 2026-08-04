#!/usr/bin/env python3
"""Regenerate the frozen-scope SafeForge scientific-hardening artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.hardening import run_hardening_study


if __name__ == "__main__":
    print(
        json.dumps(
            run_hardening_study(
                repo_root=ROOT,
                outdir="reports/safeforge_hardening",
            ),
            indent=2,
            sort_keys=True,
        )
    )
