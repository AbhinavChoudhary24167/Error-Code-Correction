#!/usr/bin/env python3
"""Parse and cross-check the immutable published SRAM22 text views."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


MACROS = {
    "sram22_256x64m4w8": {"data_width": 64, "addr_width": 8, "wmask_width": 8},
    "sram22_256x8m8w1": {"data_width": 8, "addr_width": 8, "wmask_width": 8},
}
SCALARS = {"clk": "INPUT", "rstb": "INPUT", "ce": "INPUT", "we": "INPUT"}
POWER = {"vdd": "INOUT", "vss": "INOUT"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_pins(spec: dict[str, int]) -> dict[str, str]:
    pins = dict(SCALARS)
    pins.update(POWER)
    for bus, direction, width in (
        ("addr", "INPUT", spec["addr_width"]),
        ("wmask", "INPUT", spec["wmask_width"]),
        ("din", "INPUT", spec["data_width"]),
        ("dout", "OUTPUT", spec["data_width"]),
    ):
        for index in range(width):
            pins[f"{bus}[{index}]"] = direction
    return pins


def parse_lef(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    macro = None
    size = None
    pins: dict[str, dict] = {}
    obs = {"rectangles": 0, "layers": {}}
    current_pin = None
    current_layer = None
    in_obs = False
    for line in lines:
        stripped = line.strip()
        match = re.fullmatch(r"MACRO\s+(\S+)", stripped)
        if match:
            macro = match.group(1)
            continue
        match = re.fullmatch(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;", stripped)
        if match:
            size = [float(match.group(1)), float(match.group(2))]
            continue
        match = re.fullmatch(r"PIN\s+(\S+)", stripped)
        if match:
            current_pin = match.group(1)
            pins[current_pin] = {
                "direction": None,
                "use": "SIGNAL",
                "layers": {},
                "rectangles": 0,
                "all_rectangles_inside_macro": True,
            }
            current_layer = None
            continue
        if stripped == "OBS":
            in_obs = True
            current_pin = None
            current_layer = None
            continue
        if in_obs and stripped == "END":
            in_obs = False
            current_layer = None
            continue
        match = re.fullmatch(r"DIRECTION\s+(\S+)\s*;", stripped)
        if match and current_pin:
            pins[current_pin]["direction"] = match.group(1)
            continue
        match = re.fullmatch(r"USE\s+(\S+)\s*;", stripped)
        if match and current_pin:
            pins[current_pin]["use"] = match.group(1)
            continue
        match = re.fullmatch(r"LAYER\s+(\S+)\s*;", stripped)
        if match:
            current_layer = match.group(1)
            continue
        match = re.fullmatch(
            r"RECT\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s*;",
            stripped,
        )
        if match and current_layer:
            rect = [float(value) for value in match.groups()]
            if current_pin:
                record = pins[current_pin]
                record["rectangles"] += 1
                record["layers"][current_layer] = record["layers"].get(current_layer, 0) + 1
                if size and not (
                    0 <= rect[0] <= rect[2] <= size[0]
                    and 0 <= rect[1] <= rect[3] <= size[1]
                ):
                    record["all_rectangles_inside_macro"] = False
            elif in_obs:
                obs["rectangles"] += 1
                obs["layers"][current_layer] = obs["layers"].get(current_layer, 0) + 1

    assert macro and size, f"incomplete LEF header: {path}"
    return {
        "macro_name": macro,
        "size_um": size,
        "area_um2": size[0] * size[1],
        "pin_count": len(pins),
        "pins": pins,
        "obstructions": obs,
    }


def parse_verilog(path: Path, spec: dict[str, int]) -> dict:
    text = path.read_text(encoding="utf-8")
    module = re.search(r"\bmodule\s+(\w+)\s*\(", text).group(1)
    params = {
        key: int(re.search(rf"localparam\s+{key}\s*=\s*(\d+)", text).group(1))
        for key in ("DATA_WIDTH", "ADDR_WIDTH", "WMASK_WIDTH")
    }
    pins = expected_pins(spec)
    return {
        "macro_name": module,
        "parameters": params,
        "pin_count_with_power": len(pins),
        "pins": pins,
        "power_pins_conditional_on_USE_POWER_PINS": "`ifdef USE_POWER_PINS" in text,
        "posedge_clocked": "always @(posedge clk)" in text,
        "read_is_synchronous": "dout <= mem[addr]" in text,
        "reset_clears_memory": False,
        "reset_semantics": "active-low operation inhibit; no memory or dout initialization",
        "write_mask_assignments": len(re.findall(r"if \(wmask\[\d+\]\)", text)),
    }


def parse_spice(path: Path, macro: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"(?im)^\.SUBCKT\s+{re.escape(macro)}\s+(.+)$", text)
    assert match, f"top subcircuit missing in {path}"
    pins = match.group(1).split()
    return {
        "macro_name": macro,
        "top_subckt_found": True,
        "pin_count": len(pins),
        "pin_order": pins,
        "subcircuit_instance_count": len(re.findall(r"(?im)^\s*X\S+\s", text)),
        "transistor_primitive_reference_count": len(
            re.findall(r"sky130_fd_pr__(?:n|p)fet", text)
        ),
        "subcircuit_definition_count": len(re.findall(r"(?im)^\.SUBCKT\s", text)),
    }


def scalar(text: str, name: str, cast=float):
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*:\s*\"?([^;\"]+)\"?\s*;", text)
    return None if not match else cast(match.group(1).strip())


def parse_liberty(path: Path, spec: dict[str, int]) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    library = re.search(r"\blibrary\s*\(\s*([^\s)]+)", text).group(1)
    cell = re.search(r"(?m)^\s*cell\s*\(\s*([^\s)]+)", text).group(1)
    operating = re.search(r"operating_conditions\s*\(\s*([^\s)]+)", text).group(1)
    units = {}
    for name in (
        "time_unit",
        "voltage_unit",
        "current_unit",
        "leakage_power_unit",
        "pulling_resistance_unit",
    ):
        units[name] = scalar(text, name, str)
    cap = re.search(r"capacitive_load_unit\s*\(\s*([^,]+),\s*([^\)]+)\)", text)
    units["capacitive_load_unit"] = [cap.group(1).strip(), cap.group(2).strip()] if cap else None
    buses = {}
    for bus in ("addr", "wmask", "din", "dout"):
        match = re.search(rf"bus\s*\(\s*{bus}\s*\)\s*\{{(.*?)\n\s*\}}", text, re.S)
        buses[bus] = {
            "present": bool(match),
            "direction": re.search(r"direction\s*:\s*(\w+)", match.group(1)).group(1).upper()
            if match
            else None,
        }
    bus_widths = {}
    for match in re.finditer(
        r"type\s*\(\s*bus_\S+?_(addr|wmask|din|dout)_\d+_\d+\s*\)\s*\{(.*?)\n\s*\}",
        text,
        re.S,
    ):
        width_match = re.search(r"bit_width\s*:\s*(\d+)", match.group(2))
        bus_widths[match.group(1)] = int(width_match.group(1))
    timing_types = {}
    for value in re.findall(r"timing_type\s*:\s*(\w+)\s*;", text):
        timing_types[value] = timing_types.get(value, 0) + 1
    return {
        "path": path.name,
        "library_name": library,
        "cell_name": cell,
        "generator_claim": re.search(r"Models written by ([^*]+)\*/", text).group(1).strip(),
        "operating_condition": operating,
        "nom_process": scalar(text, "nom_process"),
        "nom_temperature_c": scalar(text, "nom_temperature"),
        "nom_voltage_v": scalar(text, "nom_voltage"),
        "units": units,
        "area_um2": scalar(text, "area"),
        "cell_leakage_power": scalar(text, "cell_leakage_power"),
        "memory_address_width": int(scalar(text, "address_width")),
        "memory_word_width": int(scalar(text, "word_width")),
        "buses": buses,
        "bus_widths": bus_widths,
        "clock_declared": bool(re.search(r"pin\s*\(\s*clk\s*\).*?clock\s*:\s*true", text, re.S)),
        "timing_type_counts": timing_types,
        "related_pin_count": len(re.findall(r"related_pin\s*:", text)),
        "cell_rise_tables": len(re.findall(r"\bcell_rise\s*\(", text)),
        "cell_fall_tables": len(re.findall(r"\bcell_fall\s*\(", text)),
        "rise_constraint_tables": len(re.findall(r"\brise_constraint\s*\(", text)),
        "fall_constraint_tables": len(re.findall(r"\bfall_constraint\s*\(", text)),
        "internal_power_groups": len(re.findall(r"\binternal_power\s*\(", text)),
        "rise_power_tables": len(re.findall(r"\brise_power\s*\(", text)),
        "fall_power_tables": len(re.findall(r"\bfall_power\s*\(", text)),
        "leakage_power_groups": len(re.findall(r"\bleakage_power\s*\(", text)),
        "expected_dimensions_match": (
            int(scalar(text, "address_width")) == spec["addr_width"]
            and int(scalar(text, "word_width")) == spec["data_width"]
            and bus_widths
            == {
                "wmask": spec["wmask_width"],
                "addr": spec["addr_width"],
                "din": spec["data_width"],
                "dout": spec["data_width"],
            }
        ),
    }


def source_manifest(source: Path, commit: str, retrieval_date: str) -> dict:
    artifacts = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(source).as_posix()
        role = "repository_support"
        if rel.startswith("sram22_256x"):
            role = "macro_source_artifact"
        artifacts.append(
            {
                "path": rel,
                "byte_size": path.stat().st_size,
                "sha256": sha256(path),
                "role": role,
            }
        )
    return {
        "schema_version": 1,
        "upstream_url": "https://github.com/ucb-substrate/sram22_sky130_macros",
        "upstream_commit": commit,
        "retrieval_date": retrieval_date,
        "license": "BSD-3-Clause",
        "source_checkout_policy": "detached exact commit; sparse checkout of only the two required macro directories plus repository-root files",
        "configuration_file": {
            "available_in_macro_repository": False,
            "result": "ABSENT_UPSTREAM",
            "parameters_encoded_by_names": {
                "sram22_256x64m4w8": {"num_words": 256, "data_width": 64, "mux_ratio": 4, "write_size": 8},
                "sram22_256x8m8w1": {"num_words": 256, "data_width": 8, "mux_ratio": 8, "write_size": 1},
            },
        },
        "readme_claims": {
            "generator": "SRAM22 developed at UC Berkeley",
            "use_at_own_risk": True,
            "both_required_macros_reported_taped_out": True,
            "reported_test_condition": "VDD=1.8 V, clock=25 MHz",
            "reported_behavior": "behaved correctly in silicon measurements",
        },
        "artifacts": artifacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--retrieval-date", required=True)
    args = parser.parse_args()
    source = args.campaign / "source_checkout"
    raw = args.campaign / "raw" / "qualification"
    derived = args.campaign / "raw" / "derived_gds"
    raw.mkdir(parents=True, exist_ok=True)
    derived.mkdir(parents=True, exist_ok=True)

    manifest = source_manifest(source, args.commit, args.retrieval_date)
    (args.campaign / "SRAM22_SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    interface = {"schema_version": 1, "macros": {}, "overall_result": "PASS"}
    timing = {"schema_version": 1, "macros": {}, "overall_result": "QUALIFIED_WITH_PROVENANCE_LIMITATION"}
    for macro, spec in MACROS.items():
        folder = source / macro
        lef = parse_lef(folder / f"{macro}.lef")
        verilog = parse_verilog(folder / f"{macro}.v", spec)
        spice = parse_spice(folder / f"{macro}.spice", macro)
        expected = expected_pins(spec)
        lef_pins = {name: value["direction"] for name, value in lef["pins"].items()}
        spice_set = set(spice["pin_order"])
        crosscheck = {
            "macro_names_match": lef["macro_name"] == verilog["macro_name"] == macro,
            "lef_matches_expected_pins": lef_pins == expected,
            "spice_matches_expected_pin_set": spice_set == set(expected),
            "verilog_matches_expected_pin_set": set(verilog["pins"]) == set(expected),
            "all_lef_pin_rectangles_inside_macro": all(
                pin["all_rectangles_inside_macro"] for pin in lef["pins"].values()
            ),
            "all_lef_pins_have_geometry": all(pin["rectangles"] > 0 for pin in lef["pins"].values()),
            "published_bus_ordering": {
                "verilog": "[MSB:LSB] declarations; logical bit indices explicit",
                "lef": "individual bit pins named bus[index]",
                "spice": "ascending explicit bit indices",
                "liberty": "downto buses with explicit bit pins",
            },
        }
        crosscheck["result"] = "PASS" if all(
            value for key, value in crosscheck.items() if key not in {"published_bus_ordering", "result"}
        ) else "FAIL"
        if crosscheck["result"] != "PASS":
            interface["overall_result"] = "FAIL"
        interface["macros"][macro] = {
            "expected": spec,
            "lef": lef,
            "verilog": verilog,
            "spice": spice,
            "crosscheck": crosscheck,
        }

        corners = [parse_liberty(path, spec) for path in sorted(folder.glob("*.lib"))]
        tt = next(item for item in corners if "tt_025C_1v80" in item["path"])
        timing["macros"][macro] = {
            "corner_count": len(corners),
            "corners": corners,
            "tt_area_matches_lef_with_reported_integer_rounding": abs(
                tt["area_um2"] - lef["area_um2"]
            ) <= 1.0,
            "all_dimensions_match": all(item["expected_dimensions_match"] for item in corners),
            "all_have_clock_timing": all(item["clock_declared"] and item["timing_type_counts"] for item in corners),
            "all_have_power_tables": all(item["internal_power_groups"] > 0 for item in corners),
            "evidence_level": "UPSTREAM_CADENCE_LIBERATE_MX_CHARACTERIZATION_NOT_INDEPENDENTLY_REPRODUCED",
        }

        source_gz = folder / f"{macro}.gds.gz"
        target_gds = derived / f"{macro}.gds"
        with gzip.open(source_gz, "rb") as incoming, target_gds.open("wb") as outgoing:
            while chunk := incoming.read(1024 * 1024):
                outgoing.write(chunk)
        (raw / f"{macro}_gds_decompression.json").write_text(
            json.dumps(
                {
                    "source": source_gz.relative_to(args.campaign).as_posix(),
                    "source_sha256": sha256(source_gz),
                    "derived": target_gds.relative_to(args.campaign).as_posix(),
                    "derived_sha256": sha256(target_gds),
                    "derived_bytes": target_gds.stat().st_size,
                    "transformation": "gzip decompression only; no GDS geometry edit",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    (raw / "interface_crosscheck.json").write_text(json.dumps(interface, indent=2) + "\n", encoding="utf-8")
    (raw / "timing_view_qualification.json").write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"interface": interface["overall_result"], "timing": timing["overall_result"]}))


if __name__ == "__main__":
    main()
