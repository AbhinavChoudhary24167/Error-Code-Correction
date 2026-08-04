"""Finite, auditable placement and exact syndrome-policy co-design.

A placement assigns the *unchanged multiset* of Hsiao data columns to physical data
bit positions.  Parity positions are fixed in the current production-compatible
domain.  Exactness claims are limited to the enumerated, constraint-filtered
placement library.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from .ambiguity import SupportPattern
from .certificates import canonical_hash
from .exact_policy import compile_exact_robust_policy
from .gf2 import bit_string, matrix_columns_as_ints, syndrome_from_columns, systematic_matrices
from .robust import code_with_actions, evaluate_actions


def _placement_cost(mapping: Sequence[int]) -> dict[str, Any]:
    displacement = [abs(physical - logical) for physical, logical in enumerate(mapping)]
    return {
        "maximum_data_displacement_bits": max(displacement, default=0),
        "total_data_displacement_bits": sum(displacement),
        "moved_data_bits": sum(value != index for index, value in enumerate(mapping)),
        "routing_model": "logical-to-physical bit-index displacement proxy; not routed wirelength",
    }


def _valid_mapping(mapping: Sequence[int], k: int) -> bool:
    return len(mapping) == k and sorted(int(value) for value in mapping) == list(range(k))


def _satisfies_constraints(mapping: Sequence[int], constraints: Mapping[str, Any]) -> bool:
    k = len(mapping)
    if not _valid_mapping(mapping, k):
        return False
    cost = _placement_cost(mapping)
    maximum = constraints.get("maximum_data_displacement_bits")
    if maximum is not None and cost["maximum_data_displacement_bits"] > int(maximum):
        return False
    total = constraints.get("maximum_total_data_displacement_bits")
    if total is not None and cost["total_data_displacement_bits"] > int(total):
        return False
    fixed = {int(value) for value in constraints.get("fixed_data_positions", [])}
    if any(int(mapping[position]) != position for position in fixed):
        return False
    if constraints.get("preserve_bank_membership", False):
        banks = [tuple(int(value) for value in bank) for bank in constraints.get("data_banks", [])]
        membership = {
            position: bank_index
            for bank_index, bank in enumerate(banks)
            for position in bank
        }
        if set(membership) != set(range(k)):
            raise ValueError("data_banks must partition all data positions")
        if any(membership[physical] != membership[int(logical)] for physical, logical in enumerate(mapping)):
            return False
    return True


def enumerate_placement_library(
    code: Mapping[str, Any], constraints: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Enumerate a deterministic finite library and filter it by physical rules."""

    k, n = int(code["k"]), int(code["n"])
    if n - k != int(code["r"]):
        raise ValueError("placement library requires a systematic k+r code")
    allowed = set(
        constraints.get(
            "allowed_families",
            ["identity", "interleaved", "cyclic", "adjacent_swap", "bank_rotation"],
        )
    )
    candidates: list[tuple[str, str, tuple[int, ...]]] = []
    identity = tuple(range(k))
    if "identity" in allowed:
        candidates.append(("conventional-fixed", "identity", identity))
    if "interleaved" in allowed and k > 1:
        mapping = tuple(list(range(0, k, 2)) + list(range(1, k, 2)))
        candidates.append(("even-odd-interleave", "interleaved", mapping))
    if "cyclic" in allowed:
        for shift in range(1, min(k, int(constraints.get("cyclic_shift_count", 15)) + 1)):
            candidates.append(
                (f"cyclic-{shift:02d}", "cyclic", tuple((index + shift) % k for index in range(k)))
            )
    if "adjacent_swap" in allowed:
        for swap in range(k - 1):
            mapping = list(identity)
            mapping[swap], mapping[swap + 1] = mapping[swap + 1], mapping[swap]
            candidates.append((f"adjacent-swap-{swap:02d}", "adjacent_swap", tuple(mapping)))
    if "bank_rotation" in allowed:
        bank_size = int(constraints.get("bank_rotation_size", 8))
        if bank_size > 1 and k % bank_size == 0:
            for shift in range(1, bank_size):
                mapping = []
                for start in range(0, k, bank_size):
                    mapping.extend(start + ((offset + shift) % bank_size) for offset in range(bank_size))
                candidates.append((f"bank{bank_size}-rotate-{shift}", "bank_rotation", tuple(mapping)))

    unique: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    for placement_id, family, mapping in candidates:
        if mapping in seen or not _satisfies_constraints(mapping, constraints):
            continue
        seen.add(mapping)
        cost = _placement_cost(mapping)
        document = {
            "placement_id": placement_id,
            "family": family,
            "physical_data_position_to_logical_column": list(mapping),
            "physical_parity_positions": list(range(k, n)),
            "parity_placement": "fixed",
            "constraints_sha256": canonical_hash(dict(constraints)),
            "cost": cost,
        }
        document["placement_sha256"] = canonical_hash(document)
        unique.append(document)
    if not unique or unique[0]["family"] != "identity":
        raise ValueError("physical constraints exclude the mandatory conventional placement")
    return unique


