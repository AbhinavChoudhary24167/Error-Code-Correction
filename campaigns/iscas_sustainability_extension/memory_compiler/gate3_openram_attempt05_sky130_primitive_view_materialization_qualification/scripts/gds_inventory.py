#!/usr/bin/env python3
"""Read-only GDS record inventory for Attempt05.

This deliberately small parser records structure names, hierarchy references,
and layer/datatype use.  It does not rewrite or interpret geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path


RECORD_NAMES = {
    0x05: "BGNSTR",
    0x06: "STRNAME",
    0x07: "ENDSTR",
    0x08: "BOUNDARY",
    0x09: "PATH",
    0x0A: "SREF",
    0x0B: "AREF",
    0x0C: "TEXT",
    0x0D: "LAYER",
    0x0E: "DATATYPE",
    0x11: "ENDEL",
    0x12: "SNAME",
    0x16: "TEXTTYPE",
    0x2D: "BOX",
    0x2E: "BOXTYPE",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ascii_value(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def int2(payload: bytes) -> int:
    return struct.unpack(">h", payload[:2])[0]


def inspect(path: Path) -> dict:
    structures: dict[str, dict] = {}
    current_structure = "<library>"
    current_element = None
    current_layer = None
    current_datatype = None
    record_counts = Counter()
    hierarchy = defaultdict(Counter)

    data = path.read_bytes()
    offset = 0
    while offset + 4 <= len(data):
        length, record_type, data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if length < 4 or offset + length > len(data):
            raise ValueError(f"invalid GDS record at byte {offset}: length={length}")
        payload = data[offset + 4 : offset + length]
        record_counts[RECORD_NAMES.get(record_type, f"0x{record_type:02x}")] += 1
        if record_type == 0x06:
            current_structure = ascii_value(payload)
            structures.setdefault(
                current_structure,
                {"layers": Counter(), "references": Counter(), "elements": Counter()},
            )
        elif record_type in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x2D):
            current_element = RECORD_NAMES[record_type]
            current_layer = None
            current_datatype = None
            structures.setdefault(
                current_structure,
                {"layers": Counter(), "references": Counter(), "elements": Counter()},
            )["elements"][current_element] += 1
        elif record_type == 0x0D and payload:
            current_layer = int2(payload)
        elif record_type in (0x0E, 0x16, 0x2E) and payload:
            current_datatype = int2(payload)
        elif record_type == 0x12:
            target = ascii_value(payload)
            hierarchy[current_structure][target] += 1
            structures[current_structure]["references"][target] += 1
        elif record_type == 0x11:
            if current_layer is not None:
                key = f"{current_layer}/{current_datatype if current_datatype is not None else 0}"
                structures[current_structure]["layers"][key] += 1
            current_element = None
        offset += length

    serial_structures = {}
    all_layers = Counter()
    referenced = set()
    for name, value in structures.items():
        all_layers.update(value["layers"])
        referenced.update(value["references"])
        serial_structures[name] = {
            "layers": dict(sorted(value["layers"].items())),
            "references": dict(sorted(value["references"].items())),
            "elements": dict(sorted(value["elements"].items())),
        }
    roots = sorted(set(structures) - referenced)
    return {
        "path": path.as_posix(),
        "byte_size": path.stat().st_size,
        "sha256": digest(path),
        "root_structures": roots,
        "structure_count": len(structures),
        "all_layers": dict(sorted(all_layers.items())),
        "record_counts": dict(sorted(record_counts.items())),
        "structures": serial_structures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gds", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = inspect(args.gds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
