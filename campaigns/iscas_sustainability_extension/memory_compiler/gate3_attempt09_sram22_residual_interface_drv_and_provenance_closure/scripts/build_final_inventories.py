#!/usr/bin/env python3
"""Build exact canonical residual and Class-C measurement inventories."""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT.parent / "gate3_attempt08_sram22_slew_provenance_and_drv_closure"
WORK = ROOT / "raw" / "openroad" / "work"
FLOWS = {"U0": "attempt09_u0", "E0": "attempt09_e0"}
TARGETS = {
    "U0": ["u_data/rstb", "u_data/clk"],
    "E0": [
        "u_protected_memory.u_data/rstb",
        "u_protected_memory.u_data/clk",
        "u_protected_memory.u_ecc/rstb",
        "u_protected_memory.u_ecc/clk",
    ],
}


def norm(value: str) -> str:
    return value.replace("\\[", "[").replace("\\]", "]").replace("\\.", ".")


def slew_details(log: Path) -> dict[str, dict]:
    rows = {}
    pattern = re.compile(
        r"^(?P<object>\S+) \^ (?P<rmin>[\d.]+):(?P<rmax>[\d.]+) v (?P<fmin>[\d.]+):(?P<fmax>[\d.]+)$",
        re.M,
    )
    for match in pattern.finditer(log.read_text(encoding="utf-8", errors="replace")):
        rise = [float(match["rmin"]), float(match["rmax"])]
        fall = [float(match["fmin"]), float(match["fmax"])]
        values = rise + fall
        rows[norm(match["object"])] = {
            "rise_transition_ns_min_max_analysis": rise,
            "fall_transition_ns_min_max_analysis": fall,
            "transition_value_ns": max(values),
            "limiting_transition": "rise" if max(rise) >= max(fall) else "fall",
        }
    return rows


