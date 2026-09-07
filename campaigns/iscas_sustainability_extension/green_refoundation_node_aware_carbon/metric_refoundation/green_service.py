"""Functional-unit GREEN service metrics.

This module is additive and intentionally independent of the legacy selector.
It contains no percentile normalization, preference weights, or implicit
reliability/SLA thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence


_PROBABILITY_TOLERANCE = 1e-12


def _finite_nonnegative(name: str, value: float) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return numeric


@dataclass(frozen=True)
class ServiceOutcomes:
    """Mutually exclusive transaction-outcome probabilities.

    A detected error recovered inside the declared service policy belongs in
    ``success_after_retry``.  Only an unrecovered detected failure belongs in
    ``detected_failure``.  A correction that violates an external SLA belongs
    in ``timeout_or_sla_failure``, not ``success_corrected``.
    """

    success_normal: float
    success_corrected: float
    success_after_retry: float
    detected_failure: float
    silent_data_corruption: float
    timeout_or_sla_failure: float = 0.0

    def __post_init__(self) -> None:
        values = self.as_dict()
        for name, value in values.items():
            _finite_nonnegative(name, value)
        total = sum(values.values())
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=_PROBABILITY_TOLERANCE):
            raise ValueError(f"service outcome probabilities must sum to 1, got {total!r}")

    def as_dict(self) -> dict[str, float]:
        return {
            "success_normal": float(self.success_normal),
            "success_corrected": float(self.success_corrected),
            "success_after_retry": float(self.success_after_retry),
            "detected_failure": float(self.detected_failure),
            "silent_data_corruption": float(self.silent_data_corruption),
            "timeout_or_sla_failure": float(self.timeout_or_sla_failure),
        }

    @property
    def service_success_probability(self) -> float:
        return self.success_normal + self.success_corrected + self.success_after_retry

    @property
    def unrecovered_due_probability(self) -> float:
        return self.detected_failure

    @property
    def sdc_probability(self) -> float:
        return self.silent_data_corruption


@dataclass(frozen=True)
class FeasibilityThresholds:
    """Externally justified thresholds; ``None`` means no threshold exists."""

    max_sdc_probability: float | None = None
    max_unrecovered_due_probability: float | None = None
    max_latency_ns: float | None = None
    require_physical_feasibility: bool = True

    def __post_init__(self) -> None:
        for name in (
            "max_sdc_probability",
            "max_unrecovered_due_probability",
            "max_latency_ns",
        ):
            value = getattr(self, name)
            if value is not None:
                _finite_nonnegative(name, value)


def useful_service_bits(
    payload_bits_per_transaction: int,
    transaction_count: int,
    outcomes: ServiceOutcomes,
) -> float:
    """Return expected correct useful payload bits delivered."""
    if isinstance(payload_bits_per_transaction, bool) or payload_bits_per_transaction <= 0:
        raise ValueError("payload_bits_per_transaction must be a positive integer")
    if isinstance(transaction_count, bool) or transaction_count < 0:
        raise ValueError("transaction_count must be a non-negative integer")
    if not isinstance(payload_bits_per_transaction, int) or not isinstance(transaction_count, int):
        raise TypeError("payload bits and transaction count must be integers")
    return (
        float(payload_bits_per_transaction)
        * float(transaction_count)
        * outcomes.service_success_probability
    )


def lifecycle_carbon_kgco2e(
    embodied_kgco2e: float,
    operational_kgco2e: float,
    recovery_or_replacement_kgco2e: float = 0.0,
) -> float:
    """Sum disjoint lifecycle-carbon terms.

    Retry, scrub, and local recovery energy belong in operational carbon and
    must not also be passed as recovery/replacement carbon.
    """
    return sum(
        _finite_nonnegative(name, value)
        for name, value in (
            ("embodied_kgco2e", embodied_kgco2e),
            ("operational_kgco2e", operational_kgco2e),
            ("recovery_or_replacement_kgco2e", recovery_or_replacement_kgco2e),
        )
    )


def gse(useful_service_bits_value: float, lifecycle_carbon_kgco2e_value: float) -> float:
    """GREEN Service Efficiency in correct useful payload bits/kgCO2e."""
    service = _finite_nonnegative("useful_service_bits", useful_service_bits_value)
    carbon = float(lifecycle_carbon_kgco2e_value)
    if not math.isfinite(carbon) or carbon <= 0.0:
        raise ValueError("lifecycle_carbon_kgco2e must be finite and strictly positive")
    result = service / carbon
    if not math.isfinite(result):
        raise OverflowError(
            "GSE exceeds the finite float range; rescale service or carbon units"
        )
    return result


def gci(useful_service_bits_value: float, lifecycle_carbon_kgco2e_value: float) -> float:
    """GREEN Carbon Intensity in kgCO2e/correct useful payload bit."""
    service = float(useful_service_bits_value)
    if not math.isfinite(service) or service <= 0.0:
        raise ValueError("useful_service_bits must be finite and strictly positive")
    carbon = _finite_nonnegative("lifecycle_carbon_kgco2e", lifecycle_carbon_kgco2e_value)
    result = carbon / service
    if not math.isfinite(result):
        raise OverflowError(
            "GCI exceeds the finite float range; rescale service or carbon units"
        )
    return result


def gse_relative(
    candidate_service_bits: float,
    candidate_carbon_kgco2e: float,
    baseline_service_bits: float,
    baseline_carbon_kgco2e: float,
) -> float:
    """Return candidate GSE divided by the matched U0 baseline GSE."""
    baseline = gse(baseline_service_bits, baseline_carbon_kgco2e)
    if baseline <= 0.0:
        raise ValueError("baseline GSE must be strictly positive")
    return gse(candidate_service_bits, candidate_carbon_kgco2e) / baseline


def matched_gse_relative(
    candidate_success_probability: float,
    candidate_carbon_kgco2e: float,
    baseline_success_probability: float,
    baseline_carbon_kgco2e: float,
) -> float:
    """Matched-B,N form: (Q_c/Q_U0)*(C_U0/C_c)."""
    q_candidate = _finite_nonnegative(
        "candidate_success_probability", candidate_success_probability
    )
    q_baseline = float(baseline_success_probability)
    if not math.isfinite(q_baseline) or q_baseline <= 0.0:
        raise ValueError("baseline_success_probability must be strictly positive")
    c_candidate = float(candidate_carbon_kgco2e)
    c_baseline = float(baseline_carbon_kgco2e)
    if not math.isfinite(c_candidate) or c_candidate <= 0.0:
        raise ValueError("candidate_carbon_kgco2e must be strictly positive")
    if not math.isfinite(c_baseline) or c_baseline <= 0.0:
        raise ValueError("baseline_carbon_kgco2e must be strictly positive")
    result = (q_candidate / q_baseline) * (c_baseline / c_candidate)
    if not math.isfinite(result):
        raise OverflowError(
            "relative GSE exceeds the finite float range; rescale carbon units"
        )
    return result


def evaluate_feasibility(
    outcomes: ServiceOutcomes,
    *,
    thresholds: FeasibilityThresholds | None,
    latency_ns: float | None,
    physical_feasible: bool | None,
) -> dict[str, object]:
    """Evaluate only declared constraints and expose unconstrained axes."""
    if latency_ns is not None:
        _finite_nonnegative("latency_ns", latency_ns)
    if thresholds is None:
        return {
            "status": "NO_DEFENSIBLE_THRESHOLDS_PARETO_REQUIRED",
            "feasible": None,
            "violations": [],
            "pareto_dimensions": ["GCI", "SDC", "DUE", "latency"],
        }
    violations: list[str] = []
    if (
        thresholds.max_sdc_probability is not None
        and outcomes.sdc_probability > thresholds.max_sdc_probability
    ):
        violations.append("SDC_THRESHOLD")
    if (
        thresholds.max_unrecovered_due_probability is not None
        and outcomes.unrecovered_due_probability
        > thresholds.max_unrecovered_due_probability
    ):
        violations.append("DUE_THRESHOLD")
    if thresholds.max_latency_ns is not None:
        if latency_ns is None:
            violations.append("LATENCY_NOT_MEASURED")
        elif latency_ns > thresholds.max_latency_ns:
            violations.append("LATENCY_THRESHOLD")
    if thresholds.require_physical_feasibility and physical_feasible is not True:
        violations.append("PHYSICAL_FEASIBILITY")
    return {
        "status": "FEASIBLE" if not violations else "INFEASIBLE",
        "feasible": not violations,
        "violations": violations,
        "pareto_dimensions": [],
    }


def dominates_service_carbon(
    service_a: float,
    carbon_a: float,
    service_b: float,
    carbon_b: float,
) -> bool:
    """Whether A weakly improves service/carbon with at least one strict gain."""
    sa = _finite_nonnegative("service_a", service_a)
    sb = _finite_nonnegative("service_b", service_b)
    ca = _finite_nonnegative("carbon_a", carbon_a)
    cb = _finite_nonnegative("carbon_b", carbon_b)
    return sa >= sb and ca <= cb and (sa > sb or ca < cb)


def quantile(values: Sequence[float], probability: float) -> float:
    """Deterministic linear-interpolation quantile."""
    if not values:
        raise ValueError("values must not be empty")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0,1]")
    ordered = sorted(_finite_nonnegative("sample", value) for value in values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def summarize_gse_samples(samples: Iterable[float]) -> dict[str, float]:
    """Return transparent risk summaries without selecting one implicitly."""
    values = [_finite_nonnegative("GSE sample", value) for value in samples]
    if not values:
        raise ValueError("GSE samples must not be empty")
    return {
        "mean": sum(values) / len(values),
        "median": quantile(values, 0.5),
        "p05": quantile(values, 0.05),
        "p95": quantile(values, 0.95),
        "worst_case_interval_lower": min(values),
        "worst_case_interval_upper": max(values),
    }


def exact_pareto_indices(
    rows: Sequence[Mapping[str, float]],
    *,
    maximize: Sequence[str],
    minimize: Sequence[str],
) -> list[int]:
    """Return exact deterministic non-dominated row indices."""
    if set(maximize) & set(minimize):
        raise ValueError("an objective cannot be both maximized and minimized")

    def dominates(left: Mapping[str, float], right: Mapping[str, float]) -> bool:
        no_worse = True
        strict = False
        for key in maximize:
            lv, rv = float(left[key]), float(right[key])
            no_worse = no_worse and lv >= rv
            strict = strict or lv > rv
        for key in minimize:
            lv, rv = float(left[key]), float(right[key])
            no_worse = no_worse and lv <= rv
            strict = strict or lv < rv
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


__all__ = [
    "FeasibilityThresholds",
    "ServiceOutcomes",
    "dominates_service_carbon",
    "evaluate_feasibility",
    "exact_pareto_indices",
    "gci",
    "gse",
    "gse_relative",
    "lifecycle_carbon_kgco2e",
    "matched_gse_relative",
    "quantile",
    "summarize_gse_samples",
    "useful_service_bits",
]
