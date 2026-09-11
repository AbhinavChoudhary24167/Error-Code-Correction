"""Executable external-bank mapping and bounded physical-fault topologies.

I1/I2 are logical-to-macro implementation contracts.  They are not claims
about SRAM22 internal bitcell coordinates, adjacency, routed cost, or upset
probability.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class InterleavingId(str, Enum):
    I0 = "I0"
    I1 = "I1"
    I2 = "I2"


class TopologyScenario(str, Enum):
    BEST_CASE_INTERLEAVING = "BEST_CASE_INTERLEAVING"
    NOMINAL_PARAMETRIC = "NOMINAL_PARAMETRIC"
    WORST_CASE_CLUSTERING = "WORST_CASE_CLUSTERING"


_BANKS = {InterleavingId.I0: 1, InterleavingId.I1: 2, InterleavingId.I2: 4}


@dataclass(frozen=True, order=True)
class PhysicalSlot:
    macro_kind: str
    bank: int
    macro_address: int
    macro_data_pin: int

    def __post_init__(self) -> None:
        if self.macro_kind not in {"data", "ecc"}:
            raise ValueError("macro_kind must be data or ecc")
        for name in ("bank", "macro_address", "macro_data_pin"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class CodewordFault:
    word_address: int
    codeword_bits: tuple[int, ...]

    @property
    def error_multiplicity(self) -> int:
        return len(self.codeword_bits)

    @property
    def error_mask(self) -> int:
        return sum(1 << bit for bit in self.codeword_bits)


def _as_interleaving(value: InterleavingId | str) -> InterleavingId:
    try:
        return InterleavingId(value)
    except ValueError as exc:
        raise ValueError("interleaving must be I0, I1, or I2") from exc


def logical_to_slot(
    word_address: int,
    codeword_bit: int,
    interleaving: InterleavingId | str,
    *,
    protected: bool,
) -> PhysicalSlot:
    """Map one logical bit to the proposed SRAM22 bank/address/pin slot."""
    if isinstance(word_address, bool) or not isinstance(word_address, int):
        raise TypeError("word_address must be an integer")
    if isinstance(codeword_bit, bool) or not isinstance(codeword_bit, int):
        raise TypeError("codeword_bit must be an integer")
    maximum_bit = 72 if protected else 64
    if not 0 <= word_address < 256 or not 0 <= codeword_bit < maximum_bit:
        raise ValueError("logical word or bit is outside the architecture")
    config = _as_interleaving(interleaving)
    banks = _BANKS[config]
    macro_kind = "data" if codeword_bit < 64 else "ecc"
    local_bit = codeword_bit if macro_kind == "data" else codeword_bit - 64
    return PhysicalSlot(
        macro_kind=macro_kind,
        bank=local_bit % banks,
        macro_address=word_address // banks,
        macro_data_pin=(local_bit // banks) * banks + word_address % banks,
    )


def slot_to_logical(
    slot: PhysicalSlot,
    interleaving: InterleavingId | str,
    *,
    protected: bool,
) -> tuple[int, int]:
    """Invert a used slot; reject spare rows and impossible macro pins."""
    config = _as_interleaving(interleaving)
    banks = _BANKS[config]
    if slot.bank >= banks:
        raise ValueError("slot bank is outside the interleaving configuration")
    if slot.macro_kind == "ecc" and not protected:
        raise ValueError("unprotected architecture has no ECC macro")
    macro_width = 64 if slot.macro_kind == "data" else 8
    if slot.macro_data_pin >= macro_width or slot.macro_address >= 256:
        raise ValueError("slot is outside the SRAM macro")
    word_address = slot.macro_address * banks + slot.macro_data_pin % banks
    local_bit = (slot.macro_data_pin // banks) * banks + slot.bank
    if word_address >= 256 or local_bit >= macro_width:
        raise ValueError("slot belongs to unused capacity in this mapping")
    codeword_bit = local_bit if slot.macro_kind == "data" else local_bit + 64
    return word_address, codeword_bit


def map_physical_slots_to_codewords(
    slots: Iterable[PhysicalSlot],
    interleaving: InterleavingId | str,
    *,
    protected: bool,
) -> tuple[CodewordFault, ...]:
    """Join externally established physical slots to per-codeword masks."""
    slot_list = list(slots)
    if len(set(slot_list)) != len(slot_list):
        raise ValueError("a physical upset event cannot contain duplicate slots")
    grouped: dict[int, set[int]] = defaultdict(set)
    for slot in slot_list:
        word, bit = slot_to_logical(slot, interleaving, protected=protected)
        grouped[word].add(bit)
    return tuple(
        CodewordFault(word, tuple(sorted(bits)))
        for word, bits in sorted(grouped.items())
    )


def bounded_codeword_multiplicities(
    fault_weight: int,
    scenario: TopologyScenario | str,
    *,
    nominal_codeword_spread: int | None = None,
) -> tuple[int, ...]:
    """Return an evidence-bounded error partition, never a probability model."""
    if isinstance(fault_weight, bool) or not isinstance(fault_weight, int):
        raise TypeError("fault_weight must be an integer")
    if fault_weight <= 0:
        raise ValueError("fault_weight must be positive")
    try:
        topology = TopologyScenario(scenario)
    except ValueError as exc:
        raise ValueError("unknown topology scenario") from exc
    if topology == TopologyScenario.BEST_CASE_INTERLEAVING:
        spread = fault_weight
    elif topology == TopologyScenario.WORST_CASE_CLUSTERING:
        spread = 1
    else:
        if nominal_codeword_spread is None:
            raise ValueError("nominal topology requires an explicit codeword spread")
        if (
            isinstance(nominal_codeword_spread, bool)
            or not isinstance(nominal_codeword_spread, int)
            or not 1 <= nominal_codeword_spread <= fault_weight
        ):
            raise ValueError("nominal_codeword_spread must be in [1, fault_weight]")
        spread = nominal_codeword_spread
    quotient, remainder = divmod(fault_weight, spread)
    return tuple(
        quotient + (1 if index < remainder else 0) for index in range(spread)
    )


__all__ = [
    "CodewordFault",
    "InterleavingId",
    "PhysicalSlot",
    "TopologyScenario",
    "bounded_codeword_multiplicities",
    "logical_to_slot",
    "map_physical_slots_to_codewords",
    "slot_to_logical",
]
