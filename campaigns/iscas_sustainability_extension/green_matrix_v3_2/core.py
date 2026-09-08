"""Executable scientific semantics for GREEN Matrix v3.2.

The module separates physical event occurrence, conditional architecture
response, implementation/resource consequence, and lifecycle consequence.
Functions fail closed: absent, diagnostic, mismatched, or scenario evidence is
never coerced into an absolute physical quantity.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Iterable, Mapping, Sequence


EVIDENCE_TIERS = ("E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7")
SEMANTIC_STATUSES = frozenset(
    {
        "MEASURED",
        "DERIVED",
        "ANALYTICAL",
        "LITERATURE_NATIVE",
        "CONDITIONAL",
        "DIAGNOSTIC",
        "SCENARIO_ASSUMPTION",
        "STRUCTURALLY_MISSING",
        "BLOCKED",
    }
)
UNCERTAINTY_FORMS = frozenset(
    {
        "exact",
        "measured_distribution",
        "interval",
        "literature_native",
        "diagnostic",
        "conditional",
        "unknown",
        "structurally_missing",
        "blocked",
    }
)
DECISION_STATES = frozenset({"QUALIFIED", "CONDITIONAL", "DIAGNOSTIC", "BLOCKED"})
PHYSICAL_EVENT_RATE_FORBIDDEN_SOURCE_KINDS = frozenset(
    {
        "LOGICAL_INJECTION_FREQUENCY",
        "ENUMERATED_MASK_FREQUENCY",
        "SCENARIO_ASSUMPTION",
        "LITERATURE_TECHNOLOGY_MISMATCH",
        "DIAGNOSTIC",
    }
)
FORBIDDEN_IMEC_CLAIMS = (
    "imec compliant",
    "imec certification",
    "imec certified",
    "imec validated",
    "imec standard",
    "imec-approved",
    "sky130 carbon from imec",
)


class GuardViolation(ValueError):
    """Raised when a requested inference violates a scientific guard."""


def _finite(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise GuardViolation(f"{name} must be finite")
    return number


def _nonnegative(name: str, value: float) -> float:
    number = _finite(name, value)
    if number < 0:
        raise GuardViolation(f"{name} must be non-negative")
    return number


def tier_at_least(actual: str, minimum: str) -> bool:
    if actual not in EVIDENCE_TIERS or minimum not in EVIDENCE_TIERS:
        raise GuardViolation("evidence tier must be one of E0..E7")
    return EVIDENCE_TIERS.index(actual) >= EVIDENCE_TIERS.index(minimum)


@dataclass(frozen=True)
class GreenVector:
    """Evidence-aware architecture/scenario vector; no default scalar score."""

    reliability_consequence: Any
    operational_resource_consequence: Any
    physical_implementation_cost: Any
    environmental_lifecycle_consequence: Any
    evidence_quality: Any

    def as_dict(self) -> dict[str, Any]:
        return {
            "R_reliability_consequence": self.reliability_consequence,
            "E_operational_resource_consequence": self.operational_resource_consequence,
            "P_physical_implementation_cost": self.physical_implementation_cost,
            "C_environmental_lifecycle_consequence": self.environmental_lifecycle_consequence,
            "Q_evidence_quality": self.evidence_quality,
        }


@dataclass(frozen=True)
class Objective:
    metric: str
    direction: str
    units: str

    def __post_init__(self) -> None:
        if self.direction not in {"min", "max"}:
            raise GuardViolation("objective direction must be 'min' or 'max'")
        if not self.metric or not self.units:
            raise GuardViolation("objective metric and units are required")


@dataclass(frozen=True)
class ActivityCompleteness:
    """Inputs required to qualify a matched post-route result at E5."""

    annotation_coverage_fraction: float
    unannotated_instance_pin_count: int
    unmatched_activity_object_count: int
    default_activity_used: bool
    postroute_gate_level_activity: bool
    macro_internal_activity_characterized: bool
    whole_service_boundary_covered: bool
    operation_window_isolated: bool
    duration_s: float
    operation_count: int
    clock_period_s: float
    workload_hash: str
    activity_hash: str
    implementation_hash: str
    netlist_hash: str
    configuration_hash: str
    constraint_hash: str
    power_report_hash: str


def qualify_e5_activity(activity: ActivityCompleteness) -> dict[str, Any]:
    """Apply the explicit all-of E5 activity-completeness criterion."""

    reasons: list[str] = []
    coverage = _finite("annotation_coverage_fraction", activity.annotation_coverage_fraction)
    if not math.isclose(coverage, 1.0, rel_tol=0.0, abs_tol=1e-12):
        reasons.append("ANNOTATION_COVERAGE_NOT_100_PERCENT")
    if activity.unannotated_instance_pin_count != 0:
        reasons.append("UNANNOTATED_INSTANCE_PINS_PRESENT")
    if activity.unmatched_activity_object_count != 0:
        reasons.append("UNMATCHED_ACTIVITY_OBJECTS_PRESENT")
    if activity.default_activity_used:
        reasons.append("DEFAULT_ACTIVITY_USED")
    if not activity.postroute_gate_level_activity:
        reasons.append("POSTROUTE_GATE_LEVEL_ACTIVITY_ABSENT")
    if not activity.macro_internal_activity_characterized:
        reasons.append("MACRO_INTERNAL_ACTIVITY_NOT_CHARACTERIZED")
    if not activity.whole_service_boundary_covered:
        reasons.append("WHOLE_SERVICE_BOUNDARY_NOT_COVERED")
    if not activity.operation_window_isolated:
        reasons.append("OPERATION_WINDOW_NOT_ISOLATED")
    if activity.duration_s <= 0:
        reasons.append("NONPOSITIVE_ACTIVITY_WINDOW")
    if isinstance(activity.operation_count, bool) or activity.operation_count <= 0:
        reasons.append("NO_COUNTED_OPERATIONS")
    if activity.clock_period_s <= 0:
        reasons.append("CLOCK_PERIOD_NOT_DECLARED")
    hashes = {
        "WORKLOAD_HASH": activity.workload_hash,
        "ACTIVITY_HASH": activity.activity_hash,
        "IMPLEMENTATION_HASH": activity.implementation_hash,
        "NETLIST_HASH": activity.netlist_hash,
        "CONFIGURATION_HASH": activity.configuration_hash,
        "CONSTRAINT_HASH": activity.constraint_hash,
        "POWER_REPORT_HASH": activity.power_report_hash,
    }
    reasons.extend(f"{name}_MISSING" for name, value in hashes.items() if not value.strip())
    return {
        "qualified": not reasons,
        "evidence_tier": "E5" if not reasons else "E4",
        "qualification_status": "QUALIFIED" if not reasons else "DIAGNOSTIC",
        "reasons": reasons,
    }


def validate_physical_event_rate_evidence(record: Mapping[str, Any]) -> None:
    """Require matched absolute evidence before treating a value as an event rate."""

    if record.get("value") is None:
        raise GuardViolation("PHYSICAL_EVENT_RATE_BLOCKED: value is unavailable")
    source_kind = str(record.get("source_kind", ""))
    if source_kind in PHYSICAL_EVENT_RATE_FORBIDDEN_SOURCE_KINDS:
        raise GuardViolation(f"PHYSICAL_EVENT_RATE_BLOCKED: forbidden source {source_kind}")
    if record.get("semantic_status") != "MEASURED":
        raise GuardViolation("PHYSICAL_EVENT_RATE_BLOCKED: matched measured evidence required")
    if record.get("qualification_status") != "ABSOLUTE_QUALIFIED":
        raise GuardViolation("PHYSICAL_EVENT_RATE_BLOCKED: absolute qualification required")
    if not tier_at_least(str(record.get("evidence_tier", "E0")), "E2"):
        raise GuardViolation("PHYSICAL_EVENT_RATE_BLOCKED: evidence below E2")
    compatibility = record.get("compatibility", {})
    required = ("technology", "process", "pvt", "geometry", "environment")
    mismatched = [name for name in required if compatibility.get(name) is not True]
    if mismatched:
        raise GuardViolation(
            "PHYSICAL_EVENT_RATE_BLOCKED: incompatible " + ",".join(sorted(mismatched))
        )


def conditional_outcome_rate_per_hour(
    event_rate_record: Mapping[str, Any], conditional_probability: float
) -> float:
    validate_physical_event_rate_evidence(event_rate_record)
    probability = _nonnegative("conditional_probability", conditional_probability)
    if probability > 1:
        raise GuardViolation("conditional_probability must not exceed one")
    return _nonnegative("event_rate_per_hour", event_rate_record["value"]) * probability


def fit_from_event_rate(
    event_rate_record: Mapping[str, Any], conditional_failure_probability: float
) -> float:
    """Return failures per billion hours only after the physical-rate guard passes."""

    return conditional_outcome_rate_per_hour(
        event_rate_record, conditional_failure_probability
    ) * 1.0e9


def validate_literature_numeric_transfer(
    *, source_technology: str, target_technology: str, numeric_transfer: bool
) -> None:
    if numeric_transfer and source_technology.strip().casefold() != target_technology.strip().casefold():
        raise GuardViolation("LITERATURE_NUMERIC_TRANSFER_TO_SKY130_FORBIDDEN")


def validate_throughput_claim(*, label: str, saturated_measurement_present: bool) -> None:
    if label == "MAXIMUM_SUSTAINABLE_THROUGHPUT" and not saturated_measurement_present:
        raise GuardViolation("maximum sustainable throughput requires an independent saturation test")


def validate_interleaver_reliability_claim(
    *, physically_implemented: bool, physical_logical_mapping_complete: bool
) -> None:
    if not physically_implemented or not physical_logical_mapping_complete:
        raise GuardViolation(
            "interleaver reliability benefit requires routed implementation and complete physical/logical mapping"
        )


def validate_manufacturing_label(*, label: str, technology_matched_inventory: bool) -> None:
    if label == "SKY130_MANUFACTURING_CARBON" and not technology_matched_inventory:
        raise GuardViolation("reference manufacturing scenario cannot be relabelled as SKY130 carbon")


def validate_scenario_semantics(*, semantic_status: str, promoted_to_evidence: bool) -> None:
    if semantic_status == "SCENARIO_ASSUMPTION" and promoted_to_evidence:
        raise GuardViolation("scenario assumptions are not measured evidence")


def require_numeric(value: Any, *, metric: str) -> float:
    if value is None or value == "" or isinstance(value, bool):
        raise GuardViolation(f"{metric} is UNKNOWN/BLOCKED and cannot be treated as zero")
    return _finite(metric, value)


def validate_imec_language(text: str) -> None:
    lowered = re.sub(r"\s+", " ", text.casefold())
    for phrase in FORBIDDEN_IMEC_CLAIMS:
        if phrase in lowered:
            raise GuardViolation(f"forbidden imec claim: {phrase}")


def exact_pareto_ids(
    records: Sequence[Mapping[str, Any]], objectives: Sequence[Objective]
) -> list[str]:
    """Exact deterministic Pareto enumeration over the declared full metric set."""

    if not records or not objectives:
        raise GuardViolation("Pareto enumeration requires records and declared objectives")
    ids: list[str] = []
    vectors: list[tuple[float, ...]] = []
    for record in records:
        record_id = str(record.get("architecture_id", record.get("id", "")))
        if not record_id:
            raise GuardViolation("Pareto record requires an architecture_id or id")
        values: list[float] = []
        for objective in objectives:
            if objective.metric not in record:
                raise GuardViolation(
                    f"blocked metric {objective.metric} may not be silently discarded"
                )
            value = require_numeric(record[objective.metric], metric=objective.metric)
            values.append(value if objective.direction == "min" else -value)
        ids.append(record_id)
        vectors.append(tuple(values))
    front: list[str] = []
    for index, candidate in enumerate(vectors):
        dominated = False
        for other_index, other in enumerate(vectors):
            if index == other_index:
                continue
            if all(left <= right for left, right in zip(other, candidate)) and any(
                left < right for left, right in zip(other, candidate)
            ):
                dominated = True
                break
        if not dominated:
            front.append(ids[index])
    return front


def decision_admissibility(
    *,
    architecture: str,
    scenario: str,
    metric_records: Mapping[str, Mapping[str, Any]],
    mandatory_metrics: Sequence[str],
    target_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Return eligibility and a complete blocking set, not only a Boolean."""

    blocking: list[str] = []
    for metric in mandatory_metrics:
        record = metric_records.get(metric)
        if record is None:
            blocking.append(f"{metric}:MISSING_RECORD")
            continue
        if record.get("value") is None or record.get("semantic_status") in {
            "STRUCTURALLY_MISSING",
            "BLOCKED",
        }:
            blocking.append(f"{metric}:BLOCKED")
            continue
        if record.get("qualification_status") != "QUALIFIED":
            blocking.append(f"{metric}:NOT_QUALIFIED")
            continue
        compatibility = record.get("compatibility", {})
        for field in record.get("required_compatibility_fields", []):
            if compatibility.get(field) is not True:
                blocking.append(f"{metric}:{field.upper()}_MISMATCH")
        record_boundary = record.get("measurement_boundary")
        required_boundary = target_context.get("measurement_boundary")
        if required_boundary and record_boundary != required_boundary:
            blocking.append(f"{metric}:BOUNDARY_MISMATCH")
    blocking = sorted(set(blocking))
    return {
        "architecture": architecture,
        "scenario": scenario,
        "qualified": not blocking,
        "status": "QUALIFIED" if not blocking else "BLOCKED",
        "blocking_metrics": blocking,
    }


