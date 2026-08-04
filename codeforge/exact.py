"""Exact exhaustive synthesis for small systematic short-block codes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import itertools
import math
import time
from typing import Any, Iterable, Mapping, Sequence

from .faults import ErrorPattern, FaultDistribution
from .gf2 import (
    bit_string,
    matrix_columns_as_ints,
    syndrome_from_columns,
    systematic_matrices,
)
from .hardware import hardware_key, structural_cost


@dataclass(frozen=True)
class ExactSynthesisResult:
    code: dict[str, Any] | None
    search: dict[str, Any]


def _patterns_in_families(
    distribution: FaultDistribution, families: Iterable[str]
) -> list[ErrorPattern]:
    wanted = set(families)
    return [pattern for pattern in distribution.patterns if pattern.family in wanted]


def _decoder_options(
    *,
    h: Sequence[Sequence[int]],
    distribution: FaultDistribution,
    mandatory_patterns: Sequence[ErrorPattern],
    detect_only_patterns: Sequence[ErrorPattern],
    max_sdc_probability: float,
) -> tuple[dict[int, int], dict[str, float]] | None:
    n = distribution.bit_width
    h_columns = matrix_columns_as_ints(h)
    mandatory_ids = {pattern.pattern_id for pattern in mandatory_patterns}
    detect_only_ids = {pattern.pattern_id for pattern in detect_only_patterns}
    mandatory_map: dict[int, ErrorPattern] = {}
    for pattern in mandatory_patterns:
        syndrome_value = syndrome_from_columns(pattern.mask(n), h_columns)
        if syndrome_value == 0 or syndrome_value in mandatory_map:
            return None
        mandatory_map[syndrome_value] = pattern

    detect_only_syndromes: set[int] = set()
    for pattern in detect_only_patterns:
        syndrome_value = syndrome_from_columns(pattern.mask(n), h_columns)
        if syndrome_value == 0 or syndrome_value in mandatory_map:
            return None
        detect_only_syndromes.add(syndrome_value)

    base_sdc = 0.0
    groups: dict[int, list[ErrorPattern]] = defaultdict(list)
    mandatory_probability = 0.0
    for pattern in distribution.patterns:
        syndrome_value = syndrome_from_columns(pattern.mask(n), h_columns)
        if pattern.pattern_id in mandatory_ids:
            mandatory_probability += pattern.probability
            continue
        if syndrome_value == 0 or syndrome_value in mandatory_map:
            base_sdc += pattern.probability
            continue
        if pattern.pattern_id in detect_only_ids or syndrome_value in detect_only_syndromes:
            continue
        groups[syndrome_value].append(pattern)

    if base_sdc > max_sdc_probability + 1e-15:
        return None

    candidates: list[tuple[int, ErrorPattern, float]] = []
    for syndrome_value, patterns in sorted(groups.items()):
        best = min(
            patterns,
            key=lambda pattern: (
                -pattern.probability,
                len(pattern.positions),
                pattern.positions,
                pattern.pattern_id,
            ),
        )
        induced_sdc = math.fsum(pattern.probability for pattern in patterns) - best.probability
        candidates.append((syndrome_value, best, induced_sdc))

    best_choice: tuple[tuple[Any, ...], dict[int, int], dict[str, float]] | None = None
    for selection_bits in range(1 << len(candidates)):
        selected: dict[int, int] = {
            syndrome_value: pattern.mask(n)
            for syndrome_value, pattern in mandatory_map.items()
        }
        corrected = mandatory_probability
        sdc = base_sdc
        for index, (syndrome_value, pattern, induced_sdc) in enumerate(candidates):
            if (selection_bits >> index) & 1:
                selected[syndrome_value] = pattern.mask(n)
                corrected += pattern.probability
                sdc += induced_sdc
        if sdc > max_sdc_probability + 1e-15:
            continue
        due = 1.0 - corrected - sdc
        key = (
            -round(corrected, 15),
            round(sdc, 15),
            len(selected),
            tuple(sorted(selected.items())),
        )
        metrics = {"corrected": corrected, "sdc": sdc, "due": max(0.0, due)}
        if best_choice is None or key < best_choice[0]:
            best_choice = (key, selected, metrics)
    if best_choice is None:
        return None
    return best_choice[1], best_choice[2]


def _candidate_columns(k: int, r: int, require_all_sbu: bool) -> tuple[list[int], int]:
    parity_columns = {1 << row for row in range(r)}
    values = list(range(1, 1 << r))
    if require_all_sbu:
        values = [value for value in values if value not in parity_columns]
    theoretical = math.perm(len(values), k) if len(values) >= k else 0
    return values, theoretical


def synthesize_exact(
    config: Mapping[str, Any], distribution: FaultDistribution
) -> ExactSynthesisResult:
    """Enumerate every permitted systematic data-column assignment."""

    started = time.perf_counter()
    k = int(config["k"])
    r = int(config["r"])
    n = k + r
    if distribution.bit_width != n:
        raise ValueError(f"fault distribution width {distribution.bit_width} must equal k+r={n}")
    search_cfg = config.get("search", {})
    timeout_seconds = float(search_cfg.get("timeout_seconds", 60.0))
    if timeout_seconds <= 0:
        raise ValueError("search.timeout_seconds must be positive")
    constraints = config.get("constraints", {})
    max_sdc = float(constraints.get("max_sdc_probability", 1.0))
    mandatory_families = tuple(config.get("decoder_policy", {}).get("mandatory_correct_families", []))
    detect_only_families = tuple(config.get("decoder_policy", {}).get("detect_only_families", []))
    mandatory_patterns = _patterns_in_families(distribution, mandatory_families)
    detect_only_patterns = _patterns_in_families(distribution, detect_only_families)
    require_all_sbu = "sbu" in mandatory_families
    values, theoretical = _candidate_columns(k, r, require_all_sbu)
    matrix_constraints = config.get("matrix_constraints", {})
    min_row_weight = int(matrix_constraints.get("min_row_weight", 1))
    max_row_weight = int(matrix_constraints.get("max_row_weight", n))
    min_data_column_weight = int(matrix_constraints.get("min_data_column_weight", 1))
    max_data_column_weight = int(matrix_constraints.get("max_data_column_weight", r))
    max_matrix_xors = constraints.get("max_matrix_xor_gates")
    max_xor_fanin = int(config.get("hardware_model", {}).get("max_xor_fanin", 2))
    hardware_aware = bool(config.get("hardware_model", {}).get("hardware_aware", True))

    considered = 0
    feasible = 0
    decoder_assignments = 0
    best: tuple[tuple[Any, ...], dict[str, Any]] | None = None
    timed_out = False
    for data_columns in itertools.permutations(values, k):
        if time.perf_counter() - started >= timeout_seconds:
            timed_out = True
            break
        considered += 1
        if any(
            not min_data_column_weight <= int(column).bit_count() <= max_data_column_weight
            for column in data_columns
        ):
            continue
        h, g = systematic_matrices(data_columns, r)
        row_weights = [sum(row) for row in h]
        if any(weight < min_row_weight or weight > max_row_weight for weight in row_weights):
            continue
        decoder = _decoder_options(
            h=h,
            distribution=distribution,
            mandatory_patterns=mandatory_patterns,
            detect_only_patterns=detect_only_patterns,
            max_sdc_probability=max_sdc,
        )
        if decoder is None:
            continue
        decoder_entries, probability = decoder
        decoder_assignments += 1
        cost = structural_cost(h, g, decoder_entries, max_xor_fanin=max_xor_fanin)
        if max_matrix_xors is not None and cost["matrix_xor_gates"] > int(max_matrix_xors):
            continue
        feasible += 1
        key = (
            -round(probability["corrected"], 15),
            round(probability["sdc"], 15),
            *(hardware_key(cost) if hardware_aware else ()),
            tuple(data_columns),
        )
        if best is None or key < best[0]:
            correction_entries = [
                {
                    "syndrome": bit_string(syndrome_value, r),
                    "positions": [position for position in range(n) if (mask >> position) & 1],
                }
                for syndrome_value, mask in sorted(decoder_entries.items())
            ]
            best = (
                key,
                {
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
                    "decoder": {
                        "type": "hard_decision_syndrome_table",
                        "correction_entries": correction_entries,
                    },
                    "constraints": dict(constraints),
                    "synthesis_distribution_id": distribution.distribution_id,
                    "synthesis_probability_mass": probability,
                    "structural_hardware": cost,
                },
            )

    runtime = time.perf_counter() - started
    complete = not timed_out and considered == theoretical
    status = "optimal" if best is not None and complete else "feasible_timeout" if best else "timeout" if timed_out else "infeasible"
    search = {
        "method": "exact_exhaustive_systematic_column_enumeration",
        "solver_dependency": None,
        "status": status,
        "runtime_seconds": runtime,
        "timeout_seconds": timeout_seconds,
        "theoretical_candidate_matrices": theoretical,
        "candidate_matrices_considered": considered,
        "decoder_assignments_evaluated": decoder_assignments,
        "feasible_candidates": feasible,
        "search_complete": complete,
        "optimality_proven": bool(best is not None and complete),
        "objective_order": (
            [
                "maximize corrected probability mass",
                "minimize SDC probability mass",
                "minimize structural matrix XOR count",
                "minimize syndrome-table entries",
                "minimize correction-mask ones",
                "minimize balanced XOR depth",
                "lexicographic matrix tie-break",
            ]
            if hardware_aware
            else [
                "maximize corrected probability mass",
                "minimize SDC probability mass",
                "lexicographic matrix tie-break",
            ]
        ),
        "hardware_aware_tie_break": hardware_aware,
    }
    if best is None:
        return ExactSynthesisResult(code=None, search=search)
    code = best[1]
    code["synthesis"] = search
    return ExactSynthesisResult(code=code, search=search)
