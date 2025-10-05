"""Simple ECC multiplexer parameter helpers."""

from __future__ import annotations

from typing import Dict, Tuple

# Latency in ns, energy in pJ, area in square microns for each ECC scheme.
_MUX_TABLE: Dict[str, Tuple[float, float, float, int]] = {
    # The fan-in values (final column) capture the effective mux size that the
    # datapath must steer parity bits through for each ECC topology.  They are
    # expressed as the number of inputs to a single output (e.g. 2 indicates a
    # 2:1 multiplexer).
    "Hamming_SEC": (0.05, 0.02, 1.0, 2),
    "SEC_DAEC": (0.065, 0.027, 1.25, 6),
    "TAEC": (0.07, 0.03, 1.4, 8),
    "BCH": (0.09, 0.04, 1.9, 16),
}


def compute_ecc_mux_params(scheme: str) -> Tuple[float, float, float, int]:
    """Return multiplexer latency, energy, area and fan-in for *scheme*.

    Parameters are derived from a simple look-up table and are intended for
    illustrative benchmarking rather than detailed circuit modelling.
    """

    try:
        return _MUX_TABLE[scheme]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown scheme: {scheme}") from exc


__all__ = ["compute_ecc_mux_params"]
