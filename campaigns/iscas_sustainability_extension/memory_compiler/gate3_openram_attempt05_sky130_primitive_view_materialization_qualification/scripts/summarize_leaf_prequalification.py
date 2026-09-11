#!/usr/bin/env python3
"""Summarize the immutable Attempt05 leaf-verification evidence.

This script only reads campaign-local copies/logs.  The direct-GDS normal-tech
path is the qualification baseline.  MAGLEF and full-MAG results are retained
as diagnostic comparisons, never substituted for that baseline.
"""

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "leaf_prequalification"


def text(path):
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def drc(path):
    data = text(path)
    count = re.search(r"COUNT_TOTAL_WITH_HIERARCHICAL_DOUBLE_COUNTING=(\d+)", data)
    total = re.search(r"RULE_TOTAL=(\d+)", data)
    rules = []
    match = re.search(r"__RULE_CSV_BEGIN__\s*rule,count\s*(.*?)\s*__RULE_CSV_END__", data, re.S)
    if match:
        for line in match.group(1).splitlines():
            item = re.match(r'"(.*)",(\d+)$', line.strip())
            if item:
                rules.append({"rule": item.group(1), "count": int(item.group(2))})
    return {
        "error_tiles": int(count.group(1)) if count else None,
        "rule_occurrences": int(total.group(1)) if total else None,
        "rule_histogram": rules,
    }


def subckt_ports(path, cell):
    data = text(path)
    logical = []
    for line in data.splitlines():
        if line.startswith("+") and logical:
            logical[-1] += " " + line[1:].strip()
        else:
            logical.append(line.strip())
    for line in logical:
        fields = line.split()
        if len(fields) >= 2 and fields[0].lower() == ".subckt" and fields[1].lower() == cell.lower():
            return fields[2:]
    return []


def subckt_models(path, cell):
    data = text(path)
    in_cell = False
    counts = Counter()
    for raw_line in data.splitlines():
        line = raw_line.strip()
        fields = line.split()
        if len(fields) >= 2 and fields[0].lower() == ".subckt":
            in_cell = fields[1].lower() == cell.lower()
            continue
        if in_cell and line.lower().startswith(".ends"):
            break
        if not in_cell or not fields or line[0] in ".*+":
            continue
        if fields[0][0].lower() == "x":
            positional = [x for x in fields[1:] if "=" not in x]
            if positional:
                counts[positional[-1]] += 1
        elif fields[0][0].lower() == "m" and len(fields) >= 6:
            counts[fields[5]] += 1
    return dict(sorted(counts.items()))


def lvs(directory, cell):
    log = text(directory / "netgen.log")
    report = text(directory / "lvs.report")
    json_path = directory / "lvs.json"
    if not log:
        return {"status": "NOT_AVAILABLE"}
    if "Circuits match uniquely." in log and "failed pin matching" not in log:
        status = "PASS"
    elif "Not checked." in log:
        status = "NOT_CHECKED_NON_ELECTRICAL_ABSTRACT"
    else:
        status = "FAIL"
    devices = [None, None]
    nets = [None, None]
    pin_match = None
    if json_path.is_file():
        try:
            records = json.loads(text(json_path))
            candidates = [x for x in records if isinstance(x, dict) and "name" in x]
            record = candidates[-1] if candidates else {}
            if record:
                device_sides = record.get("devices", [[], []])
                devices = [sum(int(x[1]) for x in side) for side in device_sides]
                nets = record.get("nets", nets)
                pin_match = record.get("pins")
        except (ValueError, TypeError, IndexError):
            pass
    disconnected = sorted(set(re.findall(r"disconnected node:\s*(\S+)", report)))
    unmatched_extracted = sorted(set(re.findall(r"Net:\s*(\S+).*?\|\(no matching net\)", report)))
    unmatched_schematic = sorted(set(re.findall(r"\(no matching net\).*?\|Net:\s*(\S+)", report)))
    extracted_spice = directory / (cell + ".spice")
    schematic_spice = directory / (cell + ".schematic.spice")
    return {
        "status": status,
        "devices": {"extracted": devices[0], "schematic": devices[1]},
        "nets": {"extracted": nets[0], "schematic": nets[1]},
        "ports": {
            "extracted": subckt_ports(extracted_spice, cell),
            "schematic": subckt_ports(schematic_spice, cell),
            "netgen_pin_correspondence": pin_match,
        },
        "device_models": {
            "extracted": subckt_models(extracted_spice, cell),
            "schematic": subckt_models(schematic_spice, cell),
        },
        "disconnected_nodes_reported": disconnected,
        "unmatched_extracted_nets": unmatched_extracted,
        "unmatched_schematic_nets": unmatched_schematic,
        "report": str((directory / "lvs.report").relative_to(ROOT)).replace("\\", "/"),
    }


