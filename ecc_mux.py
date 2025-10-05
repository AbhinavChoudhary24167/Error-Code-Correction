"""Simple ECC multiplexer parameter helpers."""

from __future__ import annotations

from typing import Dict, Mapping, Tuple

# Base calibration per ECC scheme captured at 28 nm.
_BASE_MUX_PARAMS: Dict[str, Tuple[float, float, float, int]] = {
    # The fan-in values (final column) capture the effective mux size that the
    # datapath must steer parity bits through for each ECC topology. They are
    # expressed as the number of inputs to a single output (e.g. 2 indicates a
    # 2:1 multiplexer).
    "Hamming_SEC": (0.05, 0.02, 1.0, 2),
    "SEC_DAEC": (0.065, 0.027, 1.25, 6),
    "TAEC": (0.07, 0.03, 1.4, 8),
    "BCH": (0.09, 0.04, 1.9, 16),
}


def _scale_mux_params(
    base: Tuple[float, float, float, int],
    scaling: Mapping[str, float],
) -> Tuple[float, float, float, int]:
    """Return *base* parameters scaled for a particular technology node."""

    latency, energy, area, fanin = base
    return (
        latency * scaling["latency"],
        energy * scaling["energy"],
        area * scaling["area"],
        fanin,
    )


_NODE_SCALING: Dict[str, Dict[str, float]] = {
    "28nm": {"latency": 1.0, "energy": 1.0, "area": 1.0},
    "16nm": {"latency": 0.85, "energy": 0.8, "area": 0.7},
    "7nm": {"latency": 0.65, "energy": 0.6, "area": 0.5},
}


# Latency in ns, energy in pJ, area in square microns for each ECC scheme and node.
_MUX_TABLE: Dict[str, Dict[str, Tuple[float, float, float, int]]] = {
    scheme: {
        node: _scale_mux_params(params, node_scaling)
        for node, node_scaling in _NODE_SCALING.items()
    }
    for scheme, params in _BASE_MUX_PARAMS.items()
}


def compute_ecc_mux_params(scheme: str, node: str) -> Tuple[float, float, float, int]:
    """Return multiplexer latency, energy, area and fan-in for *scheme* and *node*.

    Parameters are derived from a simple look-up table and are intended for
    illustrative benchmarking rather than detailed circuit modelling.
    """

    try:
        node_table = _MUX_TABLE[scheme]
    except KeyError as exc:  # pragma: no cover - defensive
        available = ", ".join(sorted(_MUX_TABLE))
        raise ValueError(
            f"Unknown scheme: {scheme!r}. Available schemes: {available}"
        ) from exc

    try:
        return node_table[node]
    except KeyError as exc:
        available_nodes = ", ".join(sorted(node_table))
        raise ValueError(
            f"No mux calibration for node {node!r} and scheme {scheme!r}. "
            f"Available nodes: {available_nodes}"
        ) from exc


__all__ = ["compute_ecc_mux_params"]
