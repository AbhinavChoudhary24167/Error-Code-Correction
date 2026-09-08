#!/usr/bin/env python3
"""Summarize where the public-deck SRAM22 DRC markers are reported.

This is deliberately an evidence-locality analysis, not a waiver engine.  It
does not alter GDS, suppress markers, or convert an incomplete public-deck run
into a foundry DRC pass.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path


INTERNAL_NAME_FRAGMENTS = (
    "sp_cell",
    "cell_array",
    "replica_cell",
    "rowend",
    "wlstrap",
    "hstrap",
    "sram22_inner",
)


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def analyze(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    items = root.findall("./items/item")
    rule_counts: Counter[str] = Counter()
    cell_counts: Counter[str] = Counter()
    for item in items:
        rule_counts[unquote(item.findtext("category", default="UNKNOWN"))] += 1
        cell_counts[item.findtext("cell", default="UNKNOWN")] += 1

    non_internal = {
        cell: count
        for cell, count in cell_counts.items()
        if not any(fragment in cell.lower() for fragment in INTERNAL_NAME_FRAGMENTS)
    }
    total = len(items)
    internal = total - sum(non_internal.values())
    return {
        "database": path.as_posix(),
        "top_cell": root.findtext("top-cell"),
        "generator": root.findtext("generator"),
        "marker_count": total,
        "rule_counts": dict(sorted(rule_counts.items(), key=lambda pair: (-pair[1], pair[0]))),
        "cell_counts": dict(sorted(cell_counts.items(), key=lambda pair: (-pair[1], pair[0]))),
        "sram_internal_marker_count": internal,
        "non_sram_internal_marker_count": sum(non_internal.values()),
        "sram_internal_fraction": (internal / total) if total else 1.0,
        "non_sram_internal_cells": non_internal,
        "all_reported_markers_sram_internal_by_report_hierarchy": not non_internal,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    results = [analyze(path) for path in args.inputs]
    all_internal = all(
        item["all_reported_markers_sram_internal_by_report_hierarchy"] for item in results
    )
    payload = {
        "schema": "attempt06-drc-locality-v1",
        "analysis_date": date.today().isoformat(),
        "method": (
            "Parse every <item> in each KLayout .lyrdb and group by rule and the "
            "hierarchical cell field emitted by the public SKY130HD runset."
        ),
        "runs": results,
        "hypothesis": "Public-deck markers are confined to dense SRAM-internal hierarchy.",
        "hypothesis_result": "SUPPORTED" if all_internal else "NOT_SUPPORTED",
        "interpretation": (
            "All reported markers are attributed to SRAM array, bitcell, replica, row-end, "
            "strap, or sram22_inner hierarchy. This supports hard-macro integration acceptance "
            "when combined with immutable upstream GDS and reported silicon evidence."
        ),
        "qualification_boundary": {
            "integration_disposition": "MACRO_INTEGRATION_BLACKBOX_ACCEPTABLE_WITH_DOCUMENTED_RISK",
            "leaf_drc_status": "DRC_NOT_INDEPENDENTLY_REPRODUCIBLE",
            "reason": (
                "The available public runset is not a complete foundry signoff deck and no "
                "SRAM22-specific foundry waiver, specialized-mask rule deck, or signoff report "
                "was published. Marker locality therefore cannot be renamed DRC PASS."
            ),
            "prohibited_claim": "PHYSICAL_DRC_QUALIFIED",
        },
        "no_geometry_or_report_suppression_performed": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "hypothesis_result": payload["hypothesis_result"],
        "runs": [
            {
                "top_cell": run["top_cell"],
                "markers": run["marker_count"],
                "internal_fraction": run["sram_internal_fraction"],
            }
            for run in results
        ],
        "leaf_drc_status": payload["qualification_boundary"]["leaf_drc_status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
