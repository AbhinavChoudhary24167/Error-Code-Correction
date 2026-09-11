"""Scientific kernel for GREEN Matrix 3.0.

The module keeps model structure, parameter values, and evidence status
separate.  It contains no cohort normalization, hidden epsilon floors, or
stakeholder weights.  Missing inputs remain missing and metric functions
return explicit status objects for scientifically meaningful undefined cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import math
import random
from typing import Iterable, Mapping, Sequence


class EvidenceTier(IntEnum):
    """Evidence maturity; ordering is only a default gating aid.

    A higher tier is not universally superior: relevance, boundary match, and
    metric-specific requirements are evaluated independently.
    """

    E0 = 0  # absent
    E1 = 1  # assumed / exploratory parametric
    E2 = 2  # published literature / external model
    E3 = 3  # analytical, logical enumeration, or RTL-derived
    E4 = 4  # synthesis / place-and-route tool estimate
    E5 = 5  # activity-qualified matched post-route result
    E6 = 6  # independently cross-validated characterization
    E7 = 7  # silicon or manufacturing measured


RESULT_CLASSES = {
    "ABSOLUTE_QUALIFIED",
    "RELATIVE_QUALIFIED",
    "PARAMETRIC",
    "BOUNDED",
    "DIAGNOSTIC",
    "LOGICAL_CONTROL",
    "UNQUALIFIED",
}


def _finite(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _nonnegative(name: str, value: float) -> float:
    number = _finite(name, value)
    if number < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _positive(name: str, value: float) -> float:
    number = _finite(name, value)
    if number <= 0.0:
        raise ValueError(f"{name} must be strictly positive")
    return number


def _probability(name: str, value: float) -> float:
    number = _finite(name, value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return number


@dataclass(frozen=True)
class MetricResult:
    value: float | None
    unit: str
    status: str
    reason: str | None
    boundary_id: str

    def __post_init__(self) -> None:
        if not self.boundary_id.strip():
            raise ValueError("a metric result requires a system-boundary ID")
        if self.value is not None:
            _finite("metric value", self.value)


@dataclass(frozen=True)
class EvidenceRecord:
    quantity_id: str
    tier: EvidenceTier
    result_class: str
    boundary_id: str
    source_ids: tuple[str, ...] = ()
    blocking_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.quantity_id.strip() or not self.boundary_id.strip():
            raise ValueError("evidence requires quantity and boundary IDs")
        if self.result_class not in RESULT_CLASSES:
            raise ValueError(f"unsupported result class: {self.result_class}")
        if self.tier is EvidenceTier.E0 and not self.blocking_reason:
            raise ValueError("E0 evidence must explain what is missing")


_UNITS: dict[str, tuple[str, float]] = {
    "J": ("energy", 1.0),
    "Wh": ("energy", 3_600.0),
    "kWh": ("energy", 3_600_000.0),
    "W": ("power", 1.0),
    "s": ("time", 1.0),
    "h": ("time", 3_600.0),
    "kgCO2e": ("carbon", 1.0),
    "gCO2e": ("carbon", 1e-3),
    "cm2": ("area", 1.0),
    "mm2": ("area", 1e-2),
    "um2": ("area", 1e-8),
    "probability": ("probability", 1.0),
    "ppm": ("probability", 1e-6),
    "failures_per_hour": ("failure_rate", 1.0),
    "FIT": ("failure_rate", 1e-9),
}


def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    """Perform an explicit same-dimension conversion.

    Callers must name both units; there is deliberately no implicit coercion.
    """

    number = _finite("value", value)
    if from_unit not in _UNITS or to_unit not in _UNITS:
        raise ValueError("unknown unit")
    source_dimension, source_scale = _UNITS[from_unit]
    target_dimension, target_scale = _UNITS[to_unit]
    if source_dimension != target_dimension:
        raise ValueError(f"cannot convert {from_unit} to {to_unit}")
    return number * source_scale / target_scale


def correct_service_count(request_count: float, q_correct: float) -> float:
    requests = _nonnegative("request_count", request_count)
    probability = _probability("q_correct", q_correct)
    result = requests * probability
    if not math.isfinite(result):
        raise OverflowError("correct-service count exceeds finite range")
    return result


def csci(
    lifecycle_carbon_kgco2e: float | None,
    request_count: float,
    q_correct: float | None,
    *,
    boundary_id: str,
) -> MetricResult:
    """Correct-Service Carbon Intensity in kgCO2e/correct service.

    A zero-service denominator is undefined and is never replaced by epsilon.
    """

    if lifecycle_carbon_kgco2e is None:
        return MetricResult(
            None,
            "kgCO2e_per_correct_service",
            "BLOCKED_MISSING_LIFECYCLE_CARBON",
            "lifecycle carbon is unavailable inside the declared boundary",
            boundary_id,
        )
    if q_correct is None:
        return MetricResult(
            None,
            "kgCO2e_per_correct_service",
            "BLOCKED_MISSING_CORRECT_SERVICE_PROBABILITY",
            "a calibrated or declared correct-service probability is unavailable",
            boundary_id,
        )
    carbon = _nonnegative("lifecycle_carbon_kgco2e", lifecycle_carbon_kgco2e)
    denominator = correct_service_count(request_count, q_correct)
    if denominator == 0.0:
        return MetricResult(
            None,
            "kgCO2e_per_correct_service",
            "UNDEFINED_ZERO_CORRECT_SERVICE",
            "N_req * Q_correct is zero; no epsilon floor is permitted",
            boundary_id,
        )
    return MetricResult(
        carbon / denominator,
        "kgCO2e_per_correct_service",
        "DEFINED",
        None,
        boundary_id,
    )


def csci_bit(
    lifecycle_carbon_kgco2e: float | None,
    payload_bits: int,
    request_count: float,
    q_correct: float | None,
    *,
    boundary_id: str,
) -> MetricResult:
    """Payload-normalized CSCI in kgCO2e/correct payload bit."""

    if isinstance(payload_bits, bool) or not isinstance(payload_bits, int):
        raise TypeError("payload_bits must be an integer")
    if payload_bits <= 0:
        raise ValueError("payload_bits must be strictly positive")
    access = csci(
        lifecycle_carbon_kgco2e,
        request_count,
        q_correct,
        boundary_id=boundary_id,
    )
    if access.value is None:
        return MetricResult(
            None,
            "kgCO2e_per_correct_payload_bit",
            access.status,
            access.reason,
            boundary_id,
        )
    return MetricResult(
        access.value / payload_bits,
        "kgCO2e_per_correct_payload_bit",
        "DEFINED",
        None,
        boundary_id,
    )


def mrcc(
    candidate_carbon_kgco2e: float | None,
    baseline_carbon_kgco2e: float | None,
    candidate_correct_services: float | None,
    baseline_correct_services: float | None,
    *,
    boundary_id: str,
) -> MetricResult:
    """Marginal Reliability Carbon Cost against one fixed baseline.

    Negative numerators with positive service improvement are meaningful carbon
    savings.  Non-positive service improvement is classified, not regularized.
    """

    values = (
        candidate_carbon_kgco2e,
        baseline_carbon_kgco2e,
        candidate_correct_services,
        baseline_correct_services,
    )
    if any(value is None for value in values):
        return MetricResult(
            None,
            "kgCO2e_per_additional_correct_service",
            "BLOCKED_MISSING_MATCHED_BASELINE_INPUT",
            "candidate and baseline carbon/service values must all be present",
            boundary_id,
        )
    candidate_carbon = _nonnegative("candidate_carbon", float(values[0]))
    baseline_carbon = _nonnegative("baseline_carbon", float(values[1]))
    candidate_service = _nonnegative("candidate_correct_services", float(values[2]))
    baseline_service = _nonnegative("baseline_correct_services", float(values[3]))
    delta_service = candidate_service - baseline_service
    if delta_service == 0.0:
        return MetricResult(
            None,
            "kgCO2e_per_additional_correct_service",
            "UNDEFINED_ZERO_SERVICE_IMPROVEMENT",
            "Delta N_correct is zero; no epsilon floor is permitted",
            boundary_id,
        )
    if delta_service < 0.0:
        return MetricResult(
            None,
            "kgCO2e_per_additional_correct_service",
            "NOT_AN_INCREMENTAL_RELIABILITY_GAIN",
            "Delta N_correct is negative; use dominance/Pareto classification",
            boundary_id,
        )
    delta_carbon = candidate_carbon - baseline_carbon
    status = "DEFINED"
    if delta_carbon < 0.0:
        status = "DEFINED_CARBON_SAVING_AND_SERVICE_GAIN"
    return MetricResult(
        delta_carbon / delta_service,
        "kgCO2e_per_additional_correct_service",
        status,
        None,
        boundary_id,
    )


@dataclass(frozen=True)
class BoundaryTerm:
    name: str
    value: float | None
    unit: str
    treatment: str

    def __post_init__(self) -> None:
        allowed = {
            "INCLUDED_VALUE",
            "INCLUDED_ZERO",
            "PARAMETRIC",
            "EXCLUDED_BY_BOUNDARY",
            "UNAVAILABLE",
        }
        if self.treatment not in allowed:
            raise ValueError(f"unsupported boundary treatment: {self.treatment}")
        if self.treatment in {"INCLUDED_VALUE", "INCLUDED_ZERO", "PARAMETRIC"}:
            if self.value is None:
                raise ValueError("included terms require a value")
            value = _nonnegative(self.name, self.value)
            if self.treatment == "INCLUDED_ZERO" and value != 0.0:
                raise ValueError("INCLUDED_ZERO requires an explicit zero")
        elif self.value is not None:
            raise ValueError("excluded or unavailable terms must not carry a value")


def lifecycle_carbon(
    boundary_id: str, terms: Sequence[BoundaryTerm]
) -> MetricResult:
    if not boundary_id.strip():
        raise ValueError("boundary_id must be non-empty")
    missing = [term.name for term in terms if term.treatment == "UNAVAILABLE"]
    if missing:
        return MetricResult(
            None,
            "kgCO2e",
            "BLOCKED_INCLUDED_TERM_UNAVAILABLE",
            "unavailable included terms: " + ", ".join(sorted(missing)),
            boundary_id,
        )
    total = sum(
        float(term.value)
        for term in terms
        if term.treatment
        in {"INCLUDED_VALUE", "INCLUDED_ZERO", "PARAMETRIC"}
    )
    status = (
        "PARAMETRIC"
        if any(term.treatment == "PARAMETRIC" for term in terms)
        else "DEFINED"
    )
    return MetricResult(total, "kgCO2e", status, None, boundary_id)


@dataclass(frozen=True)
class ProcessGasUse:
    gas: str
    consumed_mass_kg: float
    effective_release_fraction: float
    abatement_efficiency: float
    gwp100_kgco2e_per_kg: float
    gwp_basis: str

    def __post_init__(self) -> None:
        if not self.gas.strip() or not self.gwp_basis.strip():
            raise ValueError("gas and GWP basis must be declared")
        _nonnegative("consumed_mass_kg", self.consumed_mass_kg)
        _probability("effective_release_fraction", self.effective_release_fraction)
        _probability("abatement_efficiency", self.abatement_efficiency)
        _nonnegative("gwp100_kgco2e_per_kg", self.gwp100_kgco2e_per_kg)

    @property
    def scope1_kgco2e(self) -> float:
        return (
            self.consumed_mass_kg
            * self.effective_release_fraction
            * (1.0 - self.abatement_efficiency)
            * self.gwp100_kgco2e_per_kg
        )


@dataclass(frozen=True)
class ProcessStep:
    step_id: str
    module: str
    electricity_kwh: float
    gases: tuple[ProcessGasUse, ...] = ()
    patterning: bool = False

    def __post_init__(self) -> None:
        if not self.step_id.strip() or not self.module.strip():
            raise ValueError("process step ID and module must be declared")
        _nonnegative("electricity_kwh", self.electricity_kwh)


@dataclass(frozen=True)
class WaferCarbonResult:
    scope1_kgco2e: float
    scope2_kgco2e: float
    upstream_kgco2e: float | None
    total_kgco2e: float | None
    patterning_scope2_diagnostic_kgco2e: float
    status: str
    boundary_id: str


def wafer_carbon(
    steps: Sequence[ProcessStep],
    electricity_ci_kgco2e_per_kwh: float,
    upstream_terms: Sequence[BoundaryTerm],
    *,
    boundary_id: str,
) -> WaferCarbonResult:
    """Bottom-up step sum with disjoint Scope 1, Scope 2, and upstream.

    Patterning Scope 2 is a diagnostic subset of total Scope 2 and is not added
    again.  Duplicate step IDs are rejected to prevent route double counting.
    """

    identifiers = [step.step_id for step in steps]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate process step ID would double count the route")
    ci = _nonnegative("electricity_ci_kgco2e_per_kwh", electricity_ci_kgco2e_per_kwh)
    scope1 = sum(gas.scope1_kgco2e for step in steps for gas in step.gases)
    total_energy = sum(step.electricity_kwh for step in steps)
    scope2 = total_energy * ci
    patterning = sum(step.electricity_kwh for step in steps if step.patterning) * ci
    upstream_result = lifecycle_carbon(boundary_id, upstream_terms)
    if upstream_result.value is None:
        return WaferCarbonResult(
            scope1,
            scope2,
            None,
            None,
            patterning,
            upstream_result.status,
            boundary_id,
        )
    upstream = upstream_result.value
    total = scope1 + scope2 + upstream
    status = "PARAMETRIC" if upstream_result.status == "PARAMETRIC" else "DEFINED"
    return WaferCarbonResult(
        scope1, scope2, upstream, total, patterning, status, boundary_id
    )


def poisson_yield(defect_density_per_cm2: float, die_area_mm2: float) -> float:
    density = _nonnegative("defect_density_per_cm2", defect_density_per_cm2)
    area_cm2 = convert_unit(_positive("die_area_mm2", die_area_mm2), "mm2", "cm2")
    return math.exp(-density * area_cm2)


def negative_binomial_yield(
    defect_density_per_cm2: float, die_area_mm2: float, alpha: float
) -> float:
    density = _nonnegative("defect_density_per_cm2", defect_density_per_cm2)
    area_cm2 = convert_unit(_positive("die_area_mm2", die_area_mm2), "mm2", "cm2")
    clustering = _positive("alpha", alpha)
    return (1.0 + density * area_cm2 / clustering) ** (-clustering)


def murphy_yield(defect_density_per_cm2: float, die_area_mm2: float) -> float:
    density = _nonnegative("defect_density_per_cm2", defect_density_per_cm2)
    area_cm2 = convert_unit(_positive("die_area_mm2", die_area_mm2), "mm2", "cm2")
    defect_area = density * area_cm2
    if defect_area == 0.0:
        return 1.0
    return ((1.0 - math.exp(-defect_area)) / defect_area) ** 2


def yield_fraction(
    model: str,
    defect_density_per_cm2: float | None,
    die_area_mm2: float,
    *,
    alpha: float | None = None,
    measured_yield: float | None = None,
) -> float:
    normalized = model.strip().upper().replace("-", "_")
    if normalized == "MEASURED":
        if measured_yield is None:
            raise ValueError("MEASURED yield requires measured_yield")
        return _probability("measured_yield", measured_yield)
    if defect_density_per_cm2 is None:
        raise ValueError(f"{normalized} yield requires explicit defect density")
    if normalized == "POISSON":
        return poisson_yield(defect_density_per_cm2, die_area_mm2)
    if normalized == "NEGATIVE_BINOMIAL":
        if alpha is None:
            raise ValueError("NEGATIVE_BINOMIAL yield requires alpha")
        return negative_binomial_yield(defect_density_per_cm2, die_area_mm2, alpha)
    if normalized == "MURPHY":
        return murphy_yield(defect_density_per_cm2, die_area_mm2)
    raise ValueError(f"unsupported yield model: {model}")


def gross_dies_per_wafer(wafer_diameter_mm: float, die_area_mm2: float) -> float:
    diameter = _positive("wafer_diameter_mm", wafer_diameter_mm)
    area = _positive("die_area_mm2", die_area_mm2)
    result = math.pi * (diameter / 2.0) ** 2 / area - math.pi * diameter / math.sqrt(
        2.0 * area
    )
    if result <= 0.0:
        raise ValueError("die is too large for the gross-die approximation")
    return result


def good_dies_per_wafer(
    gross_dies: float, die_yield: float, line_yield: float
) -> float:
    result = (
        _positive("gross_dies", gross_dies)
        * _probability("die_yield", die_yield)
        * _probability("line_yield", line_yield)
    )
    if result <= 0.0:
        raise ValueError("good dies must be strictly positive")
    return result


def good_die_carbon(
    wafer_carbon_kgco2e: float,
    good_dies: float,
    *,
    maskset_kgco2e: float | None = None,
    production_wafers: float | None = None,
    package_term: BoundaryTerm,
    other_term: BoundaryTerm,
    boundary_id: str,
) -> MetricResult:
    process = _nonnegative("wafer_carbon_kgco2e", wafer_carbon_kgco2e) / _positive(
        "good_dies", good_dies
    )
    if (maskset_kgco2e is None) != (production_wafers is None):
        raise ValueError("mask carbon and production volume must be supplied together")
    terms = [BoundaryTerm("wafer_process", process, "kgCO2e", "INCLUDED_VALUE")]
    if maskset_kgco2e is None:
        terms.append(BoundaryTerm("mask_NRE", None, "kgCO2e", "EXCLUDED_BY_BOUNDARY"))
    else:
        mask = _nonnegative("maskset_kgco2e", maskset_kgco2e) / (
            _positive("production_wafers", float(production_wafers)) * good_dies
        )
        terms.append(BoundaryTerm("mask_NRE", mask, "kgCO2e", "INCLUDED_VALUE"))
    terms.extend((package_term, other_term))
    return lifecycle_carbon(boundary_id, terms)


@dataclass(frozen=True)
class OperationalWorkload:
    read_count: float
    write_count: float
    correction_count: float
    retry_count: float
    scrub_count: float
    read_energy_j: float
    write_energy_j: float
    correction_incremental_energy_j: float
    retry_incremental_energy_j: float
    scrub_energy_j: float
    idle_power_w: float
    idle_time_s: float
    read_energy_includes_correction: bool = False


def lifetime_energy_j(workload: OperationalWorkload) -> float:
    for field in (
        "read_count",
        "write_count",
        "correction_count",
        "retry_count",
        "scrub_count",
        "read_energy_j",
        "write_energy_j",
        "correction_incremental_energy_j",
        "retry_incremental_energy_j",
        "scrub_energy_j",
        "idle_power_w",
        "idle_time_s",
    ):
        _nonnegative(field, getattr(workload, field))
    if (
        workload.read_energy_includes_correction
        and workload.correction_count > 0.0
        and workload.correction_incremental_energy_j > 0.0
    ):
        raise ValueError("correction energy would be counted twice")
    correction = (
        0.0
        if workload.read_energy_includes_correction
        else workload.correction_count * workload.correction_incremental_energy_j
    )
    return (
        workload.read_count * workload.read_energy_j
        + workload.write_count * workload.write_energy_j
        + correction
        + workload.retry_count * workload.retry_incremental_energy_j
        + workload.scrub_count * workload.scrub_energy_j
        + workload.idle_power_w * workload.idle_time_s
    )


def operational_carbon(
    energy_j: float, use_grid_ci_kgco2e_per_kwh: float
) -> float:
    energy_kwh = convert_unit(_nonnegative("energy_j", energy_j), "J", "kWh")
    return energy_kwh * _nonnegative(
        "use_grid_ci_kgco2e_per_kwh", use_grid_ci_kgco2e_per_kwh
    )


@dataclass(frozen=True)
class EvidenceRequirement:
    quantity_id: str
    min_tier: EvidenceTier
    allowed_result_classes: tuple[str, ...]


@dataclass(frozen=True)
class QualificationRule:
    metric_id: str
    requirements: tuple[EvidenceRequirement, ...]
    permits_parametric: bool = False


@dataclass(frozen=True)
class QualificationResult:
    metric_id: str
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ServiceConstraints:
    """Externally supplied hard service constraints.

    ``None`` means the scenario owner did not declare that constraint; it does
    not mean an unconstrained quantity has passed.
    """

    max_sdc_probability: float | None = None
    max_due_probability: float | None = None
    max_latency_s: float | None = None
    min_throughput_services_per_s: float | None = None

    def __post_init__(self) -> None:
        for name in ("max_sdc_probability", "max_due_probability"):
            value = getattr(self, name)
            if value is not None:
                _probability(name, value)
        if self.max_latency_s is not None:
            _nonnegative("max_latency_s", self.max_latency_s)
        if self.min_throughput_services_per_s is not None:
            _nonnegative(
                "min_throughput_services_per_s",
                self.min_throughput_services_per_s,
            )


@dataclass(frozen=True)
class FeasibilityResult:
    status: str
    feasible: bool | None
    violations: tuple[str, ...]


def evaluate_feasibility(
    *,
    constraints: ServiceConstraints | None,
    sdc_probability: float | None,
    due_probability: float | None,
    latency_s: float | None,
    throughput_services_per_s: float | None,
) -> FeasibilityResult:
    """Apply only declared SDC/DUE/latency/throughput constraints."""

    if constraints is None:
        return FeasibilityResult("NO_DECLARED_CONSTRAINTS", None, ())
    violations: list[str] = []
    checks = (
        (
            "SDC",
            constraints.max_sdc_probability,
            sdc_probability,
            lambda value, threshold: value <= threshold,
        ),
        (
            "DUE",
            constraints.max_due_probability,
            due_probability,
            lambda value, threshold: value <= threshold,
        ),
        (
            "LATENCY",
            constraints.max_latency_s,
            latency_s,
            lambda value, threshold: value <= threshold,
        ),
        (
            "THROUGHPUT",
            constraints.min_throughput_services_per_s,
            throughput_services_per_s,
            lambda value, threshold: value >= threshold,
        ),
    )
    for name, threshold, value, predicate in checks:
        if threshold is None:
            continue
        if value is None:
            violations.append(f"{name}_MISSING")
            continue
        number = _nonnegative(name, value)
        if name in {"SDC", "DUE"}:
            _probability(name, number)
        if not predicate(number, threshold):
            violations.append(f"{name}_CONSTRAINT")
    return FeasibilityResult(
        "FEASIBLE" if not violations else "INFEASIBLE",
        not violations,
        tuple(violations),
    )


def qualify(
    rule: QualificationRule, records: Mapping[str, EvidenceRecord]
) -> QualificationResult:
    reasons: list[str] = []
    parametric = False
    for requirement in rule.requirements:
        record = records.get(requirement.quantity_id)
        if record is None:
            reasons.append(f"{requirement.quantity_id}:MISSING_RECORD")
            continue
        if record.tier < requirement.min_tier:
            reasons.append(
                f"{requirement.quantity_id}:TIER_{record.tier.name}_BELOW_{requirement.min_tier.name}"
            )
        if record.result_class not in requirement.allowed_result_classes:
            reasons.append(
                f"{requirement.quantity_id}:CLASS_{record.result_class}_NOT_ALLOWED"
            )
        if record.result_class == "PARAMETRIC":
            parametric = True
    if reasons:
        return QualificationResult(rule.metric_id, "BLOCKED", tuple(reasons))
    if parametric and not rule.permits_parametric:
        return QualificationResult(
            rule.metric_id,
            "BLOCKED",
            ("PARAMETRIC_INPUT_NOT_PERMITTED",),
        )
    return QualificationResult(
        rule.metric_id,
        "PARAMETRIC" if parametric else "QUALIFIED",
        (),
    )


@dataclass(frozen=True)
class Objective:
    field: str
    direction: str

    def __post_init__(self) -> None:
        if self.direction not in {"min", "max"}:
            raise ValueError("objective direction must be min or max")


def exact_pareto_indices(
    rows: Sequence[Mapping[str, float]], objectives: Sequence[Objective]
) -> list[int]:
    if not objectives:
        raise ValueError("at least one objective is required")

    def dominates(left: Mapping[str, float], right: Mapping[str, float]) -> bool:
        no_worse = True
        strict = False
        for objective in objectives:
            left_value = _finite(objective.field, left[objective.field])
            right_value = _finite(objective.field, right[objective.field])
            if objective.direction == "min":
                no_worse = no_worse and left_value <= right_value
                strict = strict or left_value < right_value
            else:
                no_worse = no_worse and left_value >= right_value
                strict = strict or left_value > right_value
        return no_worse and strict

    return [
        index
        for index, row in enumerate(rows)
        if not any(
            dominates(other, row)
            for other_index, other in enumerate(rows)
            if other_index != index
        )
    ]


@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float
    uncertainty_kind: str

    def __post_init__(self) -> None:
        low = _finite("lower", self.lower)
        high = _finite("upper", self.upper)
        if low > high:
            raise ValueError("interval lower bound exceeds upper bound")
        if self.uncertainty_kind not in {"EPISTEMIC", "ALEATORY", "MIXED"}:
            raise ValueError("uncertainty kind must be explicit")


def scenario_envelope(values: Iterable[float]) -> Interval:
    samples = [_finite("scenario", value) for value in values]
    if not samples:
        raise ValueError("scenario envelope requires values")
    return Interval(min(samples), max(samples), "EPISTEMIC")


def latin_hypercube(
    bounds: Mapping[str, tuple[float, float]], sample_count: int, seed: int
) -> list[dict[str, float]]:
    """Deterministic stratified scenarios; not a confidence interval."""

    if isinstance(sample_count, bool) or sample_count <= 0:
        raise ValueError("sample_count must be a positive integer")
    rng = random.Random(seed)
    columns: dict[str, list[float]] = {}
    for name in sorted(bounds):
        low, high = bounds[name]
        low = _finite(f"{name}.lower", low)
        high = _finite(f"{name}.upper", high)
        if low > high:
            raise ValueError(f"invalid bounds for {name}")
        unit_samples = [(index + rng.random()) / sample_count for index in range(sample_count)]
        rng.shuffle(unit_samples)
        columns[name] = [low + sample * (high - low) for sample in unit_samples]
    return [
        {name: columns[name][index] for name in sorted(columns)}
        for index in range(sample_count)
    ]


@dataclass(frozen=True)
class BoundarySignature:
    boundary_id: str
    technology: str
    wafer_diameter_mm: float | None
    lifecycle_stage: str
    package_included: bool
    mask_nre_included: bool
    upstream_scope3: str


def boundary_mismatches(
    left: BoundarySignature, right: BoundarySignature
) -> tuple[str, ...]:
    fields = (
        "technology",
        "wafer_diameter_mm",
        "lifecycle_stage",
        "package_included",
        "mask_nre_included",
        "upstream_scope3",
    )
    return tuple(field for field in fields if getattr(left, field) != getattr(right, field))


def validate_coefficient_transfer(
    source_technology: str, target_technology: str, allowed_use: str
) -> None:
    """Reject unsupported advanced-node-to-SKY130 numerical translation."""

    if (
        target_technology.upper() == "SKY130"
        and source_technology.upper() != "SKY130"
        and allowed_use.upper() not in {"TREND_ONLY", "QUALITATIVE_ONLY"}
    ):
        raise ValueError("ADVANCED_NODE_COEFFICIENT_NOT_TRANSFERABLE_TO_SKY130")


def physical_outcome_probability(
    conditional_outcomes: Mapping[str, float], fault_probabilities: Mapping[str, float]
) -> float:
    """Apply the law of total probability without inventing event weights."""

    if set(conditional_outcomes) != set(fault_probabilities):
        raise ValueError("fault topology domains must match")
    total_fault_probability = sum(
        _probability(name, value) for name, value in fault_probabilities.items()
    )
    if not math.isclose(total_fault_probability, 1.0, abs_tol=1e-12, rel_tol=0.0):
        raise ValueError("physical fault probabilities must sum to one")
    return sum(
        _probability(f"P(outcome|{fault})", conditional_outcomes[fault])
        * fault_probabilities[fault]
        for fault in conditional_outcomes
    )


__all__ = [
    "BoundarySignature",
    "BoundaryTerm",
    "EvidenceRecord",
    "EvidenceRequirement",
    "EvidenceTier",
    "FeasibilityResult",
    "Interval",
    "MetricResult",
    "Objective",
    "OperationalWorkload",
    "ProcessGasUse",
    "ProcessStep",
    "QualificationResult",
    "QualificationRule",
    "ServiceConstraints",
    "WaferCarbonResult",
    "boundary_mismatches",
    "convert_unit",
    "correct_service_count",
    "csci",
    "csci_bit",
    "exact_pareto_indices",
    "evaluate_feasibility",
    "good_die_carbon",
    "good_dies_per_wafer",
    "gross_dies_per_wafer",
    "latin_hypercube",
    "lifecycle_carbon",
    "lifetime_energy_j",
    "mrcc",
    "murphy_yield",
    "negative_binomial_yield",
    "operational_carbon",
    "physical_outcome_probability",
    "poisson_yield",
    "qualify",
    "scenario_envelope",
    "validate_coefficient_transfer",
    "wafer_carbon",
    "yield_fraction",
]
