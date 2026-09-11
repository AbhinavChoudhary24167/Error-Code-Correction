"""Evidence-aware operational-energy accounting for the GREEN refoundation.

The module does not estimate power from RTL toggles.  It combines energy terms
only after their evidence tier and the activity-annotation status are explicit.
Missing decision-critical terms remain missing; a partial subtotal is retained
without being promoted to a lifecycle-energy result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import math
from typing import Iterable, Mapping


class EvidenceTier(IntEnum):
    """SRAM/energy evidence hierarchy; a smaller number is stronger."""

    TIER_1_INDEPENDENT_CHARACTERIZATION = 1
    TIER_2_VALIDATED_LIBERTY = 2
    TIER_3_PUBLISHED_REFERENCE = 3
    TIER_4_BOUNDED_PARAMETRIC = 4
    TIER_5_NOT_QUALIFIED = 5


@dataclass(frozen=True)
class Interval:
    """Closed, finite, non-negative interval."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = float(self.lower)
        upper = float(self.upper)
        if not math.isfinite(lower) or not math.isfinite(upper):
            raise ValueError("interval endpoints must be finite")
        if lower < 0.0 or upper < lower:
            raise ValueError("interval must satisfy 0 <= lower <= upper")

    def scale(self, factor: float) -> "Interval":
        factor = float(factor)
        if not math.isfinite(factor) or factor < 0.0:
            raise ValueError("scale factor must be finite and non-negative")
        return Interval(self.lower * factor, self.upper * factor)

    def add(self, other: "Interval") -> "Interval":
        return Interval(self.lower + other.lower, self.upper + other.upper)

    def multiply(self, other: "Interval") -> "Interval":
        return Interval(self.lower * other.lower, self.upper * other.upper)


@dataclass(frozen=True)
class EnergyQuantity:
    """A per-event energy or leakage-power quantity with provenance."""

    interval: Interval | None
    unit: str
    tier: EvidenceTier | None
    evidence_class: str
    source_ids: tuple[str, ...]
    applicable: bool = True

    def __post_init__(self) -> None:
        if self.unit not in {"J/event", "W"}:
            raise ValueError("energy quantity unit must be J/event or W")
        if not self.evidence_class:
            raise ValueError("evidence_class must not be empty")
        if not self.source_ids:
            raise ValueError("source_ids must not be empty")
        if self.applicable:
            if self.tier is None:
                raise ValueError("an applicable quantity requires an evidence tier")
            if self.tier == EvidenceTier.TIER_5_NOT_QUALIFIED:
                if self.interval is not None:
                    raise ValueError("Tier-5 data cannot carry a decision value")
            elif self.interval is None:
                raise ValueError("Tier-1 through Tier-4 quantities require an interval")
        else:
            if self.tier is not None or self.interval != Interval(0.0, 0.0):
                raise ValueError("a non-applicable term must be an un-tiered zero interval")

    @classmethod
    def not_applicable(cls, unit: str, reason_source_id: str) -> "EnergyQuantity":
        return cls(
            interval=Interval(0.0, 0.0),
            unit=unit,
            tier=None,
            evidence_class="NOT_APPLICABLE",
            source_ids=(reason_source_id,),
            applicable=False,
        )


@dataclass(frozen=True)
class ActivityCoverage:
    """Coverage for one disjoint physical component class."""

    component: str
    annotated_pin_count: int | None
    total_pin_count: int | None
    required_for_power: bool
    mapping_status: str

    def __post_init__(self) -> None:
        if not self.component or not self.mapping_status:
            raise ValueError("component and mapping_status must not be empty")
        if (self.annotated_pin_count is None) != (self.total_pin_count is None):
            raise ValueError("coverage counts must both be known or both be unknown")
        if self.total_pin_count is not None:
            if isinstance(self.total_pin_count, bool) or isinstance(
                self.annotated_pin_count, bool
            ):
                raise TypeError("coverage counts must be integers")
            if self.total_pin_count < 0 or not 0 <= self.annotated_pin_count <= self.total_pin_count:
                raise ValueError("coverage counts are inconsistent")

    @property
    def fraction(self) -> float | None:
        if self.total_pin_count is None or self.total_pin_count == 0:
            return None
        assert self.annotated_pin_count is not None
        return self.annotated_pin_count / self.total_pin_count


def classify_activity_coverage(
    rows: Iterable[ActivityCoverage], *, minimum_fraction: float = 0.95
) -> dict[str, object]:
    """Apply an explicit per-component activity qualification threshold."""
    minimum_fraction = float(minimum_fraction)
    if not math.isfinite(minimum_fraction) or not 0.0 < minimum_fraction <= 1.0:
        raise ValueError("minimum_fraction must be in (0, 1]")
    required = [row for row in rows if row.required_for_power]
    if not required:
        raise ValueError("at least one required activity component is needed")
    blockers: list[str] = []
    for row in required:
        fraction = row.fraction
        if fraction is None:
            blockers.append(f"{row.component}:COVERAGE_NOT_MEASURED")
        elif fraction < minimum_fraction:
            blockers.append(f"{row.component}:COVERAGE_{fraction:.6f}")
    return {
        "status": "ACTIVITY_QUALIFIED" if not blockers else "NOT_QUALIFIED",
        "qualified": not blockers,
        "minimum_fraction": minimum_fraction,
        "blockers": blockers,
    }