def apply_data_column_placement(
    base_code: Mapping[str, Any], placement: Mapping[str, Any]
) -> dict[str, Any]:
    """Assign the original Hsiao data-column multiset to physical data positions."""

    k, r = int(base_code["k"]), int(base_code["r"])
    mapping = [int(value) for value in placement["physical_data_position_to_logical_column"]]
    if not _valid_mapping(mapping, k):
        raise ValueError("placement is not a permutation of data-column indexes")
    original = matrix_columns_as_ints(base_code["H"])
    if original[k:] != [1 << row for row in range(r)]:
        raise ValueError("current placement domain requires conventional fixed parity basis columns")
    data_columns = [original[logical] for logical in mapping]
    h, g = systematic_matrices(data_columns, r)
    result = copy.deepcopy(dict(base_code))
    result["code_id"] = f"{base_code.get('code_id', 'fixed-code')}-placement-{placement['placement_id']}"
    result["H"] = h
    result["G"] = g
    result["column_syndromes"] = [bit_string(value, r) for value in matrix_columns_as_ints(h)]
    conventional_actions = {value: 1 << position for position, value in enumerate(matrix_columns_as_ints(h))}
    result = code_with_actions(result, conventional_actions, code_id_suffix="")
    result["placement"] = dict(placement)
    result["equivalence_scope"] = {
        "data_column_multiset_preserved": sorted(data_columns) == sorted(original[:k]),
        "parity_columns_fixed": matrix_columns_as_ints(h)[k:] == original[k:],
        "new_code_claim": False,
    }
    return result


def _placement_only_collision_score(
    code: Mapping[str, Any], support: Sequence[SupportPattern]
) -> dict[str, Any]:
    """Score syndrome isolation without selecting a decoder policy."""

    columns = matrix_columns_as_ints(code["H"])
    k = int(code["k"])
    data_mask = (1 << k) - 1
    groups: dict[int, list[int]] = {}
    for index, pattern in enumerate(support):
        syndrome = syndrome_from_columns(pattern.mask, columns)
        if syndrome:
            groups.setdefault(syndrome, []).append(index)
    protected_indexes: set[int] = set()
    for indexes in groups.values():
        for candidate in sorted({support[index].mask for index in indexes}):
            if all(((support[index].mask ^ candidate) & data_mask) == 0 for index in indexes):
                protected_indexes.update(indexes)
                break
    protected_nominal = sum(
        pattern.nominal_probability
        for index, pattern in enumerate(support)
        if index in protected_indexes
    )
    return {
        "objective": "maximize nominal mass in support-universal syndrome-isolated groups",
        "protected_nominal_probability": protected_nominal,
        "unprotected_nominal_probability": 1.0 - protected_nominal,
        "protected_support_pattern_count": len(protected_indexes),
        "support_pattern_count": len(support),
        "uses_decoder_action_selection": False,
    }


