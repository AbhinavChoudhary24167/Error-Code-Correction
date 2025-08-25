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
        vols_sorted = sorted(calib[node])
        for gate_name in ["xor", "and", "adder_stage"]:
            vals = [calib[node][vol]["gates"][gate_name] for vol in vols_sorted]
            if any(b < a for a, b in zip(vals, vals[1:])):
                raise ValueError(
                    f"{gate_name} energy non-monotonic in VDD for node {node_str}"
                )
    return calib
