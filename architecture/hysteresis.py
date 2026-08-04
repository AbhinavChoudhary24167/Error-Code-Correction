"""Deployment-oriented horizon and uncertainty aware ECC switching rule."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from .scheduling import EpochModeCost, ScheduleResult, TransitionLookup, evaluate_path
from .transitions import ArchitectureDesign


def _normal_confidence_positive(mean: float, std: float) -> float:
    if std <= 0:
        return 1.0 if mean > 0 else 0.0
    return 0.5 * (1.0 + math.erf(mean / (std * math.sqrt(2.0))))


def hysteresis_schedule(
    *,
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
    prediction_horizon_epochs: int,
    min_dwell_epochs: int,
    minimum_benefit_margin: float,
    max_transitions: int | None,
    confidence_threshold: float,
    uncertainty_z: float,
    safe_fallback: str,
) -> ScheduleResult:
    if prediction_horizon_epochs <= 0 or min_dwell_epochs <= 0:
        raise ValueError("prediction horizon and minimum dwell must be positive")
    if minimum_benefit_margin < 0 or uncertainty_z < 0:
        raise ValueError("hysteresis margins must be non-negative")
    if not 0 <= confidence_threshold <= 1:
        raise ValueError("confidence_threshold must be in [0, 1]")
    if not epoch_costs:
        raise ValueError("epoch_costs must not be empty")

    initial_feasible = [
        item for item in epoch_costs[0].values() if item.feasible and item.objective_cost is not None
    ]
    if safe_fallback in epoch_costs[0] and epoch_costs[0][safe_fallback].feasible:
        current = safe_fallback
    elif initial_feasible:
        current = min(initial_feasible, key=lambda item: float(item.objective_cost)).ecc_id
    else:
        return ScheduleResult(
            "robust_hysteresis", "infeasible", objective, (), None, None, None, None,
            0, (), "O(T*H*M)", "initial epoch has no feasible mode",
        )

    path: list[str] = []
    reasons: list[str] = []
    dwell = 0
    switches = 0
    for index, costs in enumerate(epoch_costs):
        current_cost = costs[current]
        if not current_cost.feasible or current_cost.objective_cost is None:
            feasible = [item for item in costs.values() if item.feasible and item.objective_cost is not None]
            if not feasible:
                return ScheduleResult(
                    "robust_hysteresis", "infeasible", objective, tuple(path), None, None,
                    None, None, switches, (), "O(T*H*M)",
                    f"epoch {index} has no feasible fallback",
                )
            new_mode = min(feasible, key=lambda item: float(item.objective_cost)).ecc_id
            transition = transition_lookup(index, current, new_mode) if index else None
            if index and transition.objective_cost(objective) is None:
                new_mode = safe_fallback
            current = new_mode
            switches += int(bool(path) and path[-1] != current)
            dwell = 1
            path.append(current)
            reasons.append("mandatory safety switch because current mode violates a hard constraint")
            continue

        horizon_end = min(len(epoch_costs), index + prediction_horizon_epochs)
        candidates = []
        for alternative in costs:
            if alternative == current:
                continue
            current_sum = 0.0
            alternative_sum = 0.0
            variance = 0.0
            horizon_feasible = True
            for future in range(index, horizon_end):
                c_current = epoch_costs[future][current]
                c_alternative = epoch_costs[future][alternative]
                if (
                    not c_current.feasible
                    or not c_alternative.feasible
                    or c_current.objective_cost is None
                    or c_alternative.objective_cost is None
                ):
                    horizon_feasible = False
                    break
                current_sum += float(c_current.objective_cost)
                alternative_sum += float(c_alternative.objective_cost)
                variance += c_current.objective_std**2 + c_alternative.objective_std**2
            if not horizon_feasible:
                continue
            transition_value = 0.0
            if index or path:
                transition = transition_lookup(index, current, alternative)
                raw = transition.objective_cost(objective)
                if raw is None:
                    continue
                transition_value = float(raw)
            gross_benefit = current_sum - alternative_sum
            std = math.sqrt(variance)
            uncertainty_margin = uncertainty_z * std
            net_evidence = gross_benefit - transition_value - minimum_benefit_margin
            confidence = _normal_confidence_positive(net_evidence, std)
            candidates.append(
                (
                    net_evidence - uncertainty_margin,
                    alternative,
                    gross_benefit,
                    transition_value,
                    uncertainty_margin,
                    confidence,
                )
            )
        best = max(candidates, default=None)
        rate_limited = max_transitions is not None and switches >= max_transitions
        dwell_limited = dwell < min_dwell_epochs
        if (
            best is not None
            and best[0] > 0
            and best[5] >= confidence_threshold
            and not rate_limited
            and not dwell_limited
        ):
            _, alternative, gross, transition_value, margin, confidence = best
            current = alternative
            switches += 1
            dwell = 1
            reasons.append(
                "switch: forecast gross benefit "
                f"{gross:.6g} exceeds transition {transition_value:.6g}, "
                f"benefit margin {minimum_benefit_margin:.6g}, and uncertainty {margin:.6g}; "
                f"confidence={confidence:.3f}"
            )
        else:
            dwell += 1
            if dwell_limited:
                reason = f"stay: minimum dwell of {min_dwell_epochs} epochs not met"
            elif rate_limited:
                reason = "stay: maximum switching count reached"
            elif best is None:
                reason = "stay: no feasible alternative across prediction horizon"
            elif best[5] < confidence_threshold:
                reason = f"abstain: benefit confidence {best[5]:.3f} below {confidence_threshold:.3f}"
            else:
                reason = "stay: forecast benefit does not exceed transition and uncertainty margins"
            reasons.append(reason)
        path.append(current)

    return evaluate_path(
        policy_name="robust_hysteresis",
        path=path,
        epoch_costs=epoch_costs,
        transition_lookup=transition_lookup,
        design=design,
        objective=objective,
        theoretical_complexity="O(T*H*M) for T epochs, horizon H, and M modes",
        selection_reasons=reasons,
    )
