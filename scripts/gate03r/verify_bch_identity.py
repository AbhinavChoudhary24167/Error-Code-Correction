#!/usr/bin/env python3
"""Independent Gate 03R reconstruction of shortened BCH(78,64,t=2).

This module deliberately does not import ``green_ecc_phy.bch``.  It rebuilds
the field, generator, systematic matrices, shortened coordinate map, and packed
syndrome columns from the frozen contract using only the Python standard
library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any


M = 7
T = 2
PRIMITIVE_POLYNOMIAL = 0x83
PARENT_N = 127
PARENT_K = 113
SHORTENED_K = 64
N = 78
GENERATOR = 21629
EXPECTED_MATRIX_SHA256 = "d518cab40c77da302afecab0e8199f3f0c4e0b2c095660d5d0df8a1e2dae4e89"


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def gf_mul(left: int, right: int) -> int:
    result = 0
    a, b = left, right
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & (1 << M):
            a ^= PRIMITIVE_POLYNOMIAL
    return result & ((1 << M) - 1)


def gf_pow(value: int, exponent: int) -> int:
    result, base = 1, value
    while exponent:
        if exponent & 1:
            result = gf_mul(result, base)
        base = gf_mul(base, base)
        exponent >>= 1
    return result


def gf_inverse(value: int) -> int:
    """Return the multiplicative inverse used by the bounded RTL locator."""

    if value == 0:
        return 0
    return gf_pow(value, (1 << M) - 2)


def coset(exponent: int) -> tuple[int, ...]:
    values: list[int] = []
    current = exponent % PARENT_N
    while current not in values:
        values.append(current)
        current = (2 * current) % PARENT_N
    return tuple(values)


def multiply_field_polynomials(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] ^= gf_mul(a, b)
    return result


def reconstruct_generator() -> tuple[int, list[tuple[int, ...]]]:
    selected: list[tuple[int, ...]] = []
    roots: set[int] = set()
    for exponent in range(1, 2 * T + 1):
        candidate = coset(exponent)
        if not roots.intersection(candidate):
            selected.append(candidate)
        roots.update(candidate)
    polynomial = [1]
    for exponent in sorted(roots):
        polynomial = multiply_field_polynomials(polynomial, [gf_pow(2, exponent), 1])
    if any(value not in (0, 1) for value in polynomial):
        raise AssertionError("conjugate-root product did not reduce to GF(2)")
    value = sum(bit << degree for degree, bit in enumerate(polynomial))
    return value, selected


def remainder(dividend: int, divisor: int) -> int:
    divisor_degree = divisor.bit_length() - 1
    work = dividend
    while work and work.bit_length() - 1 >= divisor_degree:
        work ^= divisor << (work.bit_length() - 1 - divisor_degree)
    return work


def encode(data: int) -> int:
    if data < 0 or data >= 1 << SHORTENED_K:
        raise ValueError("payload does not fit 64 bits")
    native = data << 14
    parity = remainder(native, GENERATOR)
    return data | (parity << SHORTENED_K)


def matrices() -> tuple[list[list[int]], list[list[int]]]:
    g: list[list[int]] = []
    for source in range(SHORTENED_K):
        codeword = encode(1 << source)
        g.append([(codeword >> bit) & 1 for bit in range(N)])
    h = [
        [g[data][SHORTENED_K + parity] for data in range(SHORTENED_K)]
        + [1 if parity == other else 0 for other in range(14)]
        for parity in range(14)
    ]
    return h, g


def coordinate_exponent(position: int) -> int:
    if position < 0 or position >= N:
        raise ValueError("coordinate is outside shortened codeword")
    return position + 14 if position < SHORTENED_K else position - SHORTENED_K


def syndrome_column(position: int) -> int:
    exponent = coordinate_exponent(position)
    packed = 0
    for syndrome_index in range(1, 2 * T + 1):
        packed |= gf_pow(2, syndrome_index * exponent) << ((syndrome_index - 1) * M)
    return packed


def syndrome(word: int) -> int:
    value = 0
    for position in range(N):
        if word & (1 << position):
            value ^= syndrome_column(position)
    return value


def bounded_decode(received: int) -> dict[str, Any]:
    """Execute the frozen syndrome/locator/Chien decoder algorithm.

    The function is an independent executable statement of the RTL contract.
    In particular, it does not use the reference decoder's lookup table.
    """

    if received < 0 or received >= 1 << N:
        raise ValueError("received word does not fit 78 bits")
    packed = syndrome(received)
    s1 = packed & 0x7F
    s3 = (packed >> 14) & 0x7F
    sigma2 = gf_mul(s3 ^ gf_pow(s1, 3), gf_inverse(s1))
    positions: list[int] = []
    if packed and s1:
        for position in range(N):
            location = gf_pow(2, coordinate_exponent(position))
            locator = gf_mul(location, location) ^ gf_mul(s1, location) ^ sigma2
            if locator == 0:
                positions.append(position)
    candidate_mask = sum(1 << position for position in positions)
    candidate = received ^ candidate_mask
    correction_is_valid = (
        packed != 0
        and s1 != 0
        and len(positions) in (1, 2)
        and syndrome(candidate) == 0
    )
    if packed == 0:
        return {
            "data": received & ((1 << SHORTENED_K) - 1),
            "corrected_codeword": received,
            "syndrome": 0,
            "correction_mask": 0,
            "detected": False,
            "corrected": False,
            "uncorrectable": False,
        }
    if correction_is_valid:
        return {
            "data": candidate & ((1 << SHORTENED_K) - 1),
            "corrected_codeword": candidate,
            "syndrome": packed,
            "correction_mask": candidate_mask,
            "detected": True,
            "corrected": True,
            "uncorrectable": False,
        }
    return {
        "data": received & ((1 << SHORTENED_K) - 1),
        "corrected_codeword": received,
        "syndrome": packed,
        "correction_mask": 0,
        "detected": True,
        "corrected": False,
        "uncorrectable": True,
    }


def reconstruct() -> dict[str, Any]:
    generator, selected_cosets = reconstruct_generator()
    if gf_pow(2, PARENT_N) != 1 or any(gf_pow(2, PARENT_N // factor) == 1 for factor in (7, 127)):
        raise AssertionError("0x83 did not establish the required primitive field")
    if generator != GENERATOR:
        raise AssertionError(f"generator mismatch: {generator} != {GENERATOR}")
    h, g = matrices()
    matrix_sha256 = canonical_hash({"G": g, "H": h})
    if matrix_sha256 != EXPECTED_MATRIX_SHA256:
        raise AssertionError(f"matrix mismatch: {matrix_sha256}")
    row_syndromes = [syndrome(encode(1 << source)) for source in range(SHORTENED_K)]
    if any(row_syndromes):
        raise AssertionError("packed BCH syndromes reject a generator basis row")

    locator: dict[int, tuple[int, ...]] = {}
    collisions: list[dict[str, Any]] = []
    for weight in (1, 2):
        for positions in combinations(range(N), weight):
            packed = 0
            for position in positions:
                packed ^= syndrome_column(position)
            prior = locator.get(packed)
            if prior is not None and prior != positions:
                collisions.append({"syndrome": packed, "left": prior, "right": positions})
            locator[packed] = positions
    if collisions or len(locator) != 78 + 3003:
        raise AssertionError("locator collision inside t=2 radius")

    return {
        "schema_version": 1,
        "status": "PASS",
        "independence": "standard-library reconstruction; green_ecc_phy.bch not imported",
        "m": M,
        "t": T,
        "primitive_polynomial": PRIMITIVE_POLYNOMIAL,
        "parent_n": PARENT_N,
        "parent_k": PARENT_K,
        "shortened_n": N,
        "shortened_k": SHORTENED_K,
        "fixed_zero_parent_data_positions": list(range(64, 113)),
        "removed_parent_codeword_positions": list(range(78, 127)),
        "cyclotomic_cosets": [list(item) for item in selected_cosets],
        "generator_polynomial": generator,
        "generator_polynomial_binary": format(generator, "015b"),
        "matrix_sha256": matrix_sha256,
        "coordinate_parent_exponents": [coordinate_exponent(position) for position in range(N)],
        "packed_syndrome_columns": [syndrome_column(position) for position in range(N)],
        "bounded_locator_entries": len(locator),
        "bounded_locator_collisions": collisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = reconstruct()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
