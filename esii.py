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
        Dynamic energy attributable to ECC in Joules.
    e_leak : float
        Leakage energy attributable to ECC in Joules.
    ci_kgco2e_per_kwh : float
        Grid carbon intensity.
    embodied_kgco2e : float
        Embodied carbon from added logic and memory.
    basis : {"per_gib", "system"}
        Reliability basis.  Optional metadata for reports.
    """

    fit_base: float
    fit_ecc: float
    e_dyn: float
    e_leak: float
    ci_kgco2e_per_kwh: float
    embodied_kgco2e: float
    basis: Literal["per_gib", "system"] = "per_gib"


def _j_to_kwh(x: float) -> float:
    return x / KWH_PER_J


def compute_esii(inp: ESIIInputs) -> Dict[str, float]:
    """Return ESII and a compact breakdown.

    The dictionary contains the ESII value along with the individual components
    contributing to the carbon footprint.
    """

    e_dyn_kwh = _j_to_kwh(inp.e_dyn)
    e_leak_kwh = _j_to_kwh(inp.e_leak)
    operational_kgco2e = inp.ci_kgco2e_per_kwh * (e_dyn_kwh + e_leak_kwh)
    total_kgco2e = operational_kgco2e + inp.embodied_kgco2e

    delta_fit = max(inp.fit_base - inp.fit_ecc, 0.0)
    esii = 0.0 if total_kgco2e < 1e-12 else delta_fit / total_kgco2e

    return {
        "ESII": esii,
        "delta_FIT": delta_fit,
        "operational_kgCO2e": operational_kgco2e,
        "embodied_kgCO2e": inp.embodied_kgco2e,
        "total_kgCO2e": total_kgco2e,
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

