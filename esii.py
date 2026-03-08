"""Environmental Sustainability Improvement Index (ESII).

The revised ESII is a bounded sustainability utility in ``[0, 1]``:

``ESII = U_rel * (w_E * U_energy + w_C * U_carbon) / (w_E + w_C)``

where ``U_rel`` captures reliability improvement in log-risk space and
``U_energy``/``U_carbon`` penalise operational and carbon burdens through
dimensionless saturating transforms.  The formulation avoids exploding ratios,
is monotonic in expected directions and remains finite across wide FIT ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Tuple

import numpy as np

KWH_PER_J = 3_600_000.0  # 1 kWh = 3.6e6 J
FIT_FLOOR = 1e-30
LOG_RELIABILITY_HALFSAT_DECADES = 2.0
ENERGY_HALFSAT_KWH = 1.0
CARBON_HALFSAT_KG = 1.0
EPS = 1e-12


def safe_div(num: float, den: float, eps: float = EPS) -> float:
    """Return ``num / den`` using ``eps`` to prevent divide-by-zero."""
    return num / max(abs(den), eps)


def safe_log10(x: float, floor: float = FIT_FLOOR) -> float:
    """Return ``log10(max(x, floor))`` for stable log-domain arithmetic."""
    return float(np.log10(max(x, floor)))


def clamp01(x: float) -> float:
    """Clamp ``x`` to the closed interval ``[0, 1]``."""
    return max(0.0, min(1.0, float(x)))


def bounded_cost_utility(cost: float, halfsat: float, eps: float = EPS) -> float:
    """Map a non-negative cost to a bounded utility in ``(0, 1]``."""
    c = max(float(cost), 0.0)
    h = max(float(halfsat), eps)
    return 1.0 / (1.0 + c / h)


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
    e_scrub: float = 0.0
    basis: Literal["per_gib", "system"] = "per_gib"


def _j_to_kwh(x: float) -> float:
    return x / KWH_PER_J


def compute_esii(inp: ESIIInputs) -> Dict[str, float]:
    """Return ESII and a compact breakdown.

    Reliability term
    ----------------
    ``U_rel`` uses log-risk reduction in FIT decades:

    ``d_rel = max(log10(fit_base + floor) - log10(fit_ecc + floor), 0)``
    ``U_rel = d_rel / (d_rel + LOG_RELIABILITY_HALFSAT_DECADES)``

    Burden terms
    ------------
    Operational energy and total carbon are converted to bounded utilities via
    reciprocal saturation.  The final ESII is bounded in ``[0, 1]``.
    """

    e_dyn_kwh = _j_to_kwh(inp.e_dyn)
    e_leak_kwh = _j_to_kwh(inp.e_leak)
    e_scrub_kwh = _j_to_kwh(inp.e_scrub)
    operational_kgco2e = inp.ci_kgco2e_per_kwh * (
        e_dyn_kwh + e_leak_kwh + e_scrub_kwh
    )
    total_kgco2e = operational_kgco2e + inp.embodied_kgco2e

    log_fit_base = safe_log10(max(inp.fit_base, 0.0) + FIT_FLOOR)
    log_fit_ecc = safe_log10(max(inp.fit_ecc, 0.0) + FIT_FLOOR)
    reliability_decades = max(log_fit_base - log_fit_ecc, 0.0)
    reliability_score = safe_div(
        reliability_decades,
        reliability_decades + LOG_RELIABILITY_HALFSAT_DECADES,
    )
    energy_score = bounded_cost_utility(e_dyn_kwh + e_leak_kwh + e_scrub_kwh, ENERGY_HALFSAT_KWH)
    carbon_score = bounded_cost_utility(total_kgco2e, CARBON_HALFSAT_KG)

    burden_blend = 0.5 * energy_score + 0.5 * carbon_score
    esii = clamp01(reliability_score * burden_blend)
    delta_fit = max(inp.fit_base - inp.fit_ecc, 0.0)

    return {
        "ESII": esii,
        "delta_FIT": delta_fit,
        "reliability_decades": reliability_decades,
        "reliability_score": reliability_score,
        "energy_score": energy_score,
        "carbon_score": carbon_score,
        "operational_kgCO2e": operational_kgco2e,
        "embodied_kgCO2e": inp.embodied_kgco2e,
        "total_kgCO2e": total_kgco2e,
        "E_dyn_kWh": e_dyn_kwh,
        "E_leak_kWh": e_leak_kwh,
        "E_scrub_kWh": e_scrub_kwh,
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


def normalise_esii(values: Iterable[float], eps: float = 1e-9) -> Tuple[List[float], float, float]:
    """Return normalised ESII scores and percentile bounds.

    The normalisation follows a winsorised min–max scheme using the 5th and
    95th percentiles as anchors.  Values outside this interval are clipped
    before mapping the range to ``[0, 100]``.  The function returns a tuple of
    ``(scores, p5, p95)`` where ``scores`` mirrors the input order.

    Parameters
    ----------
    values:
        Iterable of raw ESII values.
    eps:
        Small stabiliser to avoid division by zero when ``p5`` and ``p95``
        coincide.
    """

    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return [], float("nan"), float("nan")

    p5, p95 = np.percentile(arr, [5, 95])
    clipped = np.clip(arr, p5, p95)
    denom = p95 - p5 + eps
    norm = 100.0 * (clipped - p5) / denom
    return norm.tolist(), float(p5), float(p95)
