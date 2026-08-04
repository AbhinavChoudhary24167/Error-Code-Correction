import json
from pathlib import Path

from codeforge.ambiguity import build_support
from codeforge.faults import load_fault_distribution
from codeforge.gf2 import matrix_columns_as_ints
from codeforge.placement_policy import (
    apply_data_column_placement,
    enumerate_placement_library,
    optimize_placement_and_policy,
)


ROOT = Path(__file__).resolve().parents[2]


def _fixture():
    code = json.loads(
        (ROOT / "reports/code_synthesis/baselines/odd_column_secded_code.json").read_text()
    )
    nominal = load_fault_distribution(
        "configs/fault_distributions/small_hotspot_8bit.json", repo_root=ROOT
    )
    support = build_support(nominal)
    return code, support


def test_placement_preserves_the_fixed_code_column_multiset():
    code, _ = _fixture()
    placements = enumerate_placement_library(
        code,
        {"allowed_families": ["identity", "interleaved", "adjacent_swap"]},
    )
    placed = apply_data_column_placement(code, placements[-1])
    before = matrix_columns_as_ints(code["H"])
    after = matrix_columns_as_ints(placed["H"])
    assert sorted(before[: code["k"]]) == sorted(after[: code["k"]])
    assert before[code["k"] :] == after[code["k"] :]
    assert not placed["equivalence_scope"]["new_code_claim"]


def test_bank_constraints_filter_cross_bank_permutations():
    code, _ = _fixture()
    placements = enumerate_placement_library(
        code,
        {
            "allowed_families": ["identity", "interleaved", "adjacent_swap"],
            "preserve_bank_membership": True,
            "data_banks": [[0, 1], [2, 3]],
        },
    )
    assert all(item["family"] != "interleaved" for item in placements)


def test_joint_result_is_exact_only_over_declared_library():
    code, support = _fixture()
    result = optimize_placement_and_policy(
        code,
        support,
        {"ambiguity_id": "test-tv", "type": "total_variation", "radius": 0.02},
        sdc_limit=0.001,
        placement_constraints={
            "allowed_families": ["identity", "interleaved", "adjacent_swap"],
        },
    )
    assert result["joint_optimality"]["proven_over_declared_library"]
    assert not result["joint_optimality"]["global_permutation_optimality_claim"]
    assert result["placement_library_size"] >= 2
