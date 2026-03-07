"""Centralized output sanity checks for energy and prediction flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class SanityIssue:
    """Human-readable sanity issue."""

    message: str


class OutputSanityError(ValueError):
    """Raised when strict sanity mode is enabled and issues are detected."""


def _interp_gate(calib: Mapping[int, Mapping[float, Mapping[str, Mapping[str, float]]]], node_nm: float, vdd: float, gate: str) -> float:
    nodes = np.array(sorted(int(k) for k in calib.keys()), dtype=float)
    per_node = []
    for node in nodes:
        table = calib[int(node)]
        vols = np.array(sorted(float(k) for k in table.keys()), dtype=float)
        vals = np.array([float(table[float(vol)]["gates"][gate]) for vol in vols], dtype=float)
        per_node.append(float(np.interp(vdd, vols, vals)))
    return float(np.interp(node_nm, nodes, np.array(per_node, dtype=float)))


def _nearest_nodes(calib: Mapping[int, Mapping[float, Mapping[str, Mapping[str, float]]]], node_nm: float) -> list[int]:
    nodes = sorted(int(k) for k in calib.keys())
    if not nodes:
        return []
    if node_nm <= nodes[0]:
        return [nodes[0]]
    if node_nm >= nodes[-1]:
        return [nodes[-1]]
    below = max(n for n in nodes if n <= node_nm)
    above = min(n for n in nodes if n >= node_nm)
    return sorted({below, above})


def validate_operating_point(
    calib: Mapping[int, Mapping[float, Mapping[str, Mapping[str, float]]]],
    *,
    node_nm: float,
    vdd: float,
    max_delta_ratio: float = 1.0,
) -> list[str]:
    """Validate interpolated gate energies around an operating point."""

    issues: list[str] = []
    gates = ("xor", "and", "adder_stage")
    energies = {gate: _interp_gate(calib, node_nm, vdd, gate) for gate in gates}

    for gate, energy in energies.items():
        if energy < 0.0:
            issues.append(f"energy < 0 for node={node_nm:g}, vdd={vdd:g}, gate={gate}")

    xor_energy = energies["xor"]
    if xor_energy > 0.0:
        and_ratio = energies["and"] / xor_energy
        if not (0.2 <= and_ratio <= 1.2):
            issues.append(
                f"ratio out of bounds for node={node_nm:g}, vdd={vdd:g}, ratio=and/xor, value={and_ratio:.6g}, expected=[0.2,1.2]"
            )
        adder_ratio = energies["adder_stage"] / xor_energy
        if not (1.0 <= adder_ratio <= 3.0):
            issues.append(
                f"ratio out of bounds for node={node_nm:g}, vdd={vdd:g}, ratio=adder_stage/xor, value={adder_ratio:.6g}, expected=[1.0,3.0]"
            )

    # Monotonic trend check along VDD for the nearest characterization node(s).
    for node in _nearest_nodes(calib, node_nm):
        table = calib[int(node)]
        vols = sorted(float(k) for k in table.keys())
        for gate in gates:
            for lo, hi in zip(vols, vols[1:]):
                e_lo = float(table[lo]["gates"][gate])
                e_hi = float(table[hi]["gates"][gate])
                if e_hi + 1e-18 < e_lo:
                    issues.append(
                        f"non-monotonic trend for node={node:g}, gate={gate}: energy decreases from vdd={lo:g} ({e_lo:.6g}) to vdd={hi:g} ({e_hi:.6g})"
                    )

    # Plausible local delta check around nearby operating points.
    for gate, energy in energies.items():
        refs: list[tuple[float, float, str]] = []
        for node in _nearest_nodes(calib, node_nm):
            table = calib[int(node)]
            vols = sorted(float(k) for k in table.keys())
            near_v = min(vols, key=lambda x: abs(x - vdd))
            refs.append((float(table[near_v]["gates"][gate]), node, near_v))
        for ref, ref_node, ref_vdd in refs:
            denom = max(abs(ref), 1e-18)
            delta = abs(energy - ref) / denom
            if delta > max_delta_ratio:
                issues.append(
                    f"delta too large for node={node_nm:g}, vdd={vdd:g}, gate={gate}: relative_delta={delta:.6g} vs nearby node={ref_node:g}, vdd={ref_vdd:g}"
                )

    return issues


def validate_metric_non_negative(metrics: Mapping[str, float], *, context: Mapping[str, object]) -> list[str]:
    """Validate non-negative numeric output metrics."""

    issues: list[str] = []
    context_bits = [f"{k}={context[k]}" for k in sorted(context)]
    context_text = ", ".join(context_bits)
    for key, value in metrics.items():
        try:
            as_float = float(value)
        except (TypeError, ValueError):
            continue
        if as_float < 0.0:
            issues.append(f"energy < 0 for metric={key}, value={as_float:.6g}, {context_text}")
    return issues


def enforce_sanity(issues: list[str], *, strict: bool) -> None:
    if issues and strict:
        raise OutputSanityError("; ".join(issues))


__all__ = [
    "OutputSanityError",
    "SanityIssue",
    "enforce_sanity",
    "validate_metric_non_negative",
    "validate_operating_point",
]
