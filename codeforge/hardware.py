"""Technology-independent structural cost models for generated linear codes."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Mapping, Sequence

from .gf2 import matrix_columns_as_ints, validate_matrix


def _xor_tree_cost(input_count: int, max_fanin: int) -> tuple[int, int]:
    if input_count <= 1:
        return 0, 0
    if max_fanin < 2:
        raise ValueError("max_xor_fanin must be at least 2")
    gates = math.ceil((input_count - 1) / (max_fanin - 1))
    depth = math.ceil(math.log(input_count, max_fanin))
    return gates, depth


def structural_cost(
    h: Sequence[Sequence[int]],
    g: Sequence[Sequence[int]],
    decoder_entries: Mapping[int, int],
    *,
    max_xor_fanin: int = 2,
) -> dict[str, Any]:
    """Return auditable gate/routing proxies, never characterized physical PPA."""

    r, n = validate_matrix(h, name="H")
    k, g_n = validate_matrix(g, name="G")
    if n != g_n:
        raise ValueError("H and G codeword widths differ")
    encoder_inputs = [sum(int(g[data][k + parity]) for data in range(k)) for parity in range(r)]
    syndrome_inputs = [sum(int(value) for value in row) for row in h]
    encoder_costs = [_xor_tree_cost(count, max_xor_fanin) for count in encoder_inputs]
    syndrome_costs = [_xor_tree_cost(count, max_xor_fanin) for count in syndrome_inputs]
    encoder_xors = sum(cost[0] for cost in encoder_costs)
    syndrome_xors = sum(cost[0] for cost in syndrome_costs)
    matrix_xors = encoder_xors + syndrome_xors
    correction_mask_ones = sum(int(mask).bit_count() for mask in decoder_entries.values())
    syndrome_compare_literals = len(decoder_entries) * r
    correction_output_ors = sum(
        max(0, sum(1 for mask in decoder_entries.values() if (int(mask) >> bit) & 1) - 1)
        for bit in range(n)
    )
    columns = matrix_columns_as_ints(h)
    fanout_by_codeword_bit = [int(column).bit_count() for column in columns]
    return {
        "model": "technology-independent structural proxy",
        "physical_ppa": None,
        "max_xor_fanin": max_xor_fanin,
        "encoder": {
            "parity_equation_inputs": encoder_inputs,
            "naive_xor_gates": encoder_xors,
            "max_balanced_depth": max((cost[1] for cost in encoder_costs), default=0),
        },
        "syndrome": {
            "equation_inputs": syndrome_inputs,
            "naive_xor_gates": syndrome_xors,
            "max_balanced_depth": max((cost[1] for cost in syndrome_costs), default=0),
        },
        "matrix_xor_gates": matrix_xors,
        "decoder": {
            "syndrome_table_entries": len(decoder_entries),
            "syndrome_compare_literals": syndrome_compare_literals,
            "correction_mask_ones": correction_mask_ones,
            "correction_output_or_proxy": correction_output_ors,
        },
        "routing": {
            "codeword_bit_fanout": fanout_by_codeword_bit,
            "max_codeword_bit_fanout": max(fanout_by_codeword_bit, default=0),
            "column_weight_histogram": {
                str(weight): count
                for weight, count in sorted(Counter(int(column).bit_count() for column in columns).items())
            },
        },
    }


def hardware_key(cost: Mapping[str, Any]) -> tuple[int, int, int, int]:
    """Lexicographic structural key used only after reliability objectives."""

    return (
        int(cost["matrix_xor_gates"]),
        int(cost["decoder"]["syndrome_table_entries"]),
        int(cost["decoder"]["correction_mask_ones"]),
        max(
            int(cost["encoder"]["max_balanced_depth"]),
            int(cost["syndrome"]["max_balanced_depth"]),
        ),
    )