def optimize_placement_and_policy(
    base_code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    *,
    sdc_limit: float,
    placement_constraints: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate every allowed placement and report exactness only over that library."""

    placements = enumerate_placement_library(base_code, placement_constraints)
    candidates: list[dict[str, Any]] = []
    full_policies: dict[str, dict[str, Any]] = {}
    for placement in placements:
        code = apply_data_column_placement(base_code, placement)
        conventional_actions = {
            int(str(entry["syndrome"]), 2): sum(
                1 << int(position) for position in entry["positions"]
            )
            for entry in code["decoder"]["correction_entries"]
        }
        conventional = evaluate_actions(
            code, support, conventional_actions, ambiguity, bit_width=int(code["n"])
        )
        try:
            policy = compile_exact_robust_policy(
                code,
                support,
                ambiguity,
                sdc_limit=sdc_limit,
                verified_fallback_available=True,
            )
            policy_status = "feasible"
            full_policies[placement["placement_id"]] = policy
            policy_metrics = {
                "nominal": policy["metrics"]["nominal"],
                "worst_case": policy["metrics"]["worst_case"],
                "selected_correction_count": policy["selected_correction_count"],
                "a_posteriori_absolute_gap": policy["optimization"]["a_posteriori_absolute_gap"],
                "policy_id": policy["policy_id"],
            }
        except ValueError as exc:
            policy_status = "infeasible"
            policy_metrics = {"reason": str(exc)}
        candidates.append(
            {
                "placement": placement,
                "placement_only_collision_score": _placement_only_collision_score(code, support),
                "conventional_decoder": {
                    "nominal": conventional["nominal"],
                    "worst_case": conventional["worst_case"],
                },
                "optimized_policy_status": policy_status,
                "optimized_policy": policy_metrics,
            }
        )

    feasible = [item for item in candidates if item["optimized_policy_status"] == "feasible"]
    if not feasible:
        raise ValueError("no placement in the declared library has a feasible syndrome policy")
    identity = next(item for item in candidates if item["placement"]["family"] == "identity")
    interleaved = next(
        (item for item in candidates if item["placement"]["family"] == "interleaved"), None
    )
    fault_aware_conventional = min(
        candidates,
        key=lambda item: (
            float(item["conventional_decoder"]["worst_case"]["sdc"]),
            float(item["conventional_decoder"]["worst_case"]["due"]),
            float(item["conventional_decoder"]["nominal"]["sdc"]),
            item["placement"]["cost"]["total_data_displacement_bits"],
            item["placement"]["placement_id"],
        ),
    )
    sequential = min(
        feasible,
        key=lambda item: (
            float(item["placement_only_collision_score"]["unprotected_nominal_probability"]),
            -int(item["placement_only_collision_score"]["protected_support_pattern_count"]),
            item["placement"]["cost"]["total_data_displacement_bits"],
            item["placement"]["placement_id"],
        ),
    )
    joint = min(
        feasible,
        key=lambda item: (
            float(item["optimized_policy"]["worst_case"]["due"]),
            float(item["optimized_policy"]["nominal"]["due"]),
            item["placement"]["cost"]["total_data_displacement_bits"],
            item["placement"]["placement_id"],
        ),
    )
    selected_ids = {
        "policy_only": identity["placement"]["placement_id"],
        "fault_aware_conventional": fault_aware_conventional["placement"]["placement_id"],
        "sequential": sequential["placement"]["placement_id"],
        "joint": joint["placement"]["placement_id"],
    }
    result = {
        "schema_version": 1,
        "method": "exact_selection_over_constraint_filtered_finite_placement_library",
        "fixed_code_id": str(base_code.get("code_id", "external-code")),
        "fixed_matrix_sha256": canonical_hash(base_code["H"]),
        "algebraic_code_changed": False,
        "placement_constraints": dict(placement_constraints),
        "placement_library_size": len(candidates),
        "candidate_table": candidates,
        "baselines": {
            "conventional_fixed_placement_conventional_decoder": identity["conventional_decoder"],
            "conventional_placement_optimized_policy": identity["optimized_policy"],
            "interleaved_placement_conventional_decoder": (
                None if interleaved is None else interleaved["conventional_decoder"]
            ),
            "fault_aware_placement_conventional_decoder": fault_aware_conventional[
                "conventional_decoder"
            ],
            "sequential_placement_then_policy": sequential["optimized_policy"],
            "joint_placement_and_policy": joint["optimized_policy"],
        },
        "selected_placement_ids": selected_ids,
        "joint_optimality": {
            "proven_over_declared_library": True,
            "absolute_gap_over_declared_library": 0.0,
            "global_permutation_optimality_claim": False,
            "excluded_domain": "all other data-column permutations and non-fixed parity placements",
        },
        "selected_policies": {
            name: full_policies[placement_id]
            for name, placement_id in selected_ids.items()
            if placement_id in full_policies
        },
    }
    result["study_sha256"] = canonical_hash(result)
    return result
