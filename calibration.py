"""Shared technology calibration loader.

This module centralises parsing of :mod:`tech_calib.json` so that both
Python utilities and any external tooling can rely on a single validated
schema.  It returns a nested mapping indexed by technology node and
voltage, mirroring the structure used by :mod:`energy_model`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def load_calibration(path: Path) -> Dict[int, Dict[float, dict]]:
    """Load and validate gate energy calibration data.

    Parameters
    ----------
    path : Path
        Location of the JSON calibration file.

    Returns
    -------
    dict
        Nested mapping ``{node_nm: {vdd: entry}}`` where ``entry`` contains
        metadata and gate energy information.
    """
    raw = json.load(open(path))
    calib: Dict[int, Dict[float, dict]] = {}
    for node_str, node_data in raw.items():
        node = int(node_str)
        calib[node] = {}
        for vdd_str, entry in node_data.items():
            vdd = float(vdd_str)
            required = {"source", "date", "tempC", "gates"}
            missing = required - entry.keys()
            if missing:
                raise ValueError(
                    f"Missing {missing} for node {node_str} VDD {vdd_str}"
                )
            gates = entry["gates"]
            if set(gates) != {"xor", "and", "adder_stage"}:
                raise ValueError(
                    f"Missing gate energies for node {node_str} VDD {vdd_str}"
                )
            calib[node][vdd] = {
                "source": entry["source"],
                "date": entry["date"],
                "tempC": entry["tempC"],
                "gates": gates,
            }
            for optional_field in ["corner", "activity_class"]:
                if optional_field in entry:
                    calib[node][vdd][optional_field] = entry[optional_field]
        vols_sorted = sorted(calib[node])
        for gate_name in ["xor", "and", "adder_stage"]:
            vals = [calib[node][vol]["gates"][gate_name] for vol in vols_sorted]
            if any(b < a for a, b in zip(vals, vals[1:])):
                raise ValueError(
                    f"{gate_name} energy non-monotonic in VDD for node {node_str}"
                )
    return calib


def get_calibration_envelope(calib: Dict[int, Dict[float, dict]]) -> dict:
    """Return read-only envelope metadata for runtime range checks.

    The returned metadata is additive and does not alter existing CLI output
    formatting or the schema returned by :func:`load_calibration`.
    """

    nodes = sorted(calib)
    vdds = sorted({vdd for node_data in calib.values() for vdd in node_data})
    temperatures = sorted(
        {
            float(entry["tempC"])
            for node_data in calib.values()
            for entry in node_data.values()
        }
    )
    corners = sorted(
        {
            str(entry["corner"])
            for node_data in calib.values()
            for entry in node_data.values()
            if "corner" in entry
        }
    )
    activity_classes = sorted(
        {
            str(entry["activity_class"])
            for node_data in calib.values()
            for entry in node_data.values()
            if "activity_class" in entry
        }
    )

    return {
        "nodes_nm": nodes,
        "node_nm_min": min(nodes),
        "node_nm_max": max(nodes),
        "vdd_points": vdds,
        "vdd_min": min(vdds),
        "vdd_max": max(vdds),
        "tempC_points": temperatures,
        "tempC_min": min(temperatures),
        "tempC_max": max(temperatures),
        "corners": corners,
        "activity_classes": activity_classes,
    }
