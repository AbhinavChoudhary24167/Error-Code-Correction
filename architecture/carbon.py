"""Explicit-unit operational and embodied carbon accounting."""

from __future__ import annotations

from dataclasses import asdict, dataclass


JOULES_PER_KWH = 3.6e6
GRAMS_PER_KILOGRAM = 1000.0


def joules_to_kwh(energy_j: float) -> float:
    if energy_j < 0:
        raise ValueError("energy_j must be non-negative")
    return energy_j / JOULES_PER_KWH


def grams_to_kilograms(value_g: float) -> float:
    if value_g < 0:
        raise ValueError("carbon mass must be non-negative")
    return value_g / GRAMS_PER_KILOGRAM


def kilograms_to_grams(value_kg: float) -> float:
    if value_kg < 0:
        raise ValueError("carbon mass must be non-negative")
    return value_kg * GRAMS_PER_KILOGRAM


def operational_carbon_kg(
    energy_j: float,
    carbon_intensity: float,
    *,
    intensity_unit: str = "kgco2e_per_kwh",
) -> float:
    if carbon_intensity < 0:
        raise ValueError("carbon_intensity must be non-negative")
    if intensity_unit == "gco2e_per_kwh":
        intensity_kg = grams_to_kilograms(carbon_intensity)
    elif intensity_unit == "kgco2e_per_kwh":
        intensity_kg = carbon_intensity
    else:
        raise ValueError("intensity_unit must be gco2e_per_kwh or kgco2e_per_kwh")
    return joules_to_kwh(energy_j) * intensity_kg


@dataclass(frozen=True)
class EmbodiedCarbonAssumptions:
    manufacturing_intensity_kgco2e_per_cm2: float
    yield_allocation_factor: float
    die_allocation_factor: float = 1.0
    packaging_allocation_kgco2e: float = 0.0
    amortized_systems: int = 1
    source: str = "user_supplied"

    def __post_init__(self) -> None:
        if self.manufacturing_intensity_kgco2e_per_cm2 < 0:
            raise ValueError("manufacturing intensity must be non-negative")
        if self.yield_allocation_factor <= 0 or self.die_allocation_factor < 0:
            raise ValueError("yield factor must be positive and die allocation non-negative")
        if self.packaging_allocation_kgco2e < 0 or self.amortized_systems <= 0:
            raise ValueError("packaging allocation must be non-negative and amortized_systems positive")


def embodied_carbon_kg(area_um2: float, assumptions: EmbodiedCarbonAssumptions) -> dict:
    if area_um2 < 0:
        raise ValueError("area_um2 must be non-negative")
    area_cm2 = area_um2 * 1e-8
    manufacturing = (
        area_cm2
        * assumptions.manufacturing_intensity_kgco2e_per_cm2
        * assumptions.yield_allocation_factor
        * assumptions.die_allocation_factor
    )
    total = (manufacturing + assumptions.packaging_allocation_kgco2e) / assumptions.amortized_systems
    return {
        "area_um2": area_um2,
        "area_cm2": area_cm2,
        "manufacturing_kgco2e": manufacturing,
        "packaging_allocation_kgco2e": assumptions.packaging_allocation_kgco2e,
        "total_embodied_kgco2e": total,
        "assumptions": asdict(assumptions),
    }


def carbon_breakdown(
    *,
    base_system_carbon_kg: float | None,
    incremental_energy_j: float | None,
    incremental_area_um2: float | None,
    carbon_intensity_kgco2e_per_kwh: float,
    total_accesses: int,
    embodied_assumptions: EmbodiedCarbonAssumptions | None,
) -> dict:
    operational = (
        operational_carbon_kg(
            incremental_energy_j,
            carbon_intensity_kgco2e_per_kwh,
        )
        if incremental_energy_j is not None
        else None
    )
    embodied = (
        embodied_carbon_kg(incremental_area_um2, embodied_assumptions)
        if incremental_area_um2 is not None and embodied_assumptions is not None
        else None
    )
    embodied_total = embodied["total_embodied_kgco2e"] if embodied is not None else None
    incremental_total = (
        operational + embodied_total
        if operational is not None and embodied_total is not None
        else None
    )
    absolute = (
        base_system_carbon_kg + incremental_total
        if base_system_carbon_kg is not None and incremental_total is not None
        else None
    )
    return {
        "absolute_system_carbon_kgco2e": absolute,
        "base_system_carbon_kgco2e": base_system_carbon_kg,
        "incremental_operational_carbon_kgco2e": operational,
        "incremental_embodied_carbon_kgco2e": embodied_total,
        "incremental_total_carbon_kgco2e": incremental_total,
        "amortized_incremental_carbon_kgco2e_per_access": (
            incremental_total / total_accesses
            if incremental_total is not None and total_accesses > 0
            else None
        ),
        "embodied_detail": embodied,
        "operational_equation": "CI[kgCO2e/kWh] * energy[J] / 3.6e6",
    }