def qualified_pareto_or_blocked(
    *,
    records: Sequence[Mapping[str, Any]],
    objectives: Sequence[Objective],
    admissibility: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    blocked = [row for row in admissibility if not row.get("qualified")]
    if blocked:
        return {
            "status": "BLOCKED",
            "front_classification": "QUALIFIED_FRONT_BLOCKED",
            "front": [],
            "blocking_sets": {
                str(row["architecture"]): row["blocking_metrics"] for row in blocked
            },
        }
    return {
        "status": "QUALIFIED",
        "front_classification": "QUALIFIED_FRONT",
        "front": exact_pareto_ids(records, objectives),
        "blocking_sets": {},
    }


def scenario_space_nondominance_fraction(
    architecture: str, scenario_fronts: Mapping[str, Sequence[str]]
) -> float:
    if not scenario_fronts:
        raise GuardViolation("declared scenario space must not be empty")
    present = sum(architecture in front for front in scenario_fronts.values())
    return present / len(scenario_fronts)


def diagnostic_scalarization(
    record: Mapping[str, Any],
    *,
    weights: Mapping[str, float],
    normalizers: Mapping[str, tuple[float, float]],
    directions: Mapping[str, str],
    qualified: bool,
) -> dict[str, Any]:
    """Optional transparent scalarization that can never override qualification."""

    if set(weights) != set(normalizers) or set(weights) != set(directions):
        raise GuardViolation("weights, normalizers, and directions must declare the same metrics")
    if not math.isclose(math.fsum(weights.values()), 1.0, abs_tol=1e-12):
        raise GuardViolation("scalarization weights must sum to one")
    score = 0.0
    for metric in sorted(weights):
        value = require_numeric(record.get(metric), metric=metric)
        lower, upper = normalizers[metric]
        if upper <= lower:
            raise GuardViolation(f"normalization interval invalid for {metric}")
        normalized = (value - lower) / (upper - lower)
        direction = directions[metric]
        if direction == "max":
            normalized = 1.0 - normalized
        elif direction != "min":
            raise GuardViolation("metric direction must be min or max")
        score += weights[metric] * normalized
    return {
        "score": score,
        "status": "QUALIFIED" if qualified else "DIAGNOSTIC",
        "winner_eligible": bool(qualified),
        "weights": dict(weights),
        "normalizers": {key: list(value) for key, value in normalizers.items()},
        "directions": dict(directions),
    }


def csci_kgco2e_per_correct_service(
    lifecycle_carbon_kgco2e: Any, correct_service_count: Any
) -> float:
    """Auditable CSCI equation; unavailable operands remain a guard failure."""

    carbon = require_numeric(lifecycle_carbon_kgco2e, metric="LIFECYCLE_CARBON")
    services = require_numeric(correct_service_count, metric="CORRECT_SERVICE_COUNT")
    if services <= 0:
        raise GuardViolation("CORRECT_SERVICE_COUNT must be strictly positive")
    return carbon / services


def mrcc_kgco2e_per_additional_correct_service(
    delta_lifecycle_carbon_kgco2e: Any, delta_correct_service_count: Any
) -> float:
    """Auditable MRCC equation; availability is separate from formula validity."""

    carbon = require_numeric(delta_lifecycle_carbon_kgco2e, metric="DELTA_LIFECYCLE_CARBON")
    services = require_numeric(delta_correct_service_count, metric="DELTA_CORRECT_SERVICE_COUNT")
    if services <= 0:
        raise GuardViolation("DELTA_CORRECT_SERVICE_COUNT must be strictly positive")
    return carbon / services
