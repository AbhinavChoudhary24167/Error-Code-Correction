"""Deterministic matrix generators referenced by code manifests."""

from __future__ import annotations

from typing import Any

from codeforge.gf2 import systematic_matrices


def hsiao_odd_column(*, k: int = 64, redundancy: int = 8) -> dict[str, Any]:
    """Minimum-total-ones systematic odd-column SECDED construction."""

    basis = {1 << row for row in range(redundancy)}
    candidates = [
        value
        for value in range(1, 1 << redundancy)
        if value.bit_count() % 2 == 1 and value not in basis
    ]
    candidates.sort(key=lambda value: (value.bit_count(), value))
    if len(candidates) < k:
        raise ValueError("dimensions exceed the available odd non-basis columns")
    h, g = systematic_matrices(candidates[:k], redundancy)
    return {"H": h, "G": g, "data_positions": list(range(k))}


def conventional_extended_hamming(*, k: int = 64) -> dict[str, Any]:
    """Systematic form of conventional positional extended Hamming SECDED."""

    parity_count = 0
    while (1 << parity_count) < k + parity_count + 1:
        parity_count += 1
    code_without_overall = k + parity_count
    original_h = [
        [((position >> parity) & 1) for position in range(1, code_without_overall + 1)] + [0]
        for parity in range(parity_count)
    ]
    original_h.append([1] * code_without_overall + [1])
    parity_positions = [1 << row for row in range(parity_count)] + [code_without_overall + 1]
    data_positions = [
        position for position in range(1, code_without_overall + 2) if position not in parity_positions
    ]
    order = data_positions + parity_positions
    reordered = [[row[position - 1] for position in order] for row in original_h]
    parity_block = [row[k:] for row in reordered]
    inverse = _gf2_inverse(parity_block)
    h = _matmul(inverse, reordered)
    data_columns = [sum(h[row][column] << row for row in range(len(h))) for column in range(k)]
    h_systematic, g = systematic_matrices(data_columns, len(h))
    if h_systematic != h:
        raise AssertionError("extended-Hamming systematic conversion failed")
    return {
        "H": h,
        "G": g,
        "data_positions": list(range(k)),
        "native_coordinate_order": order,
    }


def cyclic_systematic(*, n: int = 63, k: int = 51, generator_polynomial: int = 0b1000111101011) -> dict[str, Any]:
    """Systematic cyclic-code matrices matching the repository polynomial encoder."""

    redundancy = n - k
    if generator_polynomial.bit_length() != redundancy + 1:
        raise ValueError("generator polynomial degree must equal n-k")
    g: list[list[int]] = []
    for source in range(k):
        data = 1 << source
        native = _cyclic_encode(data, n=n, k=k, polynomial=generator_polynomial)
        canonical = (native >> redundancy) | ((native & ((1 << redundancy) - 1)) << k)
        g.append([(canonical >> bit) & 1 for bit in range(n)])
    h = []
    for parity in range(redundancy):
        h.append(
            [g[data][k + parity] for data in range(k)]
            + [1 if parity == other else 0 for other in range(redundancy)]
        )
    return {"H": h, "G": g, "data_positions": list(range(k))}


def _cyclic_encode(data: int, *, n: int, k: int, polynomial: int) -> int:
    redundancy = n - k
    work = data << redundancy
    for bit in range(n - 1, redundancy - 1, -1):
        if (work >> bit) & 1:
            work ^= polynomial << (bit - redundancy)
    return (data << redundancy) | (work & ((1 << redundancy) - 1))


def _gf2_inverse(matrix: list[list[int]]) -> list[list[int]]:
    size = len(matrix)
    if any(len(row) != size for row in matrix):
        raise ValueError("matrix must be square")
    work = [list(map(int, row)) + [1 if row_index == col else 0 for col in range(size)] for row_index, row in enumerate(matrix)]
    for col in range(size):
        pivot = next((row for row in range(col, size) if work[row][col]), None)
        if pivot is None:
            raise ValueError("matrix is singular")
        work[col], work[pivot] = work[pivot], work[col]
        for row in range(size):
            if row != col and work[row][col]:
                work[row] = [left ^ right for left, right in zip(work[row], work[col])]
    return [row[size:] for row in work]


def _matmul(left: list[list[int]], right: list[list[int]]) -> list[list[int]]:
    return [
        [sum(a * b for a, b in zip(row, column)) & 1 for column in zip(*right)]
        for row in left
    ]

