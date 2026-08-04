"""Deterministic beam search with independent exact post-verification."""

from __future__ import annotations

from collections import defaultdict
import math
import random
import time
from typing import Any, Mapping, Sequence

from .exact import ExactSynthesisResult
from .faults import ErrorPattern, FaultDistribution
from .gf2 import (
    bit_string,
    matrix_columns_as_ints,
    syndrome_from_columns,
    systematic_matrices,
)
from .hardware import hardware_key, structural_cost


def _families(distribution: FaultDistribution, names: Sequence[str]) -> list[ErrorPattern]:
    selected = set(names)
    return [pattern for pattern in distribution.patterns if pattern.family in selected]


def _greedy_decoder(
    h: Sequence[Sequence[int]],
    distribution: FaultDistribution,
    mandatory_patterns: Sequence[ErrorPattern],
    detect_only_patterns: Sequence[ErrorPattern],
    max_sdc_probability: float,
) -> tuple[dict[int, int], dict[str, float]] | None:
    """Construct a feasible decoder greedily; never reports decoder optimality."""

    n = distribution.bit_width
    h_columns = matrix_columns_as_ints(h)
    mandatory_ids = {pattern.pattern_id for pattern in mandatory_patterns}
    detect_ids = {pattern.pattern_id for pattern in detect_only_patterns}
    mandatory: dict[int, ErrorPattern] = {}
    corrected = 0.0
    for pattern in mandatory_patterns:
        syn = syndrome_from_columns(pattern.mask(n), h_columns)
        if syn == 0 or syn in mandatory:
            return None
        mandatory[syn] = pattern
        corrected += pattern.probability
    protected_detect_syndromes: set[int] = set()
    for pattern in detect_only_patterns:
        syn = syndrome_from_columns(pattern.mask(n), h_columns)
        if syn == 0 or syn in mandatory:
            return None
        protected_detect_syndromes.add(syn)

    base_sdc = 0.0
    groups: dict[int, list[ErrorPattern]] = defaultdict(list)
    for pattern in distribution.patterns:
        if pattern.pattern_id in mandatory_ids:
            continue
        syn = syndrome_from_columns(pattern.mask(n), h_columns)
        if syn == 0 or syn in mandatory:
            base_sdc += pattern.probability
        elif pattern.pattern_id not in detect_ids and syn not in protected_detect_syndromes:
            groups[syn].append(pattern)
    if base_sdc > max_sdc_probability + 1e-15:
        return None

    choices: list[tuple[float, float, int, ErrorPattern]] = []
    for syn, patterns in groups.items():
        best = min(
            patterns,
            key=lambda pattern: (-pattern.probability, len(pattern.positions), pattern.positions),
        )
        induced_sdc = math.fsum(item.probability for item in patterns) - best.probability
        choices.append((best.probability, induced_sdc, syn, best))
    choices.sort(
        key=lambda item: (
            0 if item[1] == 0 else 1,
            -(item[0] / item[1]) if item[1] > 0 else -math.inf,
            -item[0],
            item[1],
            item[2],
        )
    )
    decoder = {syn: pattern.mask(n) for syn, pattern in mandatory.items()}
    sdc = base_sdc
    for gain, induced_sdc, syn, pattern in choices:
        if sdc + induced_sdc <= max_sdc_probability + 1e-15:
            decoder[syn] = pattern.mask(n)
            corrected += gain
            sdc += induced_sdc
    return decoder, {
        "corrected": corrected,
        "sdc": sdc,
        "due": max(0.0, 1.0 - corrected - sdc),
    }


