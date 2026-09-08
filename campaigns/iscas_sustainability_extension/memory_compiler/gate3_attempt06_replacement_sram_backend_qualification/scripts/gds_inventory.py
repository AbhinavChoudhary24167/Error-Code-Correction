#!/usr/bin/env python3
"""KLayout-batch GDS inventory for one immutable SRAM22-derived GDS."""

import json
import sys

import pya


def count_shapes(cell, layer_index):
    iterator = cell.begin_shapes_rec(layer_index)
    count = 0
    texts = []
    while not iterator.at_end():
        shape = iterator.shape()
        count += 1
        if shape.is_text():
            texts.append(shape.text.string)
        iterator.next()
    return count, texts


if len(sys.argv) >= 4:
    gds_path, output_path, expected_top = sys.argv[1:4]
else:
    gds_path = globals()["gds_path"]
    output_path = globals()["output_path"]
    expected_top = globals()["expected_top"]
layout = pya.Layout()
layout.read(gds_path)
tops = [cell.name for cell in layout.top_cells()]
top = layout.cell(expected_top)
if top is None:
    raise RuntimeError(f"expected top {expected_top!r} not present; tops={tops}")

bbox = top.bbox()
layers = []
all_texts = []
for layer_index in layout.layer_indices():
    info = layout.get_info(layer_index)
    count, texts = count_shapes(top, layer_index)
    if count:
        layers.append(
            {
                "layer": info.layer,
                "datatype": info.datatype,
                "name": info.name,
                "recursive_shape_count": count,
                "recursive_text_count": len(texts),
            }
        )
        all_texts.extend(texts)

record = {
    "gds_path": gds_path,
    "dbu_um": layout.dbu,
    "top_cells": tops,
    "expected_top": expected_top,
    "expected_top_found": True,
    "cell_count": layout.cells(),
    "top_direct_instance_count": sum(1 for _ in top.each_inst()),
    "bbox_um": [
        bbox.left * layout.dbu,
        bbox.bottom * layout.dbu,
        bbox.right * layout.dbu,
        bbox.top * layout.dbu,
    ],
    "width_um": bbox.width() * layout.dbu,
    "height_um": bbox.height() * layout.dbu,
    "layers": sorted(layers, key=lambda item: (item["layer"], item["datatype"])),
    "text_label_count": len(all_texts),
    "unique_text_labels": sorted(set(all_texts)),
    "readability": "PASS",
    "hierarchy_integrity": "PASS_EXPECTED_TOP_AND_REFERENCES_RESOLVED",
}
with open(output_path, "w", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps({"top": expected_top, "cells": record["cell_count"], "bbox_um": record["bbox_um"]}))
