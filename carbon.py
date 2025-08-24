from __future__ import annotations

"""Carbon accounting helpers.

This module provides small utilities to estimate the embodied and
operational carbon associated with an ECC technique or hardware block.
"""

from pathlib import Path
import json
from typing import Tuple


def embodied_kgco2e(
    area_logic_mm2: float,
    area_macro_mm2: float,
    alpha_logic_kg_per_mm2: float,
    alpha_macro_kg_per_mm2: float,
) -> float:
    """Return embodied carbon for logic and macro areas.

    Parameters
    ----------
    area_logic_mm2 : float
        Added logic area in square millimetres.
    area_macro_mm2 : float
        Added memory macro area in square millimetres.
    alpha_logic_kg_per_mm2 : float
        Embodied carbon factor for logic in ``kgCO2e/mm²``.
    alpha_macro_kg_per_mm2 : float
        Embodied carbon factor for macros in ``kgCO2e/mm²``.

    Returns
    -------
    float
        Total embodied carbon in kilograms of CO2e.
    """

    if (
        area_logic_mm2 < 0
        or area_macro_mm2 < 0
        or alpha_logic_kg_per_mm2 < 0
        or alpha_macro_kg_per_mm2 < 0
    ):
        raise ValueError("areas and alpha factors must be non-negative")

    return area_logic_mm2 * alpha_logic_kg_per_mm2 + area_macro_mm2 * alpha_macro_kg_per_mm2


def operational_kgco2e(
    E_dyn_kWh: float,
    E_leak_kWh: float,
    CI_kgco2e_per_kWh: float,
    E_scrub_kWh: float = 0.0,
) -> float:
    """Return operational carbon given energy terms and carbon intensity."""
    if (
        E_dyn_kWh < 0
        or E_leak_kWh < 0
        or E_scrub_kWh < 0
        or CI_kgco2e_per_kWh < 0
    ):
        raise ValueError("energy and carbon intensity must be non-negative")
    return CI_kgco2e_per_kWh * (E_dyn_kWh + E_leak_kWh + E_scrub_kWh)


def _load_defaults(path: Path) -> dict:
    """Load alpha defaults from ``carbon_defaults.json``."""
    data = json.load(open(path))
    for node_str, entry in data.items():
        if {"source", "date", "alpha_logic", "alpha_macro"} - entry.keys():
            raise ValueError(f"Missing fields for node {node_str}")
    return data


_DEFAULTS = _load_defaults(Path(__file__).with_name("carbon_defaults.json"))


def default_alpha(node_nm: int) -> Tuple[float, float]:
    """Return ``(alpha_logic, alpha_macro)`` for the given technology node."""
    entry = _DEFAULTS[str(int(node_nm))]
    return entry["alpha_logic"], entry["alpha_macro"]
