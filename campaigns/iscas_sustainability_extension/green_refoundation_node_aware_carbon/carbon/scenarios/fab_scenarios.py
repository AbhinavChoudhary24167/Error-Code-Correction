"""Explicit parametric fab-decarbonization scenario accounting."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FactorInterval:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = float(self.lower)
        upper = float(self.upper)
        if not math.isfinite(lower) or not math.isfinite(upper):
            raise ValueError("factor endpoints must be finite")
        if lower < 0.0 or upper < lower:
            raise ValueError("factor interval must satisfy 0 <= lower <= upper")


@dataclass(frozen=True)
class FabScenario:
    scenario_id: str
    scope1_residual_factor: FactorInterval
    scope2_grid_ci_factor: FactorInterval
    upstream_factor: FactorInterval
    evidence_class: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.evidence_class or not self.source_ids:
            raise ValueError("scenario ID, evidence class, and source IDs are required")


@dataclass(frozen=True)
class ScenarioCarbonInterval:
    scope1_lower: float
    scope1_upper: float
    scope2_lower: float
    scope2_upper: float
    upstream_lower: float
    upstream_upper: float
    total_lower: float
    total_upper: float
    evidence_class: str


def _nonnegative(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def apply_fab_scenario(
    *,
    current_scope1_kgco2e: float,
    current_scope2_kgco2e: float,
    current_upstream_kgco2e: float,
    scenario: FabScenario,
) -> ScenarioCarbonInterval:
    """Scale a matched baseline breakdown; terms remain mutually exclusive.

    The Scope-1 factor is the combined residual-emission factor after gas use,
    utilization/release, and abatement. It is not relabeled as an independently
    measured abatement efficiency.
    """
    scope1 = _nonnegative("current_scope1_kgco2e", current_scope1_kgco2e)
    scope2 = _nonnegative("current_scope2_kgco2e", current_scope2_kgco2e)
    upstream = _nonnegative("current_upstream_kgco2e", current_upstream_kgco2e)
    s1_low = scope1 * scenario.scope1_residual_factor.lower
    s1_high = scope1 * scenario.scope1_residual_factor.upper
    s2_low = scope2 * scenario.scope2_grid_ci_factor.lower
    s2_high = scope2 * scenario.scope2_grid_ci_factor.upper
    up_low = upstream * scenario.upstream_factor.lower
    up_high = upstream * scenario.upstream_factor.upper
    return ScenarioCarbonInterval(
        scope1_lower=s1_low,
        scope1_upper=s1_high,
        scope2_lower=s2_low,
        scope2_upper=s2_high,
        upstream_lower=up_low,
        upstream_upper=up_high,
        total_lower=s1_low + s2_low + up_low,
        total_upper=s1_high + s2_high + up_high,
        evidence_class=scenario.evidence_class,
    )


__all__ = [
    "FabScenario",
    "FactorInterval",
    "ScenarioCarbonInterval",
    "apply_fab_scenario",
]
