"""Auditable semiconductor manufacturing and lifecycle-carbon equations.

The module intentionally contains no hidden node coefficients.  Every process
inventory is supplied by the caller with an evidence label and source IDs.
The functions are suitable for calibrated, translated, bounded, or purely
parametric studies without presenting one evidence class as another.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable, Mapping, Sequence


JOULES_PER_KWH = 3_600_000.0
MM2_PER_CM2 = 100.0

# IPCC AR6 WGI Chapter 7 Supplementary Material, Table 7.SM.7, GWP-100.
# These are characterization factors, not process-gas use or release factors.
IPCC_AR6_GWP100: Mapping[str, float] = {
    "CF4": 7_380.0,
    "C2F6": 12_400.0,
    "NF3": 17_400.0,
    "SF6": 25_200.0,
}
IPCC_AR6_GWP_SOURCE_ID = "SRC_IPCC_AR6_WGI_CH7_SM"


class EvidenceLabel(str, Enum):
    SOURCE_CALIBRATED = "SOURCE_CALIBRATED"
    CROSS_MODEL_VALIDATED = "CROSS_MODEL_VALIDATED"
    MEASURED_SKY130_PHYSICAL = "MEASURED_SKY130_PHYSICAL"
    IMEC_CALIBRATED_ADVANCED_NODE = "IMEC_CALIBRATED_ADVANCED_NODE"
    TECHNOLOGY_TRANSLATED_SCENARIO = "TECHNOLOGY_TRANSLATED_SCENARIO"
    PARAMETRIC_EXTRAPOLATION = "PARAMETRIC_EXTRAPOLATION"
    PARAMETRIC_UNCERTAIN = "PARAMETRIC_UNCERTAIN"
    BOUND_ONLY = "BOUND_ONLY"
    NOT_QUALIFIED = "NOT_QUALIFIED"


class FabEnergyBoundary(str, Enum):
    """Declares whether the supplied fab energy already contains patterning."""

    TOTAL_INCLUDING_PATTERNING = "TOTAL_INCLUDING_PATTERNING"
    NON_PATTERNING_ONLY = "NON_PATTERNING_ONLY"


@dataclass(frozen=True)
class Evidence:
    label: EvidenceLabel
    source_ids: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        if not self.note.strip():
            raise ValueError("evidence note must be non-empty")
        if self.label in {
            EvidenceLabel.SOURCE_CALIBRATED,
            EvidenceLabel.CROSS_MODEL_VALIDATED,
            EvidenceLabel.IMEC_CALIBRATED_ADVANCED_NODE,
        } and not self.source_ids:
            raise ValueError(f"{self.label.value} evidence requires source IDs")
        if any(not source_id.strip() for source_id in self.source_ids):
            raise ValueError("source IDs must be non-empty")


def _finite_nonnegative(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def _finite_positive(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be finite and strictly positive")
    return number


def _fraction(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be a finite fraction in [0, 1]")
    return number


def joules_to_kwh(joules: float) -> float:
    return _finite_nonnegative("joules", joules) / JOULES_PER_KWH


def kwh_to_joules(kwh: float) -> float:
    return _finite_nonnegative("kwh", kwh) * JOULES_PER_KWH


def mm2_to_cm2(area_mm2: float) -> float:
    return _finite_nonnegative("area_mm2", area_mm2) / MM2_PER_CM2


def grams_to_kg(grams: float) -> float:
    return _finite_nonnegative("grams", grams) / 1_000.0


@dataclass(frozen=True)
class ProcessGasUse:
    gas: str
    mass_kg_per_wafer: float
    gwp100_kgco2e_per_kg: float
    effective_release_fraction: float
    abatement_efficiency: float
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.gas.strip():
            raise ValueError("gas must be non-empty")
        _finite_nonnegative("mass_kg_per_wafer", self.mass_kg_per_wafer)
        _finite_nonnegative("gwp100_kgco2e_per_kg", self.gwp100_kgco2e_per_kg)
        _fraction("effective_release_fraction", self.effective_release_fraction)
        _fraction("abatement_efficiency", self.abatement_efficiency)

    @property
    def emitted_kgco2e_per_wafer(self) -> float:
        return (
            self.mass_kg_per_wafer
            * self.gwp100_kgco2e_per_kg
            * self.effective_release_fraction
            * (1.0 - self.abatement_efficiency)
        )


@dataclass(frozen=True)
class PatterningStep:
    family: str
    count: int
    electricity_kwh_per_step: float
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.family.strip():
            raise ValueError("patterning family must be non-empty")
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 0:
            raise ValueError("patterning step count must be a non-negative integer")
        _finite_nonnegative("electricity_kwh_per_step", self.electricity_kwh_per_step)

    @property
    def electricity_kwh_per_wafer(self) -> float:
        return self.count * self.electricity_kwh_per_step


@dataclass(frozen=True)
class PatterningRoute:
    name: str
    exposure_route: str
    steps: tuple[PatterningStep, ...]
    evidence: Evidence

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.exposure_route.strip():
            raise ValueError("patterning route name and exposure route must be non-empty")

    @property
    def electricity_kwh_per_wafer(self) -> float:
        return sum(step.electricity_kwh_per_wafer for step in self.steps)

    def counts_by_family(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for step in self.steps:
            result[step.family] = result.get(step.family, 0) + step.count
        return result


@dataclass(frozen=True)
class WaferProcessInventory:
    node_name: str
    process_route: str
    maturity: str
    wafer_diameter_mm: float
    fab_electricity_kwh: float
    fab_ci_kgco2e_per_kwh: float
    process_gases: tuple[ProcessGasUse, ...]
    upstream_kgco2e_per_wafer: float
    evidence: Evidence
    energy_boundary: FabEnergyBoundary = FabEnergyBoundary.TOTAL_INCLUDING_PATTERNING
    patterning_route: PatterningRoute | None = None

    def __post_init__(self) -> None:
        if not self.node_name.strip() or not self.process_route.strip():
            raise ValueError("node name and process route must be non-empty")
        if not self.maturity.strip():
            raise ValueError("maturity metadata must be non-empty")
        _finite_positive("wafer_diameter_mm", self.wafer_diameter_mm)
        _finite_nonnegative("fab_electricity_kwh", self.fab_electricity_kwh)
        _finite_nonnegative("fab_ci_kgco2e_per_kwh", self.fab_ci_kgco2e_per_kwh)
        _finite_nonnegative(
            "upstream_kgco2e_per_wafer", self.upstream_kgco2e_per_wafer
        )
        if (
            self.energy_boundary is FabEnergyBoundary.TOTAL_INCLUDING_PATTERNING
            and self.patterning_route is not None
            and self.patterning_route.electricity_kwh_per_wafer
            > self.fab_electricity_kwh + 1e-12
        ):
            raise ValueError(
                "diagnostic patterning energy cannot exceed total fab energy"
            )


@dataclass(frozen=True)
class WaferCarbonBreakdown:
    total_energy_kwh: float
    scope1_kgco2e: float
    scope2_kgco2e: float
    upstream_kgco2e: float
    total_kgco2e: float
    patterning_scope2_kgco2e_diagnostic: float
    evidence: Evidence


def wafer_carbon(inventory: WaferProcessInventory) -> WaferCarbonBreakdown:
    """Calculate mutually exclusive Scope 1, Scope 2, and upstream terms.

    Patterning carbon is a diagnostic allocation within Scope 2.  It is never
    added to total carbon a second time.  For a NON_PATTERNING_ONLY inventory,
    patterning electricity is first added to the energy boundary exactly once.
    """
    patterning_energy = (
        inventory.patterning_route.electricity_kwh_per_wafer
        if inventory.patterning_route is not None
        else 0.0
    )
    if inventory.energy_boundary is FabEnergyBoundary.NON_PATTERNING_ONLY:
        total_energy = inventory.fab_electricity_kwh + patterning_energy
    else:
        total_energy = inventory.fab_electricity_kwh
    scope1 = sum(gas.emitted_kgco2e_per_wafer for gas in inventory.process_gases)
    scope2 = total_energy * inventory.fab_ci_kgco2e_per_kwh
    upstream = inventory.upstream_kgco2e_per_wafer
    total = scope1 + scope2 + upstream
    if not math.isfinite(total):
        raise OverflowError("wafer carbon exceeds the finite float range")
    return WaferCarbonBreakdown(
        total_energy_kwh=total_energy,
        scope1_kgco2e=scope1,
        scope2_kgco2e=scope2,
        upstream_kgco2e=upstream,
        total_kgco2e=total,
        patterning_scope2_kgco2e_diagnostic=(
            patterning_energy * inventory.fab_ci_kgco2e_per_kwh
        ),
        evidence=inventory.evidence,
    )


def gross_dies_per_wafer(wafer_diameter_mm: float, die_area_mm2: float) -> float:
    """Continuous expected gross-die approximation with circular-edge loss.

    N ~= pi(D/2)^2/A - pi*D/sqrt(2*A).  Scribe lanes, exclusion rings,
    rectangular aspect ratio, and reticle constraints remain out of boundary.
    """
    diameter = _finite_positive("wafer_diameter_mm", wafer_diameter_mm)
    area = _finite_positive("die_area_mm2", die_area_mm2)
    gross = math.pi * (diameter / 2.0) ** 2 / area - math.pi * diameter / math.sqrt(
        2.0 * area
    )
    if gross <= 0.0:
        raise ValueError("die is too large for the gross-die approximation")
    return gross


def poisson_yield(defect_density_per_cm2: float, die_area_mm2: float) -> float:
    defect_density = _finite_nonnegative(
        "defect_density_per_cm2", defect_density_per_cm2
    )
    return math.exp(-defect_density * mm2_to_cm2(die_area_mm2))


def negative_binomial_yield(
    defect_density_per_cm2: float, die_area_mm2: float, alpha: float
) -> float:
    defect_density = _finite_nonnegative(
        "defect_density_per_cm2", defect_density_per_cm2
    )
    clustering = _finite_positive("alpha", alpha)
    return (1.0 + defect_density * mm2_to_cm2(die_area_mm2) / clustering) ** (
        -clustering
    )


def murphy_yield(defect_density_per_cm2: float, die_area_mm2: float) -> float:
    defect_density = _finite_nonnegative(
        "defect_density_per_cm2", defect_density_per_cm2
    )
    defect_area = defect_density * mm2_to_cm2(die_area_mm2)
    if defect_area == 0.0:
        return 1.0
    return ((1.0 - math.exp(-defect_area)) / defect_area) ** 2


def die_yield(
    model: str,
    defect_density_per_cm2: float,
    die_area_mm2: float,
    *,
    alpha: float | None = None,
) -> float:
    normalized = model.strip().lower().replace("-", "_")
    if normalized == "poisson":
        return poisson_yield(defect_density_per_cm2, die_area_mm2)
    if normalized in {"negative_binomial", "negativebinomial"}:
        if alpha is None:
            raise ValueError("negative-binomial yield requires alpha")
        return negative_binomial_yield(defect_density_per_cm2, die_area_mm2, alpha)
    if normalized == "murphy":
        return murphy_yield(defect_density_per_cm2, die_area_mm2)
    raise ValueError(f"unsupported yield model: {model}")


def expected_good_dies(
    wafer_diameter_mm: float,
    die_area_mm2: float,
    die_yield_fraction: float,
    *,
    line_yield_fraction: float = 1.0,
) -> float:
    die_fraction = _fraction("die_yield_fraction", die_yield_fraction)
    line_fraction = _fraction("line_yield_fraction", line_yield_fraction)
    good = (
        gross_dies_per_wafer(wafer_diameter_mm, die_area_mm2)
        * die_fraction
        * line_fraction
    )
    if good <= 0.0:
        raise ValueError("expected good dies must be strictly positive")
    return good


def mask_nre_per_die_kgco2e(
    maskset_kgco2e: float, product_wafers: float, good_dies_per_wafer: float
) -> float:
    maskset = _finite_nonnegative("maskset_kgco2e", maskset_kgco2e)
    wafers = _finite_positive("product_wafers", product_wafers)
    good_dies = _finite_positive("good_dies_per_wafer", good_dies_per_wafer)
    return maskset / (wafers * good_dies)


@dataclass(frozen=True)
class DieCarbonBreakdown:
    die_area_mm2: float
    gross_dies_per_wafer: float
    die_yield_fraction: float
    line_yield_fraction: float
    good_dies_per_wafer: float
    process_kgco2e: float
    mask_nre_kgco2e: float | None
    package_kgco2e: float
    other_kgco2e: float
    total_kgco2e: float
    evidence: Evidence


def die_embodied_carbon(
    inventory: WaferProcessInventory,
    die_area_mm2: float,
    defect_density_per_cm2: float,
    *,
    yield_model: str,
    yield_alpha: float | None = None,
    line_yield_fraction: float = 1.0,
    maskset_kgco2e: float | None = None,
    product_wafers: float | None = None,
    package_kgco2e: float = 0.0,
    other_kgco2e: float = 0.0,
) -> DieCarbonBreakdown:
    """Allocate wafer carbon to expected good dies and add disjoint terms."""
    area = _finite_positive("die_area_mm2", die_area_mm2)
    line_yield = _fraction("line_yield_fraction", line_yield_fraction)
    if line_yield == 0.0:
        raise ValueError("line_yield_fraction must be strictly positive")
    y = die_yield(
        yield_model,
        defect_density_per_cm2,
        area,
        alpha=yield_alpha,
    )
    gross = gross_dies_per_wafer(inventory.wafer_diameter_mm, area)
    good = expected_good_dies(
        inventory.wafer_diameter_mm,
        area,
        y,
        line_yield_fraction=line_yield,
    )
    process = wafer_carbon(inventory).total_kgco2e / good
    if (maskset_kgco2e is None) != (product_wafers is None):
        raise ValueError(
            "maskset_kgco2e and product_wafers must both be supplied or both omitted"
        )
    mask = (
        None
        if maskset_kgco2e is None
        else mask_nre_per_die_kgco2e(maskset_kgco2e, product_wafers, good)  # type: ignore[arg-type]
    )
    package = _finite_nonnegative("package_kgco2e", package_kgco2e)
    other = _finite_nonnegative("other_kgco2e", other_kgco2e)
    total = process + (mask or 0.0) + package + other
    return DieCarbonBreakdown(
        die_area_mm2=area,
        gross_dies_per_wafer=gross,
        die_yield_fraction=y,
        line_yield_fraction=line_yield,
        good_dies_per_wafer=good,
        process_kgco2e=process,
        mask_nre_kgco2e=mask,
        package_kgco2e=package,
        other_kgco2e=other,
        total_kgco2e=total,
        evidence=inventory.evidence,
    )


@dataclass(frozen=True)
class IncrementalECCCarbon:
    baseline_die_area_mm2: float
    candidate_die_area_mm2: float
    baseline_kgco2e: float
    candidate_kgco2e: float
    incremental_kgco2e: float
    evidence: Evidence


def incremental_ecc_embodied_carbon(
    inventory: WaferProcessInventory,
    host_area_mm2: float,
    baseline_ecc_area_mm2: float,
    candidate_ecc_area_mm2: float,
    defect_density_per_cm2: float,
    *,
    yield_model: str,
    yield_alpha: float | None = None,
    line_yield_fraction: float = 1.0,
) -> IncrementalECCCarbon:
    host = _finite_nonnegative("host_area_mm2", host_area_mm2)
    baseline_area = _finite_nonnegative(
        "baseline_ecc_area_mm2", baseline_ecc_area_mm2
    )
    candidate_area = _finite_nonnegative(
        "candidate_ecc_area_mm2", candidate_ecc_area_mm2
    )
    if candidate_area < baseline_area:
        raise ValueError("candidate ECC area must not be smaller than baseline ECC area")
    common = {
        "yield_model": yield_model,
        "yield_alpha": yield_alpha,
        "line_yield_fraction": line_yield_fraction,
    }
    baseline = die_embodied_carbon(
        inventory,
        host + baseline_area,
        defect_density_per_cm2,
        **common,
    )
    candidate = die_embodied_carbon(
        inventory,
        host + candidate_area,
        defect_density_per_cm2,
        **common,
    )
    delta = candidate.total_kgco2e - baseline.total_kgco2e
    tolerance = 1e-12 * max(1.0, candidate.total_kgco2e, baseline.total_kgco2e)
    if delta < -tolerance:
        raise ArithmeticError("incremental area unexpectedly reduced embodied carbon")
    return IncrementalECCCarbon(
        baseline_die_area_mm2=baseline.die_area_mm2,
        candidate_die_area_mm2=candidate.die_area_mm2,
        baseline_kgco2e=baseline.total_kgco2e,
        candidate_kgco2e=candidate.total_kgco2e,
        incremental_kgco2e=max(0.0, delta),
        evidence=inventory.evidence,
    )


def operational_carbon_kgco2e(
    transaction_energy_j: float,
    transaction_count: float,
    use_phase_ci_kgco2e_per_kwh: float,
    *,
    recovery_energy_j: float = 0.0,
) -> float:
    """Convert activity-qualified transaction and recovery energy once."""
    base_energy = _finite_nonnegative("transaction_energy_j", transaction_energy_j)
    recovery_energy = _finite_nonnegative("recovery_energy_j", recovery_energy_j)
    count = _finite_nonnegative("transaction_count", transaction_count)
    ci = _finite_nonnegative(
        "use_phase_ci_kgco2e_per_kwh", use_phase_ci_kgco2e_per_kwh
    )
    return joules_to_kwh((base_energy + recovery_energy) * count) * ci


def lifecycle_carbon_kgco2e(
    embodied_kgco2e: float,
    operational_kgco2e: float,
    *,
    replacement_or_external_recovery_kgco2e: float = 0.0,
) -> float:
    """Sum disjoint lifecycle terms; operational recovery energy stays in op."""
    return sum(
        _finite_nonnegative(name, value)
        for name, value in (
            ("embodied_kgco2e", embodied_kgco2e),
            ("operational_kgco2e", operational_kgco2e),
            (
                "replacement_or_external_recovery_kgco2e",
                replacement_or_external_recovery_kgco2e,
            ),
        )
    )


def act_compatible_logic_carbon_kgco2e(
    area_cm2: float,
    fab_ci_kgco2e_per_kwh: float,
    energy_per_area_kwh_per_cm2: float,
    gas_per_area_kgco2e_per_cm2: float,
    materials_per_area_kgco2e_per_cm2: float,
    yield_fraction: float,
) -> float:
    """Independent ACT/ACT3-compatible SoC equation under matched inputs.

    E_SoC = Area * (CI_fab*EPA + GPA + MPA) / Y.
    """
    area = _finite_nonnegative("area_cm2", area_cm2)
    ci = _finite_nonnegative("fab_ci_kgco2e_per_kwh", fab_ci_kgco2e_per_kwh)
    epa = _finite_nonnegative("energy_per_area_kwh_per_cm2", energy_per_area_kwh_per_cm2)
    gpa = _finite_nonnegative(
        "gas_per_area_kgco2e_per_cm2", gas_per_area_kgco2e_per_cm2
    )
    mpa = _finite_nonnegative(
        "materials_per_area_kgco2e_per_cm2", materials_per_area_kgco2e_per_cm2
    )
    yield_value = _fraction("yield_fraction", yield_fraction)
    if yield_value == 0.0:
        raise ValueError("yield_fraction must be strictly positive")
    return area * (ci * epa + gpa + mpa) / yield_value


def merge_source_ids(*groups: Iterable[str]) -> tuple[str, ...]:
    """Stable deduplication for derived-value provenance."""
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for source_id in group:
            if source_id not in seen:
                seen.add(source_id)
                merged.append(source_id)
    return tuple(merged)


def route_energy_by_family(route: PatterningRoute) -> dict[str, float]:
    """Return process-family energy without treating mask count as carbon."""
    result: dict[str, float] = {}
    for step in route.steps:
        result[step.family] = result.get(step.family, 0.0) + step.electricity_kwh_per_wafer
    return result


def process_gas_breakdown(gases: Sequence[ProcessGasUse]) -> dict[str, float]:
    result: dict[str, float] = {}
    for gas in gases:
        result[gas.gas] = result.get(gas.gas, 0.0) + gas.emitted_kgco2e_per_wafer
    return result
