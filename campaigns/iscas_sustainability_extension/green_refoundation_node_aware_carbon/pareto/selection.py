"""Exact deterministic Pareto and transparent robust summaries."""

from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import fmean, median
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Objective:
    name: str
    direction: str

    def __post_init__(self) -> None:
        if self.direction not in {"min", "max"}:
            raise ValueError("objective direction must be 'min' or 'max'")


def _number(row: Mapping[str, object], name: str) -> float:
    value = row.get(name)
    if value in (None, ""):
        raise ValueError(f"objective {name} is missing")
    number = float(value)  # type: ignore[arg-type]
    if not math.isfinite(number):
        raise ValueError(f"objective {name} must be finite")
    return number


def dominates(
    left: Mapping[str, object],
    right: Mapping[str, object],
    objectives: Sequence[Objective],
) -> bool:
    if not objectives:
        raise ValueError("at least one objective is required")
    no_worse = True
    strict = False
    for objective in objectives:
        lv = _number(left, objective.name)
        rv = _number(right, objective.name)
        if objective.direction == "min":
            no_worse = no_worse and lv <= rv
            strict = strict or lv < rv
        else:
            no_worse = no_worse and lv >= rv
            strict = strict or lv > rv
    return no_worse and strict


def exact_pareto_front(
    rows: Sequence[Mapping[str, object]], objectives: Sequence[Objective]
) -> list[int]:
    """Enumerate the exact non-dominated set in stable input order."""
    names = [objective.name for objective in objectives]
    if len(names) != len(set(names)):
        raise ValueError("objective names must be unique")
    for row in rows:
        for name in names:
            _number(row, name)
    return [
        index
        for index, row in enumerate(rows)
        if not any(
            dominates(other, row, objectives)
            for other_index, other in enumerate(rows)
            if other_index != index
        )
    ]


def qualified_rows(
    rows: Sequence[Mapping[str, object]], required_fields: Sequence[str]
) -> list[Mapping[str, object]]:
    """Return rows with qualified status and all required numeric objectives."""
    eligible: list[Mapping[str, object]] = []
    for row in rows:
        if row.get("qualification_status") not in {
            "QUALIFIED_ABSOLUTE",
            "QUALIFIED_RELATIVE",
            "BOUNDED_RESULT",
        }:
            continue
        try:
            for field in required_fields:
                _number(row, field)
        except (TypeError, ValueError):
            continue
        eligible.append(row)
    return eligible


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def robust_summary(samples: Sequence[float]) -> dict[str, float]:
    values = [float(value) for value in samples]
    if not values or any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("samples must be finite, non-negative, and non-empty")
    return {
        "mean": fmean(values),
        "median": median(values),
        "p05": _quantile(values, 0.05),
        "worst_case_interval_lower": min(values),
        "worst_case_interval_upper": max(values),
    }


__all__ = [
    "Objective",
    "dominates",
    "exact_pareto_front",
    "qualified_rows",
    "robust_summary",
]
