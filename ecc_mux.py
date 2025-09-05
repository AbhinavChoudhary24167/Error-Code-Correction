"""Simple ECC multiplexer parameter helpers."""

from __future__ import annotations

from typing import Dict, Tuple

# Latency in ns, energy in pJ, area in square microns for each ECC scheme.
_MUX_TABLE: Dict[str, Tuple[float, float, float]] = {
    "Hamming_SEC": (0.05, 0.02, 1.0),
    "SEC_DED": (0.06, 0.025, 1.2),
    "TAEC": (0.07, 0.03, 1.4),
    "DEC": (0.08, 0.035, 1.6),
}


def compute_ecc_mux_params(scheme: str) -> Tuple[float, float, float]:
    """Return multiplexer latency, energy and area for *scheme*.

    Parameters are derived from a simple look-up table and are intended for
    illustrative benchmarking rather than detailed circuit modelling.
    """

    try:
        return _MUX_TABLE[scheme]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown scheme: {scheme}") from exc


__all__ = ["compute_ecc_mux_params"]