@dataclass(frozen=True)
class OperationalWorkload:
    """Disjoint event counts in the declared use-phase boundary.

    ``base_read_count`` includes clean and corrected reads.  Correction energy
    is incremental and multiplied only by ``corrected_read_count``.  Retry and
    recovery counts are extra events, so callers must not also add their energy
    to base read/write quantities.
    """

    base_read_count: int
    base_write_count: int
    corrected_read_count: int = 0
    scrub_count: int = 0
    retry_count: int = 0
    recovery_count: int = 0
    idle_seconds: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "base_read_count",
            "base_write_count",
            "corrected_read_count",
            "scrub_count",
            "retry_count",
            "recovery_count",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        idle = float(self.idle_seconds)
        if not math.isfinite(idle) or idle < 0.0:
            raise ValueError("idle_seconds must be finite and non-negative")
        if self.corrected_read_count > self.base_read_count:
            raise ValueError("corrected reads cannot exceed base reads")


_CATEGORY_SPEC = {
    "normal_read": ("J/event", "base_read_count"),
    "normal_write": ("J/event", "base_write_count"),
    "ecc_encode": ("J/event", "base_write_count"),
    "ecc_decode": ("J/event", "base_read_count"),
    "correction": ("J/event", "corrected_read_count"),
    "scrub": ("J/event", "scrub_count"),
    "retry": ("J/event", "retry_count"),
    "recovery": ("J/event", "recovery_count"),
    "idle_leakage": ("W", "idle_seconds"),
}


@dataclass(frozen=True)
class OperationalEnergyResult:
    classification: str
    total_interval_j: Interval | None
    accounted_subtotal_j: Interval
    breakdown_j: Mapping[str, Interval | None]
    blockers: tuple[str, ...]
    active_evidence_tiers: tuple[int, ...]


def account_operational_energy(
    workload: OperationalWorkload,
    quantities: Mapping[str, EnergyQuantity],
    *,
    activity_qualified: bool,
) -> OperationalEnergyResult:
    """Compute the Phase-Q energy boundary without filling missing terms."""
    unknown = set(quantities) - set(_CATEGORY_SPEC)
    missing = set(_CATEGORY_SPEC) - set(quantities)
    if unknown:
        raise ValueError(f"unknown energy categories: {sorted(unknown)!r}")
    if missing:
        raise ValueError(f"missing energy categories: {sorted(missing)!r}")

    subtotal = Interval(0.0, 0.0)
    breakdown: dict[str, Interval | None] = {}
    blockers: list[str] = []
    active_tiers: list[int] = []
    for category, (expected_unit, multiplier_name) in _CATEGORY_SPEC.items():
        quantity = quantities[category]
        if quantity.unit != expected_unit:
            raise ValueError(f"{category} requires unit {expected_unit}")
        multiplier = float(getattr(workload, multiplier_name))
        if multiplier == 0.0 or not quantity.applicable:
            contribution = Interval(0.0, 0.0)
        elif quantity.interval is None:
            contribution = None
            blockers.append(f"{category}:TIER_5_NOT_QUALIFIED")
        else:
            contribution = quantity.interval.scale(multiplier)
            assert quantity.tier is not None
            active_tiers.append(int(quantity.tier))
        breakdown[category] = contribution
        if contribution is not None:
            subtotal = subtotal.add(contribution)

    if not activity_qualified:
        blockers.append("ACTIVITY_NOT_QUALIFIED")
    if blockers:
        classification = "UNQUALIFIED"
        total = None
    elif any(tier == int(EvidenceTier.TIER_4_BOUNDED_PARAMETRIC) for tier in active_tiers):
        classification = "PARAMETRIC_SENSITIVITY"
        total = subtotal
    elif any(tier == int(EvidenceTier.TIER_3_PUBLISHED_REFERENCE) for tier in active_tiers):
        classification = "BOUNDED_RESULT"
        total = subtotal
    else:
        classification = "QUALIFIED_ABSOLUTE"
        total = subtotal
    return OperationalEnergyResult(
        classification=classification,
        total_interval_j=total,
        accounted_subtotal_j=subtotal,
        breakdown_j=breakdown,
        blockers=tuple(blockers),
        active_evidence_tiers=tuple(sorted(set(active_tiers))),
    )


def operational_carbon_interval(
    energy: OperationalEnergyResult, grid_ci_kgco2e_per_kwh: Interval
) -> Interval | None:
    """Return C_op = E_lifetime[kWh] * CI_use, preserving uncertainty."""
    if energy.total_interval_j is None:
        return None
    energy_kwh = energy.total_interval_j.scale(1.0 / 3_600_000.0)
    return energy_kwh.multiply(grid_ci_kgco2e_per_kwh)


__all__ = [
    "ActivityCoverage",
    "EnergyQuantity",
    "EvidenceTier",
    "Interval",
    "OperationalEnergyResult",
    "OperationalWorkload",
    "account_operational_energy",
    "classify_activity_coverage",
    "operational_carbon_interval",
]
