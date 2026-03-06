from __future__ import annotations

"""Pareto frontier helpers for analysis and plotting paths."""

from dataclasses import dataclass
from typing import Iterable, Mapping


DEFAULT_OBJECTIVES: dict[str, str] = {
    "FIT": "min",
    "carbon_kg": "min",
    "latency_ns": "min",
}


@dataclass(frozen=True)
class ParetoPartition:
    """Indices partitioned into frontier and dominated subsets."""

    frontier_indices: list[int]
    dominated_indices: list[int]


def _normalise_objectives(objectives: Mapping[str, str]) -> dict[str, str]:
    if not objectives:
        raise ValueError("At least one objective must be specified")
    normalised: dict[str, str] = {}
    for key, value in objectives.items():
        direction = str(value).strip().lower()
        if direction not in {"min", "max"}:
            raise ValueError(f"Unsupported objective direction for {key!r}: {value!r}")
        normalised[str(key)] = direction
    return normalised


def dominates(
    left: Mapping[str, float],
    right: Mapping[str, float],
    *,
    objectives: Mapping[str, str],
    eps: float = 1e-12,
) -> bool:
    """Return True when ``left`` Pareto-dominates ``right``."""

    dirs = _normalise_objectives(objectives)
    strictly_better = False
    for metric, direction in dirs.items():
        lv = float(left[metric])
        rv = float(right[metric])
        if direction == "min":
            if lv > rv + eps:
                return False
            if lv < rv - eps:
                strictly_better = True
        else:
            if lv < rv - eps:
                return False
            if lv > rv + eps:
                strictly_better = True
    return strictly_better


def pareto_partition(
    records: Iterable[Mapping[str, float]],
    *,
    objectives: Mapping[str, str] | None = None,
    eps: float = 1e-12,
) -> ParetoPartition:
    """Partition records into frontier and dominated indices."""

    recs = list(records)
    dirs = _normalise_objectives(objectives or DEFAULT_OBJECTIVES)
    frontier: list[int] = []
    dominated: list[int] = []
    for idx, rec in enumerate(recs):
        is_dominated = False
        for jdx, other in enumerate(recs):
            if idx == jdx:
                continue
            if dominates(other, rec, objectives=dirs, eps=eps):
                is_dominated = True
                break
        if is_dominated:
            dominated.append(idx)
        else:
            frontier.append(idx)
    return ParetoPartition(frontier_indices=frontier, dominated_indices=dominated)


def pareto_frontier(
    records: Iterable[Mapping[str, float]],
    *,
    objectives: Mapping[str, str] | None = None,
    eps: float = 1e-12,
) -> list[dict[str, float]]:
    """Return frontier rows while preserving deterministic input ordering."""

    recs = [dict(r) for r in records]
    part = pareto_partition(recs, objectives=objectives, eps=eps)
    return [recs[idx] for idx in part.frontier_indices]


def annotate_frontier(
    records: Iterable[Mapping[str, float]],
    *,
    objectives: Mapping[str, str] | None = None,
    eps: float = 1e-12,
    frontier_column: str = "frontier",
) -> list[dict[str, float | bool]]:
    """Return records with a boolean frontier membership column attached."""

    recs = [dict(r) for r in records]
    part = pareto_partition(recs, objectives=objectives, eps=eps)
    front = set(part.frontier_indices)
    out: list[dict[str, float | bool]] = []
    for idx, rec in enumerate(recs):
        row = dict(rec)
        row[frontier_column] = idx in front
        out.append(row)
    return out


__all__ = [
    "DEFAULT_OBJECTIVES",
    "ParetoPartition",
    "annotate_frontier",
    "dominates",
    "pareto_frontier",
    "pareto_partition",
]
