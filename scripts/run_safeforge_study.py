#!/usr/bin/env python3
"""Reproduce the authoritative SafeForge comparison and all publication figures."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.safeforge_study import run_authoritative_study


if __name__ == "__main__":
    result = run_authoritative_study(repo_root=ROOT, outdir="reports/safeforge_study")
    print(json.dumps(result, indent=2, sort_keys=True))
