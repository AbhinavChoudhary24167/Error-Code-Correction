"""Safety-first parity-matrix and abstaining-policy co-synthesis."""

from __future__ import annotations

import itertools
import time
from typing import Any, Mapping, Sequence

from .ambiguity import SupportPattern
from .gf2 import bit_string, matrix_columns_as_ints, syndrome_from_columns, systematic_matrices
from .hardware import hardware_key, structural_cost
from .robust import code_with_actions, compile_safe_decoder, evaluate_actions


def universally_safe_actions(
    code: Mapping[str, Any], support: Sequence[SupportPattern]
) -> dict[int, int]:
    """Maximal actions with zero SDC for every PMF over the declared support."""

    k, n = int(code["k"]), int(code["n"])
    data_mask = (1 << k) - 1
    columns = matrix_columns_as_ints(code["H"])
    grouped: dict[int, list[SupportPattern]] = {}
    for pattern in support:
        syndrome = syndrome_from_columns(pattern.mask, columns)
        if syndrome:
            grouped.setdefault(syndrome, []).append(pattern)
    actions: dict[int, int] = {}
    for syndrome, patterns in grouped.items():
        candidates = sorted({item.mask for item in patterns}, key=lambda mask: (mask.bit_count(), mask))
        safe = [
            candidate
            for candidate in candidates
            if all(((item.mask ^ candidate) & data_mask) == 0 for item in patterns)
        ]
        if safe:
            actions[syndrome] = safe[0]
    return actions


def _code_document(
    *, code_id: str, k: int, r: int, data_columns: Sequence[int], actions: Mapping[int, int]
) -> dict[str, Any]:
    h, g = systematic_matrices(data_columns, r)
    n = k + r
    code = {
        "schema_version": 1,
        "code_id": code_id,
        "code_class": "binary_systematic_linear_block",
        "baseline_kind": "SafeForge matrix-policy candidate",
        "k": k,
        "r": r,
        "n": n,
        "systematic": True,
        "H": h,
        "G": g,
        "column_syndromes": [bit_string(value, r) for value in matrix_columns_as_ints(h)],
        "decoder": {"type": "hard_decision_syndrome_table", "correction_entries": []},
        "constraints": {},
    }
    code = code_with_actions(code, actions, code_id_suffix="")
    code["code_id"] = code_id
    code["structural_hardware"] = structural_cost(h, g, actions, max_xor_fanin=2)
    return code


def _matrix_candidate(
    data_columns: Sequence[int], *, k: int, r: int, candidate_id: str
) -> dict[str, Any]:
    h, g = systematic_matrices(data_columns, r)
    return {
        "schema_version": 1,
        "code_id": candidate_id,
        "code_class": "binary_systematic_linear_block",
        "baseline_kind": "SafeForge matrix-policy candidate",
        "k": k,
        "r": r,
        "n": k + r,
        "systematic": True,
        "H": h,
        "G": g,
        "column_syndromes": [bit_string(value, r) for value in matrix_columns_as_ints(h)],
        "decoder": {"type": "hard_decision_syndrome_table", "correction_entries": []},
        "constraints": {},
    }


def _score_candidate(
    candidate: Mapping[str, Any],
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    *,
    raw_fit: float | None,
    residual_fit_limit: float | None,
) -> tuple[tuple[Any, ...], dict[str, Any], dict[int, int]] | None:
    actions = universally_safe_actions(candidate, support)
    evaluated = evaluate_actions(
        candidate, support, actions, ambiguity, bit_width=int(candidate["n"])
    )
    if evaluated["worst_case"]["sdc"] > 1e-14:
        return None
    worst_fit = (
        None if raw_fit is None else raw_fit * float(evaluated["worst_case"]["residual"])
    )
    if residual_fit_limit is not None and (worst_fit is None or worst_fit > residual_fit_limit + 1e-12):
        return None
    h, g = candidate["H"], candidate["G"]
    hardware = structural_cost(h, g, actions, max_xor_fanin=2)
    key = (
        float(evaluated["worst_case"]["due"]),
        float(evaluated["nominal"]["due"]),
        hardware_key(hardware),
        tuple(matrix_columns_as_ints(h)[: int(candidate["k"])]),
    )
    return key, {**evaluated, "worst_case_residual_fit": worst_fit, "hardware": hardware}, actions


