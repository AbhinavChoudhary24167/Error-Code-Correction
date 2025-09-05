from __future__ import annotations

"""SRAM column multiplexer trade-off modelling.

This module evaluates three multiplexer sharing ratios (4, 8 and 16) for a
256-column SRAM array.  It produces metrics such as total area, latency and an
energy--delay style figure of merit alongside coarse carbon-footprint
estimates.  The calculations mirror the analytical table discussed in the
project documentation and are intended for quick experimentation rather than
layout-accurate prediction.
"""

from dataclasses import dataclass
from typing import Dict

CARBON_INTENSITY = 0.000111  # g CO₂ per joule
EMBODIED_PER_UM2 = 5e-6      # g CO₂ per square micron
COLUMNS = 256
SA_AREA_UM2 = 20.0           # area of a sense amplifier

# Modelling parameters for each MUX configuration.
#   mux_area_input : area in µm² for each input leg of the mux
#   energy_pj      : dynamic energy per read in pJ
#   latency_ns     : added read latency in ns
_MUX_PARAMS = {
    4: {"mux_area_input": 2.0, "energy_pj": 1.2, "latency_ns": 0.8},
    8: {"mux_area_input": 2.4, "energy_pj": 1.0, "latency_ns": 1.0},
    16: {"mux_area_input": 3.0, "energy_pj": 1.1, "latency_ns": 1.3},
}


@dataclass(frozen=True)
class MuxMetrics:
    sense_amps: int
    total_area_um2: float
    latency_ns: float
    dyn_energy_pj: float
    esii: float  # energy × delay product in pJ·ns
    nesii: float
    green_score: float
    operational_energy_kj: float
    operational_footprint_g: float
    embodied_footprint_g: float


def _raw_metrics(ratio: int) -> Dict[str, float]:
    params = _MUX_PARAMS[ratio]
    sa_count = COLUMNS // ratio
    mux_area = ratio * params["mux_area_input"]
    total_area = sa_count * (SA_AREA_UM2 + mux_area)

    latency = params["latency_ns"]
    energy_pj = params["energy_pj"]
    esii = latency * energy_pj

    energy_j = energy_pj * 1e-12
    op_energy_j = energy_j * 1e15  # for 10^15 reads
    op_energy_kj = op_energy_j / 1000.0
    op_footprint = op_energy_j * CARBON_INTENSITY
    embodied = total_area * EMBODIED_PER_UM2

    return {
        "sense_amps": sa_count,
        "total_area_um2": total_area,
        "latency_ns": latency,
        "dyn_energy_pj": energy_pj,
        "esii": esii,
        "operational_energy_kj": op_energy_kj,
        "operational_footprint_g": op_footprint,
        "embodied_footprint_g": embodied,
    }


def evaluate_mux_configs() -> Dict[int, MuxMetrics]:
    """Return metrics for all supported MUX sharing ratios."""

    raw: Dict[int, Dict[str, float]] = {
        ratio: _raw_metrics(ratio) for ratio in _MUX_PARAMS
    }
    best_esii = min(v["esii"] for v in raw.values())
    for v in raw.values():
        v["nesii"] = v["esii"] / best_esii
        v["green_score"] = 100.0 / v["nesii"]
    return {r: MuxMetrics(**vals) for r, vals in raw.items()}


__all__ = ["MuxMetrics", "evaluate_mux_configs"]
