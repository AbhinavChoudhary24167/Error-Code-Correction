"""Transparent exact selection, baselines, regret, and score diagnostics."""

from __future__ import annotations

import math
import time
import tracemalloc
from typing import Iterable, Mapping, Sequence

from analysis.pareto import pareto_frontier


DEFAULT_OBJECTIVES = {
    "FIT": "min",
    "architecture_carbon_kg": "min",
    "architecture_latency_ns": "min",
}


def apply_hard_constraints(
    records: Iterable[Mapping[str, object]], constraints: Mapping[str, float]
) -> tuple[list[dict], list[dict]]:
    feasible: list[dict] = []
    infeasible: list[dict] = []
    mapping = {
        "fit_max": ("FIT", "max"),
        "latency_ns_max": ("architecture_latency_ns", "max"),
        "carbon_kg_max": ("architecture_carbon_kg", "max"),
        "energy_j_max": ("architecture_energy_j", "max"),
        "area_mm2_max": ("architecture_area_mm2", "max"),
        "capacity_efficiency_min": ("capacity_efficiency", "min"),
    }
    for raw in records:
        record = dict(raw)
        violations: list[str] = []
        margins: dict[str, float | None] = {}
        for constraint, bound in constraints.items():
            if constraint not in mapping:
                raise ValueError(f"Unknown hard constraint: {constraint}")
            metric, direction = mapping[constraint]
            value = record.get(metric)
            if value is None:
                violations.append(f"{constraint}:uncharacterized")
                margins[constraint] = None
            elif direction == "max" and float(value) > float(bound):
                violations.append(constraint)
                margins[constraint] = float(bound) - float(value)
            elif direction == "max":
                margins[constraint] = float(bound) - float(value)
            elif direction == "min" and float(value) < float(bound):
                violations.append(constraint)
                margins[constraint] = float(value) - float(bound)
            else:
                margins[constraint] = float(value) - float(bound)
        record["constraint_violations"] = violations
        record["constraint_margins"] = margins
        record["feasible"] = not violations
        (feasible if not violations else infeasible).append(record)
    return feasible, infeasible


def exact_pareto(
    records: Sequence[Mapping[str, object]],
    objectives: Mapping[str, str] | None = None,
) -> list[dict]:
    if not records:
        return []
    active = dict(objectives or DEFAULT_OBJECTIVES)
    available = {
        key: direction
        for key, direction in active.items()
        if all(record.get(key) is not None for record in records)
    }
    if not available:
        raise ValueError("No fully characterized objective is available for exact Pareto selection")
    return pareto_frontier(records, objectives=available)


def _normalised_costs(records: Sequence[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    fields = ("FIT", "architecture_carbon_kg", "architecture_latency_ns")
    costs: dict[str, dict[str, float]] = {str(item["config_id"]): {} for item in records}
    for field in fields:
        values = [float(item[field]) for item in records if item.get(field) is not None]
        if not values:
            for item in records:
                costs[str(item["config_id"])][field] = 0.0
            continue
        if field == "FIT":
            values = [math.log10(max(value, 1e-30)) for value in values]
        low, high = min(values), max(values)
        for item in records:
            raw = item.get(field)
            if raw is None or high <= low:
                normalised = 0.0
            else:
                value = math.log10(max(float(raw), 1e-30)) if field == "FIT" else float(raw)
                normalised = (value - low) / (high - low)
            costs[str(item["config_id"])][field] = normalised
    return costs


def preference_costs(
    records: Sequence[Mapping[str, object]],
    weights: Mapping[str, float],
) -> dict[str, float]:
    resolved = {
        "FIT": max(float(weights.get("reliability", 1.0)), 0.0),
        "architecture_carbon_kg": max(float(weights.get("carbon", 1.0)), 0.0),
        "architecture_latency_ns": max(float(weights.get("latency", 0.25)), 0.0),
    }
    total = sum(resolved.values())
    if total <= 0:
        raise ValueError("At least one preference weight must be positive")
    costs = _normalised_costs(records)
    return {
        config_id: sum((resolved[field] / total) * values[field] for field in resolved)
        for config_id, values in costs.items()
    }


def fault_regime_lookup(records: Sequence[Mapping[str, object]], fault_regime: str) -> dict | None:
    preferences = {
        "none": ("SEC-DED",),
        "light": ("SEC-DED",),
        "moderate": ("SEC-DAEC", "TAEC", "BCH"),
        "heavy": ("BCH", "TAEC"),
    }
    wanted = preferences.get(fault_regime, preferences["moderate"])
    for family in wanted:
        match = next((dict(item) for item in records if str(item.get("family")) == family), None)
        if match is not None:
            return match
    return dict(records[0]) if records else None


def select_baselines(
    feasible: Sequence[Mapping[str, object]],
    *,
    fault_regime: str,
    preference_weights: Mapping[str, float],
) -> dict:
    records = [dict(item) for item in feasible]
    if not records:
        return {"status": "no_feasible_candidates", "selections": {}, "regret": {}}

    frontier = exact_pareto(records)
    costs = preference_costs(records, preference_weights)
    best_cost = min(costs.values())
    active_objectives = [
        field
        for field in ("FIT", "architecture_carbon_kg", "architecture_latency_ns")
        if all(item.get(field) is not None for item in records)
    ]

    def choose_min(field: str) -> dict:
        available = [item for item in records if item.get(field) is not None]
        if not available:
            return min(records, key=lambda item: (costs[str(item["config_id"])], str(item["config_id"])))
        return min(available, key=lambda item: (float(item[field]), str(item["config_id"])))

    secded = next((item for item in records if item.get("family") == "SEC-DED"), records[0])
    lookup = fault_regime_lookup(records, fault_regime) or records[0]
    green = min(frontier, key=lambda item: (costs[str(item["config_id"])], str(item["config_id"])))
    selections = {
        "static_secded": secded,
        "strongest_reliability": choose_min("FIT"),
        "minimum_energy_feasible": choose_min("architecture_energy_j"),
        "minimum_carbon_feasible": choose_min("architecture_carbon_kg"),
        "fault_regime_lookup": lookup,
        "exact_pareto_preference": green,
        "green_ecc_policy": green,
    }
    compact = {name: str(item["config_id"]) for name, item in selections.items()}
    regret = {
        name: {
            "preference_cost": costs[config_id],
            "absolute_regret": costs[config_id] - best_cost,
        }
        for name, config_id in compact.items()
    }
    return {
        "status": "ok",
        "selections": compact,
        "regret": regret,
        "pareto_configurations": [str(item["config_id"]) for item in frontier],
        "preference_costs": costs,
        "active_objectives": active_objectives,
        "green_differs_from_lookup": compact["green_ecc_policy"] != compact["fault_regime_lookup"],
        "limitations": [
            f"{field} unavailable; corresponding baseline falls back to preference cost"
            for field in ("architecture_energy_j", "architecture_carbon_kg")
            if not any(item.get(field) is not None for item in records)
        ],
    }


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + end - 1) / 2.0 + 1.0
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def spearman_rank_correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    a, b = _ranks(left), _ranks(right)
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    denominator = math.sqrt(
        sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b)
    )
    return numerator / denominator if denominator else None


