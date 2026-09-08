#!/usr/bin/env python3
"""Build the immutable Attempt05 source-view inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_ROOT))
from gds_inventory import inspect as inspect_gds  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path, logical_path: str) -> dict | None:
    if not path.is_file():
        return None
    return {
        "path": logical_path,
        "byte_size": path.stat().st_size,
        "sha256": sha256(path),
    }


def spice_subckt(path: Path, cell: str) -> dict:
    if not path.is_file():
        return {"available": False, "pins": [], "subcircuits": []}
    text = path.read_text(encoding="utf-8", errors="replace")
    logical_lines = []
    for line in text.splitlines():
        if line.startswith("+") and logical_lines:
            logical_lines[-1] += " " + line[1:].strip()
        else:
            logical_lines.append(line.strip())
    subckts = []
    selected = []
    for line in logical_lines:
        match = re.match(r"(?i)^\.subckt\s+(\S+)\s*(.*)$", line)
        if not match:
            continue
        name = match.group(1)
        pins = [token for token in match.group(2).split() if "=" not in token]
        subckts.append({"name": name, "pins": pins})
        if name.lower() == cell.lower():
            selected = pins
    return {"available": True, "pins": selected, "subcircuits": subckts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt04-root", type=Path, default=Path("/attempt"))
    parser.add_argument("--campaign-root", type=Path, default=Path("/campaign"))
    args = parser.parse_args()

    openram = args.attempt04_root / "source/OpenRAM"
    technology = openram / "technology/sky130"
    vendor = args.attempt04_root / "pdk/sky130_fd_bd_sram"
    cells = json.loads((args.campaign_root / "scripts/leaf_cells.json").read_text(encoding="utf-8"))
    analysis_root = args.campaign_root / "raw/gds_analysis"
    analysis_root.mkdir(parents=True, exist_ok=True)

    records = []
    hash_lines = []
    for descriptor in cells:
        cell = descriptor["cell"]
        prefix = "sky130_fd_bd_sram__"
        short = cell[len(prefix):] if cell.startswith(prefix) else cell
        vendor_dir = vendor / "cells" / short
        vendor_specs = {
            "gds": vendor_dir / f"{cell}.gds",
            "mag": vendor_dir / f"{cell}.mag",
            "maglef": vendor_dir / f"{cell}.maglef",
            "spice": vendor_dir / f"{cell}.spice",
            "lvs_spice": vendor_dir / f"{cell}.lvs.spice",
            "calibre_lvs_spice": vendor_dir / f"{cell}.lvs.calibre.spice",
            "klayout_lvs_spice": vendor_dir / f"{cell}.lvs.klayout.spice",
            "gds_pins": vendor_dir / f"{cell}.gds.pins",
            "magic_lef": vendor_dir / f"{cell}.magic.lef",
        }
        wrapper_specs = {
            "gds": technology / "gds_lib" / f"{cell}.gds",
            "mag": technology / "mag_lib" / f"{cell}.mag",
            "maglef": technology / "maglef_lib" / f"{cell}.mag",
            "spice": technology / "sp_lib" / f"{cell}.sp",
            "lvs_spice": technology / "lvs_lib" / f"{cell}.sp",
        }
        vendor_views = {}
        wrapper_views = {}
        for name, path in vendor_specs.items():
            rec = file_record(path, f"sky130_fd_bd_sram/cells/{short}/{path.name}")
            vendor_views[name] = rec
            if rec:
                hash_lines.append(f"{rec['sha256']}  {rec['path']}")
        for name, path in wrapper_specs.items():
            rec = file_record(path, f"OpenRAM/technology/sky130/{path.parent.name}/{path.name}")
            wrapper_views[name] = rec
            if rec:
                hash_lines.append(f"{rec['sha256']}  {rec['path']}")

        gds_path = vendor_specs["gds"] if vendor_specs["gds"].is_file() else wrapper_specs["gds"]
        gds_payload = inspect_gds(gds_path) if gds_path.is_file() else None
        if gds_payload:
            gds_payload["path"] = (
                vendor_views["gds"]["path"] if vendor_views["gds"] else wrapper_views["gds"]["path"]
            )
            (analysis_root / f"{cell}.json").write_text(
                json.dumps(gds_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

        schematic_path = (
            vendor_specs["lvs_spice"]
            if vendor_specs["lvs_spice"].is_file()
            else wrapper_specs["lvs_spice"]
        )
        schematic = spice_subckt(schematic_path, cell)
        ordinary = spice_subckt(vendor_specs["spice"], cell)
        equality = {}
        for name in sorted(set(vendor_views) & set(wrapper_views)):
            left = vendor_views[name]
            right = wrapper_views[name]
            equality[name] = (
                "BYTE_IDENTICAL" if left and right and left["sha256"] == right["sha256"] else
                "DIFFERENT" if left and right else "VIEW_NOT_AVAILABLE_ON_BOTH_SIDES"
            )
        records.append(
            {
                **descriptor,
                "canonical_cell_name": cell,
                "required_by_unchanged_16x8_control": True,
                "layout_origin": "imported_vendor_hard_cell",
                "source_repository": "VLSIDA/sky130_fd_bd_sram",
                "source_repository_commit": "dd64256961317205343a3fd446908b42bafba388",
                "package_origin": "pinned sky130_fd_bd_sram build-space library",
                "vendor_views": vendor_views,
                "openram_wrapper_views": wrapper_views,
                "wrapper_vs_vendor": equality,
                "schematic_pin_list": schematic["pins"] or ordinary["pins"],
                "lvs_subcircuits": schematic["subcircuits"],
                "ordinary_spice_subcircuits": ordinary["subcircuits"],
                "gds_root_structures": gds_payload["root_structures"] if gds_payload else [],
                "gds_structure_count": gds_payload["structure_count"] if gds_payload else 0,
                "gds_hierarchy": gds_payload["structures"] if gds_payload else {},
                "gds_layer_datatype_counts": gds_payload["all_layers"] if gds_payload else {},
                "observed_add_mask_layers": {
                    key: (gds_payload["all_layers"].get(key, 0) if gds_payload else 0)
                    for key in ("115/43", "22/21", "33/43", "92/44")
                },
            }
        )

    payload = {
        "campaign": args.campaign_root.name,
        "algorithm": "sha256",
        "inventory_policy": "read-only; no source view modified in place",
        "openram_commit": "b6a6f12642df6b84facc24a77f9a6f67a0d62dab",
        "sky130_fd_bd_sram_commit": "dd64256961317205343a3fd446908b42bafba388",
        "required_imported_cell_count": len(records),
        "cells": records,
    }
    (args.campaign_root / "SOURCE_VIEW_INVENTORY.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.campaign_root / "raw/source_view_hashes.sha256").write_text(
        "\n".join(sorted(set(hash_lines))) + "\n", encoding="utf-8"
    )

    lines = [
        "# Immutable source-view inventory",
        "",
        "All source views were read from pinned commit `dd64256961317205343a3fd446908b42bafba388`; none was modified in place. OpenRAM wrapper views are from commit `b6a6f12642df6b84facc24a77f9a6f67a0d62dab`. Paths in the JSON are logical provenance paths; hashes bind the exact bytes.",
        "",
        "| Cell | Category | Pins | GDS hierarchy | Add layers (shape records) | Vendor/OpenRAM view relation |",
        "|---|---|---|---:|---|---|",
    ]
    for row in records:
        masks = ", ".join(
            f"{name}={count}" for name, count in row["observed_add_mask_layers"].items() if count
        ) or "none"
        relations = ", ".join(f"{k}:{v}" for k, v in row["wrapper_vs_vendor"].items())
        lines.append(
            f"| `{row['canonical_cell_name']}` | {row['category']} | "
            f"{', '.join(row['schematic_pin_list']) or 'none'} | {row['gds_structure_count']} | "
            f"{masks} | {relations} |"
        )
    lines.extend(
        [
            "",
            "Full per-structure hierarchy, layer/datatype counts, every view path, size, and SHA-256 are in `SOURCE_VIEW_INVENTORY.json` and `raw/gds_analysis/`.",
        ]
    )
    (args.campaign_root / "SOURCE_VIEW_INVENTORY.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
