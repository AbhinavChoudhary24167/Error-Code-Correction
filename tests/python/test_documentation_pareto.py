from __future__ import annotations

import math

from green_ecc_phy.pareto_validation import (
    Objective,
    crowding_distance,
    hypervolume_2d,
    knee_point,
    pareto_front,
)


MIN_X = Objective("x", lambda item: item.get("x"), "min")
MIN_Y = Objective("y", lambda item: item.get("y"), "min")


def candidate(identifier: str, x: float | None, y: float | None, **extra):
    return {"implementation_id": identifier, "x": x, "y": y, "eligible": True, **extra}


def identifiers(front):
    return [item["implementation_id"] for item in front]


def test_dominated_equal_and_one_candidate_fronts():
    front, excluded = pareto_front(
        [candidate("a", 1, 2), candidate("b", 2, 3), candidate("a-duplicate", 1, 2)],
        [MIN_X, MIN_Y],
    )
    assert identifiers(front) == ["a", "a-duplicate"]
    assert excluded == {}
    assert identifiers(pareto_front([candidate("only", 4, 5)], [MIN_X, MIN_Y])[0]) == ["only"]


def test_mixed_direction_and_tie_handling():
    maximize_y = Objective("y", lambda item: item.get("y"), "max")
    front, _ = pareto_front(
        [candidate("trade-a", 1, 2), candidate("trade-b", 2, 4), candidate("dominated", 3, 1)],
        [MIN_X, maximize_y],
    )
    assert identifiers(front) == ["trade-a", "trade-b"]


def test_null_rejected_infeasible_and_no_candidate_fronts():
    records = [
        candidate("null", None, 1),
        candidate("rejected", 1, 1, eligible=False),
        candidate("infeasible", 1, 1, feasible=False),
    ]
    front, excluded = pareto_front(
        records,
        [MIN_X, MIN_Y],
        eligibility=lambda item: item["eligible"] and item.get("feasible", True),
    )
    assert front == []
    assert excluded == {
        "infeasible": "ineligible_or_hard_constraint_failed",
        "null": "null_objective",
        "rejected": "ineligible_or_hard_constraint_failed",
    }


def test_epsilon_boundary_preserves_equivalent_points():
    objectives = [Objective("x", lambda item: item.get("x"), "min", epsilon=0.1), MIN_Y]
    front, _ = pareto_front(
        [candidate("base", 1.0, 1.0), candidate("within", 1.05, 1.0), candidate("outside", 1.11, 1.0)],
        objectives,
    )
    assert identifiers(front) == ["base", "within"]


def test_crowding_knee_and_hypervolume_are_hand_verifiable():
    records = [candidate("left", 1, 4), candidate("knee", 2, 2), candidate("right", 4, 1)]
    distances = crowding_distance(records, [MIN_X, MIN_Y])
    assert math.isinf(distances["left"])
    assert math.isinf(distances["right"])
    assert distances["knee"] > 0
    assert knee_point(records, MIN_X, MIN_Y)["implementation_id"] == "knee"
    assert hypervolume_2d(records, MIN_X, MIN_Y, (5, 5)) == 11.0


def test_empty_crowding_knee_and_hypervolume():
    assert crowding_distance([], [MIN_X, MIN_Y]) == {}
    assert knee_point([], MIN_X, MIN_Y) is None
    assert hypervolume_2d([], MIN_X, MIN_Y, (1, 1)) == 0.0
