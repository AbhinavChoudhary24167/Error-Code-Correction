from __future__ import annotations

from itertools import combinations

import pytest

from green_ecc_phy.bch import (
    BinaryExtensionField,
    PrimitiveBCHAdapter,
    primitive_bch_generator,
    primitive_bch_systematic,
)
from green_ecc_phy.contracts import DecodeStatus


SPECS = [
    (6, 2, 0x43, None, 63, 51),
    (7, 1, 0x83, 64, 71, 64),
    (7, 2, 0x83, 64, 78, 64),
    (7, 3, 0x83, 64, 85, 64),
]


def _adapter(m: int, t: int, polynomial: int, shortened_k: int | None) -> PrimitiveBCHAdapter:
    matrix = primitive_bch_systematic(
        m=m, t=t, primitive_polynomial=polynomial, shortened_k=shortened_k
    )
    return PrimitiveBCHAdapter(
        h=matrix["H"], g=matrix["G"], k=len(matrix["G"]),
        n=len(matrix["G"][0]), m=m, t=t, primitive_polynomial=polynomial,
    )


def test_bch_field_and_generators_are_reproducible() -> None:
    field = BinaryExtensionField(6, 0x43)
    assert field.order == 63
    assert field.pow(2, 63) == 1
    construction = primitive_bch_generator(m=6, t=2, primitive_polynomial=0x43)
    assert construction["k_parent"] == 51
    assert construction["generator_degree"] == 12
    assert construction["generator_polynomial_binary"] == "1010100111001"
    assert construction["defining_consecutive_roots"] == [1, 2, 3, 4]
    assert construction["designed_distance_lower_bound"] == 5


@pytest.mark.parametrize("m,t,polynomial,shortened_k,n,k", SPECS)
def test_bch_no_error_malformed_and_shortening(
    m: int, t: int, polynomial: int, shortened_k: int | None, n: int, k: int
) -> None:
    matrix = primitive_bch_systematic(
        m=m, t=t, primitive_polynomial=polynomial, shortened_k=shortened_k
    )
    adapter = _adapter(m, t, polynomial, shortened_k)
    assert (adapter.n, adapter.k) == (n, k)
    for data in (0, 1, (1 << k) - 1, 0xA55AA55AA55AA55A & ((1 << k) - 1)):
        codeword = adapter.encode(data)
        assert adapter.syndrome(codeword) == 0
        result = adapter.decode(codeword)
        assert result.status == DecodeStatus.NO_ERROR
        assert result.data == data
    with pytest.raises(ValueError):
        adapter.encode(-1)
    with pytest.raises(ValueError):
        adapter.encode(1 << k)
    assert adapter.decode(-1).status == DecodeStatus.INVALID_CONFIGURATION
    assert adapter.decode(1 << n).status == DecodeStatus.INVALID_CONFIGURATION
    assert matrix["shortening"]["enabled"] is (shortened_k is not None)
    if shortened_k is not None:
        assert len(matrix["shortening"]["fixed_zero_parent_data_positions"]) > 0


@pytest.mark.parametrize("m,t,polynomial,shortened_k,n,k", SPECS)
def test_bch_exhaustively_corrects_every_mask_through_t(
    m: int, t: int, polynomial: int, shortened_k: int | None, n: int, k: int
) -> None:
    adapter = _adapter(m, t, polynomial, shortened_k)
    data = 0x123456789ABCDEF & ((1 << k) - 1)
    clean = adapter.encode(data)
    examined = 0
    for weight in range(1, t + 1):
        for positions in combinations(range(n), weight):
            corrupted = clean ^ sum(1 << position for position in positions)
            result = adapter.decode(corrupted)
            assert result.status == DecodeStatus.CORRECTED
            assert result.data == data
            assert result.corrected_codeword_optional == clean
            examined += 1
    assert examined == sum(__import__("math").comb(n, weight) for weight in range(1, t + 1))


def test_valid_bch_identity_is_not_the_rejected_repository_cyclic_identity() -> None:
    valid = primitive_bch_generator(m=6, t=2, primitive_polynomial=0x43)
    rejected_generator = 0b1000111101011
    assert valid["generator_polynomial"] != rejected_generator
    assert valid["generator_polynomial_binary"] == "1010100111001"
