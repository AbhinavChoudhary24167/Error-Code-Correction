"""Built-in ECC plugins; family-specific behavior stays outside framework core."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from codeforge.gf2 import encode_from_row_masks, generator_row_masks, matrix_columns_as_ints, syndrome_from_columns

from .contracts import DecodeResult, DecodeStatus


@dataclass
class LinearSyndromeAdapter:
    h: Sequence[Sequence[int]]
    g: Sequence[Sequence[int]]
    k: int
    n: int
    decoder_policy: str = "single_error"
    encoder_latency: int = 0
    decoder_latency: int = 0

    def __post_init__(self) -> None:
        self._columns = matrix_columns_as_ints(self.h)
        self._rows = generator_row_masks(self.g)
        self._single_map = {column: position for position, column in enumerate(self._columns)}
        self._adjacent_pairs: dict[int, tuple[int, int]] = {}
        self._adjacent_triples: dict[int, tuple[int, int, int]] = {}
        for start in range(self.k - 1):
            positions = (start, start + 1)
            self._adjacent_pairs.setdefault(self._columns[start] ^ self._columns[start + 1], positions)
        for start in range(self.k - 2):
            positions = (start, start + 1, start + 2)
            self._adjacent_triples.setdefault(
                self._columns[start] ^ self._columns[start + 1] ^ self._columns[start + 2], positions
            )

    def encode(self, data: int) -> int:
        if data < 0 or data >= (1 << self.k):
            raise ValueError(f"data does not fit k={self.k}")
        return encode_from_row_masks(data, self._rows)

    def decode(self, codeword: int) -> DecodeResult:
        if codeword < 0 or codeword >= (1 << self.n):
            return DecodeResult(None, DecodeStatus.INVALID_CONFIGURATION, None, None, None, self.decoder_latency)
        syndrome = syndrome_from_columns(codeword, self._columns)
        if syndrome == 0:
            return DecodeResult(codeword & ((1 << self.k) - 1), DecodeStatus.NO_ERROR, 0, codeword, None, self.decoder_latency)

        location: int | tuple[int, ...] | None = None
        if syndrome in self._single_map:
            location = self._single_map[syndrome]
        elif self.decoder_policy == "bounded_adjacent_double" and syndrome in self._adjacent_pairs:
            location = self._adjacent_pairs[syndrome]
        elif self.decoder_policy == "bounded_adjacent_triple" and syndrome in self._adjacent_triples:
            location = self._adjacent_triples[syndrome]

        if location is None:
            return DecodeResult(None, DecodeStatus.DETECTED_UNCORRECTABLE, syndrome, None, None, self.decoder_latency)
        positions = (location,) if isinstance(location, int) else location
        mask = sum(1 << position for position in positions)
        corrected = codeword ^ mask
        if syndrome_from_columns(corrected, self._columns) != 0:
            return DecodeResult(None, DecodeStatus.DETECTED_UNCORRECTABLE, syndrome, None, location, self.decoder_latency)
        return DecodeResult(
            corrected & ((1 << self.k) - 1), DecodeStatus.CORRECTED, syndrome, corrected, location, self.decoder_latency
        )


@dataclass
class BoundedCyclicAdapter:
    h: Sequence[Sequence[int]]
    g: Sequence[Sequence[int]]
    k: int
    n: int
    search_weight: int = 2
    encoder_latency: int = 0
    decoder_latency: int = 0

    def __post_init__(self) -> None:
        self._columns = matrix_columns_as_ints(self.h)
        self._rows = generator_row_masks(self.g)

    def encode(self, data: int) -> int:
        if data < 0 or data >= (1 << self.k):
            raise ValueError(f"data does not fit k={self.k}")
        return encode_from_row_masks(data, self._rows)

    def decode(self, codeword: int) -> DecodeResult:
        if codeword < 0 or codeword >= (1 << self.n):
            return DecodeResult(None, DecodeStatus.INVALID_CONFIGURATION, None, None, None, self.decoder_latency)
        syndrome = syndrome_from_columns(codeword, self._columns)
        if syndrome == 0:
            return DecodeResult(codeword & ((1 << self.k) - 1), DecodeStatus.NO_ERROR, 0, codeword, None, self.decoder_latency)
        for weight in range(1, self.search_weight + 1):
            for positions in combinations(range(self.n), weight):
                mask = sum(1 << position for position in positions)
                candidate = codeword ^ mask
                if syndrome_from_columns(candidate, self._columns) == 0:
                    location: int | tuple[int, ...] = positions[0] if weight == 1 else positions
                    return DecodeResult(
                        candidate & ((1 << self.k) - 1), DecodeStatus.CORRECTED, syndrome, candidate, location, self.decoder_latency
                    )
        return DecodeResult(None, DecodeStatus.DETECTED_UNCORRECTABLE, syndrome, None, None, self.decoder_latency)


@dataclass
class DeclaredSyndromeTableAdapter:
    """Execute an archived, deployed hard-decision syndrome table verbatim."""

    h: Sequence[Sequence[int]]
    g: Sequence[Sequence[int]]
    k: int
    n: int
    correction_entries: Sequence[Mapping[str, Any]]
    encoder_latency: int = 0
    decoder_latency: int = 0

    def __post_init__(self) -> None:
        self._columns = matrix_columns_as_ints(self.h)
        self._rows = generator_row_masks(self.g)
        self._correction_map: dict[int, tuple[int, ...]] = {}
        for entry in self.correction_entries:
            syndrome = int(str(entry["syndrome"]), 2)
            positions = tuple(map(int, entry["positions"]))
            if not positions or any(position < 0 or position >= self.n for position in positions):
                raise ValueError("invalid archived correction-table position")
            if syndrome in self._correction_map and self._correction_map[syndrome] != positions:
                raise ValueError("ambiguous archived syndrome correction table")
            self._correction_map[syndrome] = positions

    def encode(self, data: int) -> int:
        if data < 0 or data >= (1 << self.k):
            raise ValueError(f"data does not fit k={self.k}")
        return encode_from_row_masks(data, self._rows)

    def decode(self, codeword: int) -> DecodeResult:
        if codeword < 0 or codeword >= (1 << self.n):
            return DecodeResult(None, DecodeStatus.INVALID_CONFIGURATION, None, None, None, self.decoder_latency)
        syndrome = syndrome_from_columns(codeword, self._columns)
        if syndrome == 0:
            return DecodeResult(codeword & ((1 << self.k) - 1), DecodeStatus.NO_ERROR, 0, codeword, None, self.decoder_latency)
        positions = self._correction_map.get(syndrome)
        if positions is None:
            return DecodeResult(None, DecodeStatus.DETECTED_UNCORRECTABLE, syndrome, None, None, self.decoder_latency)
        mask = sum(1 << position for position in positions)
        corrected = codeword ^ mask
        if syndrome_from_columns(corrected, self._columns) != 0:
            return DecodeResult(None, DecodeStatus.DETECTED_UNCORRECTABLE, syndrome, None, positions, self.decoder_latency)
        location: int | tuple[int, ...] = positions[0] if len(positions) == 1 else positions
        return DecodeResult(
            corrected & ((1 << self.k) - 1), DecodeStatus.CORRECTED, syndrome,
            corrected, location, self.decoder_latency,
        )


def create_linear_adapter(*, code: Mapping[str, Any], implementation: Mapping[str, Any], policy: str = "single_error") -> LinearSyndromeAdapter:
    matrix = code["_resolved_matrix"]
    return LinearSyndromeAdapter(
        h=matrix["H"], g=matrix["G"], k=int(code["k"]), n=int(code["n"]),
        decoder_policy=policy, encoder_latency=int(implementation["encoder_latency"]),
        decoder_latency=int(implementation["decoder_latency"]),
    )


def create_bounded_cyclic_adapter(*, code: Mapping[str, Any], implementation: Mapping[str, Any], search_weight: int = 2) -> BoundedCyclicAdapter:
    matrix = code["_resolved_matrix"]
    return BoundedCyclicAdapter(
        h=matrix["H"], g=matrix["G"], k=int(code["k"]), n=int(code["n"]),
        search_weight=int(search_weight), encoder_latency=int(implementation["encoder_latency"]),
        decoder_latency=int(implementation["decoder_latency"]),
    )


def create_declared_table_adapter(
    *, code: Mapping[str, Any], implementation: Mapping[str, Any], table_path: str
) -> DeclaredSyndromeTableAdapter:
    path = Path(table_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("decoder", {}).get("correction_entries")
    if not isinstance(entries, list):
        raise ValueError(f"archived code has no deterministic correction table: {table_path}")
    matrix = code["_resolved_matrix"]
    return DeclaredSyndromeTableAdapter(
        h=matrix["H"], g=matrix["G"], k=int(code["k"]), n=int(code["n"]),
        correction_entries=entries, encoder_latency=int(implementation["encoder_latency"]),
        decoder_latency=int(implementation["decoder_latency"]),
    )
