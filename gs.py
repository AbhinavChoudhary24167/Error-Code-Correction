"""GREEN Score (GS) metric.

GS is a bounded composite merit score in ``[0, 100]`` built from normalised
sub-utilities:

* ``Sr`` (reliability utility): log-risk reduction utility in FIT decades.
* ``Sc`` (carbon utility): saturating inverse burden utility.
* ``Sl`` (latency utility): saturating inverse burden utility.
* ``So`` (overhead utility): optional saturating inverse burden utility.

The final score uses a weighted geometric mean of strictly positive bounded
utilities, preserving monotonicity while strongly penalising weak dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass

import logging
import math

from typing import Dict, Tuple


FIT_FLOOR = 1e-30
LOG_RELIABILITY_HALFSAT_DECADES = 2.0
CARBON_HALFSAT_KG = 1.0
LATENCY_HALFSAT_NS = 10.0
OVERHEAD_HALFSAT = 0.25
EPS = 1e-12


@dataclass(frozen=True)
class GSInputs:
    """Inputs required to compute the GS metric.

    ``carbon_kg`` may be ``None`` when carbon is unavailable; in that case GS
    treats carbon as neutral (utility 1.0) and re-normalises active weights.
    ``overhead_norm`` is an optional dimensionless implementation burden in
    ``[0, +inf)`` (e.g., area/parity overhead ratio).
    """

    fit_base: float
    fit_ecc: float
    carbon_kg: float | None
    latency_ns: float

    carbon_scope: str = "total"
    latency_base_ns: float = 0.0
    overhead_norm: float = 0.0


_log = logging.getLogger(__name__)


def safe_div(num: float, den: float, eps: float = EPS) -> float:
    return num / max(abs(den), eps)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _safe_log10(x: float) -> float:
    return math.log10(max(x, FIT_FLOOR))


def _benefit_utility_log_decades(base: float, improved: float) -> float:
    decades = max(_safe_log10(max(base, 0.0) + FIT_FLOOR) - _safe_log10(max(improved, 0.0) + FIT_FLOOR), 0.0)
    return clamp01(safe_div(decades, decades + LOG_RELIABILITY_HALFSAT_DECADES))


def _cost_utility(cost: float, halfsat: float) -> float:
    c = max(float(cost), 0.0)
    h = max(float(halfsat), EPS)
    return 1.0 / (1.0 + c / h)


def compute_gs(
    inp: GSInputs,
    *,
    weights: Tuple[float, float, float, float] = (0.6, 0.25, 0.1, 0.05),
    carbon_halfsat_kg: float = CARBON_HALFSAT_KG,
    latency_halfsat_ns: float = LATENCY_HALFSAT_NS,
    overhead_halfsat: float = OVERHEAD_HALFSAT,
) -> Dict[str, float]:
    """Return GS and individual sub-scores.

    The result is mathematically bounded to ``[0, 100]`` and finite for all
    non-negative inputs.
    """

    fit_base = max(inp.fit_base, 0.0)
    fit_ecc = max(inp.fit_ecc, 0.0)
    latency = max(inp.latency_ns - inp.latency_base_ns, 0.0)

    sr = _benefit_utility_log_decades(fit_base, fit_ecc)
    sl = _cost_utility(latency, latency_halfsat_ns)
    so = _cost_utility(inp.overhead_norm, overhead_halfsat)

    carbon_available = inp.carbon_kg is not None
    sc = _cost_utility(inp.carbon_kg or 0.0, carbon_halfsat_kg) if carbon_available else 1.0

    if len(weights) == 3:
        wR, wC, wL = weights
        wO = 0.0
    elif len(weights) == 4:
        wR, wC, wL, wO = weights
    else:
        raise ValueError("weights must have length 3 or 4")

    active = [
        ("Sr", sr, max(wR, 0.0), True),
        ("Sc", sc, max(wC, 0.0), carbon_available),
        ("Sl", sl, max(wL, 0.0), True),
        ("So", so, max(wO, 0.0), True),
    ]
    active = [item for item in active if item[3] and item[2] > 0.0]
    if not active:
        raise ValueError("at least one positive active weight is required")

    total_w = sum(item[2] for item in active)
    if not math.isclose(total_w, 1.0):
        _log.warning("renormalizing GS weights to sum to 1 across active dimensions")

    log_sum = 0.0
    for _, score, w, _ in active:
        wn = w / total_w
        log_sum += wn * math.log(max(score, EPS))

    gs = clamp01(math.exp(log_sum)) * 100.0
    delta_fit = max(fit_base - fit_ecc, 0.0)

    return {
        "GS": gs,
        "Sr": sr,
        "Sc": sc,
        "Sl": sl,
        "So": so,
        "delta_FIT": delta_fit,
        "total_kgCO2e": float(inp.carbon_kg or 0.0),
        "latency_ns": latency,
        "carbon_scope": inp.carbon_scope,
    }


__all__ = ["GSInputs", "compute_gs"]
