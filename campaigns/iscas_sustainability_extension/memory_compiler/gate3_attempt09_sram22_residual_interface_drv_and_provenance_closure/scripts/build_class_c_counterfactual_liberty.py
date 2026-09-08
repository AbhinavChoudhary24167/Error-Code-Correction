#!/usr/bin/env python3
"""Create diagnostic-only SRAM22 views with the inherited output rule excluded."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "raw" / "liberty"
OUT = ROOT / "raw" / "diagnostics" / "class_c_counterfactual" / "liberty"
FILES = (
    "sram22_256x64m4w8_tt_025C_1v80.lib",
    "sram22_256x8m8w1_tt_025C_1v80.lib",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for name in FILES:
        source = SOURCE / name
        before = digest(source)
        text = source.read_text(encoding="utf-8")
        needle = "default_max_transition : 0.04;"
        if text.count(needle) != 1:
            raise RuntimeError(f"expected exactly one inherited SRAM output rule in {source}")
        # Diagnostic copy only: keep all tables, pin-level 0.351 ns input rules,
        # cell names, and thresholds unchanged while excluding the 0.04 ns
        # library default that output pins inherit.
        output = OUT / name
        output.write_text(text.replace(needle, "default_max_transition : 1.50;", 1), encoding="utf-8")
        after = digest(source)
        if before != after:
            raise RuntimeError(f"production Liberty changed while creating diagnostic copy: {source}")
        records.append({
            "file": name,
            "production_path": str(source.relative_to(ROOT)).replace("\\", "/"),
            "production_sha256_before": before,
            "production_sha256_after": after,
            "diagnostic_copy_path": str(output.relative_to(ROOT)).replace("\\", "/"),
            "diagnostic_copy_sha256": digest(output),
            "only_intentional_difference": "library default_max_transition 0.04 ns -> 1.50 ns to exclude the inherited SRAM-output rule",
        })
    manifest = {
        "schema_version": 1,
        "purpose": "COUNTERFACTUAL_DIAGNOSTIC_ONLY_NOT_PRODUCTION",
        "production_liberty_immutable": True,
        "timing_tables_pin_rules_thresholds_unchanged": True,
        "records": records,
    }
    (OUT.parent / "diagnostic_liberty_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
