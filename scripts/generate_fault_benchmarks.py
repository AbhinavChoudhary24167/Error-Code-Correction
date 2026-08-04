#!/usr/bin/env python3
"""Generate the versioned synthetic SRAM fault-PMF benchmark suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from codeforge.benchmarks import BENCHMARK_FAMILIES, build_benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outdir",
        type=Path,
        default=REPO / "configs" / "fault_distributions" / "benchmarks",
    )
    parser.add_argument("--bit-width", type=int, default=72)
    parser.add_argument("--seed", type=int, default=5200)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "generator": "codeforge.benchmarks.build_benchmark",
        "bit_width": args.bit_width,
        "base_seed": args.seed,
        "benchmarks": [],
    }
    for offset, family in enumerate(BENCHMARK_FAMILIES):
        seed = args.seed + offset
        payload = build_benchmark(family, bit_width=args.bit_width, seed=seed)
        path = args.outdir / f"{family}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest["benchmarks"].append(
            {
                "family": family,
                "file": path.name,
                "distribution_id": payload["distribution_id"],
                "seed": seed,
                "pattern_count": len(payload["patterns"]),
                "provenance_kind": "synthetic",
            }
        )
    (args.outdir / "benchmark_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