def cosynthesize_exact_small(
    *,
    k: int,
    r: int,
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    code_id: str,
    sdc_limit: float = 0.0,
    raw_fit: float | None = None,
    residual_fit_limit: float | None = None,
) -> dict[str, Any]:
    """Enumerate every ordered systematic SEC matrix and its maximal zero-SDC policy."""

    if r > 4:
        raise ValueError("exact SafeForge co-synthesis is intentionally limited to r<=4")
    if sdc_limit != 0:
        raise ValueError("exact matrix co-synthesis currently proves the strict sdc_limit=0 case")
    started = time.perf_counter()
    basis = {1 << row for row in range(r)}
    available = [value for value in range(1, 1 << r) if value not in basis]
    theoretical = 1
    for offset in range(k):
        theoretical *= len(available) - offset
    best: tuple[tuple[Any, ...], dict[str, Any], dict[int, int], tuple[int, ...]] | None = None
    evaluated_count = 0
    feasible_count = 0
    for columns in itertools.permutations(available, k):
        evaluated_count += 1
        candidate = _matrix_candidate(columns, k=k, r=r, candidate_id=code_id)
        scored = _score_candidate(
            candidate,
            support,
            ambiguity,
            raw_fit=raw_fit,
            residual_fit_limit=residual_fit_limit,
        )
        if scored is None:
            continue
        feasible_count += 1
        key, report, actions = scored
        record = (key, report, actions, columns)
        if best is None or record[0] < best[0]:
            best = record
    if best is None:
        raise ValueError("no matrix-policy pair satisfies the robust constraints")
    _, report, actions, columns = best
    code = _code_document(code_id=code_id, k=k, r=r, data_columns=columns, actions=actions)
    return {
        "schema_version": 1,
        "method": "exact_ordered_systematic_matrix_enumeration_with_maximal_support_safe_policy",
        "status": "optimal",
        "optimality_proven": True,
        "optimality_scope": (
            "all ordered selections of k distinct nonzero non-basis r-bit data columns; "
            "all selected corrections are SDC-free for every distribution on the declared support"
        ),
        "sdc_limit": 0.0,
        "candidate_matrices_evaluated": evaluated_count,
        "theoretical_candidate_matrices": theoretical,
        "feasible_candidate_matrices": feasible_count,
        "runtime_seconds": time.perf_counter() - started,
        "code": code,
        "verification": report,
    }


def cosynthesize_scalable_verified_heuristic(
    base_code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    *,
    code_id: str,
    raw_fit: float | None = None,
    residual_fit_limit: float | None = None,
) -> dict[str, Any]:
    """Deterministically explore physical data-column mappings, then certify the winner."""

    k, r = int(base_code["k"]), int(base_code["r"])
    original = matrix_columns_as_ints(base_code["H"])[:k]
    candidates: list[tuple[int, ...]] = [tuple(original)]
    candidates.extend(
        tuple(original[(index + shift) % k] for index in range(k))
        for shift in range(1, min(k, 16))
    )
    candidates.extend(
        tuple(
            original[index + 1] if index == swap else original[index - 1] if index == swap + 1 else original[index]
            for index in range(k)
        )
        for swap in range(k - 1)
    )
    candidates = list(dict.fromkeys(candidates))
    best = None
    for index, columns in enumerate(candidates):
        candidate = _matrix_candidate(columns, k=k, r=r, candidate_id=code_id)
        scored = _score_candidate(
            candidate,
            support,
            ambiguity,
            raw_fit=raw_fit,
            residual_fit_limit=residual_fit_limit,
        )
        if scored is not None and (best is None or scored[0] < best[0]):
            best = (*scored, columns, index)
    if best is None:
        raise ValueError("no heuristic mapping satisfies the robust constraints")
    key, report, actions, columns, winner_index = best
    code = _code_document(code_id=code_id, k=k, r=r, data_columns=columns, actions=actions)
    return {
        "schema_version": 1,
        "method": "deterministic_physical_column_mapping_search_with_independent_full_support_verification",
        "status": "feasible_verified_heuristic",
        "optimality_proven": False,
        "candidate_mappings_evaluated": len(candidates),
        "winning_candidate_index": winner_index,
        "base_matrix_changed": list(columns) != list(original),
        "code": code,
        "verification": report,
    }