def def_data(path: Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    dbu_match = re.search(r"UNITS DISTANCE MICRONS\s+(\d+)\s*;", text)
    dbu = int(dbu_match.group(1)) if dbu_match else 1000
    components_text = text.split("COMPONENTS", 1)[1].split("END COMPONENTS", 1)[0]
    masters = {norm(inst): master for inst, master in re.findall(r"^\s*-\s+(\S+)\s+(\S+)", components_text, re.M)}
    nets_text = text.split("NETS", 1)[1].split("END NETS", 1)[0]
    blocks = re.findall(r"^\s*-\s+.*?\s;\s*$", nets_text, re.M | re.S)
    nets = {}
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
    return nets


def spef_caps(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    prefix = text.split("*PORTS", 1)[0] if "*PORTS" in text else text
    names = {f"*{idx}": norm(name) for idx, name in re.findall(r"^\*(\d+)\s+(\S+)", prefix, re.M)}
    return {names.get(name, norm(name)): float(cap) for name, cap in re.findall(r"^\*D_NET\s+(\S+)\s+([\deE+.-]+)", text, re.M)}


def is_output(pin: str) -> bool:
    return pin in {"X", "Y", "Q", "Q_N", "CLKOUT", "GCLK"} or pin.startswith("dout[")


def find_net(obj: str, nets: dict[str, dict]) -> tuple[str, dict]:
    for name, data in nets.items():
        if obj in {endpoint["object"] for endpoint in data["endpoints"]}:
            return name, data
    raise KeyError(f"no DEF net for {obj}")


def roles(obj: str, data: dict) -> tuple[dict, list[dict]]:
    target = next(endpoint for endpoint in data["endpoints"] if endpoint["object"] == obj)
    if is_output(target["pin"]):
        driver = target
    else:
        candidates = [endpoint for endpoint in data["endpoints"] if is_output(endpoint["pin"])]
        driver = candidates[0] if candidates else next(endpoint for endpoint in data["endpoints"] if endpoint != target)
    return driver, [endpoint for endpoint in data["endpoints"] if endpoint != driver]


def stats(values: list[float]) -> dict:
    return {"minimum": min(values), "median": statistics.median(values), "maximum": max(values)}


def main() -> None:
    prior = json.loads((PRIOR / "SLEW_VIOLATION_INVENTORY.json").read_text(encoding="utf-8"))
    original = {(r["design"], r["violating_object"]): r for r in prior["records"]}
    residual, repaired, class_c = [], [], []

    for design, flow in FLOWS.items():
        base = WORK / "results" / "sky130hd" / flow / "seed11"
        nets = def_data(base / "6_final.def")
        caps = spef_caps(base / "6_final.spef")
        detail = slew_details(ROOT / "raw" / "slew_detail" / f"final_{design.lower()}.log")

        for obj in TARGETS[design]:
            if obj not in detail:
                raise RuntimeError(f"missing exact final slew for {design} {obj}")
            net_name, net = find_net(obj, nets)
            driver, receivers = roles(obj, net)
            row = {
                "design": design,
                "seed": 11,
                "object": obj,
                "net": net_name,
                "driver": driver["object"],
                "driver_cell": driver["master"],
                "driver_strength_suffix": driver["master"].rsplit("_", 1)[-1],
                "driver_pin": driver["pin"],
                "receivers": [r["object"] for r in receivers],
                "fanout": len(receivers),
                "extracted_spef_parasitic_capacitance_pf": caps.get(net_name),
                "estimated_parasitic_wire_length_um": net["wire_length_um"],
                "route_layers": net["route_layer_lengths_um"],
                **detail[obj],
                "maximum_permitted_transition_ns": 0.351,
                "violation_magnitude_ns": round(detail[obj]["transition_value_ns"] - 0.351, 9),
                "requirement": "explicit SRAM22 input-pin max_transition and characterization-axis ceiling",
                "classification": "B" if obj.endswith("/rstb") else "E",
                "timing_path_impact": (
                    "asynchronous SRAM reset-control interface; closure impact is evaluated by whole-design setup/hold STA"
                    if obj.endswith("/rstb") else
                    "propagated SRAM clock-tree endpoint; repair preserves polarity and is evaluated by whole-design setup/hold STA"
                ),
                "status": "VIOLATING" if detail[obj]["transition_value_ns"] > 0.351 else "CLOSED",
                "original_attempt08": original.get((design, obj)),
            }
            (residual if row["status"] == "VIOLATING" else repaired).append(row)

        for obj, measurement in detail.items():
            if "/dout[" not in obj:
                continue
            net_name, net = find_net(obj, nets)
            driver, receivers = roles(obj, net)
            cap = caps.get(net_name)
            class_c.append({
                "design": design,
                "seed": 11,
                "object": obj,
                "macro": driver["master"],
                "net": net_name,
                "receivers": [r["object"] for r in receivers],
                "fanout": len(receivers),
                "extracted_spef_parasitic_capacitance_pf": cap,
                "extracted_load_vs_characterized_minimum_0p007": None if cap is None else cap / 0.007,
                "extracted_load_vs_characterized_maximum_0p52": None if cap is None else cap / 0.52,
                "estimated_parasitic_wire_length_um": net["wire_length_um"],
                **measurement,
                "inherited_max_transition_ns": 0.04,
                "transition_to_inherited_limit_ratio": measurement["transition_value_ns"] / 0.04,
            })

    expected = {"U0": 64, "E0": 72}
    actual = Counter(r["design"] for r in class_c)
    if dict(actual) != expected:
        raise RuntimeError(f"Class-C population mismatch: {actual}, expected {expected}")

    payload = {
        "schema_version": 1,
        "scope": "canonical final-route seed 11 after Attempt09 common repairs",
        "count": len(residual),
        "per_design_count": dict(Counter(r["design"] for r in residual)),
        "records": residual,
        "closed_target_records": repaired,
        "notes": {
            "capacitance": "SPEF D_NET parasitic capacitance in pF; SPEF declares PIN_CAP NONE, so Liberty receiver pin capacitance is not invented.",
            "wire_length": "Manhattan sum of routed DEF segments excluding via vertical distance, in um.",
        },
    }
    (ROOT / "RESIDUAL_EXTERNAL_DRV_INVENTORY.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Residual external DRV inventory", "",
        "Canonical final-route seed 11 retains exactly two genuine external rows, one per design. Exact values come from OpenSTA over the final ODB/SDC/SPEF; topology and route length come from final DEF.", "",
        "| Design | Object | Driver / cell | Actual / required (ns) | Fanout | SPEF cap (pF) | Wire (um) | Status |", "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in residual:
        md.append(f"| {row['design']} | `{row['object']}` | `{row['driver']}` / `{row['driver_cell']}` | {row['transition_value_ns']:.9f} / 0.351 | {row['fanout']} | {row['extracted_spef_parasitic_capacitance_pf']:.9g} | {row['estimated_parasitic_wire_length_um']:.3f} | VIOLATING |")
    md += ["", "Closed targeted interfaces:", "", "| Design | Object | Actual / required (ns) | Status |", "|---|---|---:|---|"]
    for row in repaired:
        md.append(f"| {row['design']} | `{row['object']}` | {row['transition_value_ns']:.9f} / 0.351 | CLOSED |")
    (ROOT / "RESIDUAL_EXTERNAL_DRV_INVENTORY.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    class_payload = {
        "schema_version": 1,
        "scope": "canonical final-route seed 11",
        "count": len(class_c),
        "per_design_count": dict(actual),
        "characterized_domain": {"input_transition_ns": [0.002, 0.351], "output_capacitance_pf": [0.007, 0.52]},
        "load_measurement_caveat": "Extracted SPEF D_NET capacitance is a reproducible parasitic-only lower-bound because PIN_CAP NONE; no receiver Liberty cap is invented.",
        "statistics": {},
        "records": class_c,
    }
    for design in ("U0", "E0"):
        rows = [r for r in class_c if r["design"] == design]
        caps = [r["extracted_spef_parasitic_capacitance_pf"] for r in rows if r["extracted_spef_parasitic_capacitance_pf"] is not None]
        class_payload["statistics"][design] = {
            "transition_ns": stats([r["transition_value_ns"] for r in rows]),
            "transition_to_0p04_ratio": stats([r["transition_to_inherited_limit_ratio"] for r in rows]),
            "extracted_parasitic_capacitance_pf": stats(caps),
            "loads_below_characterized_minimum": sum(v < 0.007 for v in caps),
            "loads_within_characterized_domain": sum(0.007 <= v <= 0.52 for v in caps),
            "loads_above_characterized_maximum": sum(v > 0.52 for v in caps),
        }
    (ROOT / "raw" / "class_c_output_measurements.json").write_text(json.dumps(class_payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
