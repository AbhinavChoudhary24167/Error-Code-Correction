#!/usr/bin/env python3
"""Regenerate the complete probability-aware code-forging study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.pipeline import run_code_synthesis
from codeforge.portfolio_pipeline import run_portfolio_cosynthesis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "reports",
        help="Parent directory for the three canonical studies.",
    )
    args = parser.parse_args()
    output = args.outdir.resolve()
    results = {
        "small_exact": run_code_synthesis(
            ROOT / "configs" / "code_synthesis.example.json",
            output / "code_synthesis",
            repo_root=ROOT,
        ),
        "k64_scalable": run_code_synthesis(
            ROOT / "configs" / "code_synthesis_64.example.json",
            output / "code_synthesis_64",
            repo_root=ROOT,
        ),
        "portfolio": run_portfolio_cosynthesis(
            ROOT / "configs" / "portfolio_cosynthesis.example.json",
            output / "portfolio_cosynthesis",
            repo_root=ROOT,
        ),
    }
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

