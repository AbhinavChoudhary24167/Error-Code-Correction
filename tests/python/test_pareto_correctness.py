from __future__ import annotations

import pytest

from analysis.pareto import dominates, pareto_partition


def test_dominates_minimise_and_maximise() -> None:
    left = {"fit": 1.0, "score": 9.0}
    right = {"fit": 2.0, "score": 8.0}
    assert dominates(left, right, objectives={"fit": "min", "score": "max"})


def test_pareto_partition_handles_ties_without_dropping_duplicates() -> None:
    records = [
        {"code": "a", "fit": 1.0, "carbon": 2.0},
        {"code": "b", "fit": 1.0, "carbon": 2.0},
        {"code": "c", "fit": 1.2, "carbon": 2.4},
    ]
    part = pareto_partition(records, objectives={"fit": "min", "carbon": "min"})
    assert part.frontier_indices == [0, 1]
    assert part.dominated_indices == [2]


def test_pareto_partition_is_deterministic_and_traceable() -> None:
    records = [
        {"row_id": "r0", "fit": 5.0, "carbon": 5.0},
        {"row_id": "r1", "fit": 4.0, "carbon": 7.0},
        {"row_id": "r2", "fit": 6.0, "carbon": 3.0},
        {"row_id": "r3", "fit": 7.0, "carbon": 8.0},
    ]
    part_a = pareto_partition(records, objectives={"fit": "min", "carbon": "min"})
    part_b = pareto_partition(records, objectives={"fit": "min", "carbon": "min"})
    assert part_a == part_b
    assert part_a.frontier_indices == [0, 1, 2]
    assert [records[i]["row_id"] for i in part_a.frontier_indices] == ["r0", "r1", "r2"]


def test_invalid_objective_direction_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported objective direction"):
        pareto_partition([{"fit": 1.0}], objectives={"fit": "lower-is-better"})
