"""Finite-support ambiguity sets and machine-checkable worst-case risks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import permutations
import json
import math
from typing import Any, Mapping, Sequence

from .faults import FaultDistribution


@dataclass(frozen=True)
class SupportPattern:
    pattern_id: str
    positions: tuple[int, ...]
    family: str
    metadata: Mapping[str, Any]
    nominal_probability: float
    source_distribution_ids: tuple[str, ...]

    @property
    def mask(self) -> int:
        return sum(1 << position for position in self.positions)


def _hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def build_support(
    nominal: FaultDistribution,
    expansions: Sequence[FaultDistribution] = (),
) -> tuple[SupportPattern, ...]:
    """Build a union support while retaining the nominal PMF exactly."""

    distributions = (nominal, *tuple(expansions))
    if any(item.bit_width != nominal.bit_width for item in distributions):
        raise ValueError("all ambiguity-support distributions must have the same bit width")
    records: dict[int, dict[str, Any]] = {}
    nominal_by_mask = {pattern.mask(nominal.bit_width): pattern.probability for pattern in nominal.patterns}
    for distribution in distributions:
        for pattern in distribution.patterns:
            mask = pattern.mask(nominal.bit_width)
            if mask not in records:
                records[mask] = {
                    "pattern_id": pattern.pattern_id,
                    "positions": pattern.positions,
                    "family": pattern.family,
                    "metadata": dict(pattern.metadata),
                    "sources": [],
                }
            records[mask]["sources"].append(distribution.distribution_id)
    support = tuple(
        SupportPattern(
            pattern_id=str(record["pattern_id"]),
            positions=tuple(record["positions"]),
            family=str(record["family"]),
            metadata=dict(record["metadata"]),
            nominal_probability=float(nominal_by_mask.get(mask, 0.0)),
            source_distribution_ids=tuple(sorted(set(record["sources"]))),
        )
        for mask, record in sorted(records.items())
    )
    if not math.isclose(sum(item.nominal_probability for item in support), 1.0, abs_tol=1e-12):
        raise ValueError("nominal probabilities do not normalize on the ambiguity support")
    return support


def support_document(support: Sequence[SupportPattern], *, bit_width: int) -> dict[str, Any]:
    patterns = [
        {
            "support_index": index,
            "pattern_id": item.pattern_id,
            "positions": list(item.positions),
            "mask": item.mask,
            "family": item.family,
            "metadata": dict(item.metadata),
            "nominal_probability": item.nominal_probability,
            "source_distribution_ids": list(item.source_distribution_ids),
        }
        for index, item in enumerate(support)
    ]
    return {
        "bit_width": int(bit_width),
        "pattern_count": len(patterns),
        "patterns": patterns,
        "support_sha256": _hash(
            [{"positions": item["positions"], "family": item["family"]} for item in patterns]
        ),
        "nominal_pmf_sha256": _hash([item["nominal_probability"] for item in patterns]),
    }


def _adversary_summary(
    support: Sequence[SupportPattern], nominal: Sequence[float], adversarial: Sequence[float]
) -> list[dict[str, Any]]:
    return [
        {
            "support_index": index,
            "pattern_id": support[index].pattern_id,
            "positions": list(support[index].positions),
            "nominal_probability": float(nominal[index]),
            "adversarial_probability": float(adversarial[index]),
            "probability_change": float(adversarial[index] - nominal[index]),
        }
        for index in range(len(support))
        if abs(adversarial[index] - nominal[index]) > 1e-15
    ]


def _finalize_certificate(payload: Mapping[str, Any]) -> dict[str, Any]:
    document = dict(payload)
    document["certificate_sha256"] = _hash(document)
    return document


def _validate_binary_losses(losses: Sequence[int], support: Sequence[SupportPattern]) -> list[int]:
    values = [int(value) for value in losses]
    if len(values) != len(support):
        raise ValueError("loss vector length does not match ambiguity support")
    if any(value not in (0, 1) for value in values):
        raise ValueError("SafeForge risk certificates currently require binary losses")
    return values


def solve_total_variation(
    support: Sequence[SupportPattern], losses: Sequence[int], radius: float
) -> dict[str, Any]:
    if not 0 <= radius <= 1:
        raise ValueError("total-variation radius must be in [0,1]")
    loss = _validate_binary_losses(losses, support)
    nominal = [item.nominal_probability for item in support]
    risk = [index for index, value in enumerate(loss) if value]
    safe = [index for index, value in enumerate(loss) if not value]
    adversarial = list(nominal)
    transfers: list[dict[str, Any]] = []
    remaining = float(radius)
    if risk and safe:
        target = risk[0]
        for source in sorted(safe, key=lambda index: nominal[index], reverse=True):
            amount = min(adversarial[source], remaining)
            if amount <= 0:
                continue
            adversarial[source] -= amount
            adversarial[target] += amount
            remaining -= amount
            transfers.append({"source": source, "target": target, "mass": amount, "cost": amount})
            if remaining <= 1e-15:
                break
    nominal_risk = sum(probability * value for probability, value in zip(nominal, loss))
    objective = sum(probability * value for probability, value in zip(adversarial, loss))
    analytic_bound = (
        nominal_risk if not risk or not safe else min(1.0, nominal_risk + float(radius))
    )
    tv_distance = 0.5 * sum(abs(left - right) for left, right in zip(nominal, adversarial))
    return _finalize_certificate(
        {
            "schema_version": 1,
            "ambiguity_type": "total_variation",
            "radius": float(radius),
            "solver": "exact_binary_loss_closed_form",
            "solver_status": "optimal",
            "optimality_proven": True,
            "nominal_risk": nominal_risk,
            "worst_case_risk": objective,
            "dual_bound": analytic_bound,
            "optimality_gap": abs(analytic_bound - objective),
            "distance_used": tv_distance,
            "loss_vector": loss,
            "nominal_pmf": nominal,
            "adversarial_pmf": adversarial,
            "transfers": transfers,
            "patterns_receiving_probability": _adversary_summary(support, nominal, adversarial),
        }
    )


def _matching_displacement(left: Sequence[int], right: Sequence[int], n: int) -> float:
    if not left or not right:
        return 1.0
    size = min(len(left), len(right))
    if size > 7:
        left_center = sum(left) / len(left)
        right_center = sum(right) / len(right)
        return abs(left_center - right_center) / max(1, n - 1)
    best = min(
        sum(abs(left[index] - candidate[index]) for index in range(size))
        for candidate in permutations(right, size)
    )
    return best / (max(1, n - 1) * size)


def _adjacency_class(positions: Sequence[int]) -> str:
    ordered = sorted(positions)
    if len(ordered) == 1:
        return "sbu"
    if all(right == left + 1 for left, right in zip(ordered, ordered[1:])):
        return "adjacent_burst"
    return "non_adjacent_mbu"


def geometry_distance(
    left: SupportPattern,
    right: SupportPattern,
    *,
    bit_width: int,
    config: Mapping[str, Any],
) -> float:
    if left.mask == right.mask:
        return 0.0
    weights = {
        "multiplicity": float(config.get("multiplicity_weight", 1.0)),
        "hamming": float(config.get("hamming_weight", 1.0)),
        "displacement": float(config.get("displacement_weight", 1.0)),
        "burst_length": float(config.get("burst_length_weight", 0.5)),
        "adjacency": float(config.get("adjacency_class_weight", 0.5)),
        "row_column": float(config.get("row_column_weight", 0.5)),
    }
    if any(value < 0 for value in weights.values()) or not any(weights.values()):
        raise ValueError("geometry weights must be nonnegative with at least one positive")
    left_positions = tuple(left.positions)
    right_positions = tuple(right.positions)
    multiplicity = abs(len(left_positions) - len(right_positions)) / max(
        1, max(len(left_positions), len(right_positions))
    )
    hamming = (left.mask ^ right.mask).bit_count() / max(1, bit_width)
    displacement = _matching_displacement(left_positions, right_positions, bit_width)
    left_span = max(left_positions) - min(left_positions) + 1
    right_span = max(right_positions) - min(right_positions) + 1
    burst = abs(left_span - right_span) / max(1, bit_width)
    adjacency = 0.0 if _adjacency_class(left_positions) == _adjacency_class(right_positions) else 1.0
    columns = int(config.get("sram_columns", max(1, round(math.sqrt(bit_width)))))
    left_centroid = (
        sum(position // columns for position in left_positions) / len(left_positions),
        sum(position % columns for position in left_positions) / len(left_positions),
    )
    right_centroid = (
        sum(position // columns for position in right_positions) / len(right_positions),
        sum(position % columns for position in right_positions) / len(right_positions),
    )
    rows = math.ceil(bit_width / columns)
    row_column = (
        abs(left_centroid[0] - right_centroid[0]) / max(1, rows - 1)
        + abs(left_centroid[1] - right_centroid[1]) / max(1, columns - 1)
    ) / 2.0
    components = {
        "multiplicity": multiplicity,
        "hamming": hamming,
        "displacement": displacement,
        "burst_length": burst,
        "adjacency": adjacency,
        "row_column": row_column,
    }
    return sum(weights[name] * components[name] for name in weights)


def _wasserstein_costs(
    support: Sequence[SupportPattern], *, bit_width: int, config: Mapping[str, Any]
) -> list[list[float]]:
    return [
        [
            geometry_distance(left, right, bit_width=bit_width, config=config)
            for right in support
        ]
        for left in support
    ]


def solve_geometry_wasserstein(
    support: Sequence[SupportPattern],
    losses: Sequence[int],
    radius: float,
    *,
    bit_width: int,
    geometry: Mapping[str, Any],
) -> dict[str, Any]:
    if radius < 0:
        raise ValueError("Wasserstein radius must be nonnegative")
    loss = _validate_binary_losses(losses, support)
    nominal = [item.nominal_probability for item in support]
    risk = [index for index, value in enumerate(loss) if value]
    safe = [index for index, value in enumerate(loss) if not value]
    costs = _wasserstein_costs(support, bit_width=bit_width, config=geometry)
    adversarial = list(nominal)
    moves: list[tuple[float, int, int]] = []
    if risk:
        for source in safe:
            target = min(risk, key=lambda index: (costs[source][index], index))
            distance = costs[source][target]
            if distance <= 0:
                raise ValueError("geometry distance is zero between distinct safe/risk patterns")
            moves.append((distance, source, target))
    budget = float(radius)
    transfers: list[dict[str, Any]] = []
    for distance, source, target in sorted(moves):
        amount = min(adversarial[source], budget / distance if distance else adversarial[source])
        if amount <= 0:
            continue
        adversarial[source] -= amount
        adversarial[target] += amount
        used = amount * distance
        budget -= used
        transfers.append(
            {"source": source, "target": target, "mass": amount, "unit_cost": distance, "cost": used}
        )
        if budget <= 1e-15:
            break
    transport = list(transfers)
    moved_by_source = {item["source"]: item["mass"] for item in transfers}
    transport.extend(
        {
            "source": index,
            "target": index,
            "mass": probability - moved_by_source.get(index, 0.0),
            "unit_cost": 0.0,
            "cost": 0.0,
        }
        for index, probability in enumerate(nominal)
        if probability - moved_by_source.get(index, 0.0) > 1e-15
    )
    nominal_risk = sum(probability * value for probability, value in zip(nominal, loss))
    objective = sum(probability * value for probability, value in zip(adversarial, loss))
    lambda_candidates = {0.0}
    for distance, _, _ in moves:
        lambda_candidates.add(1.0 / distance)
    dual_values = []
    for multiplier in sorted(lambda_candidates):
        bound = multiplier * radius + sum(
            nominal[source]
            * max(loss[target] - multiplier * costs[source][target] for target in range(len(support)))
            for source in range(len(support))
        )
        dual_values.append((bound, multiplier))
    dual_bound, multiplier = min(dual_values) if dual_values else (objective, 0.0)
    return _finalize_certificate(
        {
            "schema_version": 1,
            "ambiguity_type": "geometry_wasserstein",
            "radius": float(radius),
            "solver": "exact_binary_loss_fractional_transport_and_finite_dual_breakpoints",
            "solver_status": "optimal",
            "optimality_proven": True,
            "nominal_risk": nominal_risk,
            "worst_case_risk": objective,
            "dual_bound": dual_bound,
            "dual_multiplier": multiplier,
            "optimality_gap": abs(dual_bound - objective),
            "distance_used": sum(item["cost"] for item in transfers),
            "loss_vector": loss,
            "nominal_pmf": nominal,
            "adversarial_pmf": adversarial,
            "transport_plan": transport,
            "geometry": dict(geometry),
            "bit_width": int(bit_width),
            "patterns_receiving_probability": _adversary_summary(support, nominal, adversarial),
        }
    )


def _category(pattern: SupportPattern, dimension: str, config: Mapping[str, Any]) -> str:
    if dimension == "family":
        return pattern.family
    if dimension == "multiplicity":
        return str(len(pattern.positions))
    if dimension == "adjacency_class":
        return _adjacency_class(pattern.positions)
    if dimension == "burst_length":
        return str(max(pattern.positions) - min(pattern.positions) + 1)
    if dimension in {"vdd", "temperature", "spatial_region"}:
        return str(pattern.metadata.get(dimension, "unspecified"))
    raise ValueError(f"unsupported structured interval dimension {dimension!r}")


def _interpolate(nominal: float, target: float, radius: float) -> float:
    return nominal + radius * (target - nominal)


def _structured_problem(
    support: Sequence[SupportPattern], ambiguity: Mapping[str, Any], radius: float
) -> dict[str, Any]:
    if not 0 <= radius <= 1:
        raise ValueError("structured interval radius scale must be in [0,1]")
    nominal = [item.nominal_probability for item in support]
    lower = [max(0.0, (1.0 - radius) * value) for value in nominal]
    upper = [min(1.0, value + radius * (1.0 - value)) for value in nominal]
    by_id = {item.pattern_id: index for index, item in enumerate(support)}
    for pattern_id, bounds in dict(ambiguity.get("pattern_intervals", {})).items():
        if pattern_id not in by_id:
            raise ValueError(f"pattern interval references unknown pattern {pattern_id!r}")
        index = by_id[pattern_id]
        lower[index] = _interpolate(nominal[index], float(bounds["lower"]), radius)
        upper[index] = _interpolate(nominal[index], float(bounds["upper"]), radius)
    constraints: list[dict[str, Any]] = []
    for dimension, categories in dict(ambiguity.get("category_intervals", {})).items():
        for category, bounds in dict(categories).items():
            indexes = [
                index
                for index, pattern in enumerate(support)
                if _category(pattern, dimension, ambiguity) == str(category)
            ]
            if not indexes:
                raise ValueError(f"structured category {dimension}:{category} matches no patterns")
            nominal_mass = sum(nominal[index] for index in indexes)
            constraints.append(
                {
                    "name": f"{dimension}:{category}",
                    "indexes": indexes,
                    "lower": _interpolate(nominal_mass, float(bounds["lower"]), radius),
                    "upper": _interpolate(nominal_mass, float(bounds["upper"]), radius),
                }
            )
    for aggregate in ambiguity.get("aggregate_intervals", []):
        members = [dict(member) for member in aggregate["members"]]
        indexes = [
            index
            for index, pattern in enumerate(support)
            if any(
                _category(pattern, str(member["dimension"]), ambiguity)
                == str(member["category"])
                for member in members
            )
        ]
        if not indexes:
            raise ValueError(f"structured aggregate {aggregate['name']!r} matches no patterns")
        nominal_mass = sum(nominal[index] for index in indexes)
        constraints.append(
            {
                "name": f"aggregate:{aggregate['name']}",
                "indexes": indexes,
                "lower": _interpolate(nominal_mass, float(aggregate["lower"]), radius),
                "upper": _interpolate(nominal_mass, float(aggregate["upper"]), radius),
                "members": members,
            }
        )
    return {"nominal": nominal, "lower": lower, "upper": upper, "constraints": constraints}


def solve_structured_intervals(
    support: Sequence[SupportPattern],
    losses: Sequence[int],
    radius: float,
    *,
    ambiguity: Mapping[str, Any],
) -> dict[str, Any]:
    loss = _validate_binary_losses(losses, support)
    problem = _structured_problem(support, ambiguity, radius)
    try:
        import numpy as np
        import scipy
        from scipy.optimize import linprog
    except ImportError as exc:  # pragma: no cover - environment-dependent guard
        raise RuntimeError("structured intervals require scipy.optimize.linprog") from exc
    count = len(support)
    a_ub: list[list[float]] = []
    b_ub: list[float] = []
    inequality_names: list[str] = []
    for constraint in problem["constraints"]:
        row = [1.0 if index in constraint["indexes"] else 0.0 for index in range(count)]
        a_ub.append(row)
        b_ub.append(float(constraint["upper"]))
        inequality_names.append(constraint["name"] + ":upper")
        a_ub.append([-value for value in row])
        b_ub.append(-float(constraint["lower"]))
        inequality_names.append(constraint["name"] + ":lower")
    result = linprog(
        c=[-float(value) for value in loss],
        A_ub=a_ub or None,
        b_ub=b_ub or None,
        A_eq=[[1.0] * count],
        b_eq=[1.0],
        bounds=list(zip(problem["lower"], problem["upper"])),
        method="highs",
    )
    if not result.success:
        raise ValueError(f"structured ambiguity LP is infeasible or failed: {result.message}")
    adversarial = [float(value) for value in result.x]
    inequality_marginals = [float(value) for value in result.ineqlin.marginals]
    equality_marginals = [float(value) for value in result.eqlin.marginals]
    lower_marginals = [float(value) for value in result.lower.marginals]
    upper_marginals = [float(value) for value in result.upper.marginals]
    dual_minimum = (
        float(np.dot(b_ub, inequality_marginals))
        + equality_marginals[0]
        + float(np.dot(problem["lower"], lower_marginals))
        + float(np.dot(problem["upper"], upper_marginals))
    )
    stationarity = np.array([-float(value) for value in loss])
    if a_ub:
        stationarity -= np.asarray(a_ub).T @ np.asarray(inequality_marginals)
    stationarity -= np.asarray([[1.0] * count]).T[:, 0] * equality_marginals[0]
    stationarity -= np.asarray(lower_marginals)
    stationarity -= np.asarray(upper_marginals)
    objective = -float(result.fun)
    dual_bound = -dual_minimum
    return _finalize_certificate(
        {
            "schema_version": 1,
            "ambiguity_type": "structured_interval",
            "radius": float(radius),
            "solver": "scipy.optimize.linprog_highs",
            "solver_version": scipy.__version__,
            "solver_status": "optimal",
            "solver_message": result.message,
            "optimality_proven": True,
            "nominal_risk": sum(
                probability * value for probability, value in zip(problem["nominal"], loss)
            ),
            "worst_case_risk": objective,
            "dual_bound": dual_bound,
            "optimality_gap": abs(dual_bound - objective),
            "loss_vector": loss,
            "nominal_pmf": problem["nominal"],
            "adversarial_pmf": adversarial,
            "pattern_lower_bounds": problem["lower"],
            "pattern_upper_bounds": problem["upper"],
            "category_constraints": problem["constraints"],
            "dual": {
                "inequality_names": inequality_names,
                "inequality_marginals": inequality_marginals,
                "equality_marginals": equality_marginals,
                "lower_marginals": lower_marginals,
                "upper_marginals": upper_marginals,
                "stationarity_max_abs": float(np.max(np.abs(stationarity))),
            },
            "patterns_receiving_probability": _adversary_summary(
                support, problem["nominal"], adversarial
            ),
        }
    )


def solve_worst_case(
    support: Sequence[SupportPattern],
    losses: Sequence[int],
    ambiguity: Mapping[str, Any],
    *,
    bit_width: int,
    radius: float | None = None,
) -> dict[str, Any]:
    kind = str(ambiguity["type"])
    selected_radius = float(ambiguity.get("radius", 0.0) if radius is None else radius)
    if kind == "total_variation":
        return solve_total_variation(support, losses, selected_radius)
    if kind == "geometry_wasserstein":
        return solve_geometry_wasserstein(
            support,
            losses,
            selected_radius,
            bit_width=bit_width,
            geometry=dict(ambiguity.get("geometry", {})),
        )
    if kind == "structured_interval":
        return solve_structured_intervals(
            support, losses, selected_radius, ambiguity=ambiguity
        )
    raise ValueError(f"unsupported ambiguity type {kind!r}")


def certified_safety_radius(
    support: Sequence[SupportPattern],
    losses: Sequence[int],
    ambiguity: Mapping[str, Any],
    *,
    bit_width: int,
    risk_limit: float,
    maximum_radius: float | None = None,
    tolerance: float = 1e-10,
) -> dict[str, Any]:
    if not 0 <= risk_limit <= 1:
        raise ValueError("risk_limit must be in [0,1]")
    kind = str(ambiguity["type"])
    upper = float(
        maximum_radius
        if maximum_radius is not None
        else ambiguity.get("maximum_radius", 1.0)
    )
    nominal_certificate = solve_worst_case(
        support, losses, ambiguity, bit_width=bit_width, radius=0.0
    )
    if nominal_certificate["worst_case_risk"] > risk_limit:
        return {
            "certified_radius": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 0.0,
            "status": "nominal_policy_already_exceeds_limit",
            "risk_at_zero": nominal_certificate["worst_case_risk"],
        }
    upper_certificate = solve_worst_case(
        support, losses, ambiguity, bit_width=bit_width, radius=upper
    )
    if upper_certificate["worst_case_risk"] <= risk_limit:
        return {
            "certified_radius": upper,
            "lower_bound": upper,
            "upper_bound": None,
            "status": "safe_through_configured_maximum_radius",
            "risk_at_radius": upper_certificate["worst_case_risk"],
            "ambiguity_type": kind,
        }
    lower = 0.0
    for _ in range(64):
        midpoint = (lower + upper) / 2.0
        certificate = solve_worst_case(
            support, losses, ambiguity, bit_width=bit_width, radius=midpoint
        )
        if certificate["worst_case_risk"] <= risk_limit:
            lower = midpoint
        else:
            upper = midpoint
        if upper - lower <= tolerance:
            break
    return {
        "certified_radius": lower,
        "lower_bound": lower,
        "upper_bound": upper,
        "status": "bounded_to_tolerance",
        "tolerance": tolerance,
        "ambiguity_type": kind,
        "risk_at_lower_bound": solve_worst_case(
            support, losses, ambiguity, bit_width=bit_width, radius=lower
        )["worst_case_risk"],
        "risk_above_upper_bound": solve_worst_case(
            support, losses, ambiguity, bit_width=bit_width, radius=upper
        )["worst_case_risk"],
    }
