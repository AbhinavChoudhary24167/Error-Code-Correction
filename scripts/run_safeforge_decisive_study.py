#!/usr/bin/env python3
"""Run the decisive fixed-Hsiao placement/policy scientific gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.decisive_study import run_decisive_study


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/safeforge_decisive_72.json")
    parser.add_argument("--outdir", default="reports/safeforge_decisive_72")
    args = parser.parse_args()
    result = run_decisive_study(repo_root=ROOT, config_path=args.config, outdir=args.outdir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
