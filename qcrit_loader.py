"""Utilities for loading and interpolating Qcrit lookup tables."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import json
import warnings

import jsonschema

_QCRIT_CACHE: Dict[str, dict] = {}


def _load_qcrit_table(element: str) -> dict:
    """Load, validate and cache Qcrit tables for a given element.

    Parameters
    ----------
    element:
        Device element name such as ``"sram6t"``.
    """

    if element in _QCRIT_CACHE:
        return _QCRIT_CACHE[element]

    data_dir = Path(__file__).with_name("data")
    schema_dir = Path(__file__).with_name("schemas")
    data_path = data_dir / f"qcrit_{element}.json"
    schema_path = schema_dir / f"qcrit_{element}.schema.json"

    with data_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    with schema_path.open("r", encoding="utf-8") as sfh:
        schema = json.load(sfh)
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(raw)

    if "units" not in raw:
        raise ValueError("Qcrit table missing units section")

    grid: Dict[int, Dict[float, Dict[float, Dict[float, dict]]]] = {}
    seen = set()
    for e in raw["entries"]:
        for field in ("method", "source", "date"):
            if field not in e:
                raise ValueError(f"Unprovenanced Qcrit entry missing {field}")
        key = (e["node_nm"], e["vdd"], e["tempC"], e["pulse_rise_ps"])
        if key in seen:
            raise ValueError(f"Duplicate Qcrit entry for {key}")
        seen.add(key)

        node = grid.setdefault(e["node_nm"], {})
        v_map = node.setdefault(e["vdd"], {})
        t_map = v_map.setdefault(e["tempC"], {})
        t_map[e["pulse_rise_ps"]] = e

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


def qcrit_lookup(element: str, node_nm: int, vdd: float, tempC: float, pulse_ps: float) -> float:
    """Return interpolated critical charge in femtocoulombs.

    Performs bilinear interpolation over VDD and temperature and warns when a
    requested point lies outside the available table range. Pulse widths must
    be explicitly present in the table; no defaults are assumed.
    """

    qcrit_table = _load_qcrit_table(element)
    table = qcrit_table["data"]
    policy = qcrit_table.get("interpolation", {}).get("extrapolation_policy", "error")

    node = table[node_nm]
    v_vals = sorted(node.keys())
    v_lo, v_hi = _find_bounds(vdd, v_vals, policy)

    t_vals = sorted(set(node[v_lo].keys()) | set(node[v_hi].keys()))
    t_lo, t_hi = _find_bounds(tempC, t_vals, policy)

    def value(v: float, t: float) -> float:
        pulses = table[node_nm][v][t]
        if pulse_ps not in pulses:
            raise KeyError(f"Pulse {pulse_ps} ps not found for ({node_nm}, {v}, {t})")
        return pulses[pulse_ps]["qcrit"]["mean_fC"]

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


__all__ = ["qcrit_lookup"]
