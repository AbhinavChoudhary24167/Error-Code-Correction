#!/usr/bin/env python3
"""Regenerate the complete transition-aware GREEN-ECC study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from architecture.schedule_pipeline import run_transition_schedule


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "transition_schedule.example.json",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "reports" / "transition_aware",
    )
    args = parser.parse_args()
    result = run_transition_schedule(args.config, args.outdir, repo_root=ROOT)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
