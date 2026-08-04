"""External test-only repetition-code plugin; deliberately outside framework core."""

from __future__ import annotations

from green_ecc_phy.contracts import DecodeResult, DecodeStatus


def repetition_matrix() -> dict[str, object]:
    return {
        "G": [[1, 1, 1]],
        "H": [[1, 1, 0], [1, 0, 1]],
        "data_positions": [0],
    }


class RepetitionAdapter:
    k = 1
    n = 3

    def __init__(self, latency: int = 0) -> None:
        self.latency = latency

    def encode(self, data: int) -> int:
        if data not in (0, 1):
            raise ValueError("repetition data must be one bit")
        return 0b111 if data else 0

    def decode(self, codeword: int) -> DecodeResult:
        if codeword < 0 or codeword >= 8:
            return DecodeResult(None, DecodeStatus.INVALID_CONFIGURATION, None, None, None, self.latency)
        ones = codeword.bit_count()
        data = 1 if ones >= 2 else 0
        corrected = 0b111 if data else 0
        bit0, bit1, bit2 = (codeword >> 0) & 1, (codeword >> 1) & 1, (codeword >> 2) & 1
        syndrome = (bit0 ^ bit1) | ((bit0 ^ bit2) << 1)
        status = DecodeStatus.NO_ERROR if codeword in (0, 0b111) else DecodeStatus.CORRECTED
        differences = tuple(bit for bit in range(3) if ((codeword ^ corrected) >> bit) & 1)
        location = differences[0] if len(differences) == 1 else differences
        return DecodeResult(data, status, syndrome, corrected, location, self.latency)


def create_adapter(*, code, implementation):
    del code
    return RepetitionAdapter(latency=int(implementation["decoder_latency"]))
