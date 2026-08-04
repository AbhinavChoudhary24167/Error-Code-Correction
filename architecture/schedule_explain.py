"""Explanations and dimensionless regime diagnostics for ECC schedules."""

from __future__ import annotations

from typing import Mapping, Sequence

from .break_even import overhead_ratio
from .scheduling import ScheduleResult


def compare_schedule_to_static(
    schedule: ScheduleResult, static: ScheduleResult
) -> dict:
    if schedule.status != "ok" or static.status != "ok":
        return {
            "status": "unavailable",
            "net_saving": None,
            "net_saving_fraction": None,
            "reason": "both schedules must be feasible and characterized",
        }
    assert schedule.total_objective is not None and static.total_objective is not None
    saving = static.total_objective - schedule.total_objective
    fraction = saving / static.total_objective if static.total_objective else 0.0
    return {
        "status": "ok",
        "net_saving": saving,
        "net_saving_fraction": fraction,
        "adaptive_beneficial": saving > 0,
        "static_total": static.total_objective,
        "schedule_total": schedule.total_objective,
    }


def schedule_regime_ratios(
    *,
    schedule: ScheduleResult,
    gross_operational_benefit: float | None,
    adaptability_overhead: float | None,
) -> dict:
    transition = schedule.transition_objective if schedule.status == "ok" else None
    return {
        "rho_transition": overhead_ratio(transition, gross_operational_benefit),
        "rho_adaptive": overhead_ratio(adaptability_overhead, gross_operational_benefit),
        "interpretation": "adaptation is net beneficial only when complete overhead/gross-benefit ratios are below one",
    }


def count_avoided_transitions(reference: ScheduleResult, proposed: ScheduleResult) -> int | None:
    if reference.status != "ok" or proposed.status != "ok":
        return None
    return reference.transitions - proposed.transitions


def waterfall_terms(schedule: ScheduleResult, static: ScheduleResult) -> dict:
    return waterfall_terms_with_continuing_overhead(schedule, static, 0.0)


def waterfall_terms_with_continuing_overhead(
    schedule: ScheduleResult,
    static: ScheduleResult,
    continuing_adaptability_overhead: float,
) -> dict:
    if schedule.status != "ok" or static.status != "ok":
        return {"status": "unavailable"}
    assert schedule.epoch_objective is not None and static.epoch_objective is not None
    if continuing_adaptability_overhead < 0:
        raise ValueError("continuing adaptability overhead must be non-negative")
    gross = static.epoch_objective - (
        schedule.epoch_objective - continuing_adaptability_overhead
    )
    transition = float(schedule.transition_objective or 0.0)
    implementation_delta = float(schedule.implementation_objective or 0.0) - float(
        static.implementation_objective or 0.0
    )
    net = gross - continuing_adaptability_overhead - transition - implementation_delta
    return {
        "status": "ok",
        "gross_operational_saving": gross,
        "continuing_adaptability_overhead": continuing_adaptability_overhead,
        "transition_overhead": transition,
        "incremental_implementation_overhead": implementation_delta,
        "net_saving": net,
    }


def schedule_stability(paths: Sequence[Sequence[str]]) -> dict:
    if not paths:
        return {"samples": 0, "epoch_mode_agreement": []}
    width = len(paths[0])
    if any(len(path) != width for path in paths):
        raise ValueError("schedule stability paths must have equal length")
    agreements = []
    for index in range(width):
        counts: dict[str, int] = {}
        for path in paths:
            counts[path[index]] = counts.get(path[index], 0) + 1
        agreements.append(max(counts.values()) / len(paths))
    return {
        "samples": len(paths),
        "epoch_mode_agreement": agreements,
        "mean_epoch_mode_agreement": sum(agreements) / len(agreements),
    }


def compact_policy_table(results: Mapping[str, ScheduleResult]) -> list[dict]:
    return [
        {
            "policy": name,
            "status": result.status,
            "total_objective": result.total_objective,
            "transitions": result.transitions,
            "path": list(result.path),
            "reason": result.reason,
        }
        for name, result in sorted(results.items())
    ]
