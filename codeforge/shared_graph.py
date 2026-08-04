"""Deterministic common-subexpression graphs for binary linear transforms."""

from __future__ import annotations

from collections import Counter
import itertools
import math
from typing import Any, Mapping, Sequence


def matrix_row_masks(matrix: Sequence[Sequence[int]]) -> list[int]:
    if not matrix or not matrix[0]:
        raise ValueError("matrix must be non-empty")
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("matrix rows have inconsistent widths")
    return [sum(int(bit) << index for index, bit in enumerate(row)) for row in matrix]


def code_linear_forms(code: Mapping[str, Any]) -> tuple[dict[str, int], dict[str, int]]:
    """Return encoder-data and syndrome-codeword linear forms."""

    k, r = int(code["k"]), int(code["r"])
    g = code["G"]
    h = code["H"]
    encoder = {
        f"{code['code_id']}:parity:{parity}": sum(
            int(g[data][k + parity]) << data for data in range(k)
        )
        for parity in range(r)
    }
    syndrome_forms = {
        f"{code['code_id']}:syndrome:{row}": sum(
            int(bit) << position for position, bit in enumerate(h[row])
        )
        for row in range(r)
    }
    return encoder, syndrome_forms


def synthesize_xor_graph(forms: Mapping[str, int], *, input_width: int) -> dict[str, Any]:
    """Greedily share repeated XOR pairs and emit an exactly checkable DAG."""

    if input_width <= 0:
        raise ValueError("input_width must be positive")
    token_masks: dict[int, int] = {index: 1 << index for index in range(input_width)}
    token_depth: dict[int, int] = {index: 0 for index in range(input_width)}
    expressions: dict[str, set[int]] = {
        label: {index for index in range(input_width) if (int(mask) >> index) & 1}
        for label, mask in forms.items()
    }
    nodes: list[dict[str, Any]] = []
    next_token = input_width
    while True:
        counts: Counter[tuple[int, int]] = Counter()
        for tokens in expressions.values():
            for left, right in itertools.combinations(sorted(tokens), 2):
                counts[(left, right)] += 1
        profitable = [(count, pair) for pair, count in counts.items() if count >= 2]
        if not profitable:
            break
        count, (left, right) = max(
            profitable,
            key=lambda item: (
                item[0] - 1,
                -max(token_depth[item[1][0]], token_depth[item[1][1]]),
                -item[1][0],
                -item[1][1],
            ),
        )
        new_mask = token_masks[left] ^ token_masks[right]
        existing = next((token for token, mask in token_masks.items() if mask == new_mask), None)
        if existing is not None and existing not in {left, right}:
            new_token = existing
        else:
            new_token = next_token
            next_token += 1
            token_masks[new_token] = new_mask
            token_depth[new_token] = max(token_depth[left], token_depth[right]) + 1
            nodes.append(
                {
                    "node_id": new_token,
                    "left": left,
                    "right": right,
                    "mask": new_mask,
                    "depth": token_depth[new_token],
                    "reuse_count_at_creation": count,
                }
            )
        changed = False
        for tokens in expressions.values():
            if left in tokens and right in tokens and new_token not in tokens:
                tokens.remove(left)
                tokens.remove(right)
                tokens.add(new_token)
                changed = True
        if not changed:
            break

    output_records: dict[str, Any] = {}
    residual_gates = 0
    max_depth = max((node["depth"] for node in nodes), default=0)
    for label, tokens in sorted(expressions.items()):
        token_list = sorted(tokens)
        reconstructed = 0
        for token in token_list:
            reconstructed ^= token_masks[token]
        expected = int(forms[label])
        if reconstructed != expected:
            raise AssertionError(f"XOR graph reconstruction failed for {label}")
        output_gates = max(0, len(token_list) - 1)
        residual_gates += output_gates
        output_depth = (
            max((token_depth[token] for token in token_list), default=0)
            + (math.ceil(math.log2(len(token_list))) if len(token_list) > 1 else 0)
        )
        max_depth = max(max_depth, output_depth)
        output_records[label] = {
            "mask": expected,
            "tokens": token_list,
            "residual_xor_gates": output_gates,
            "estimated_balanced_depth": output_depth,
        }
    naive_gates = sum(max(0, int(mask).bit_count() - 1) for mask in forms.values())
    total_gates = len(nodes) + residual_gates
    return {
        "input_width": input_width,
        "basis_token_count": input_width,
        "nodes": nodes,
        "outputs": output_records,
        "naive_xor_gates": naive_gates,
        "shared_intermediate_xor_gates": len(nodes),
        "residual_output_xor_gates": residual_gates,
        "total_xor_gates": total_gates,
        "xor_gate_reduction": naive_gates - total_gates,
        "xor_gate_reduction_fraction": (
            (naive_gates - total_gates) / naive_gates if naive_gates else 0.0
        ),
        "max_estimated_depth": max_depth,
        "equivalence_verified": True,
    }


def portfolio_shared_graph(codes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not codes:
        raise ValueError("at least one code is required")
    k = int(codes[0]["k"])
    n = int(codes[0]["n"])
    if any(int(code["k"]) != k or int(code["n"]) != n for code in codes):
        raise ValueError("all portfolio codes must share k and n")
    encoder_forms: dict[str, int] = {}
    syndrome_forms: dict[str, int] = {}
    for code in codes:
        encoder, syndrome = code_linear_forms(code)
        encoder_forms.update(encoder)
        syndrome_forms.update(syndrome)
    encoder_graph = synthesize_xor_graph(encoder_forms, input_width=k)
    syndrome_graph = synthesize_xor_graph(syndrome_forms, input_width=n)
    total = encoder_graph["total_xor_gates"] + syndrome_graph["total_xor_gates"]
    naive = encoder_graph["naive_xor_gates"] + syndrome_graph["naive_xor_gates"]
    return {
        "schema_version": 1,
        "graph_kind": "shared_binary_linear_transform",
        "code_ids": [str(code["code_id"]) for code in codes],
        "encoder": encoder_graph,
        "syndrome": syndrome_graph,
        "total_xor_gates": total,
        "naive_total_xor_gates": naive,
        "xor_gate_reduction": naive - total,
        "xor_gate_reduction_fraction": (naive - total) / naive if naive else 0.0,
        "max_estimated_depth": max(
            encoder_graph["max_estimated_depth"], syndrome_graph["max_estimated_depth"]
        ),
        "physical_ppa": None,
        "equivalence_verified": bool(
            encoder_graph["equivalence_verified"] and syndrome_graph["equivalence_verified"]
        ),
    }


def sequential_graph_baseline(codes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    per_code = [portfolio_shared_graph([code]) for code in codes]
    return {
        "kind": "independent_per_code_common_subexpression_optimization",
        "per_code": per_code,
        "total_xor_gates": sum(item["total_xor_gates"] for item in per_code),
        "max_estimated_depth": max((item["max_estimated_depth"] for item in per_code), default=0),
        "physical_ppa": None,
    }