def defect(cell, category, result):
    gds = result["direct_vendor_gds_normal_tech"]["lvs"]
    drc_tiles = result["direct_vendor_gds_normal_tech"]["drc"]["error_tiles"]
    if cell.endswith("sram_sp_colend"):
        return "Gate is extracted as an internal net, absent from the top-level port list; Netgen shows '(no matching pin)' versus schematic gate."
    if cell.endswith("sram_sp_colenda"):
        return "Standalone topology/pins match, but the cell has 38 DRC tiles and its feed-through ports are disconnected at this one-device hierarchy; parent proxy risk remains."
    if category == "bitcell":
        return "WL is absent as a matching extracted net; 10 extracted versus 9 schematic nets prove a split/unjoined wordline partition."
    if category == "replica_bitcell":
        return "WL is divided between WL and an anonymous extracted net; 9 extracted versus 8 schematic nets."
    if category == "dummy_bitcell":
        return "Schematic WL has no matching extracted net; 14 extracted versus 13 schematic nets."
    if gds.get("status") == "PASS" and drc_tiles == 0:
        return "No standalone DRC or LVS connectivity defect observed in the unchanged source view."
    if gds.get("status") == "PASS":
        return "Standalone LVS passes, but nonzero DRC prevents qualification."
    if gds.get("status") == "NOT_AVAILABLE":
        return "No standalone schematic comparison is available for this physical-only helper/end view."
    return "Standalone direct-GDS LVS fails; see preserved report for pin/net/device detail."


inventory = json.loads((ROOT / "SOURCE_VIEW_INVENTORY.json").read_text(encoding="utf-8"))
rows = []
for source in inventory["cells"]:
    cell = source["cell"]
    cell_root = RAW / cell
    row = {
        "cell": cell,
        "category": source["category"],
        "required_by_unchanged_16x8_control": source["required_by_unchanged_16x8_control"],
        "source_identified": bool(source.get("openram_wrapper_views")),
        "source_expected_ports": source.get("schematic_pin_list", []),
        "maglef_abstract": {
            "drc": drc(cell_root / "maglef" / "drc.log"),
            "lvs": lvs(cell_root / "lvs", cell),
        },
        "full_vendor_mag": {
            "drc": drc(cell_root / "mag" / "drc.log"),
            "lvs": lvs(cell_root / "lvs_mag", cell),
        },
        "direct_vendor_gds_normal_tech": {
            "drc": drc(cell_root / "gds_normal" / "gds_import_drc_extract.log"),
            "lvs": lvs(cell_root / "gds_normal", cell),
        },
        "materialization_post": {
            "status": "NOT_PERFORMED_SEMANTICS_UNRESOLVED",
            "drc": None,
            "lvs": None,
        },
    }
    row["connectivity_defect"] = defect(cell, source["category"], row)
    row["qualified"] = (
        row["direct_vendor_gds_normal_tech"]["drc"]["error_tiles"] == 0
        and row["direct_vendor_gds_normal_tech"]["lvs"]["status"] == "PASS"
    )
    rows.append(row)

