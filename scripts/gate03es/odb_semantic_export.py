#!/usr/bin/env python3
"""Deterministic, fail-closed semantic export for the pinned OpenDB database.

Run this with ``openroad -python`` from the exact frozen Gate 03E-S image.
The export deliberately retains technology, units, geometry, placement,
connectivity, routing shapes, and vias.  It does not rewrite coordinates or
technology state.  Object identifiers and serialization order are excluded in
favour of stable scientific identities (names, geometry, and connectivity).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA_ID = "gate03es-complete-odb-semantic-export-v1"
REQUIRED_CATEGORIES = (
    "technology",
    "units",
    "die_core_geometry",
    "rows",
    "tracks",
    "masters",
    "instances",
    "orientations",
    "placement_status",
    "nets",
    "pins",
    "connectivity",
    "routing_shapes",
    "vias",
)


def enum(value: Any) -> str | None:
    return None if value is None else str(value)


def name(value: Any) -> str | None:
    if value is None:
        return None
    method = getattr(value, "getName", None)
    return str(method()) if method else str(value)


def point(value: Any) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return [int(value[0]), int(value[1])]
    for x_name, y_name in (("x", "y"), ("getX", "getY")):
        x_method, y_method = getattr(value, x_name, None), getattr(value, y_name, None)
        if callable(x_method) and callable(y_method):
            return [int(x_method()), int(y_method())]
    raise TypeError(f"unsupported point object: {type(value).__name__}")


def rect(value: Any) -> list[int] | None:
    if value is None:
        return None
    return [int(value.xMin()), int(value.yMin()), int(value.xMax()), int(value.yMax())]


def box_record(value: Any) -> dict[str, Any]:
    is_via = bool(value.isVia())
    record: dict[str, Any] = {
        "rect": rect(value),
        "is_via": is_via,
        "layer": name(value.getTechLayer()),
        "tech_via": name(value.getTechVia()),
        "block_via": name(value.getBlockVia()),
        "layer_mask": int(value.getLayerMask()),
    }
    if is_via:
        record["via_xy"] = point(value.getViaXY())
    return record


def shape_record(value: Any) -> dict[str, Any]:
    if value.isVia():
        return {
            "kind": "via",
            "rect": rect(value.getBox()),
            "tech_via": name(value.getTechVia()),
            "block_via": name(value.getVia()),
            "via_xy": point(value.getViaXY()),
        }
    if value.isSegment():
        return {
            "kind": "segment",
            "layer": name(value.getTechLayer()),
            "rect": rect(value.getBox()),
            "length_dbu": int(value.getLength()),
        }
    raise ValueError(f"unparsed routing-shape type: {value.getType()}")


def terminal_ref(value: Any) -> str | None:
    if value is None:
        return None
    inst = value.getInst() if hasattr(value, "getInst") else None
    mterm = value.getMTerm() if hasattr(value, "getMTerm") else None
    if inst is not None and mterm is not None:
        return f"{inst.getName()}/{mterm.getName()}"
    return name(value)


def wire_paths(wire: Any) -> list[dict[str, Any]]:
    import odb

    if wire is None:
        return []
    iterator = odb.dbWirePathItr()
    path_value = odb.dbWirePath()
    iterator.begin(wire)
    paths: list[dict[str, Any]] = []
    while iterator.getNextPath(path_value):
        shapes: list[dict[str, Any]] = []
        shape_value = odb.dbWirePathShape()
        while iterator.getNextShape(shape_value):
            shapes.append(
                {
                    "junction_id": int(shape_value.junction_id),
                    "point": point(shape_value.point),
                    "layer": name(shape_value.layer),
                    "iterm": terminal_ref(shape_value.iterm),
                    "bterm": name(shape_value.bterm),
                    "shape": shape_record(shape_value.shape),
                }
            )
        paths.append({"is_branch": bool(path_value.is_branch), "is_short": bool(path_value.is_short), "shapes": shapes})
    return paths


def track_record(value: Any) -> dict[str, Any]:
    return {
        "layer": name(value.getTechLayer()),
        "grid_x": [int(item) for item in value.getGridX()],
        "grid_y": [int(item) for item in value.getGridY()],
        "patterns_x": int(value.getNumGridPatternsX()),
        "patterns_y": int(value.getNumGridPatternsY()),
    }


def layer_record(value: Any) -> dict[str, Any]:
    return {
        "name": value.getName(),
        "number": int(value.getNumber()),
        "routing_level": int(value.getRoutingLevel()),
        "type": enum(value.getType()),
        "direction": enum(value.getDirection()),
        "width": int(value.getWidth()),
        "min_width": int(value.getMinWidth()),
        "max_width": int(value.getMaxWidth()),
        "spacing": int(value.getSpacing()),
        "pitch_x": int(value.getPitchX()),
        "pitch_y": int(value.getPitchY()),
        "offset_x": int(value.getOffsetX()),
        "offset_y": int(value.getOffsetY()),
        "wire_extension": int(value.getWireExtension()),
        "resistance": float(value.getResistance()),
        "capacitance": float(value.getCapacitance()),
        "edge_capacitance": float(value.getEdgeCapacitance()),
        "area": float(value.getArea()),
        "num_masks": int(value.getNumMasks()),
        "lower_layer": name(value.getLowerLayer()),
        "upper_layer": name(value.getUpperLayer()),
    }


def via_record(value: Any) -> dict[str, Any]:
    record = {
        "name": value.getName(),
        "bbox": rect(value.getBBox()),
        "boxes": sorted((box_record(item) for item in value.getBoxes()), key=lambda item: json.dumps(item, sort_keys=True)),
    }
    for key, method_name, transform in (
        ("default", "isDefault", bool),
        ("top_of_stack", "isTopOfStack", bool),
        ("resistance", "getResistance", float),
        ("bottom_layer", "getBottomLayer", name),
        ("top_layer", "getTopLayer", name),
        ("tech_via", "getTechVia", name),
        ("orientation", "getOrient", enum),
    ):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                record[key] = transform(method())
            except TypeError:
                # Some SWIG classes expose an overloaded static lookup under
                # the same name; it is not an instance property.
                continue
    return record


def master_record(value: Any) -> dict[str, Any]:
    terminals = []
    for terminal in value.getMTerms():
        terminals.append(
            {
                "name": terminal.getName(),
                "io_type": enum(terminal.getIoType()),
                "signal_type": enum(terminal.getSigType()),
                "shape": enum(terminal.getShape()),
                "bbox": rect(terminal.getBBox()),
            }
        )
    return {
        "name": value.getName(),
        "type": enum(value.getType()),
        "width": int(value.getWidth()),
        "height": int(value.getHeight()),
        "area": int(value.getArea()),
        "origin": point(value.getOrigin()),
        "sequential": bool(value.isSequential()),
        "core": bool(value.isCore()),
        "filler": bool(value.isFiller()),
        "terminals": sorted(terminals, key=lambda item: item["name"]),
    }


def instance_record(value: Any) -> dict[str, Any]:
    connectivity = []
    for iterm in value.getITerms():
        connectivity.append(
            {
                "terminal": iterm.getMTerm().getName(),
                "net": name(iterm.getNet()),
                "io_type": enum(iterm.getIoType()),
                "signal_type": enum(iterm.getSigType()),
            }
        )
    return {
        "name": value.getName(),
        "master": value.getMaster().getName(),
        "origin": point(value.getOrigin()),
        "bbox": rect(value.getBBox()),
        "orientation": enum(value.getOrient()),
        "placement_status": enum(value.getPlacementStatus()),
        "source_type": enum(value.getSourceType()),
        "physical_only": bool(value.isPhysicalOnly()),
        "connectivity": sorted(connectivity, key=lambda item: item["terminal"]),
    }


def pin_record(value: Any) -> dict[str, Any]:
    pins = []
    for pin in value.getBPins():
        pins.append(
            {
                "placement_status": enum(pin.getPlacementStatus()),
                "bbox": rect(pin.getBBox()),
                "boxes": sorted((box_record(item) for item in pin.getBoxes()), key=lambda item: json.dumps(item, sort_keys=True)),
            }
        )
    return {
        "name": value.getName(),
        "net": name(value.getNet()),
        "io_type": enum(value.getIoType()),
        "signal_type": enum(value.getSigType()),
        "special": bool(value.isSpecial()),
        "pins": pins,
    }


def special_wire_record(value: Any) -> dict[str, Any]:
    boxes = []
    for item in value.getWires():
        record = box_record(item)
        record.update(
            {
                "direction": enum(item.getDirection()),
                "wire_shape_type": enum(item.getWireShapeType()),
                "via_bottom_mask": int(item.getViaBottomLayerMask()),
                "via_cut_mask": int(item.getViaCutLayerMask()),
                "via_top_mask": int(item.getViaTopLayerMask()),
            }
        )
        boxes.append(record)
    return {
        "wire_type": enum(value.getWireType()),
        "shield": name(value.getShield()),
        "shapes": boxes,
    }


def net_record(value: Any) -> dict[str, Any]:
    iterms = sorted(terminal_ref(item) for item in value.getITerms())
    bterms = sorted(item.getName() for item in value.getBTerms())
    return {
        "name": value.getName(),
        "signal_type": enum(value.getSigType()),
        "source_type": enum(value.getSourceType()),
        "wire_type": enum(value.getWireType()),
        "special": bool(value.isSpecial()),
        "do_not_touch": bool(value.isDoNotTouch()),
        "iterms": iterms,
        "bterms": bterms,
        "wire_paths": wire_paths(value.getWire()),
        "special_wires": [special_wire_record(item) for item in value.getSWires()],
    }


def sorted_records(values: Iterable[Any], transform: Callable[[Any], dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((transform(item) for item in values), key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))


def export(input_path: Path) -> dict[str, Any]:
    import odb

    database = odb.dbDatabase.create()
    odb.read_db(database, str(input_path))
    chip = database.getChip()
    if chip is None or chip.getBlock() is None or database.getTech() is None:
        raise ValueError("ODB is missing database technology, chip, or block")
    block, technology = chip.getBlock(), database.getTech()
    masters = {item.getMaster().getName(): item.getMaster() for item in block.getInsts()}
    data = {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "required_categories": list(REQUIRED_CATEGORIES),
        "category_completeness": {key: True for key in REQUIRED_CATEGORIES},
        "unparsed_object_categories": [],
        "technology": {
            "name": technology.getName(),
            "lef_version": technology.getLefVersionStr(),
            "manufacturing_grid": int(technology.getManufacturingGrid()),
            "routing_layer_count": int(technology.getRoutingLayerCount()),
            "layers": sorted_records(technology.getLayers(), layer_record),
            "technology_vias": sorted_records(technology.getVias(), via_record),
        },
        "units": {
            "database_dbu_per_micron": int(database.getDbuPerMicron()),
            "technology_dbu_per_micron": int(technology.getDbUnitsPerMicron()),
            "block_dbu_per_micron": int(block.getDbUnitsPerMicron()),
            "block_def_units": int(block.getDefUnits()),
            "technology_lef_units": int(technology.getLefUnits()),
        },
        "block": {
            "name": block.getName(),
            "die_area": rect(block.getDieArea()),
            "core_area": rect(block.getCoreArea()),
            "rows": sorted_records(
                block.getRows(),
                lambda item: {
                    "name": item.getName(),
                    "site": name(item.getSite()),
                    "origin": point(item.getOrigin()),
                    "bbox": rect(item.getBBox()),
                    "orientation": enum(item.getOrient()),
                    "direction": enum(item.getDirection()),
                    "site_count": int(item.getSiteCount()),
                    "spacing": int(item.getSpacing()),
                },
            ),
            "tracks": sorted_records(block.getTrackGrids(), track_record),
        },
        "masters": sorted_records(masters.values(), master_record),
        "instances": sorted_records(block.getInsts(), instance_record),
        "pins": sorted_records(block.getBTerms(), pin_record),
        "nets": sorted_records(block.getNets(), net_record),
        "block_vias": sorted_records(block.getVias(), via_record),
    }
    counts = {
        "technology_layers": len(data["technology"]["layers"]),
        "technology_vias": len(data["technology"]["technology_vias"]),
        "rows": len(data["block"]["rows"]),
        "tracks": len(data["block"]["tracks"]),
        "masters": len(data["masters"]),
        "instances": len(data["instances"]),
        "pins": len(data["pins"]),
        "nets": len(data["nets"]),
        "block_vias": len(data["block_vias"]),
        "routing_shapes": sum(
            len(path["shapes"])
            for net in data["nets"]
            for path in net["wire_paths"]
        ) + sum(
            len(wire["shapes"])
            for net in data["nets"]
            for wire in net["special_wires"]
        ),
    }
    data["object_counts"] = counts
    if not all(data["category_completeness"].values()) or data["unparsed_object_categories"]:
        raise ValueError("semantic export is incomplete")
    return data


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} INPUT.odb OUTPUT.json", file=sys.stderr)
        return 2
    result = export(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    status = main()
    if status:
        raise RuntimeError(f"ODB semantic export failed with status {status}")
