"""Goodness Score (GS) metric.

The GS aggregates reliability, carbon efficiency and latency
friendliness into a single bounded index on [0, 100].  The
three sub-scores are mapped to [0, 1] via simple saturation
transforms before combining them using a weighted harmonic mean.

The default weights ``(wR, wC, wL) = (0.6, 0.3, 0.1)`` reflect the
primacy of reliability in SRAM contexts.  Each sub-score is
returned alongside the raw metrics for transparency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class GSInputs:
    """Inputs required to compute the GS metric.

    Parameters
    ----------
    fit_base : float
        Baseline system FIT.
    fit_ecc : float
        System FIT with ECC applied.
    carbon_kg : float
        Total carbon footprint in kilograms of CO2e.
    latency_ns : float
        Decode latency in nanoseconds.
    """

    fit_base: float
    fit_ecc: float
    carbon_kg: float
    latency_ns: float


# Placeholder scale parameters for the saturation functions
_SR_SCALE = 0.05
_SC_SCALE = 1.0
_SL_SCALE = 10.0


def _sat_improvement(x: float, k: float) -> float:
    """Saturating transform for beneficial quantities."""
    return x / (x + k)


def _sat_cost(x: float, k: float) -> float:
    """Saturating transform for cost-like quantities (lower is better)."""
    return 1.0 / (1.0 + x / k)


def compute_gs(
    inp: GSInputs,
    *,
    weights: Tuple[float, float, float] = (0.6, 0.3, 0.1),
    sr_scale: float = _SR_SCALE,
    sc_scale: float = _SC_SCALE,
    sl_scale: float = _SL_SCALE,
) -> Dict[str, float]:
    """Return GS and individual sub-scores.

    The function applies saturating transforms to each raw metric and then
    aggregates the resulting sub-scores via a weighted harmonic mean.  The
    final GS is scaled to lie within ``[0, 100]``.
    """

    fit_base = max(inp.fit_base, 0.0)
    fit_ecc = max(inp.fit_ecc, 0.0)
    carbon = max(inp.carbon_kg, 0.0)
    latency = max(inp.latency_ns, 0.0)

    delta_fit = max(fit_base - fit_ecc, 0.0)
    rel_gain = 0.0 if fit_base <= 0 else delta_fit / fit_base

    sr = _sat_improvement(rel_gain, sr_scale)
    sc = _sat_cost(carbon, sc_scale)
    sl = _sat_cost(latency, sl_scale)

    # Weighted harmonic mean; clamp sub-scores to avoid division by zero
    wR, wC, wL = weights
    eps = 1e-9
    denom = wR / max(sr, eps) + wC / max(sc, eps) + wL / max(sl, eps)
    gs = (wR + wC + wL) / denom * 100.0

    return {
        "GS": gs,
        "Sr": sr,
        "Sc": sc,
        "Sl": sl,
        "delta_FIT": delta_fit,
        "total_kgCO2e": carbon,
        "latency_ns": latency,
    }


__all__ = ["GSInputs", "compute_gs"]
