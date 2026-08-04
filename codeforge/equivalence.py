"""Exact invariants and bounded equivalence checks for generated binary codes.

The checker deliberately distinguishes algebraic code equivalence from decoder
policy and physical bit placement.  Exhaustive GL(r,2) searches are limited to
small redundancy because the group has 5,348,063,769,211,699,200 elements for
r=8; larger audits therefore report invariant-based classifications and never
pretend that a necessary invariant is a complete equivalence proof.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import permutations, product
from math import comb
from typing import Any, Iterable, Mapping, Sequence

from .gf2 import matrix_columns_as_ints, rank, validate_matrix


def _xor_rows(rows: Sequence[int], selector: int) -> int:
    value = 0
    for index, row in enumerate(rows):
        if (selector >> index) & 1:
            value ^= int(row)
    return value


def dual_weight_enumerator(h: Sequence[Sequence[int]]) -> list[int]:
    """Enumerate the dual code exactly when the parity dimension is modest."""

    r, n = validate_matrix(h, name="H")
    if r > 16:
        raise ValueError("exact dual enumeration is limited to r<=16")
    row_masks = [sum(int(bit) << col for col, bit in enumerate(row)) for row in h]
    counts = [0] * (n + 1)
    for selector in range(1 << r):
        counts[_xor_rows(row_masks, selector).bit_count()] += 1
    return counts


def _krawtchouk(n: int, weight: int, dual_weight: int) -> int:
    return sum(
        (-1) ** j * comb(dual_weight, j) * comb(n - dual_weight, weight - j)
        for j in range(max(0, weight - (n - dual_weight)), min(weight, dual_weight) + 1)
    )


def primal_weight_enumerator_from_dual(dual: Sequence[int], r: int) -> list[int]:
    """Apply the binary MacWilliams transform using exact integer arithmetic."""

    n = len(dual) - 1
    divisor = 1 << r
    result: list[int] = []
    for weight in range(n + 1):
        numerator = sum(
            int(count) * _krawtchouk(n, weight, dual_weight)
            for dual_weight, count in enumerate(dual)
        )
        quotient, remainder = divmod(numerator, divisor)
        if remainder:
            raise ValueError("MacWilliams transform did not produce an integer enumerator")
        result.append(quotient)
    return result


def weight_enumerators(h: Sequence[Sequence[int]]) -> dict[str, Any]:
    r, n = validate_matrix(h, name="H")
    dual = dual_weight_enumerator(h)
    primal = primal_weight_enumerator_from_dual(dual, r)
    minimum_distance = next((weight for weight, count in enumerate(primal[1:], 1) if count), None)
    return {
        "method": "dual enumeration plus exact binary MacWilliams transform",
        "primal": primal,
        "dual": dual,
        "minimum_distance": minimum_distance,
        "primal_word_count": sum(primal),
        "dual_word_count": sum(dual),
        "exact": True,
        "n": n,
        "r": r,
    }


def _independent_basis(candidate: Sequence[int], r: int) -> bool:
    matrix = [[(int(value) >> row) & 1 for value in candidate] for row in range(r)]
    return rank(matrix) == r


def _gl_bases(r: int) -> Iterable[tuple[int, ...]]:
    if r > 4:
        raise ValueError("exhaustive GL(r,2) enumeration is limited to r<=4")
    nonzero = range(1, 1 << r)
    for basis in permutations(nonzero, r):
        if _independent_basis(basis, r):
            yield basis


def _transform_column(column: int, basis: Sequence[int]) -> int:
    value = 0
    for bit, image in enumerate(basis):
        if (int(column) >> bit) & 1:
            value ^= int(image)
    return value


def _group_signature(columns: Sequence[int], groups: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(sorted(int(columns[index]) for index in group)) for group in groups)


def exact_grouped_column_equivalence(
    left_h: Sequence[Sequence[int]],
    right_h: Sequence[Sequence[int]],
    groups: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """Check row operations plus arbitrary permutations inside supplied groups."""

    left_r, left_n = validate_matrix(left_h, name="left H")
    right_r, right_n = validate_matrix(right_h, name="right H")
    if (left_r, left_n) != (right_r, right_n):
        return {"equivalent": False, "exact": True, "reason": "dimension mismatch"}
    if sorted(index for group in groups for index in group) != list(range(left_n)):
        raise ValueError("equivalence groups must partition all columns")
    if left_r > 4:
        return {
            "equivalent": None,
            "exact": False,
            "reason": "GL(r,2) exhaustive search is intentionally limited to r<=4",
        }
    left_columns = matrix_columns_as_ints(left_h)
    right_signature = _group_signature(matrix_columns_as_ints(right_h), groups)
    examined = 0
    for basis in _gl_bases(left_r):
        examined += 1
        transformed = [_transform_column(column, basis) for column in left_columns]
        if _group_signature(transformed, groups) == right_signature:
            return {
                "equivalent": True,
                "exact": True,
                "row_transform_basis": list(basis),
                "gl_elements_examined": examined,
            }
    return {"equivalent": False, "exact": True, "gl_elements_examined": examined}


def _sequence_equivalence(
    left: Sequence[int], right: Sequence[int], permutations_to_try: Sequence[Sequence[int]], r: int
) -> dict[str, Any]:
    if r > 4:
        return {"equivalent": None, "exact": False, "reason": "r>4 GL search limit"}
    for basis in _gl_bases(r):
        transformed = [_transform_column(value, basis) for value in left]
        for mapping in permutations_to_try:
            if [transformed[index] for index in mapping] == list(right):
                return {
                    "equivalent": True,
                    "exact": True,
                    "row_transform_basis": list(basis),
                    "physical_permutation": list(mapping),
                }
    return {"equivalent": False, "exact": True}


def _path_automorphisms(n: int) -> list[list[int]]:
    return [list(range(n)), list(reversed(range(n)))] if n > 1 else [[0]]


def _geometry_automorphisms(rows: int, cols: int) -> list[list[int]]:
    if rows * cols <= 0:
        raise ValueError("geometry rows and columns must be positive")
    coordinates = [(index // cols, index % cols) for index in range(rows * cols)]
    transforms = [
        lambda x, y: (x, y),
        lambda x, y: (rows - 1 - x, y),
        lambda x, y: (x, cols - 1 - y),
        lambda x, y: (rows - 1 - x, cols - 1 - y),
    ]
    if rows == cols:
        transforms.extend(
            [
                lambda x, y: (y, rows - 1 - x),
                lambda x, y: (cols - 1 - y, x),
                lambda x, y: (y, x),
                lambda x, y: (rows - 1 - y, cols - 1 - x),
            ]
        )
    mappings = []
    for transform in transforms:
        mapping = [transform(x, y)[0] * cols + transform(x, y)[1] for x, y in coordinates]
        if mapping not in mappings:
            mappings.append(mapping)
    return mappings


def _decoder_summary(code: Mapping[str, Any], columns: Sequence[int]) -> dict[str, Any]:
    correction_entries = list(code.get("decoder", {}).get("correction_entries", []))
    corrected = []
    for entry in correction_entries:
        corrected.append(
            {
                "syndrome": str(entry["syndrome"]),
                "positions": list(entry["positions"]),
                "weight": len(entry["positions"]),
            }
        )
    syndrome_multiplicity = Counter(columns)
    return {
        "corrected_coset_leaders": corrected,
        "correction_entry_count": len(corrected),
        "corrected_weight_histogram": dict(
            sorted(Counter(item["weight"] for item in corrected).items())
        ),
        "single_bit_syndrome_collisions": {
            str(syndrome): count for syndrome, count in sorted(syndrome_multiplicity.items()) if count > 1
        },
        "unmapped_nonzero_syndromes_are_detect_only": True,
    }


def classify_code(
    code: Mapping[str, Any],
    *,
    reference_code: Mapping[str, Any] | None = None,
    geometry: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Return exact algebraic invariants and carefully bounded family labels."""

    h = [[int(value) for value in row] for row in code["H"]]
    r, n = validate_matrix(h, name="H")
    k = int(code["k"])
    columns = matrix_columns_as_ints(h)
    enumerators = weight_enumerators(h)
    distinct_nonzero = len(set(columns)) == n and all(columns)
    all_odd = all(column.bit_count() % 2 == 1 for column in columns)
    minimum_distance = enumerators["minimum_distance"]
    labels: list[dict[str, Any]] = []
    if distinct_nonzero:
        labels.append(
            {
                "family": "shortened_hamming_sec",
                "status": "classified",
                "reason": "all parity-check columns are distinct and nonzero",
            }
        )
    if n == (1 << r) - 1 and distinct_nonzero:
        labels.append({"family": "hamming", "status": "classified"})
    if all_odd and distinct_nonzero and minimum_distance is not None and minimum_distance >= 4:
        labels.append(
            {
                "family": "odd_weight_column_SECDED_class",
                "status": "classified",
            }
        )
        eligible_odd_weights = sorted(
            value.bit_count() for value in range(1, 1 << r) if value.bit_count() % 2 == 1
        )[:n]
        if sorted(column.bit_count() for column in columns) == eligible_odd_weights:
            labels.append(
                {
                    "family": "Hsiao_minimum_total_ones_SECDED_construction",
                    "status": "classified",
                    "reason": "the column-weight multiset is the minimum possible odd-column multiset",
                }
            )
    if (
        n and n & (n - 1) == 0 and k == n - int(n.bit_length() - 1) - 1
        and minimum_distance == 4
    ):
        labels.append({"family": "extended_hamming_parameter_and_spectrum_class", "status": "classified"})

    adjacent_pairs = [(position, position + 1) for position in range(n - 1)]
    pair_syndromes = [columns[a] ^ columns[b] for a, b in adjacent_pairs]
    sbu_syndromes = set(columns)
    daec_capable = (
        distinct_nonzero
        and all(pair_syndromes)
        and len(set(pair_syndromes)) == len(pair_syndromes)
        and not (set(pair_syndromes) & sbu_syndromes)
    )
    labels.append(
        {
            "family": "SEC_DAEC_under_current_linear_adjacency",
            "status": "capable" if daec_capable else "not_capable",
            "decoder_policy_contains_all_adjacent_pairs": all(
                any(set(entry["positions"]) == set(pair) for entry in code["decoder"]["correction_entries"])
                for pair in adjacent_pairs
            ),
        }
    )
    triples = [(position, position + 1, position + 2) for position in range(n - 2)]
    triple_syndromes = [columns[a] ^ columns[b] ^ columns[c] for a, b, c in triples]
    taec_capable = (
        all(triple_syndromes)
        and len(set(triple_syndromes)) == len(triple_syndromes)
        and not (set(triple_syndromes) & (sbu_syndromes | set(pair_syndromes)))
    )
    labels.append(
        {
            "family": "TAEC_under_current_linear_adjacency",
            "status": "capable" if taec_capable else "not_capable",
        }
    )

    equivalence: dict[str, Any] = {}
    if reference_code is not None:
        reference_h = reference_code["H"]
        equivalence = {
            "row_operations_plus_arbitrary_columns": exact_grouped_column_equivalence(
                h, reference_h, [list(range(n))]
            ),
            "row_operations_plus_data_and_parity_permutations": exact_grouped_column_equivalence(
                h, reference_h, [list(range(k)), list(range(k, n))]
            ),
            "physical_path_automorphisms": _sequence_equivalence(
                columns,
                matrix_columns_as_ints(reference_h),
                _path_automorphisms(n),
                r,
            ),
        }
        if geometry is not None:
            rows = int(geometry["rows"])
            cols = int(geometry["columns"])
            if rows * cols != n:
                raise ValueError("geometry rows*columns must equal code n")
            equivalence["geometry_preserving_automorphisms"] = _sequence_equivalence(
                columns,
                matrix_columns_as_ints(reference_h),
                _geometry_automorphisms(rows, cols),
                r,
            )

    return {
        "schema_version": 1,
        "code_id": str(code.get("code_id", "external-code")),
        "dimensions": {"k": k, "r": r, "n": n},
        "rank": rank(h),
        "minimum_distance": minimum_distance,
        "weight_enumerators": enumerators,
        "column_weight_distribution": dict(
            sorted(Counter(column.bit_count() for column in columns).items())
        ),
        "column_multiset": sorted(columns),
        "physical_bit_to_column_assignment": [
            {"physical_position": position, "column": column, "column_weight": column.bit_count()}
            for position, column in enumerate(columns)
        ],
        "distinct_nonzero_columns": distinct_nonzero,
        "all_columns_odd_weight": all_odd,
        "known_family_classification": labels,
        "decoder_policy": _decoder_summary(code, columns),
        "reference_equivalence": equivalence,
        "bch_derived_status": (
            "not_equivalent_to_repository_BCH63_by_block_length"
            if n != 63
            else "not_established_without_a_matching_BCH_generator_or_reference_matrix"
        ),
        "novel_code_status": (
            "not_a_new_linear_code_family" if distinct_nonzero else "unclassified_not_proven_new"
        ),
        "limitations": [
            "For r>4, arbitrary-column equivalence is not exhaustively decided.",
            "Matching weight enumerators are necessary but not sufficient for code equivalence.",
            "SEC-DAEC and TAEC labels depend on the declared physical adjacency ordering.",
        ],
    }
