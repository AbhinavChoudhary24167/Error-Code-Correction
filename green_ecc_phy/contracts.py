"""Technology-neutral functional contract shared by ECC plugins."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Protocol


class DecodeStatus(str, Enum):
    NO_ERROR = "NO_ERROR"
    CORRECTED = "CORRECTED"
    DETECTED_UNCORRECTABLE = "DETECTED_UNCORRECTABLE"
    ABSTAINED = "ABSTAINED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"


@dataclass(frozen=True)
class DecodeResult:
    data: int | None
    status: DecodeStatus
    syndrome: int | str | None
    corrected_codeword_optional: int | None
    error_location_optional: int | tuple[int, ...] | None
    latency: int

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


class EccAdapter(Protocol):
    """Public plugin contract; implementations may wrap arbitrary native ports."""

    k: int
    n: int

    def encode(self, data: int) -> int: ...

    def decode(self, codeword: int) -> DecodeResult: ...

