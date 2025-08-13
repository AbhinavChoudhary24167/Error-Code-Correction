"""4-state soft error model for SRAM bits.

Implements the Markov model from Equations (4.1) and (4.2) of the thesis
introduction. The supply voltage influences the state transition rates
\(\epsilon_1\) through \(\epsilon_4\). The raw soft error rate (SER) for a
single cell is computed as

    SER(VDD) = (epsilon1 * epsilon2 * epsilon3 * epsilon4) / VDD**k

as shown in Equation (4.1). For a memory word containing ``nodes`` bits the
resulting bit error rate (BER) follows Equation (4.2)

    BER = 1 - (1 - SER)**nodes.

``ber`` exposes this calculation. Parameters are bundled in
``DEFAULT_PARAMS`` so the model can be tuned without changing code.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import math
from pathlib import Path
import warnings
from typing import Dict, List, Tuple
import jsonschema

# Default Markov parameters derived from the thesis tables.
DEFAULT_PARAMS: Dict[str, float] = {
    "epsilon1": 0.01,
    "epsilon2": 0.02,
    "epsilon3": 0.03,
    "epsilon4": 0.036,
    "k": 3.0,
}
"""Baseline transition probabilities and voltage exponent."""

# Alternative Gilbert-Elliott style parameters for quick experiments.
GILBERT_PARAMS: Dict[str, float] = {
    "epsilon1": 0.005,
    "epsilon2": 0.01,
    "epsilon3": 0.015,
    "epsilon4": 0.02,
    "k": 2.5,
}
"""Simplified two-state parameters."""

LOW_VOLTAGE_LIMIT = 0.4
"""Voltages below this value are outside the model's validity."""


@dataclass
class HazuchaParams:
    """Parameters for the Hazucha–Svensson SER model.

    Attributes
    ----------
    Qs_fC:
        Fitted charge collection parameter in femtocoulombs.
    flux_rel:
        Neutron flux relative to sea level at 45° latitude.
    area_um2:
        Sensitive area of the storage node in square micrometres.
    C:
        Technology dependent constant. Defaults to ``2.2e-5``.
    """

    Qs_fC: float
    flux_rel: float
    area_um2: float
    C: float = 2.2e-5


def ser_hazucha(Qcrit_fC: float, hp: HazuchaParams) -> float:
    """Return the FIT per node using the Hazucha–Svensson model.

    The model relates the critical charge of a node to the resulting soft
    error rate via an exponential law.
    """

    return hp.C * hp.flux_rel * hp.area_um2 * math.exp(-Qcrit_fC / hp.Qs_fC)


def flux_from_location(
    alt_km: float, latitude_deg: float, flux_rel: float | None = None
) -> float:
    """Return relative neutron flux for a given location.

    Parameters are currently placeholders. When ``flux_rel`` is provided it is
    returned directly, otherwise ``1.0`` is used. A real implementation would
    derive the flux from ``alt_km`` and ``latitude_deg``.
    """

    if flux_rel is not None:
        return flux_rel
    return 1.0


# --- Qcrit lookup ---------------------------------------------------------

_QCRIT_CACHE: Dict[str, dict] = {}


def _load_qcrit_table(element: str) -> dict:
    """Load, validate and cache Qcrit tables for a given element."""

    if element in _QCRIT_CACHE:
        return _QCRIT_CACHE[element]

    data_dir = Path(__file__).with_name("data")
    data_path = data_dir / f"qcrit_{element}.json"
    schema_path = data_dir / f"qcrit_{element}.schema.json"

    with data_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    # Validate against the strict schema
    with schema_path.open("r", encoding="utf-8") as sfh:
        schema = json.load(sfh)
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(raw)

    # Enforce composite key uniqueness and reshape for lookup
    grid: Dict[int, Dict[float, Dict[float, Dict[float, dict]]]] = {}
    seen = set()
    for e in raw["entries"]:
        key = (e["node_nm"], e["vdd"], e["tempC"], e["pulse_rise_ps"])
        if key in seen:
            raise ValueError(f"Duplicate Qcrit entry for {key}")
        seen.add(key)

        node = grid.setdefault(e["node_nm"], {})
        v_map = node.setdefault(e["vdd"], {})
        t_map = v_map.setdefault(e["tempC"], {})
        t_map[e["pulse_rise_ps"]] = e["qcrit"]

    _QCRIT_CACHE[element] = {
        "interpolation": raw.get("interpolation", {}),
        "data": grid,
    }
    return _QCRIT_CACHE[element]


