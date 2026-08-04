"""Independent, documentation-facing Pareto validation utilities.

This module deliberately does not import or call the study selector's private
Pareto implementation.  It gives documentation figures a second
implementation against which to check the recorded frontier.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class Objective:
    """One numeric objective extracted from a candidate record."""

    name: str
    getter: Callable[[Mapping[str, Any]], float | int | None]
    direction: str = "min"
    epsilon: float = 0.0

    def __post_init__(self) -> None:
        if self.direction not in {"min", "max"}:
            raise ValueError(f"invalid objective direction: {self.direction}")
        if self.epsilon < 0:
            raise ValueError("epsilon must be non-negative")


def eligible_candidates(
    candidates: Sequence[Mapping[str, Any]],
    objectives: Sequence[Objective],
    *,
    eligibility: Callable[[Mapping[str, Any]], bool] | None = None,
) -> tuple[list[Mapping[str, Any]], dict[str, str]]:
    """Filter constraints and null/non-finite objectives before dominance.

    Candidate identifiers use ``implementation_id`` when present.  Reasons are
    returned for audit plots and documentation.
    """

    kept: list[Mapping[str, Any]] = []
    excluded: dict[str, str] = {}
    for index, candidate in enumerate(candidates):
        identifier = str(candidate.get("implementation_id", f"candidate-{index}"))
        if eligibility is not None and not eligibility(candidate):
            excluded[identifier] = "ineligible_or_hard_constraint_failed"
            continue
        values = [objective.getter(candidate) for objective in objectives]
        if any(value is None for value in values):
            excluded[identifier] = "null_objective"
            continue
        if any(not math.isfinite(float(value)) for value in values):
            excluded[identifier] = "non_finite_objective"
            continue
        kept.append(candidate)
    return kept, excluded


def dominates(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    objectives: Sequence[Objective],
) -> bool:
    """Return True when ``left`` epsilon-dominates ``right``.

    For a minimization objective, ``left <= right + epsilon`` is no worse and
    ``left < right - epsilon`` is strictly better. Maximization reverses both
    comparisons. Equal and epsilon-equivalent points therefore coexist.
    """

    no_worse = True
    strictly_better = False
    for objective in objectives:
        left_value = float(objective.getter(left))
        right_value = float(objective.getter(right))
        epsilon = objective.epsilon
        if objective.direction == "min":
            no_worse &= left_value <= right_value + epsilon
            strictly_better |= left_value < right_value - epsilon
        else:
            no_worse &= left_value >= right_value - epsilon
            strictly_better |= left_value > right_value + epsilon
    return bool(no_worse and strictly_better)


def pareto_front(
    candidates: Sequence[Mapping[str, Any]],
    objectives: Sequence[Objective],
    *,
    eligibility: Callable[[Mapping[str, Any]], bool] | None = None,
) -> tuple[list[Mapping[str, Any]], dict[str, str]]:
    """Return a stable independent frontier and exclusion audit."""

    kept, excluded = eligible_candidates(candidates, objectives, eligibility=eligibility)
    front = [
        candidate
        for candidate in kept
        if not any(other is not candidate and dominates(other, candidate, objectives) for other in kept)
    ]
    return sorted(front, key=lambda item: str(item.get("implementation_id", ""))), excluded


def crowding_distance(
    candidates: Sequence[Mapping[str, Any]], objectives: Sequence[Objective]
) -> dict[str, float]:
    """Compute NSGA-II-style normalized crowding distance for one front."""

    result = {str(item.get("implementation_id", index)): 0.0 for index, item in enumerate(candidates)}
    if not candidates:
        return result
    if len(candidates) <= 2:
        return {key: math.inf for key in result}
    for objective in objectives:
        ordered = sorted(
            enumerate(candidates),
            key=lambda pair: (float(objective.getter(pair[1])), str(pair[1].get("implementation_id", pair[0]))),
        )
        low = float(objective.getter(ordered[0][1]))
        high = float(objective.getter(ordered[-1][1]))
        result[str(ordered[0][1].get("implementation_id", ordered[0][0]))] = math.inf
        result[str(ordered[-1][1].get("implementation_id", ordered[-1][0]))] = math.inf
        if high == low:
            continue
        for position in range(1, len(ordered) - 1):
            identifier = str(ordered[position][1].get("implementation_id", ordered[position][0]))
            if math.isinf(result[identifier]):
                continue
            previous_value = float(objective.getter(ordered[position - 1][1]))
            next_value = float(objective.getter(ordered[position + 1][1]))
            result[identifier] += (next_value - previous_value) / (high - low)
    return result


def knee_point(
    candidates: Sequence[Mapping[str, Any]], x: Objective, y: Objective
) -> Mapping[str, Any] | None:
    """Select the point farthest from the normalized endpoint chord.

    The two objectives are transformed to minimization orientation. A one-point
    front returns its only point; equal or collinear fronts use identifier order
    as the deterministic tie break.
    """

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def orient(item: Mapping[str, Any], objective: Objective) -> float:
        value = float(objective.getter(item))
        return value if objective.direction == "min" else -value

    raw = [(item, orient(item, x), orient(item, y)) for item in candidates]
    xmin, xmax = min(v[1] for v in raw), max(v[1] for v in raw)
    ymin, ymax = min(v[2] for v in raw), max(v[2] for v in raw)

    def normalize(value: float, low: float, high: float) -> float:
        return 0.0 if high == low else (value - low) / (high - low)

    points = [(item, normalize(xv, xmin, xmax), normalize(yv, ymin, ymax)) for item, xv, yv in raw]
    left = min(points, key=lambda item: (item[1], item[2], str(item[0].get("implementation_id", ""))))
    right = min(points, key=lambda item: (item[2], item[1], str(item[0].get("implementation_id", ""))))
    dx, dy = right[1] - left[1], right[2] - left[2]
    denominator = math.hypot(dx, dy)

    def distance(point: tuple[Mapping[str, Any], float, float]) -> float:
        if denominator == 0:
            return 0.0
        return abs(dy * point[1] - dx * point[2] + right[1] * left[2] - right[2] * left[1]) / denominator

    return max(points, key=lambda item: (distance(item), str(item[0].get("implementation_id", ""))))[0]


def hypervolume_2d(
    candidates: Sequence[Mapping[str, Any]],
    x: Objective,
    y: Objective,
    reference_point: tuple[float, float],
) -> float:
    """Compute exact dominated area for a two-objective minimization front.

    Max objectives are sign-transformed, so the caller must provide the
    reference point in the original objective orientation.
    """

    def orient(value: float, objective: Objective) -> float:
        return value if objective.direction == "min" else -value

    reference = (orient(float(reference_point[0]), x), orient(float(reference_point[1]), y))
    points = sorted(
        {
            (orient(float(x.getter(item)), x), orient(float(y.getter(item)), y))
            for item in candidates
        }
    )
    area = 0.0
    current_y = reference[1]
    for point_x, point_y in points:
        if point_x > reference[0] or point_y > reference[1] or point_y >= current_y:
            continue
        area += max(0.0, reference[0] - point_x) * (current_y - point_y)
        current_y = point_y
    return area


__all__ = [
    "Objective",
    "crowding_distance",
    "dominates",
    "eligible_candidates",
    "hypervolume_2d",
    "knee_point",
    "pareto_front",
]
