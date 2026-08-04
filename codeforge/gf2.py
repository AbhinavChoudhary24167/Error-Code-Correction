"""Small, dependency-free GF(2) matrix and bit-vector operations."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


class GF2Error(ValueError):
    """Raised when a matrix or vector is invalid over GF(2)."""


def validate_matrix(matrix: Sequence[Sequence[int]], *, name: str = "matrix") -> tuple[int, int]:
    if not matrix:
        raise GF2Error(f"{name} must have at least one row")
    width = len(matrix[0])
    if width == 0:
        raise GF2Error(f"{name} must have at least one column")
    for row_index, row in enumerate(matrix):
        if len(row) != width:
            raise GF2Error(f"{name} row {row_index} has width {len(row)}, expected {width}")
        for value in row:
            if value not in (0, 1):
                raise GF2Error(f"{name} must contain only 0 and 1")
    return len(matrix), width


def transpose(matrix: Sequence[Sequence[int]]) -> list[list[int]]:
    rows, cols = validate_matrix(matrix)
    return [[int(matrix[row][col]) for row in range(rows)] for col in range(cols)]


def matmul(left: Sequence[Sequence[int]], right: Sequence[Sequence[int]]) -> list[list[int]]:
    left_rows, left_cols = validate_matrix(left, name="left")
    right_rows, right_cols = validate_matrix(right, name="right")
    if left_cols != right_rows:
        raise GF2Error(
            f"matrix dimensions do not align: {left_rows}x{left_cols} and "
            f"{right_rows}x{right_cols}"
        )
    out: list[list[int]] = []
    for row in range(left_rows):
        out.append(
            [
                sum(int(left[row][inner]) * int(right[inner][col]) for inner in range(left_cols))
                & 1
                for col in range(right_cols)
            ]
        )
    return out


def rank(matrix: Sequence[Sequence[int]]) -> int:
    """Return the exact row rank using Gaussian elimination over GF(2)."""

    rows, cols = validate_matrix(matrix)
    work = [[int(value) for value in row] for row in matrix]
    pivot_row = 0
    for col in range(cols):
        pivot = next((row for row in range(pivot_row, rows) if work[row][col]), None)
        if pivot is None:
            continue
        work[pivot_row], work[pivot] = work[pivot], work[pivot_row]
        for row in range(rows):
            if row != pivot_row and work[row][col]:
                work[row] = [a ^ b for a, b in zip(work[row], work[pivot_row])]
        pivot_row += 1
        if pivot_row == rows:
            break
    return pivot_row


def systematic_matrices(data_columns: Sequence[int], r: int) -> tuple[list[list[int]], list[list[int]]]:
    """Construct ``H=[P^T|I]`` and ``G=[I|P]`` from integer data columns."""

    if r <= 0:
        raise GF2Error("r must be positive")
    k = len(data_columns)
    if k <= 0:
        raise GF2Error("at least one data column is required")
    limit = 1 << r
    if any(column < 0 or column >= limit for column in data_columns):
        raise GF2Error(f"data columns must fit within {r} bits")
    p = [[(int(data_columns[data]) >> parity) & 1 for parity in range(r)] for data in range(k)]
    h = [
        [p[data][parity] for data in range(k)]
        + [1 if parity == other else 0 for other in range(r)]
        for parity in range(r)
    ]
    g = [
        [1 if data == other else 0 for other in range(k)] + p[data]
        for data in range(k)
    ]
    return h, g


def matrix_columns_as_ints(matrix: Sequence[Sequence[int]]) -> list[int]:
    rows, cols = validate_matrix(matrix)
    return [sum(int(matrix[row][col]) << row for row in range(rows)) for col in range(cols)]


def syndrome(error_or_word: int, h: Sequence[Sequence[int]]) -> int:
    return syndrome_from_columns(error_or_word, matrix_columns_as_ints(h))


def syndrome_from_columns(error_or_word: int, columns: Sequence[int]) -> int:
    """Calculate a syndrome using prevalidated integer matrix columns."""

    value = 0
    for position, column in enumerate(columns):
        if (error_or_word >> position) & 1:
            value ^= int(column)
    return value


def encode(data: int, g: Sequence[Sequence[int]]) -> int:
    k, n = validate_matrix(g, name="G")
    if data < 0 or data >= (1 << k):
        raise GF2Error(f"data word {data} does not fit in k={k}")
    codeword = 0
    for output in range(n):
        bit = 0
        for source in range(k):
            bit ^= ((data >> source) & 1) & int(g[source][output])
        codeword |= bit << output
    return codeword


def generator_row_masks(g: Sequence[Sequence[int]]) -> list[int]:
    rows, _ = validate_matrix(g, name="G")
    return [sum(int(bit) << position for position, bit in enumerate(g[row])) for row in range(rows)]


def encode_from_row_masks(data: int, row_masks: Sequence[int]) -> int:
    if data < 0 or data >= (1 << len(row_masks)):
        raise GF2Error(f"data word {data} does not fit in k={len(row_masks)}")
    codeword = 0
    for source, mask in enumerate(row_masks):
        if (data >> source) & 1:
            codeword ^= int(mask)
    return codeword


def positions_to_mask(positions: Iterable[int], n: int) -> int:
    mask = 0
    for position in positions:
        if position < 0 or position >= n:
            raise GF2Error(f"error position {position} is outside [0,{n})")
        bit = 1 << position
        if mask & bit:
            raise GF2Error(f"duplicate error position {position}")
        mask |= bit
    return mask


def mask_to_positions(mask: int, n: int) -> tuple[int, ...]:
    if mask < 0 or mask >= (1 << n):
        raise GF2Error(f"mask {mask} does not fit in n={n}")
    return tuple(position for position in range(n) if (mask >> position) & 1)


def bit_string(value: int, width: int) -> str:
    return format(value, f"0{width}b")


def is_zero_matrix(matrix: Sequence[Sequence[int]]) -> bool:
    validate_matrix(matrix)
    return all(value == 0 for row in matrix for value in row)
