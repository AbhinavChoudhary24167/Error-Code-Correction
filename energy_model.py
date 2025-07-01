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

_CALIB_PATH = Path(__file__).with_name("tech_calib.json")


def _load_calibration() -> Dict[int, Dict[float, Dict[str, float]]]:
    """Load calibration table with numeric keys."""
    with _CALIB_PATH.open() as fh:
        raw = json.load(fh)

    calib: Dict[int, Dict[float, Dict[str, float]]] = {}
    for node_key, node_data in raw.items():
        node_nm = int(node_key)
        calib[node_nm] = {}
        for vdd_key, gates in node_data.items():
            vdd = float(vdd_key)
            calib[node_nm][vdd] = {k: float(v) for k, v in gates.items()}
    return calib


_CALIB = _load_calibration()
_NODE_VDDS = {node: sorted(vdds.keys()) for node, vdds in _CALIB.items()}

_LOGGER = logging.getLogger(__name__)


def _nearest_vdd(node_nm: int, vdd: float) -> float:
    """Return the calibration voltage closest to ``vdd``."""
    choices = np.array(_NODE_VDDS[node_nm], dtype=float)
    idx = np.abs(choices - vdd).argmin()
    nearest = float(choices[idx])
    if nearest != vdd:
        _LOGGER.warning(
            "Rounded VDD %.3fV to %.1fV for %dnm", vdd, nearest, node_nm
        )
    return nearest


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

    try:
        node_table = _CALIB[node_nm]
    except KeyError as exc:
        raise KeyError(f"Unknown node {node_nm}nm") from exc

    if mode == "nearest":
        vdd_key = vdd if vdd in node_table else _nearest_vdd(node_nm, vdd)
    elif mode == "strict":
        vdd_key = vdd
    else:
        raise ValueError(f"Unknown mode {mode}")

    try:
        return node_table[vdd_key][gate]
    except KeyError as exc:
        raise KeyError(
            f"Missing calibration for {node_nm}nm at {vdd_key}V"
        ) from exc


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
    arr = np.asarray(vdd_array, dtype=float)
    node_table = _CALIB[node_nm]
    if mode != "nearest":
        raise ValueError(f"Unknown mode {mode}")

    choices = np.array(_NODE_VDDS[node_nm], dtype=float)
    idx = np.abs(arr[:, None] - choices[None, :]).argmin(axis=1)
    selected = choices[idx]

    for req, sel in zip(arr, selected):
        if req != sel:
            _LOGGER.warning(
                "Rounded VDD %.3fV to %.1fV for %dnm", req, sel, node_nm
            )

    return np.array([node_table[float(v)][gate] for v in selected])


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

    e_xor = gate_energy(node_nm, vdd, "xor", mode="nearest")
    e_and = gate_energy(node_nm, vdd, "and", mode="nearest")
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
