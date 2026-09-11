"""Map transaction observations to the GREEN useful-service outcome space."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable


class ServiceOutcome(str, Enum):
    SUCCESS_NORMAL = "SUCCESS_NORMAL"
    SUCCESS_CORRECTED = "SUCCESS_CORRECTED"
    SUCCESS_AFTER_RETRY = "SUCCESS_AFTER_RETRY"
    DETECTED_FAILURE = "DETECTED_FAILURE"
    SILENT_DATA_CORRUPTION = "SILENT_DATA_CORRUPTION"
    TIMEOUT_OR_SLA_FAILURE = "TIMEOUT_OR_SLA_FAILURE"


_SUCCESS = {
    ServiceOutcome.SUCCESS_NORMAL,
    ServiceOutcome.SUCCESS_CORRECTED,
    ServiceOutcome.SUCCESS_AFTER_RETRY,
}


@dataclass(frozen=True)
class TransactionObservation:
    """Final externally visible state for one requested transaction."""

    delivered: bool
    payload_correct: bool
    correction_applied: bool = False
    due_detected: bool = False
    failure_detected: bool = False
    retry_count: int = 0
    latency_ns: float | None = None
    timed_out: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.retry_count, bool) or not isinstance(self.retry_count, int):
            raise TypeError("retry_count must be an integer")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if self.latency_ns is not None:
            latency = float(self.latency_ns)
            if not math.isfinite(latency) or latency < 0.0:
                raise ValueError("latency_ns must be finite and non-negative")
        if self.payload_correct and not self.delivered:
            raise ValueError("an undelivered transaction cannot claim a correct payload")
        if not self.delivered and not (
            self.failure_detected or self.due_detected or self.timed_out
        ):
            raise ValueError("an undelivered transaction requires an observed failure mode")


def classify_transaction(
    observation: TransactionObservation, *, sla_limit_ns: float | None = None
) -> ServiceOutcome:
    """Classify one transaction without equating correction flags to correctness."""
    if sla_limit_ns is not None:
        limit = float(sla_limit_ns)
        if not math.isfinite(limit) or limit < 0.0:
            raise ValueError("sla_limit_ns must be finite and non-negative")
        if observation.latency_ns is None:
            raise ValueError("latency is required when an SLA limit is declared")
        sla_failed = observation.latency_ns > limit
    else:
        sla_failed = False
    if observation.timed_out or sla_failed:
        return ServiceOutcome.TIMEOUT_OR_SLA_FAILURE
    if observation.delivered and observation.payload_correct:
        if observation.retry_count:
            return ServiceOutcome.SUCCESS_AFTER_RETRY
        if observation.correction_applied:
            return ServiceOutcome.SUCCESS_CORRECTED
        return ServiceOutcome.SUCCESS_NORMAL
    if observation.due_detected or observation.failure_detected or not observation.delivered:
        return ServiceOutcome.DETECTED_FAILURE
    return ServiceOutcome.SILENT_DATA_CORRUPTION


@dataclass(frozen=True)
class OutcomeSummary:
    transaction_count: int
    counts: dict[str, int]
    probabilities: dict[str, float]
    service_success_probability: float
    corrected_event_count: int
    retry_event_count: int


def summarize_observations(
    observations: Iterable[TransactionObservation],
    *,
    sla_limit_ns: float | None = None,
) -> OutcomeSummary:
    """Aggregate mutually exclusive final outcomes and energy-causing events."""
    items = list(observations)
    if not items:
        raise ValueError("at least one transaction observation is required")
    outcomes = [
        classify_transaction(item, sla_limit_ns=sla_limit_ns) for item in items
    ]
    counter = Counter(outcomes)
    counts = {outcome.value: counter[outcome] for outcome in ServiceOutcome}
    probabilities = {
        outcome.value: counts[outcome.value] / len(items) for outcome in ServiceOutcome
    }
    success_probability = sum(probabilities[outcome.value] for outcome in _SUCCESS)
    return OutcomeSummary(
        transaction_count=len(items),
        counts=counts,
        probabilities=probabilities,
        service_success_probability=success_probability,
        corrected_event_count=sum(item.correction_applied for item in items),
        retry_event_count=sum(item.retry_count for item in items),
    )


def useful_service_bits(payload_bits: int, summary: OutcomeSummary) -> int:
    """Return correct useful bits for an observed finite transaction set."""
    if isinstance(payload_bits, bool) or not isinstance(payload_bits, int):
        raise TypeError("payload_bits must be an integer")
    if payload_bits <= 0:
        raise ValueError("payload_bits must be positive")
    success_count = sum(summary.counts[outcome.value] for outcome in _SUCCESS)
    return payload_bits * success_count


__all__ = [
    "OutcomeSummary",
    "ServiceOutcome",
    "TransactionObservation",
    "classify_transaction",
    "summarize_observations",
    "useful_service_bits",
]
