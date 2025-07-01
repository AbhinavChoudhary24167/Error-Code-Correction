"""Voltage and technology aware energy model.

At import-time the module loads ``tech_calib.json`` which maps a CMOS process
node and supply voltage to the energy cost of XOR and AND gates.  Functions in
this module expose simple helpers that return energies in joules (``J``) or
energy-per-correction (``J/bit``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_CALIB_PATH = Path(__file__).with_name("tech_calib.json")


def _load_calibration() -> Dict[str, Dict[str, Dict[str, float]]]:
    with _CALIB_PATH.open() as fh:
        return json.load(fh)


_CALIB = _load_calibration()


def gate_energy(node_nm: int, vdd: float, gate: str) -> float:
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
    try:
        return _CALIB[str(node_nm)][f"{vdd:.1f}"][gate]
    except KeyError as exc:
        raise KeyError(
            f"Missing calibration for {node_nm}nm at {vdd:.1f}V"
        ) from exc


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

    e_xor = gate_energy(node_nm, vdd, "xor")
    e_and = gate_energy(node_nm, vdd, "and")
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