document = {
    "campaign": ROOT.name,
    "baseline": "direct vendor GDS imported by pinned normal sky130A Magic technology; no add-mask rewrite",
    "normal_verification_policy": "DRC unwaived; extraction blackbox off; Netgen topology comparison",
    "materialization_performed": False,
    "materialization_reason": "The required boolean/electrical semantics of CLI1MADD, CNTMADD, and CP1MADD remain unknown.",
    "cell_count": len(rows),
    "qualified_count": sum(1 for row in rows if row["qualified"]),
    "cells": rows,
}
(ROOT / "LEAF_PREQUALIFICATION_MATRIX.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

lines = [
    "# Leaf pre-materialization qualification matrix",
    "",
    "The qualification baseline is each original vendor GDS imported directly through the pinned normal `sky130A` Magic technology. DRC is unwaived, extraction uses `blackbox off`, and Netgen compares the extracted topology to the pinned OpenRAM LVS schematic. MAGLEF and full vendor MAG measurements are diagnostic controls only.",
    "",
    "| Cell | Devices (ext/sch) | Nets (ext/sch) | DRC tiles | Major rules (occurrences) | LVS | Connectivity defect | Required by 16x8 |",
    "|---|---:|---:|---:|---|---|---|---|",
]
for row in rows:
    base = row["direct_vendor_gds_normal_tech"]
    lv = base["lvs"]
    rules = sorted(base["drc"]["rule_histogram"], key=lambda x: (-x["count"], x["rule"]))[:3]
    major = "; ".join("{} ({})".format(x["rule"], x["count"]) for x in rules) or "n/a"
    devices = "{}/{}".format(lv.get("devices", {}).get("extracted"), lv.get("devices", {}).get("schematic"))
    nets = "{}/{}".format(lv.get("nets", {}).get("extracted"), lv.get("nets", {}).get("schematic"))
    lines.append("| `{}` | {} | {} | {} | {} | {} | {} | {} |".format(
        row["cell"], devices, nets, base["drc"]["error_tiles"], major.replace("|", "\\|"),
        lv["status"], row["connectivity_defect"].replace("|", "\\|"),
        "yes" if row["required_by_unchanged_16x8_control"] else "no"))
lines += [
    "",
    "Only the two unchanged decoder NAND source views are individually clean/equivalent. All central SRAM hard-cell families retain nonzero DRC, lack a usable standalone comparison, or fail LVS; required boolean composition semantics were not established. Raw logs, reports, extracted SPICE, and copied inputs are under `raw/leaf_prequalification/`.",
]
(ROOT / "LEAF_PREQUALIFICATION_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

qual = {
    "campaign": ROOT.name,
    "post_materialization_view_exists": False,
    "cells": [
        {
            "cell": row["cell"],
            "required_by_unchanged_16x8_control": row["required_by_unchanged_16x8_control"],
            "source_identified": row["source_identified"],
            "transformation_provenance_established": row["qualified"],
            "pre_drc_tiles": row["direct_vendor_gds_normal_tech"]["drc"]["error_tiles"],
            "pre_lvs": row["direct_vendor_gds_normal_tech"]["lvs"]["status"],
            "post_drc_tiles": row["direct_vendor_gds_normal_tech"]["drc"]["error_tiles"] if row["qualified"] else None,
            "post_lvs": "IDENTITY_SOURCE_VIEW_PASS" if row["qualified"] else "NOT_RUN_NO_EVIDENCE_SUPPORTED_TRANSFORMATION",
            "topology_verified": row["qualified"],
            "qualified": row["qualified"],
        }
        for row in rows
    ],
}
(ROOT / "LEAF_QUALIFICATION_MATRIX.json").write_text(json.dumps(qual, indent=2) + "\n", encoding="utf-8")

qlines = [
    "# Leaf qualification matrix",
    "",
    "No materialized post-view was created because the vendor add-mask composition semantics were not established. `post` is therefore not a repeated baseline measurement; it is explicitly not run.",
    "",
    "| Cell | Source identified | Pre DRC | Pre LVS | Transformation provenance | Post DRC | Post LVS | Topology verified | Qualified |",
    "|---|---|---:|---|---|---:|---|---|---|",
]
for cell in qual["cells"]:
    qlines.append("| `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(
        cell["cell"], "yes" if cell["source_identified"] else "no", cell["pre_drc_tiles"], cell["pre_lvs"],
        "identity source hash" if cell["transformation_provenance_established"] else "no qualifying transform",
        cell["post_drc_tiles"] if cell["post_drc_tiles"] is not None else "n/a", cell["post_lvs"],
        "yes" if cell["topology_verified"] else "no", "yes" if cell["qualified"] else "no"))
(ROOT / "LEAF_QUALIFICATION_MATRIX.md").write_text("\n".join(qlines) + "\n", encoding="utf-8")

print("summarized {} leaf cells; {} qualified".format(len(rows), sum(1 for cell in qual["cells"] if cell["qualified"])))
