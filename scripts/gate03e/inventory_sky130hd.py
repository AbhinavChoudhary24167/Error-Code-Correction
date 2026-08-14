#!/usr/bin/env python3
"""Create the Gate-03E SKY130HD collateral and provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


SELECTED_FOR_GCD = {
    "cdl/sky130hd.cdl": "LVS source named by CDL_FILE",
    "cells_clkgate_hd.v": "Yosys clock-gate mapping file named by CLKGATE_MAP_FILE",
    "cells_latch_hd.v": "Yosys latch mapping file named by LATCH_MAP_FILE",
    "config.mk": "selected platform configuration",
    "drc/sky130hd.lydrc": "KLayout DRC deck named by KLAYOUT_DRC_FILE",
    "fastroute.tcl": "global-routing configuration named by FASTROUTE_TCL",
    "fill.json": "metal-fill configuration named by FILL_CONFIG",
    "gds/sky130_fd_sc_hd.gds": "wildcard-selected standard-cell GDS named by GDS_FILES",
    "lef/sky130_fd_sc_hd.tlef": "technology LEF named by TECH_LEF",
    "lef/sky130_fd_sc_hd_merged.lef": "standard-cell LEF named by SC_LEF",
    "lib/sky130_fd_sc_hd__tt_025C_1v80.lib": "timing Liberty named by LIB_FILES",
    "lvs/sky130hd.lylvs": "KLayout LVS deck named by KLAYOUT_LVS_FILE",
    "make_tracks.tcl": "platform track definitions sourced during floorplanning",
    "pdn.tcl": "power-grid definition named by PDN_TCL",
    "rcx_patterns.rules": "OpenRCX rule symlink named by RCX_RULES",
    "setRC.tcl": "platform layer/wire RC definitions sourced for extraction",
    "sky130hd.lyt": "KLayout technology file named by KLAYOUT_TECH_FILE",
    "tapcell.tcl": "tap/endcap insertion script named by TAPCELL_TCL",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def category(relative: str) -> list[str]:
    categories: list[str] = []
    path = Path(relative)
    suffix = path.suffix.lower()
    if "/lib/" in f"/{relative}":
        categories.append("liberty")
    if "/lef/" in f"/{relative}":
        categories.append("lef")
    if "/gds/" in f"/{relative}":
        categories.append("gds")
    if "/cdl/" in f"/{relative}":
        categories.append("cdl")
    if "track" in path.name:
        categories.append("track")
    if path.name in {"setRC.tcl", "rcx_patterns.rules"}:
        categories.append("rc")
    if path.name in {"fastroute.tcl", "config.mk"}:
        categories.append("routing")
    if path.name == "sky130_fd_sc_hd.tlef":
        categories.append("site")
    if suffix in {".lydrc", ".lylvs", ".lyt", ".lyp"}:
        categories.append("verification")
    if suffix == ".v":
        categories.append("mapping_model")
    return categories or ["platform_support"]


def extract_number(text: str, field: str) -> float:
    match = re.search(rf"\b{re.escape(field)}\s*:\s*([-+0-9.eE]+)\s*;", text)
    if not match:
        raise ValueError(f"Liberty field {field!r} was not found")
    return float(match.group(1))


def liberty_metadata(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="strict")
    library_match = re.search(r'^library\s*\("([^"]+)"\)', text, re.MULTILINE)
    condition_match = re.search(r'operating_conditions\s*\("([^"]+)"\)', text)
    if not library_match or not condition_match:
        raise ValueError("Liberty library/operating_conditions metadata is incomplete")
    operating = {
        "name": condition_match.group(1),
        "process": extract_number(text, "process"),
        "temperature_c": extract_number(text, "temperature"),
        "voltage_v": extract_number(text, "voltage"),
    }
    nominal = {
        "process": extract_number(text, "nom_process"),
        "temperature_c": extract_number(text, "nom_temperature"),
        "voltage_v": extract_number(text, "nom_voltage"),
    }
    confirmed = (
        library_match.group(1) == "sky130_fd_sc_hd__tt_025C_1v80"
        and operating == {
            "name": "tt_025C_1v80",
            "process": 1.0,
            "temperature_c": 25.0,
            "voltage_v": 1.8,
        }
        and nominal == {
            "process": 1.0,
            "temperature_c": 25.0,
            "voltage_v": 1.8,
        }
    )
    return {
        "path": "flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
        "library": library_match.group(1),
        "operating_conditions": operating,
        "nominal_conditions": nominal,
        "metadata_confirmation_pass": confirmed,
        "selected_only_after_metadata_confirmation": confirmed,
    }


def lef_sites(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="strict")
    pattern = re.compile(
        r"^SITE\s+(\S+)\s*$.*?^\s*CLASS\s+(\S+)\s*;.*?"
        r"^\s*SIZE\s+([-+0-9.eE]+)\s+BY\s+([-+0-9.eE]+)\s*;",
        re.MULTILINE | re.DOTALL,
    )
    return [
        {
            "name": match.group(1),
            "class": match.group(2),
            "width_um": float(match.group(3)),
            "height_um": float(match.group(4)),
        }
        for match in pattern.finditer(text)
    ]


def matching_lines(path: Path, prefix: str) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="strict").splitlines()
        if line.strip().startswith(prefix)
    ]


def create_manifest(root: Path, image_digest: str) -> dict[str, Any]:
    root = root.resolve()
    platform = root / "flow/platforms/sky130hd"
    entries: list[dict[str, Any]] = []
    for path in sorted(platform.rglob("*")):
        if not path.is_file() and not path.is_symlink():
            continue
        relative = path.relative_to(platform).as_posix()
        raw = os.readlink(path).encode("utf-8") if path.is_symlink() else path.read_bytes()
        header = path.resolve().read_bytes()[:32768].decode("utf-8", errors="ignore")
        spdx = sorted(set(re.findall(r"SPDX-License-Identifier:\s*([^\s*]+)", header)))
        git_record = git_output(root, "ls-files", "-s", f"flow/platforms/sky130hd/{relative}")
        entry: dict[str, Any] = {
            "path": f"flow/platforms/sky130hd/{relative}",
            "kind": "symlink" if path.is_symlink() else "file",
            "size_bytes": len(raw),
            "sha256": sha256_bytes(raw),
            "git_index_record": git_record,
            "categories": category(relative),
            "selected_for_gcd": relative in SELECTED_FOR_GCD,
            "selection_reason": SELECTED_FOR_GCD.get(relative),
            "spdx_identifiers_in_header": spdx,
        }
        if path.is_symlink():
            resolved = path.resolve()
            entry.update(
                {
                    "link_target": os.readlink(path),
                    "resolved_path": resolved.relative_to(root).as_posix(),
                    "resolved_size_bytes": resolved.stat().st_size,
                    "resolved_sha256": sha256_file(resolved),
                    "resolved_git_index_record": git_output(
                        root, "ls-files", "-s", resolved.relative_to(root).as_posix()
                    ),
                }
            )
        entries.append(entry)

    build_license = root / "LICENSE_BUILD_RUN_SCRIPTS"
    platform_license_files = [
        item.relative_to(platform).as_posix()
        for item in platform.rglob("*")
        if item.is_file() and "license" in item.name.lower()
    ]
    return {
        "schema_version": 1,
        "source": {
            "repository": "https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git",
            "commit": git_output(root, "rev-parse", "HEAD"),
            "tree": git_output(root, "rev-parse", "HEAD^{tree}"),
            "latest_commit_touching_sky130hd": git_output(
                root, "log", "-1", "--format=%H", "--", "flow/platforms/sky130hd"
            ),
        },
        "container_oci_digest": image_digest,
        "selected_gcd_collateral_count": sum(
            1 for entry in entries if entry["selected_for_gcd"]
        ),
        "platform_file_count": len(entries),
        "files": entries,
        "liberty_pvt_selection": liberty_metadata(
            platform / "lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
        ),
        "lef_sites": lef_sites(platform / "lef/sky130_fd_sc_hd.tlef"),
        "track_definitions": matching_lines(platform / "make_tracks.tcl", "make_tracks"),
        "rc_definitions": matching_lines(platform / "setRC.tcl", "set_"),
        "license_evidence": {
            "platform_local_license_files": sorted(platform_license_files),
            "platform_local_license_file_present": bool(platform_license_files),
            "repo_build_run_scripts_license": {
                "path": "LICENSE_BUILD_RUN_SCRIPTS",
                "sha256": sha256_file(build_license),
                "scope_caveat": "The file explicitly applies only to build/run scripts, not platform collateral.",
            },
            "collateral_headers": "Per-file SPDX identifiers are recorded where text headers expose them; absence is not interpreted as a license grant.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = create_manifest(args.root, args.image_digest)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not manifest["liberty_pvt_selection"]["metadata_confirmation_pass"]:
        return 1
    print(
        json.dumps(
            {
                "platform_files": manifest["platform_file_count"],
                "selected_for_gcd": manifest["selected_gcd_collateral_count"],
                "pvt_confirmation_pass": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