def score_diagnostics(records: Sequence[Mapping[str, object]]) -> dict:
    metrics = ("ESII", "NESII", "GS")
    available = [metric for metric in metrics if all(item.get(metric) is not None for item in records)]
    correlations = {}
    for i, left in enumerate(available):
        for right in available[i + 1 :]:
            correlations[f"{left}_vs_{right}"] = spearman_rank_correlation(
                [float(item[left]) for item in records],
                [float(item[right]) for item in records],
            )
    winners = {
        metric: str(max(records, key=lambda item: float(item[metric]))["config_id"])
        for metric in available
    }

    component_winner = None
    dominance_fields = ("FIT", "architecture_carbon_kg", "architecture_latency_ns")
    if all(all(item.get(field) is not None for field in dominance_fields) for item in records):
        for candidate in records:
            if all(
                candidate is other
                or all(float(candidate[field]) <= float(other[field]) for field in dominance_fields)
                for other in records
            ):
                component_winner = str(candidate["config_id"])
                break
    return {
        "rank_correlations": correlations,
        "argmax_by_score": winners,
        "all_scores_same_winner": len(set(winners.values())) <= 1 if winners else None,
        "componentwise_dominant_candidate": component_winner,
        "coincidence_condition": (
            "Any strictly increasing utility of benefits and strictly decreasing utility of costs "
            "must select a candidate that strictly component-wise dominates all alternatives."
        ),
        "interpretation": (
            "Empirical winner agreement is not mathematical score equivalence. Correlation and "
            "component-wise ordering must be inspected separately."
        ),
    }


def benchmark_exact_pareto_scaling(
    candidate_counts: Sequence[int] = (5, 25, 50, 100),
    *,
    repeats: int = 3,
) -> dict:
    """Measure exact-enumeration scaling on a deterministic synthetic trade-off set."""

    if repeats <= 0 or any(count <= 0 for count in candidate_counts):
        raise ValueError("candidate counts and repeats must be positive")
    measurements = []
    for count in candidate_counts:
        records = [
            {
                "config_id": f"scale-{index}",
                "FIT": float(index + 1),
                "architecture_carbon_kg": float(count - index),
                "architecture_latency_ns": float(1 + (index % 7)),
            }
            for index in range(count)
        ]
        elapsed = []
        peak_bytes = []
        frontier_size = 0
        for _ in range(repeats):
            tracemalloc.start()
            started = time.perf_counter()
            frontier_size = len(exact_pareto(records))
            elapsed.append(time.perf_counter() - started)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peak_bytes.append(peak)
        measurements.append(
            {
                "candidate_count": count,
                "frontier_size": frontier_size,
                "runtime_seconds_median": sorted(elapsed)[len(elapsed) // 2],
                "peak_memory_bytes_max": max(peak_bytes),
            }
        )
    return {
        "benchmark": "deterministic_synthetic_exact_pareto",
        "repeats": repeats,
        "theoretical_time_complexity": "O(C^2)",
        "theoretical_memory_complexity": "O(C)",
        "measurements": measurements,
        "warning": "Wall-clock and allocator measurements depend on the host and are not signoff PPA data.",
    }
