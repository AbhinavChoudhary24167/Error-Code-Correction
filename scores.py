"""Unified sustainability metrics interface.

This module provides a convenience wrapper to compute ESII, NESII and the
Green Score (GS) in a single call.  The helper accepts the standard
:class:`esii.ESIIInputs` structure along with a latency value used by the
GS calculation.  Optionally a reference distribution of ESII values can be
supplied to obtain a normalised ESII (NESII); if omitted the NESII for the
provided scenario defaults to 0.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from esii import ESIIInputs, compute_esii, normalise_esii
from gs import GSInputs, compute_gs


def compute_scores(
    esii_inputs: ESIIInputs,
    *,
    latency_ns: float = 0.0,
    esii_reference: Iterable[float] | None = None,
) -> Dict[str, float]:
    """Return ESII, NESII and GS for the provided inputs.

    Parameters
    ----------
    esii_inputs:
        Parameters describing reliability and carbon components.  Passed
        directly to :func:`esii.compute_esii`.
    latency_ns:
        Additional decode latency to include in the GS calculation.  Defaults
        to ``0.0`` which treats the candidate as latency‑neutral.
    esii_reference:
        Optional iterable of ESII values used to derive percentile anchors for
        NESII normalisation.  The provided ESII result is appended to this
        sequence before calling :func:`esii.normalise_esii`.  When omitted the
        NESII score is zero with percentile bounds equal to the raw ESII.
    """

    esii_res = compute_esii(esii_inputs)
    esii_val = esii_res["ESII"]

    ref: List[float]
    if esii_reference is None:
        ref = [esii_val]
    else:
        ref = list(esii_reference) + [esii_val]

    nesii_scores, p5, p95 = normalise_esii(ref)
    nesii_val = nesii_scores[-1] if nesii_scores else float("nan")

    gs_inp = GSInputs(
        fit_base=esii_inputs.fit_base,
        fit_ecc=esii_inputs.fit_ecc,
        carbon_kg=esii_res["total_kgCO2e"],
        latency_ns=latency_ns,
    )
    gs_res = compute_gs(gs_inp)

    out = dict(esii_res)
    out.update({"NESII": nesii_val, "p5": p5, "p95": p95})
    out.update({"GS": gs_res["GS"]})
    return out


__all__ = ["compute_scores"]
