"""Deterministic uncertainty propagation for architecture recommendations."""

from __future__ import annotations

import random
from typing import Mapping, Sequence

from .selection import apply_hard_constraints, exact_pareto, preference_costs


def monte_carlo_robustness(
    records: Sequence[Mapping[str, object]],
    *,
    constraints: Mapping[str, float],
    preference_weights: Mapping[str, float],
    relative_intervals: Mapping[str, float],
    samples: int,
    seed: int,
) -> dict:
    """Propagate independent uniform metric intervals with a fixed seed.

    This is an uncertainty stress test, not a claim that the underlying input
    distributions are uniform or independent. Those assumptions are recorded
    explicitly in the returned report.
    """

    if samples <= 0:
        raise ValueError("samples must be positive")
    rng = random.Random(seed)
    optimal_counts = {str(item["config_id"]): 0 for item in records}
    feasible_counts = {str(item["config_id"]): 0 for item in records}
    pareto_counts = {str(item["config_id"]): 0 for item in records}
    regrets = {str(item["config_id"]): [] for item in records}
    fields = {
        "FIT": float(relative_intervals.get("fit", 0.0)),
        "architecture_energy_j": float(relative_intervals.get("energy", 0.0)),
        "architecture_carbon_kg": float(relative_intervals.get("carbon", 0.0)),
        "architecture_latency_ns": float(relative_intervals.get("latency", 0.0)),
    }
    for value in fields.values():
        if not 0 <= value < 1:
            raise ValueError("relative uncertainty intervals must be in [0, 1)")

    completed_samples = 0
    for _ in range(samples):
        perturbed = []
        for raw in records:
            item = dict(raw)
            for field, relative in fields.items():
                if item.get(field) is not None:
                    item[field] = float(item[field]) * rng.uniform(1.0 - relative, 1.0 + relative)
            perturbed.append(item)
        feasible, _ = apply_hard_constraints(perturbed, constraints)
        for item in feasible:
            feasible_counts[str(item["config_id"])] += 1
        if not feasible:
            continue
        for item in exact_pareto(feasible):
            pareto_counts[str(item["config_id"])] += 1
        costs = preference_costs(feasible, preference_weights)
        best = min(costs, key=lambda key: (costs[key], key))
        best_cost = costs[best]
        optimal_counts[best] += 1
        for config_id, value in costs.items():
            regrets[config_id].append(value - best_cost)
        completed_samples += 1

    def percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
        return ordered[index]

    candidates = {}
    denominator = completed_samples or 1
    for config_id in optimal_counts:
        candidates[config_id] = {
            "constraint_satisfaction_probability": feasible_counts[config_id] / samples,
            "optimal_probability": optimal_counts[config_id] / denominator,
            "robust_pareto_membership_probability": pareto_counts[config_id] / denominator,
            "regret_p50": percentile(regrets[config_id], 0.50),
            "regret_p95": percentile(regrets[config_id], 0.95),
        }
    ranked = sorted(candidates, key=lambda key: (-candidates[key]["optimal_probability"], key))
    return {
        "method": "independent_uniform_multiplicative_monte_carlo",
        "samples_requested": samples,
        "samples_with_feasible_candidate": completed_samples,
        "seed": seed,
        "relative_intervals": dict(relative_intervals),
        "independence_assumption": True,
        "distribution_assumption": "Uniform within each declared relative interval.",
        "candidates": candidates,
        "recommended": ranked[0] if ranked else None,
        "second_best_fallback": ranked[1] if len(ranked) > 1 else None,
        "recommendation_confidence": (
            candidates[ranked[0]]["optimal_probability"] if ranked else 0.0
        ),
    }
