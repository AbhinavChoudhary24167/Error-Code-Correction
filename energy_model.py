"""Voltage and technology aware energy model.

At import-time the module loads ``tech_calib.json`` which maps a CMOS process
node and supply voltage to the energy cost of XOR, AND and adder-stage
primitives.  Functions in this module expose helpers that perform piecewise
linear interpolation over voltage and node and return energies in joules
(``J``) or energy-per-correction (``J/bit``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Sequence

import numpy as np
import math



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


_CALIB = _load_calib(Path(__file__).with_name("tech_calib.json"))

_LOGGER = logging.getLogger(__name__)


def _nearest(v: float, choices) -> float:
    """Return the closest value in ``choices`` to ``v``."""
    return min(choices, key=lambda c: abs(c - v))


def gate_energy(
    node_nm: float, vdd: float, gate: str, *, mode: str = "pwl"
) -> float:
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
    if gate not in {"xor", "and", "adder_stage"}:
        raise KeyError(gate)

    return gate_energy_vec(node_nm, np.array([vdd]), gate, mode=mode).item()


def gate_energy_vec(
    node_nm: float,
    vdd_array: Sequence[float],
    gate: str,
    *,
    mode: str = "pwl",
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
    if mode == "nearest":
        table = _CALIB[int(_nearest(node_nm, _CALIB.keys()))]
        vols = np.array(sorted(table))
        idx = np.abs(vols[:, None] - v).argmin(0)
        nearest = vols[idx]
        unique_rounds = np.unique(nearest[v != nearest])
        if unique_rounds.size:
            logging.warning("VDD rounded to nearest entry: %s", unique_rounds)
        return np.vectorize(lambda x: table[x]["gates"][gate])(nearest)

    if mode == "pwl":
        nodes = np.array(sorted(_CALIB))

        all_vols = [sorted(table) for table in _CALIB.values()]
        v_min = min(vs[0] for vs in all_vols)
        v_max = max(vs[-1] for vs in all_vols)
        if np.any((v < v_min) | (v > v_max)):
            _LOGGER.warning(
                "VDD outside calibration range; clamped to [%s, %s]", v_min, v_max
            )
            v = np.clip(v, v_min, v_max)

        def energy_at_node(n: int) -> np.ndarray:
            table = _CALIB[n]
            vols = np.array(sorted(table))
            vals = [table[vol]["gates"][gate] for vol in vols]
            return np.interp(v, vols, vals)

        energies = np.stack([energy_at_node(n) for n in nodes], axis=0)
        return np.array([np.interp(node_nm, nodes, energies[:, i]) for i in range(v.size)])

    raise ValueError("mode must be 'nearest' or 'pwl'")


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

    e_xor = gate_energy_vec(node_nm, np.array([vdd]), "xor", mode="pwl").item()
    e_and = gate_energy_vec(node_nm, np.array([vdd]), "and", mode="pwl").item()
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


# ---------------------------------------------------------------------------
# Depth models


def depth_parity(bits: int) -> int:
    """Depth of a balanced XOR tree computing parity of ``bits`` inputs."""
    if bits <= 1:
        return 0
    return int(math.ceil(math.log2(bits)))


def depth_syndrome(bits: int) -> int:
    """Depth of XOR tree for syndrome calculation."""
    return depth_parity(bits)


def depth_locator(code: str) -> int:
    """Return adder depth for the locator stage of ``code``."""
    mapping = {"sec-ded": 1, "sec-daec": 2, "taec": 3}
    try:
        return mapping[code.lower()]
    except KeyError:
        raise KeyError(code)


# ---------------------------------------------------------------------------
# Leakage model


_LEAK_BASE = {28: 0.5, 16: 0.7, 7: 1.0}  # A/mm^2 at 25C


def i_leak_density_A_per_mm2(node_nm: float, temp_c: float) -> float:
    nodes = np.array(sorted(_LEAK_BASE))
    base = np.array([_LEAK_BASE[n] for n in nodes])
    density_25 = np.interp(node_nm, nodes, base)
    return density_25 * 2 ** ((temp_c - 25.0) / 10.0)


_AREA_OVERHEAD = {"sec-ded": 0.1, "sec-daec": 0.12, "taec": 0.15}


def area_overhead_mm2(code: str) -> float:
    try:
        return _AREA_OVERHEAD[code.lower()]
    except KeyError:
        raise KeyError(code)


def leakage_energy_j(
    vdd: float, node_nm: float, temp_c: float, code: str, lifetime_h: float
) -> float:
    i = i_leak_density_A_per_mm2(node_nm, temp_c)
    area = area_overhead_mm2(code)
    return vdd * i * area * (lifetime_h * 3600.0)


# ---------------------------------------------------------------------------
# Dynamic energy model per ECC


_PRIMITIVE_COUNTS: Dict[str, Dict[str, int]] = {
    "sec-ded": {"xor": 100, "and": 50, "adder_stage": 0},
    "sec-daec": {"xor": 120, "and": 60, "adder_stage": 10},
    "taec": {"xor": 150, "and": 70, "adder_stage": 20},
}


def dynamic_energy_per_op(
    code: str, node_nm: float, vdd: float, *, mode: str = "pwl"
) -> float:
    primitives = _PRIMITIVE_COUNTS[code.lower()]
    e_xor = gate_energy(node_nm, vdd, "xor", mode=mode)
    e_and = gate_energy(node_nm, vdd, "and", mode=mode)
    e_add = gate_energy(node_nm, vdd, "adder_stage", mode=mode)
    return (
        primitives["xor"] * e_xor
        + primitives["and"] * e_and
        + primitives["adder_stage"] * e_add
    )


def dynamic_energy_j(
    ops: float, code: str, node_nm: float, vdd: float, *, mode: str = "pwl"
) -> float:
    return ops * dynamic_energy_per_op(code, node_nm, vdd, mode=mode)


def energy_report(
    code: str,
    node_nm: float,
    vdd: float,
    temp_c: float,
    ops: float,
    lifetime_h: float,
    *,
    mode: str = "pwl",
) -> Dict[str, float]:
    dyn = dynamic_energy_j(ops, code, node_nm, vdd, mode=mode)
    leak = leakage_energy_j(vdd, node_nm, temp_c, code, lifetime_h)
    return {"dynamic_J": dyn, "leakage_J": leak, "total_J": dyn + leak}


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