def _find_bounds(value: float, points: List[float], policy: str) -> Tuple[float, float]:
    """Return surrounding grid points respecting an extrapolation policy."""

    if value < points[0]:
        if policy == "error":
            raise ValueError("Value below table range")
        if policy == "warn-clamp":
            warnings.warn("Value below table range", RuntimeWarning)
        return points[0], points[0]

    if value > points[-1]:
        if policy == "error":
            raise ValueError("Value above table range")
        if policy == "warn-clamp":
            warnings.warn("Value above table range", RuntimeWarning)
        return points[-1], points[-1]

    lo = points[0]
    for hi in points[1:]:
        if hi >= value:
            return lo, hi
        lo = hi
    return points[-1], points[-1]


def _interp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """Linear interpolation helper."""

    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def qcrit_lookup(
    element: str, node_nm: int, vdd: float, tempC: float, pulse_ps: float
) -> float:
    """Return interpolated critical charge in femtocoulombs.

    Performs bilinear interpolation over VDD and temperature and warns when a
    requested point lies outside the available table range.
    """

    qcrit_table = _load_qcrit_table(element)
    table = qcrit_table["data"]
    policy = qcrit_table.get("interpolation", {}).get(
        "extrapolation_policy", "warn-clamp"
    )

    node = table[node_nm]
    pulse_key = pulse_ps

    v_vals = sorted(node.keys())
    v_lo, v_hi = _find_bounds(vdd, v_vals, policy)

    t_vals = sorted(node[v_lo].keys())
    t_lo, t_hi = _find_bounds(tempC, t_vals, policy)

    def value(v: float, t: float) -> float:
        return node[v][t][pulse_key]["mean_fC"]

    if v_lo == v_hi and t_lo == t_hi:
        return value(v_lo, t_lo)
    if v_lo == v_hi:
        return _interp(tempC, t_lo, t_hi, value(v_lo, t_lo), value(v_lo, t_hi))
    if t_lo == t_hi:
        return _interp(vdd, v_lo, v_hi, value(v_lo, t_lo), value(v_hi, t_lo))

    q_ll = value(v_lo, t_lo)
    q_hl = value(v_hi, t_lo)
    q_lh = value(v_lo, t_hi)
    q_hh = value(v_hi, t_hi)

    frac_v = (vdd - v_lo) / (v_hi - v_lo)
    frac_t = (tempC - t_lo) / (t_hi - t_lo)

    return (
        q_ll * (1 - frac_v) * (1 - frac_t)
        + q_hl * frac_v * (1 - frac_t)
        + q_lh * (1 - frac_v) * frac_t
        + q_hh * frac_v * frac_t
    )


def _ser(vdd: float, params: Dict[str, float]) -> float:
    """Return the raw soft error rate for a single bit.

    Parameters
    ----------
    vdd : float
        Supply voltage in volts.
    params : Dict[str, float]
        Model parameters read from ``DEFAULT_PARAMS`` or ``GILBERT_PARAMS``.
    """
    eps = (
        params["epsilon1"]
        * params["epsilon2"]
        * params["epsilon3"]
        * params["epsilon4"]
    )
    return eps / (vdd ** params["k"])


def ber(vdd: float, nodes: int = 22, params: Dict[str, float] | None = None) -> float:
    """Estimate the bit error rate at a given supply voltage.

    Parameters
    ----------
    vdd : float
        Supply voltage in volts. Must not be lower than ``LOW_VOLTAGE_LIMIT``.
    nodes : int
        Number of storage nodes (bits) in the word.
    params : optional
        Parameter dictionary, ``DEFAULT_PARAMS`` by default.

    Returns
    -------
    float
        Bit error rate according to Equation (4.2).
    """
    if vdd < LOW_VOLTAGE_LIMIT:
        raise ValueError("Voltage below model validity range")

    if params is None:
        params = DEFAULT_PARAMS

    ser = _ser(vdd, params)
    return 1.0 - (1.0 - ser) ** nodes


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate BER for a given VDD")
    parser.add_argument("vdd", type=float, help="Supply voltage in volts")
    parser.add_argument("--nodes", type=int, default=22, help="Number of bits")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gilbert", action="store_true", help="Use Gilbert parameters")
    group.add_argument("--4mc", action="store_true", help="Use 4-state Markov parameters (default)")
    args = parser.parse_args()

    params = DEFAULT_PARAMS
    if args.gilbert:
        params = GILBERT_PARAMS

    result = ber(args.vdd, nodes=args.nodes, params=params)
    print(f"BER: {result:.3e}")


if __name__ == "__main__":
    main()
