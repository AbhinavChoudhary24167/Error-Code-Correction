#!/usr/bin/env python3
"""Build the immutable Attempt07 canonical slew inventory used by Attempt08."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT.parent / "gate3_attempt07_sram22_matched_physical_closure"
PWORK = PRIOR / "raw" / "openroad" / "work"
LIBDIR = ROOT / "raw" / "liberty"
DESIGNS = {"U0": "attempt07_u0", "E0": "attempt07_e0"}


def norm(value: str) -> str:
    return value.replace("\\[", "[").replace("\\]", "]").replace("\\.", ".")


def violations(report: Path) -> list[dict]:
    text = report.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"finish report_check_types -max_slew.*?\nmax slew\n\nPin\s+Limit\s+Slew\s+Slack\n-+\n(?P<body>.*?)(?:\n\n|\Z)",
        text,
        re.S,
    )
    if not match:
        raise RuntimeError(f"max-slew table not found in {report}")
    rows = []
    for line in match.group("body").splitlines():
        row = re.match(
            r"(?P<object>\S+)\s+(?P<limit>-?[\d.]+)\s+(?P<slew>-?[\d.]+)\s+(?P<slack>-?[\d.]+)\s+\(VIOLATED\)",
            line,
        )
        if row:
            rows.append(
                {
                    "violating_object": norm(row["object"]),
                    "reported_transition_value_ns": float(row["slew"]),
                    "reported_maximum_permitted_transition_ns": float(row["limit"]),
                    "reported_slack_ns": float(row["slack"]),
                }
            )
    return rows


def slew_details(log: Path) -> dict[str, dict]:
    rows = {}
    pattern = re.compile(
        r"^(?P<object>\S+) \^ (?P<rmin>[\d.]+):(?P<rmax>[\d.]+) v (?P<fmin>[\d.]+):(?P<fmax>[\d.]+)$",
        re.M,
    )
    for match in pattern.finditer(log.read_text(encoding="utf-8", errors="replace")):
        rise = [float(match["rmin"]), float(match["rmax"])]
        fall = [float(match["fmin"]), float(match["fmax"])]
        sense = "rise" if max(rise) >= max(fall) else "fall"
        rows[norm(match["object"])] = {
            "rise_transition_ns_min_max_analysis": rise,
            "fall_transition_ns_min_max_analysis": fall,
            "transition_value_ns": max(rise + fall),
            "limiting_transition": sense,
        }
    return rows


def def_data(path: Path) -> tuple[dict[str, str], dict[str, dict]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    dbu_match = re.search(r"UNITS DISTANCE MICRONS\s+(\d+)\s*;", text)
    dbu = int(dbu_match.group(1)) if dbu_match else 1000
    components_text = text.split("COMPONENTS", 1)[1].split("END COMPONENTS", 1)[0]
    masters = {
        norm(inst): master
        for inst, master in re.findall(r"^\s*-\s+(\S+)\s+(\S+)", components_text, re.M)
    }
    nets_text = text.split("NETS", 1)[1].split("END NETS", 1)[0]
    blocks = re.findall(r"^\s*-\s+.*?\s;\s*$", nets_text, re.M | re.S)
    nets: dict[str, dict] = {}
    for block in blocks:
        name_match = re.match(r"^\s*-\s+(\S+)", block)
        if not name_match:
            continue
        name = norm(name_match.group(1))
        header = re.split(r"\s+\+(?:\s+USE|\s+ROUTED|\s+FIXED|\s+COVER)", block, maxsplit=1)[0]
        endpoints = []
        for left, right in re.findall(r"\(\s+(\S+)\s+(\S+)\s+\)", header):
            if left == "PIN":
                endpoints.append({"object": norm(right), "instance": None, "pin": norm(right), "master": "PRIMARY_IO"})
            else:
                inst, pin = norm(left), norm(right)
                endpoints.append({"object": f"{inst}/{pin}", "instance": inst, "pin": pin, "master": masters.get(inst, "UNKNOWN")})
        layer_lengths: Counter[str] = Counter()
        for route in re.finditer(r"(?:\+\s+ROUTED|\bNEW)\s+(\S+)(.*?)(?=(?:\bNEW\s+\S+)|\s*;|$)", block, re.S):
            layer = route.group(1)
            coords = re.findall(r"\(\s+(-?\d+|\*)\s+(-?\d+|\*)", route.group(2))
            last = None
            for xraw, yraw in coords:
                if last is None and (xraw == "*" or yraw == "*"):
                    continue
                x = last[0] if xraw == "*" and last else int(xraw)
                y = last[1] if yraw == "*" and last else int(yraw)
                point = (x, y)
                if last is not None:
                    layer_lengths[layer] += abs(point[0] - last[0]) + abs(point[1] - last[1])
                last = point
        nets[name] = {
            "endpoints": endpoints,
            "wire_length_um": round(sum(layer_lengths.values()) / dbu, 3),
            "route_layer_lengths_um": {key: round(value / dbu, 3) for key, value in sorted(layer_lengths.items()) if value},
        }
    return masters, nets


def spef_caps(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    prefix = text.split("*PORTS", 1)[0] if "*PORTS" in text else text
    names = {f"*{idx}": norm(name) for idx, name in re.findall(r"^\*(\d+)\s+(\S+)", prefix, re.M)}
    caps = {}
    for name, cap in re.findall(r"^\*D_NET\s+(\S+)\s+([\deE+.-]+)", text, re.M):
        caps[names.get(name, norm(name))] = float(cap)
    return caps


def output_pin(pin: str) -> bool:
    return pin in {"X", "Y", "Q", "Q_N", "CLKOUT", "GCLK"} or pin.startswith("dout[")


def find_net(obj: str, nets: dict[str, dict]) -> tuple[str, dict]:
    for name, data in nets.items():
        if obj in {endpoint["object"] for endpoint in data["endpoints"]}:
            return name, data
    raise KeyError(f"no DEF net for {obj}")


def classify(obj: str) -> tuple[str, str, str, str, str]:
    if "/dout[" in obj or obj.startswith("u_data/dout["):
        macro = "sram22_256x8m8w1" if ".u_ecc/" in obj else "sram22_256x64m4w8"
        return (
            "C",
            "SRAM macro output transition",
            "SRAM22 Liberty",
            f"{macro}_tt_025C_1v80.lib:{macro}:default_max_transition inherited by output pin",
            "EXPLICIT_MAX_TRANSITION_DESIGN_RULE_WITH_SELF_INCONSISTENT_OUTPUT_TABLE",
        )
    if obj.endswith("/clk") and "u_data" in obj:
        return (
            "E",
            "clock network transition at immutable SRAM clock input",
            "SRAM22 Liberty",
            "sram22_256x64m4w8_tt_025C_1v80.lib:sram22_256x64m4w8:clk:max_transition",
            "EXPLICIT_MAX_TRANSITION_DESIGN_RULE_AND_CHARACTERIZATION_RANGE_LIMIT",
        )
    if any(token in obj for token in ("/rstb", "/din[56]", "/din[57]")):
        macro = "sram22_256x8m8w1" if ".u_ecc/" in obj else "sram22_256x64m4w8"
        pin = obj.rsplit("/", 1)[-1]
        return (
            "B",
            "SRAM macro input transition",
            "SRAM22 Liberty",
            f"{macro}_tt_025C_1v80.lib:{macro}:{pin}:max_transition",
            "EXPLICIT_MAX_TRANSITION_DESIGN_RULE_AND_CHARACTERIZATION_RANGE_LIMIT",
        )
    return (
        "A",
        "standard-cell integration transition",
        "top-level SDC",
        "openroad/common.sdc:set_max_transition 0.60 [current_design]",
        "EXPLICIT_TOP_LEVEL_DESIGN_RULE",
    )


def endpoint_roles(obj: str, data: dict) -> tuple[dict, list[dict]]:
    endpoints = data["endpoints"]
    target = next(endpoint for endpoint in endpoints if endpoint["object"] == obj)
    if output_pin(target["pin"]):
        driver = target
    else:
        candidates = [endpoint for endpoint in endpoints if output_pin(endpoint["pin"])]
        driver = candidates[0] if candidates else next(endpoint for endpoint in endpoints if endpoint != target)
    receivers = [endpoint for endpoint in endpoints if endpoint != driver]
    return driver, receivers


def driver_kind(driver: dict) -> str:
    master = driver["master"]
    if master == "PRIMARY_IO":
        return "primary input"
    if master.startswith("sram22_"):
        return "SRAM22 macro output"
    if "clk" in master:
        return "clock cell"
    return "standard cell"


def sink_kind(receiver: dict) -> str:
    master = receiver["master"]
    if master == "PRIMARY_IO":
        return "primary output"
    if master.startswith("sram22_"):
        return "clock pin" if receiver["pin"] == "clk" else "SRAM22 macro input"
    if "clk" in master:
        return "clock pin"
    return "standard cell"


def main() -> None:
    all_rows = []
    per_design = {}
    for design, flow in DESIGNS.items():
        base = PWORK / "results" / "sky130hd" / flow / "seed11"
        _, nets = def_data(base / "6_final.def")
        caps = spef_caps(base / "6_final.spef")
        details = slew_details(ROOT / "raw" / "slew_detail" / f"original_{design.lower()}.log")
        rows = violations(PWORK / "reports" / "sky130hd" / flow / "seed11" / "6_finish.rpt")
        for index, row in enumerate(rows, 1):
            obj = row["violating_object"]
            name, net = find_net(obj, nets)
            driver, receivers = endpoint_roles(obj, net)
            cls, title, requirement_kind, source, semantics = classify(obj)
            detail = details[obj]
            permitted = 0.04 if cls == "C" else 0.351 if cls in {"B", "E"} else 0.60
            exact = detail["transition_value_ns"]
            all_rows.append(
                {
                    "record_id": f"{design}-S11-{index:03d}",
                    "design": design,
                    "seed": 11,
                    "violating_object": obj,
                    "net": name,
                    "driver": driver["object"],
                    "driver_cell": driver["master"],
                    "driver_pin": driver["pin"],
                    "receivers": [receiver["object"] for receiver in receivers],
                    "receiver_pins": [receiver["pin"] for receiver in receivers],
                    "transition_value_ns": exact,
                    "maximum_permitted_transition_ns": permitted,
                    "violation_magnitude_ns": round(exact - permitted, 9),
                    **detail,
                    "fanout": len(receivers),
                    "capacitance_pf": caps.get(name),
                    "capacitance_kind": "extracted SPEF D_NET parasitic; SPEF PIN_CAP NONE",
                    "estimated_parasitic_wire_length_um": net["wire_length_um"],
                    "route_layers": net["route_layer_lengths_um"],
                    "driver_type": driver_kind(driver),
                    "sink_types": [sink_kind(receiver) for receiver in receivers],
                    "source_of_max_transition_requirement": requirement_kind,
                    "liberty_file_cell_pin_or_sdc": source,
                    "requirement_origin": requirement_kind,
                    "requirement_semantics": semantics,
                    "primary_class": cls,
                    "class_description": title,
                    "reported_table_values": row,
                }
            )
        per_design[design] = {
            "violation_count": len(rows),
            "class_distribution": dict(sorted(Counter(record["primary_class"] for record in all_rows if record["design"] == design).items())),
        }

    for design in per_design:
        distribution = per_design[design]["class_distribution"]
        per_design[design]["class_distribution_A_through_F"] = {key: distribution.get(key, 0) for key in "ABCDEF"}
    payload = {
        "schema_version": 1,
        "inventory_source": "frozen Attempt07 canonical final-route STA/ODB-equivalent DEF/SPEF at seed 11",
        "inventory_built_before_repair_decision": True,
        "seed": 11,
        "record_count": len(all_rows),
        "per_design": per_design,
        "measurement_notes": {
            "transition": "Exact OpenSTA report_slews min/max-analysis rise/fall values; transition_value_ns is their maximum.",
            "capacitance": "Extracted SPEF *D_NET parasitic capacitance in pF. The file declares PIN_CAP NONE, so this field does not invent a Liberty pin-cap contribution.",
            "wire_length": "Manhattan sum of routed DEF segments, excluding via vertical distance; unit um.",
            "layers": "Per-net routed DEF segment length by layer.",
        },
        "records": all_rows,
    }
    (ROOT / "SLEW_VIOLATION_INVENTORY.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Slew violation inventory",
        "",
        "This is the frozen, pre-repair canonical Attempt07 seed-11 population. Exact rise/fall values were re-queried read-only from the final ODB/SDC/SPEF; topology and wire length come from the final routed DEF, and extracted parasitic capacitance comes from the final SPEF (`PIN_CAP NONE`).",
        "",
        "| Design | Total | A | B | C | D | E | F |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for design in ("U0", "E0"):
        dist = per_design[design]["class_distribution_A_through_F"]
        md.append(f"| {design} | {per_design[design]['violation_count']} | " + " | ".join(str(dist[key]) for key in "ABCDEF") + " |")
    md += [
        "",
        "The complete machine-readable record for every row—including net, driver/master/pin, every receiver and pin, exact rise/fall values, rule source, fanout, SPEF capacitance, DEF wire length/layers, and provenance class—is in `SLEW_VIOLATION_INVENTORY.json`. The compact table below is an index, not a replacement for those records.",
        "",
        "| ID | Object | Net | Driver cell | Limiting slew / limit (ns) | Fanout | Cap (pF) | Wire (um) | Class |",
        "|---|---|---|---|---:|---:|---:|---:|:---:|",
    ]
    for row in all_rows:
        md.append(
            f"| {row['record_id']} | `{row['violating_object']}` | `{row['net']}` | `{row['driver_cell']}` | "
            f"{row['transition_value_ns']:.9f} {row['limiting_transition']} / {row['maximum_permitted_transition_ns']:.3f} | "
            f"{row['fanout']} | {row['capacitance_pf'] if row['capacitance_pf'] is not None else 'n/a'} | "
            f"{row['estimated_parasitic_wire_length_um']:.3f} | {row['primary_class']} |"
        )
    (ROOT / "SLEW_VIOLATION_INVENTORY.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
