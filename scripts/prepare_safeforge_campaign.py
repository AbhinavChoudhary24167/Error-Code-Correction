#!/usr/bin/env python3
"""Validate a raw campaign CSV and emit hashed SafeForge replay artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.experimental_data import ingest_fault_map_csv, leave_one_group_out_splits, write_campaign_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--holdout-field", choices=["device_id", "source_group", "independence_group"])
    args = parser.parse_args()
    campaign = json.loads(Path(args.campaign).read_text(encoding="utf-8"))
    package = ingest_fault_map_csv(args.csv, campaign)
    write_campaign_package(package, args.outdir)
    if args.holdout_field:
        splits = leave_one_group_out_splits(
            package["injection_vectors"], field=args.holdout_field
        )
        Path(args.outdir, "holdout_splits.json").write_text(
            json.dumps(splits, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(Path(args.outdir, "manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
