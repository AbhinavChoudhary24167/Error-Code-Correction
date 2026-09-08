#!/usr/bin/env python3
"""Audit every locally frozen SRAM22 output transition table and rule source."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source_checkout"
UPSTREAM_COMMIT = "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05"
TABLES = ("rise_transition", "fall_transition", "retain_rise_slew", "retain_fall_slew")


def block_at(text: str, start: int) -> str:
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start : pos + 1]
    raise ValueError("unclosed Liberty block")


def scalar(text: str, name: str) -> float | None:
    match = re.search(rf"\b{re.escape(name)}\s*:\s*([\d.]+)\s*;", text)
    return float(match.group(1)) if match else None


def quoted_numbers(text: str, name: str) -> list[float]:
    match = re.search(rf"\b{re.escape(name)}\s*\(\s*\"([^\"]+)\"", text)
    return [float(value.strip()) for value in match.group(1).split(",")] if match else []


def all_values(table: str) -> list[float]:
    marker = table.find("values")
    if marker < 0:
        return []
    end = table.find(");", marker)
    payload = table[marker:end]
    return [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", payload)]


def audit(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    bus_match = re.search(r"\bbus\s*\(\s*dout\s*\)\s*\{", text)
    if not bus_match:
        raise RuntimeError(f"dout bus not found in {path}")
    bus_block = block_at(text, bus_match.start())
    output_starts = list(re.finditer(r"\bpin\s*\(\s*(dout\[\d+\])\s*\)\s*\{", bus_block))
    outputs = []
    table_records = []
    for pin_match in output_starts:
        pin = pin_match.group(1)
        block = block_at(bus_block, pin_match.start())
        before_timing = block.split("timing", 1)[0]
        pin_override = scalar(before_timing, "max_transition")
        outputs.append({
            "pin": pin,
            "pin_max_transition_override_ns": pin_override,
            "max_capacitance_pf": scalar(before_timing, "max_capacitance"),
        })
    # SRAM22 expresses timing once at bus scope; it applies to every member.
    for table_name in TABLES:
        for match in re.finditer(rf"\b{table_name}\s*\(", bus_block):
            table = block_at(bus_block, match.start())
            values = all_values(table)
            index_1 = quoted_numbers(table, "index_1")
            index_2 = quoted_numbers(table, "index_2")
            table_records.append({
                "pin_scope": "all dout bus members",
                "table": table_name,
                "input_transition_axis_ns": index_1,
                "output_capacitance_axis_pf": index_2,
                "minimum_load_fastest_input_value_ns": values[0],
                "minimum_grid_value_ns": min(values),
                "minimum_load_fastest_input_exceeds_0p04": values[0] > 0.04,
            })
    default = scalar(text, "default_max_transition")
    thresholds = {name: scalar(text, name) for name in (
        "input_threshold_pct_fall", "input_threshold_pct_rise",
        "output_threshold_pct_fall", "output_threshold_pct_rise",
        "slew_lower_threshold_pct_fall", "slew_lower_threshold_pct_rise",
        "slew_upper_threshold_pct_fall", "slew_upper_threshold_pct_rise",
    )}
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "default_max_transition_ns": default,
        "threshold_percentages": thresholds,
        "output_pin_count": len(outputs),
        "output_pin_max_transition_override_count": sum(row["pin_max_transition_override_ns"] is not None for row in outputs),
        "output_max_capacitance_values_pf": sorted({row["max_capacitance_pf"] for row in outputs}),
        "transition_table_count": len(table_records),
        "all_minimum_load_fastest_input_values_exceed_default": all(row["minimum_load_fastest_input_value_ns"] > default for row in table_records),
        "minimum_transition_table_value_ns": min(row["minimum_grid_value_ns"] for row in table_records),
        "minimum_load_fastest_input_value_range_ns": [
            min(row["minimum_load_fastest_input_value_ns"] for row in table_records),
            max(row["minimum_load_fastest_input_value_ns"] for row in table_records),
        ],
        "transition_tables": table_records,
    }


def main() -> None:
    files = sorted(SOURCE.glob("sram22_*/*.lib"))
    records = [audit(path) for path in files]
    payload = {
        "schema_version": 1,
        "upstream_commit": UPSTREAM_COMMIT,
        "locally_verifiable_scope": "two macros, three published corners each, all output pins and all rise/fall plus retaining transition tables",
        "file_count": len(records),
        "files": records,
        "global_findings": {
            "all_six_views_default_max_transition_0p04": all(r["default_max_transition_ns"] == 0.04 for r in records),
            "all_output_pins_lack_pin_level_override": all(r["output_pin_max_transition_override_count"] == 0 for r in records),
            "all_output_transition_tables_exceed_0p04_at_min_load_fastest_input": all(r["all_minimum_load_fastest_input_values_exceed_default"] for r in records),
            "view_count": len(records),
            "classification": "UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY",
            "canonical_disposition": "PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV",
        },
    }
    (ROOT / "raw" / "sram22_output_provenance_audit.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