def synthesize_scalable(
    config: Mapping[str, Any], distribution: FaultDistribution
) -> ExactSynthesisResult:
    """Search matrices heuristically and rely on :mod:`codeforge.verify` for certification."""

    started = time.perf_counter()
    k, r = int(config["k"]), int(config["r"])
    n = k + r
    if distribution.bit_width != n:
        raise ValueError(f"fault distribution width {distribution.bit_width} must equal k+r={n}")
    search_cfg = config.get("search", {})
    timeout = float(search_cfg.get("timeout_seconds", 60.0))
    seed = int(search_cfg.get("seed", 0))
    rng = random.Random(seed)
    beam_width = int(search_cfg.get("beam_width", 8))
    iterations = int(search_cfg.get("iterations", 50))
    mutations = int(search_cfg.get("mutations_per_candidate", 16))
    if min(beam_width, iterations, mutations) <= 0:
        raise ValueError("beam_width, iterations, and mutations_per_candidate must be positive")
    decoder_policy = config.get("decoder_policy", {})
    mandatory = _families(distribution, decoder_policy.get("mandatory_correct_families", []))
    detect_only = _families(distribution, decoder_policy.get("detect_only_families", []))
    constraints = config.get("constraints", {})
    max_sdc = float(constraints.get("max_sdc_probability", 1.0))
    matrix_cfg = config.get("matrix_constraints", {})
    min_col_weight = int(matrix_cfg.get("min_data_column_weight", 1))
    max_col_weight = int(matrix_cfg.get("max_data_column_weight", r))
    min_row_weight = int(matrix_cfg.get("min_row_weight", 1))
    max_row_weight = int(matrix_cfg.get("max_row_weight", n))
    max_matrix_xors = constraints.get("max_matrix_xor_gates")
    max_xor_fanin = int(config.get("hardware_model", {}).get("max_xor_fanin", 2))
    hardware_aware = bool(config.get("hardware_model", {}).get("hardware_aware", True))
    parity_columns = {1 << row for row in range(r)}
    require_sbu = "sbu" in decoder_policy.get("mandatory_correct_families", [])
    pool = [
        value
        for value in range(1, 1 << r)
        if min_col_weight <= value.bit_count() <= max_col_weight
        and (not require_sbu or value not in parity_columns)
    ]
    if len(pool) < k:
        raise ValueError("matrix column constraints leave fewer than k distinct data columns")

    cache: dict[tuple[int, ...], tuple[tuple[Any, ...], dict[str, Any]] | None] = {}
    evaluated = 0

    def evaluate(columns: tuple[int, ...]) -> tuple[tuple[Any, ...], dict[str, Any]] | None:
        nonlocal evaluated
        if columns in cache:
            return cache[columns]
        evaluated += 1
        h, g = systematic_matrices(columns, r)
        row_weights = [sum(row) for row in h]
        if any(weight < min_row_weight or weight > max_row_weight for weight in row_weights):
            cache[columns] = None
            return None
        selected = _greedy_decoder(h, distribution, mandatory, detect_only, max_sdc)
        if selected is None:
            cache[columns] = None
            return None
        decoder, probability = selected
        cost = structural_cost(h, g, decoder, max_xor_fanin=max_xor_fanin)
        if max_matrix_xors is not None and cost["matrix_xor_gates"] > int(max_matrix_xors):
            cache[columns] = None
            return None
        reliability_key: tuple[Any, ...] = (
            -round(probability["corrected"], 15),
            round(probability["sdc"], 15),
        )
        key = (
            *reliability_key,
            *(hardware_key(cost) if hardware_aware else ()),
            columns,
        )
        payload = {
            "h": h,
            "g": g,
            "decoder": decoder,
            "probability": probability,
            "cost": cost,
        }
        cache[columns] = (key, payload)
        return cache[columns]

    odd_first = sorted(pool, key=lambda value: (value.bit_count() % 2 == 0, value.bit_count(), value))
    initial: set[tuple[int, ...]] = {tuple(odd_first[:k])}
    while len(initial) < beam_width:
        initial.add(tuple(rng.sample(pool, k)))
    beam = sorted((item for columns in initial if (item := evaluate(columns)) is not None), key=lambda item: item[0])[:beam_width]
    if not beam:
        return ExactSynthesisResult(
            code=None,
            search={
                "method": "deterministic_beam_search",
                "status": "infeasible_initial_beam",
                "runtime_seconds": time.perf_counter() - started,
                "search_complete": False,
                "optimality_proven": False,
            },
        )

    trajectory: list[dict[str, Any]] = []
    completed_iterations = 0
    timed_out = False
    for iteration in range(iterations):
        if time.perf_counter() - started >= timeout:
            timed_out = True
            break
        candidates: set[tuple[int, ...]] = set()
        for _, payload in beam:
            columns = tuple(matrix_columns_as_ints(payload["h"])[:k])
            candidates.add(columns)
            used = set(columns)
            for mutation_index in range(mutations):
                proposal = list(columns)
                if mutation_index % 2 == 0:
                    left, right = rng.sample(range(k), 2)
                    proposal[left], proposal[right] = proposal[right], proposal[left]
                else:
                    position = rng.randrange(k)
                    available = [value for value in pool if value not in used or value == proposal[position]]
                    proposal[position] = rng.choice(available)
                    if len(set(proposal)) != k:
                        continue
                candidates.add(tuple(proposal))
        evaluated_candidates = [item for columns in candidates if (item := evaluate(columns)) is not None]
        beam = sorted(evaluated_candidates, key=lambda item: item[0])[:beam_width]
        completed_iterations += 1
        best_key, best_payload = beam[0]
        trajectory.append(
            {
                "iteration": iteration,
                "corrected_probability": best_payload["probability"]["corrected"],
                "sdc_probability": best_payload["probability"]["sdc"],
                "matrix_xor_gates": best_payload["cost"]["matrix_xor_gates"],
                "decoder_entries": best_payload["cost"]["decoder"]["syndrome_table_entries"],
            }
        )

    _, payload = beam[0]
    h, g = payload["h"], payload["g"]
    decoder_entries = [
        {
            "syndrome": bit_string(syn, r),
            "positions": [position for position in range(n) if (mask >> position) & 1],
        }
        for syn, mask in sorted(payload["decoder"].items())
    ]
    search = {
        "method": "deterministic_beam_search_with_greedy_decoder_assignment",
        "solver_dependency": None,
        "status": "feasible_timeout" if timed_out else "feasible_heuristic",
        "runtime_seconds": time.perf_counter() - started,
        "timeout_seconds": timeout,
        "seed": seed,
        "beam_width": beam_width,
        "iteration_budget": iterations,
        "iterations_completed": completed_iterations,
        "mutations_per_candidate": mutations,
        "candidate_matrices_evaluated": evaluated,
        "search_complete": False,
        "optimality_proven": False,
        "trajectory": trajectory,
        "certification": "candidate must pass the independent exhaustive-error verifier",
        "hardware_aware_tie_break": hardware_aware,
    }
    code = {
        "schema_version": 1,
        "code_id": str(config["code_id"]),
        "code_class": "binary_systematic_linear_block",
        "k": k,
        "r": r,
        "n": n,
        "systematic": True,
        "H": h,
        "G": g,
        "column_syndromes": [bit_string(value, r) for value in matrix_columns_as_ints(h)],
        "decoder": {"type": "hard_decision_syndrome_table", "correction_entries": decoder_entries},
        "constraints": dict(constraints),
        "synthesis_distribution_id": distribution.distribution_id,
        "synthesis_probability_mass": payload["probability"],
        "structural_hardware": payload["cost"],
        "synthesis": search,
    }
    return ExactSynthesisResult(code=code, search=search)
