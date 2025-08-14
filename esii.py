"""Environmental Sustainability Improvement Index (ESII).

This module provides helpers to compute the ESII given reliability
improvements and carbon cost components.  The ESII is defined as the ratio of
failure rate improvement to the total carbon footprint associated with the
technique.  In addition to the main :func:`compute_esii` routine the module
offers utilities for deriving embodied-carbon terms from hardware properties.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

KWH_PER_J = 3_600_000.0  # 1 kWh = 3.6e6 J


@dataclass(frozen=True)
class ESIIInputs:
    """Inputs required to compute the ESII metric.

    Parameters
    ----------
    fit_base : float
        Baseline failure rate in FIT (failures / 1e9 hours).
    fit_ecc : float
        Failure rate with ECC applied.
    e_dyn : float
        Dynamic energy attributable to ECC.
    e_leak : float
        Leakage energy attributable to ECC.
    ci_kg_per_kwh : float
        Grid carbon intensity.
    embodied_kg : float
        Embodied carbon from added logic and memory.
    basis : {"per_gib", "system"}
        Reliability basis.  Optional metadata for reports.
    energy_units : {"J", "kWh"}
        Units for ``e_dyn`` and ``e_leak``.
    """

    fit_base: float
    fit_ecc: float
    e_dyn: float
    e_leak: float
    ci_kg_per_kwh: float
    embodied_kg: float
    basis: Literal["per_gib", "system"] = "per_gib"
    energy_units: Literal["J", "kWh"] = "J"


def _to_kwh(x: float, units: str) -> float:
    if units == "kWh":
        return x
    if units == "J":
        return x / KWH_PER_J
    raise ValueError(f"Unsupported energy units: {units}")


def compute_esii(inp: ESIIInputs) -> Dict[str, float]:
    """Return ESII and a compact breakdown.

    The dictionary contains the ESII value along with the individual components
    contributing to the carbon footprint.
    """

    e_dyn_kwh = _to_kwh(inp.e_dyn, inp.energy_units)
    e_leak_kwh = _to_kwh(inp.e_leak, inp.energy_units)
    operational_kg = inp.ci_kg_per_kwh * (e_dyn_kwh + e_leak_kwh)
    total_carbon_kg = operational_kg + inp.embodied_kg

    delta_fit = max(inp.fit_base - inp.fit_ecc, 0.0)
    esii = delta_fit / max(total_carbon_kg, 1e-12)

    return {
        "ESII": esii,
        "delta_FIT": delta_fit,
        "operational_kg": operational_kg,
        "embodied_kg": inp.embodied_kg,
        "total_carbon_kg": total_carbon_kg,
        "E_dyn_kWh": e_dyn_kwh,
        "E_leak_kWh": e_leak_kwh,
    }


def embodied_from_wire_area(area_mm2: float, factor_kg_per_mm2: float) -> float:
    """Return embodied carbon for additional wiring.

    Parameters
    ----------
    area_mm2 : float
        Added wire area in square millimetres.
    factor_kg_per_mm2 : float
        Embodied carbon conversion factor in ``kgCO2e/mm²``.

    Returns
    -------
    float
        Equivalent embodied carbon in kilograms of CO2e.
    """

    if area_mm2 < 0 or factor_kg_per_mm2 < 0:
        raise ValueError("area and factor must be non-negative")
    return area_mm2 * factor_kg_per_mm2

