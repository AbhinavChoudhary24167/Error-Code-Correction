"""Deterministic primitive binary BCH construction and reference decoder.

The repository's historical RTL ``bch`` block is intentionally *not* used
here: its archived degree-12 polynomial produces a distance-two cyclic code.
This module constructs a narrow-sense primitive BCH code directly from a
declared primitive polynomial, and therefore has a separate scientific
identity.

Coordinates exposed to the framework are systematic ``[data | parity]``.
For shortening, the omitted high-order information coordinates of the parent
code are fixed to zero.  Parity coordinates retain their parent-code
polynomial exponents, which is essential for valid shortened-code syndromes.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from typing import Any, Mapping, Sequence

from codeforge.gf2 import encode_from_row_masks, generator_row_masks

from .contracts import DecodeResult, DecodeStatus


def _prime_factors(value: int) -> tuple[int, ...]:
    factors: list[int] = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1
    if value > 1:
        factors.append(value)
    return tuple(factors)


@dataclass(frozen=True)
class BinaryExtensionField:
    """Polynomial-basis GF(2**m) with an explicitly verified primitive element."""

    m: int
    primitive_polynomial: int

    def __post_init__(self) -> None:
        if self.m < 2:
            raise ValueError("m must be at least two")
        if self.primitive_polynomial.bit_length() != self.m + 1:
            raise ValueError("primitive polynomial must have degree m")
        if not (self.primitive_polynomial & 1):
            raise ValueError("primitive polynomial must have a nonzero constant term")
        if self.pow(2, self.order) != 1:
            raise ValueError("polynomial does not close GF(2**m) multiplicative order")
        for factor in _prime_factors(self.order):
            if self.pow(2, self.order // factor) == 1:
                raise ValueError("declared polynomial is not primitive")

    @property
    def order(self) -> int:
        return (1 << self.m) - 1

    @property
    def mask(self) -> int:
        return (1 << self.m) - 1

    def mul(self, left: int, right: int) -> int:
        if left < 0 or left > self.mask or right < 0 or right > self.mask:
            raise ValueError("field operand is out of range")
        result = 0
        a = left
        b = right
        while b:
            if b & 1:
                result ^= a
            b >>= 1
            a <<= 1
            if a & (1 << self.m):
                a ^= self.primitive_polynomial
        return result & self.mask

    def pow(self, value: int, exponent: int) -> int:
        if exponent < 0:
            return self.pow(self.inv(value), -exponent)
        result = 1
        base = value
        power = exponent
        while power:
            if power & 1:
                result = self.mul(result, base)
            base = self.mul(base, base)
            power >>= 1
        return result

    def inv(self, value: int) -> int:
        if value == 0:
            raise ZeroDivisionError("zero has no multiplicative inverse")
        return self.pow(value, self.order - 1)


def cyclotomic_coset(exponent: int, n: int) -> tuple[int, ...]:
    """Return the binary cyclotomic coset of ``exponent`` modulo ``n``."""

    first = exponent % n
    values: list[int] = []
    current = first
    while current not in values:
        values.append(current)
        current = (2 * current) % n
    return tuple(values)


def _multiply_field_polynomials(
    left: Sequence[int], right: Sequence[int], field: BinaryExtensionField
) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] ^= field.mul(int(a), int(b))
    return result


def primitive_bch_generator(
    *, m: int, t: int, primitive_polynomial: int
) -> dict[str, Any]:
    """Construct the narrow-sense primitive BCH generator for roots alpha^1..alpha^(2t)."""

    if t < 1:
        raise ValueError("t must be positive")
    field = BinaryExtensionField(m=m, primitive_polynomial=primitive_polynomial)
    n = field.order
    roots: set[int] = set()
    cosets: list[tuple[int, ...]] = []
    for exponent in range(1, 2 * t + 1):
        coset = cyclotomic_coset(exponent, n)
        if not roots.intersection(coset):
            cosets.append(coset)
        roots.update(coset)

    polynomial = [1]
    for exponent in sorted(roots):
        root = field.pow(2, exponent)
        polynomial = _multiply_field_polynomials(polynomial, [root, 1], field)
    if any(coefficient not in (0, 1) for coefficient in polynomial):
        raise AssertionError("conjugate-root product did not reduce to GF(2)")
    generator = sum(int(bit) << degree for degree, bit in enumerate(polynomial))
    degree = len(polynomial) - 1
    if generator.bit_length() != degree + 1:
        raise AssertionError("generator polynomial is not monic")
    return {
        "m": m,
        "n_parent": n,
        "t": t,
        "primitive_polynomial": primitive_polynomial,
        "primitive_polynomial_binary": format(primitive_polynomial, f"0{m + 1}b"),
        "root_exponents": sorted(roots),
        "defining_consecutive_roots": list(range(1, 2 * t + 1)),
        "cyclotomic_cosets": [list(coset) for coset in cosets],
        "generator_polynomial": generator,
        "generator_polynomial_binary": format(generator, f"0{degree + 1}b"),
        "generator_degree": degree,
        "k_parent": n - degree,
        "designed_distance_lower_bound": 2 * t + 1,
        "bound_method": "narrow-sense BCH consecutive-root bound",
    }


def _polynomial_remainder(dividend: int, divisor: int) -> int:
    divisor_degree = divisor.bit_length() - 1
    work = dividend
    while work and work.bit_length() - 1 >= divisor_degree:
        work ^= divisor << (work.bit_length() - 1 - divisor_degree)
    return work


def _native_encode(data: int, *, k_parent: int, generator: int) -> int:
    if data < 0 or data >= (1 << k_parent):
        raise ValueError("parent BCH data is out of range")
    redundancy = generator.bit_length() - 1
    shifted = data << redundancy
    return shifted ^ _polynomial_remainder(shifted, generator)


@lru_cache(maxsize=32)
def _cached_matrix(
    m: int, t: int, primitive_polynomial: int, shortened_k: int | None
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...], tuple[tuple[str, Any], ...]]:
    construction = primitive_bch_generator(
        m=m, t=t, primitive_polynomial=primitive_polynomial
    )
    k_parent = int(construction["k_parent"])
    k = k_parent if shortened_k is None else int(shortened_k)
    if k < 1 or k > k_parent:
        raise ValueError(f"shortened k must lie in [1,{k_parent}]")
    redundancy = int(construction["generator_degree"])
    generator = int(construction["generator_polynomial"])
    g: list[list[int]] = []
    for source in range(k):
        native = _native_encode(1 << source, k_parent=k_parent, generator=generator)
        parity = native & ((1 << redundancy) - 1)
        canonical = (1 << source) | (parity << k)
        g.append([(canonical >> bit) & 1 for bit in range(k + redundancy)])
    h = [
        [g[data][k + parity] for data in range(k)]
        + [1 if parity == other else 0 for other in range(redundancy)]
        for parity in range(redundancy)
    ]
    metadata = tuple(sorted(construction.items()))
    return tuple(map(tuple, h)), tuple(map(tuple, g)), metadata


def primitive_bch_systematic(
    *, m: int, t: int, primitive_polynomial: int, shortened_k: int | None = None
) -> dict[str, Any]:
    """Return ``H`` and ``G`` for a parent or correctly shortened primitive BCH code."""

    h, g, metadata_items = _cached_matrix(m, t, primitive_polynomial, shortened_k)
    metadata = dict(metadata_items)
    k = len(g)
    parent_k = int(metadata["k_parent"])
    return {
        "H": [list(row) for row in h],
        "G": [list(row) for row in g],
        "data_positions": list(range(k)),
        "coordinate_parent_exponents": list(range(int(metadata["generator_degree"]), int(metadata["generator_degree"]) + k))
        + list(range(int(metadata["generator_degree"]))),
        "construction": metadata,
        "shortening": {
            "enabled": k != parent_k,
            "parent_n": int(metadata["n_parent"]),
            "parent_k": parent_k,
            "fixed_zero_parent_data_positions": list(range(k, parent_k)),
            "removed_parent_codeword_positions": list(
                range(int(metadata["generator_degree"]) + k, int(metadata["n_parent"]))
            ),
        },
    }


@dataclass
class PrimitiveBCHAdapter:
    """Reference decoder using exact BCH syndromes and a deterministic bounded locator table."""

    h: Sequence[Sequence[int]]
    g: Sequence[Sequence[int]]
    k: int
    n: int
    m: int
    t: int
    primitive_polynomial: int
    encoder_latency: int = 0
    decoder_latency: int = 0

    def __post_init__(self) -> None:
        self._rows = generator_row_masks(self.g)
        metadata = primitive_bch_generator(
            m=self.m, t=self.t, primitive_polynomial=self.primitive_polynomial
        )
        self._field = BinaryExtensionField(self.m, self.primitive_polynomial)
        redundancy = int(metadata["generator_degree"])
        self._parent_exponents = tuple(range(redundancy, redundancy + self.k)) + tuple(range(redundancy))
        if len(self._parent_exponents) != self.n:
            raise ValueError("BCH coordinate map does not match n")
        self._syndrome_columns = tuple(
            self._calculate_coordinate_syndrome(exponent)
            for exponent in self._parent_exponents
        )
        locator: dict[int, tuple[int, ...]] = {}
        collisions: set[int] = set()
        for weight in range(1, self.t + 1):
            for positions in combinations(range(self.n), weight):
                syndrome = self._packed_error_syndrome(positions)
                if syndrome in locator and locator[syndrome] != positions:
                    collisions.add(syndrome)
                else:
                    locator[syndrome] = positions
        if collisions:
            raise ValueError("BCH locator collision inside guaranteed correction radius")
        self._locator = locator

    def encode(self, data: int) -> int:
        if data < 0 or data >= (1 << self.k):
            raise ValueError(f"data does not fit k={self.k}")
        return encode_from_row_masks(data, self._rows)

    def _calculate_coordinate_syndrome(self, exponent: int) -> int:
        syndromes = [0] * (2 * self.t)
        for index in range(2 * self.t):
            syndromes[index] = self._field.pow(
                2, ((index + 1) * exponent) % self._field.order
            )
        packed = 0
        for index, value in enumerate(syndromes):
            packed |= int(value) << (index * self.m)
        return packed

    def _packed_error_syndrome(self, positions: Sequence[int]) -> int:
        syndrome = 0
        for position in positions:
            syndrome ^= self._syndrome_columns[position]
        return syndrome

    def syndrome(self, codeword: int) -> int:
        syndrome = 0
        work = codeword
        while work:
            least = work & -work
            position = least.bit_length() - 1
            syndrome ^= self._syndrome_columns[position]
            work ^= least
        return syndrome

    def decode(self, codeword: int) -> DecodeResult:
        if codeword < 0 or codeword >= (1 << self.n):
            return DecodeResult(
                None, DecodeStatus.INVALID_CONFIGURATION, None, None, None, self.decoder_latency
            )
        syndrome = self.syndrome(codeword)
        if syndrome == 0:
            return DecodeResult(
                codeword & ((1 << self.k) - 1),
                DecodeStatus.NO_ERROR,
                0,
                codeword,
                None,
                self.decoder_latency,
            )
        positions = self._locator.get(syndrome)
        if positions is None:
            return DecodeResult(
                None,
                DecodeStatus.DETECTED_UNCORRECTABLE,
                syndrome,
                None,
                None,
                self.decoder_latency,
            )
        mask = sum(1 << position for position in positions)
        corrected = codeword ^ mask
        if self.syndrome(corrected) != 0:
            return DecodeResult(
                None,
                DecodeStatus.DETECTED_UNCORRECTABLE,
                syndrome,
                None,
                positions,
                self.decoder_latency,
            )
        location: int | tuple[int, ...] = positions[0] if len(positions) == 1 else positions
        return DecodeResult(
            corrected & ((1 << self.k) - 1),
            DecodeStatus.CORRECTED,
            syndrome,
            corrected,
            location,
            self.decoder_latency,
        )


def create_bch_adapter(
    *,
    code: Mapping[str, Any],
    implementation: Mapping[str, Any],
    m: int,
    t: int,
    primitive_polynomial: int,
) -> PrimitiveBCHAdapter:
    matrix = code["_resolved_matrix"]
    return PrimitiveBCHAdapter(
        h=matrix["H"],
        g=matrix["G"],
        k=int(code["k"]),
        n=int(code["n"]),
        m=int(m),
        t=int(t),
        primitive_polynomial=int(primitive_polynomial),
        encoder_latency=int(implementation["encoder_latency"]),
        decoder_latency=int(implementation["decoder_latency"]),
    )
