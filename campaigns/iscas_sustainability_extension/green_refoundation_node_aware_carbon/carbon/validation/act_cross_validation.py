"""Independent matched-boundary ACT and GREEN areal calculation paths."""

from __future__ import annotations

import math


def _positive(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return number


def _nonnegative(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def act_2022_logic_path(
    *,
    area_cm2: float,
    fab_ci_kgco2e_per_kwh: float,
    energy_per_area_kwh_per_cm2: float,
    gas_per_area_kgco2e_per_cm2: float,
    materials_per_area_kgco2e_per_cm2: float,
    yield_fraction: float,
) -> float:
    """ACT equation: A * (CI*EPA + GPA + MPA) / Y."""
    area = _nonnegative("area_cm2", area_cm2)
    ci = _nonnegative("fab_ci", fab_ci_kgco2e_per_kwh)
    epa = _nonnegative("energy_per_area", energy_per_area_kwh_per_cm2)
    gpa = _nonnegative("gas_per_area", gas_per_area_kgco2e_per_cm2)
    mpa = _nonnegative("materials_per_area", materials_per_area_kgco2e_per_cm2)
    yield_value = _positive("yield_fraction", yield_fraction)
    if yield_value > 1.0:
        raise ValueError("yield_fraction cannot exceed one")
    return area * (ci * epa + gpa + mpa) / yield_value


def green_matched_areal_path(
    *,
    area_cm2: float,
    fab_ci_kgco2e_per_kwh: float,
    energy_per_area_kwh_per_cm2: float,
    gas_per_area_kgco2e_per_cm2: float,
    materials_per_area_kgco2e_per_cm2: float,
    yield_fraction: float,
) -> tuple[float, dict[str, float]]:
    """GREEN decomposition under the deliberately ACT-matched boundary."""
    area = _nonnegative("area_cm2", area_cm2)
    yield_value = _positive("yield_fraction", yield_fraction)
    if yield_value > 1.0:
        raise ValueError("yield_fraction cannot exceed one")
    scope2 = area * _nonnegative("fab_ci", fab_ci_kgco2e_per_kwh) * _nonnegative(
        "energy_per_area", energy_per_area_kwh_per_cm2
    )
    scope1_proxy = area * _nonnegative(
        "gas_per_area", gas_per_area_kgco2e_per_cm2
    )
    upstream_proxy = area * _nonnegative(
        "materials_per_area", materials_per_area_kgco2e_per_cm2
    )
    terms = {
        "scope2_kgco2e": scope2 / yield_value,
        "scope1_gas_proxy_kgco2e": scope1_proxy / yield_value,
        "upstream_material_proxy_kgco2e": upstream_proxy / yield_value,
    }
    return sum(terms.values()), terms


__all__ = ["act_2022_logic_path", "green_matched_areal_path"]
