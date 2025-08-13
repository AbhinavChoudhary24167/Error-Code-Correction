"""Voltage and technology aware energy model.

At import-time the module loads ``tech_calib.json`` which maps a CMOS process
node and supply voltage to the energy cost of XOR and AND gates.  Functions in
this module expose simple helpers that return energies in joules (``J``) or
energy-per-correction (``J/bit``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Sequence

import numpy as np



def _load_calib(path: Path) -> Dict[int, Dict[float, dict]]:
    """Load and validate gate energy calibration data."""
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
            if set(gates) != {"xor", "and"}:
                raise ValueError(
                    f"Missing gate energies for node {node_str} VDD {vdd_str}"
                )
            calib[node][vdd] = {
                "source": entry["source"],
                "date": entry["date"],
                "tempC": entry["tempC"],
                "gates": gates,
            }
    return calib


_CALIB = _load_calib(Path(__file__).with_name("tech_calib.json"))

_LOGGER = logging.getLogger(__name__)


def _nearest(v: float, choices) -> float:
    """Return the closest value in ``choices`` to ``v``."""
    return min(choices, key=lambda c: abs(c - v))


def gate_energy(node_nm: int, vdd: float, gate: str, *, mode: str = "nearest") -> float:
    """Return energy of a gate operation.

    Parameters
    ----------
    node_nm : int
        Technology node in nanometres.
    vdd : float
        Supply voltage in volts.
    gate : str
        Either ``"xor"`` or ``"and"``.

    Returns
    -------
    float
        Energy in joules (J) for the specified gate.
    """
    if gate not in {"xor", "and"}:
        raise KeyError(gate)

    return gate_energy_vec(node_nm, np.array([vdd]), gate, mode=mode).item()


def gate_energy_vec(
    node_nm: int, vdd_array: Sequence[float], gate: str, *, mode: str = "nearest"
) -> np.ndarray:
    """Vectorised gate energy lookup.

    Parameters
    ----------
    node_nm : int
        Technology node in nanometres.
    vdd_array : sequence of float
        Array of voltages.
    gate : str
        Either ``"xor"`` or ``"and"``.
    mode : str
        Currently only ``"nearest"`` is supported.
    """
    v = np.asanyarray(vdd_array, dtype=float)
    table = _CALIB[node_nm]
    vols = np.array(sorted(table))
    if mode == "nearest":
        idx = np.abs(vols[:, None] - v).argmin(0)
        nearest = vols[idx]
        unique_rounds = np.unique(nearest[v != nearest])
        if unique_rounds.size:
            logging.warning("VDD rounded to nearest entry: %s", unique_rounds)
        return np.vectorize(lambda x: table[x]["gates"][gate])(nearest)
    raise ValueError("mode must be 'nearest'")


def estimate_energy(
    parity_bits: int,
    detected_errors: int,
    *,
    node_nm: int = 28,
    vdd: float = 0.8,
) -> float:
    """Estimate the energy required to read a word.

    Parameters
    ----------
    parity_bits : int
        Number of parity bits evaluated using XOR gates.
    detected_errors : int
        Number of detected error bits which trigger AND gate checks.

    Returns
    -------
    float
        Estimated energy in joules (``J``) for the read operation.
    """
    if parity_bits < 0 or detected_errors < 0:
        raise ValueError("Counts must be non-negative")

    e_xor = gate_energy_vec(node_nm, np.array([vdd]), "xor", mode="nearest").item()
    e_and = gate_energy_vec(node_nm, np.array([vdd]), "and", mode="nearest").item()
    return parity_bits * e_xor + detected_errors * e_and


def epc(
    xor_cnt: int,
    and_cnt: int,
    corrections: int,
    *,
    node_nm: int = 28,
    vdd: float = 0.8,
) -> float:
    """Return energy per corrected bit.

    Parameters
    ----------
    xor_cnt : int
        Count of XOR operations.
    and_cnt : int
        Count of AND operations.
    corrections : int
        Number of bits corrected.

    Returns
    -------
    float
        Energy per corrected bit in joules/bit (``J/bit``).
    """
    if corrections <= 0:
        raise ValueError("corrections must be positive")

    total = estimate_energy(xor_cnt, and_cnt, node_nm=node_nm, vdd=vdd)
    return total / corrections


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Estimate energy per read")
    parser.add_argument("parity_bits", type=int, help="Number of parity bits")
    parser.add_argument(
        "detected_errors", type=int, nargs="?", default=0,
        help="Number of detected error bits (default: 0)"
    )
    parser.add_argument("--node", type=int, default=28, help="Process node in nm")
    parser.add_argument("--vdd", type=float, default=0.8, help="Supply voltage")
    args = parser.parse_args()

    energy = estimate_energy(
        args.parity_bits,
        args.detected_errors,
        node_nm=args.node,
        vdd=args.vdd,
    )
    print(f"Estimated energy per read: {energy:.3e} J")
