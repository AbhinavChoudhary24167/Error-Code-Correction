"""Polar code utilities grounded in channel polarization theory.

The implementation follows Arikan's construction for a binary symmetric
channel (BSC).  It computes synthetic-channel Bhattacharyya parameters and
uses their sum as an upper bound on the successive-cancellation (SC) block
error probability.  This provides a physics- and math-grounded proxy for
the probability that a polar code corrects a given error pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Iterable, List


def bhattacharyya_bsc(crossover_p: float) -> float:
    """Return the Bhattacharyya parameter for a BSC with crossover ``p``."""

    p = min(max(crossover_p, 0.0), 0.5)
    return 2.0 * math.sqrt(p * (1.0 - p))


def _polar_transform(z: float) -> tuple[float, float]:
    """Return (Z^-, Z^+) for the polarization transform."""

    z_minus = min(1.0, 2.0 * z - z * z)
    z_plus = z * z
    return z_minus, z_plus


@lru_cache(maxsize=256)
def synthetic_channel_bhattacharyya(n: int, crossover_p: float) -> List[float]:
    """Return Bhattacharyya parameters for ``N=2**n`` synthetic channels."""

    z = bhattacharyya_bsc(crossover_p)
    zs = [z]
    for _ in range(n):
        next_zs: List[float] = []
        for z_val in zs:
            z_minus, z_plus = _polar_transform(z_val)
            next_zs.extend((z_minus, z_plus))
        zs = next_zs
    return zs


def polar_block_error_bound(n: int, k: int, crossover_p: float) -> float:
    """Upper bound on SC block error for a polar (N=2**n, K=k) code."""

    if k <= 0:
        return 1.0
    if k >= 2**n:
        return 0.0
    zs = synthetic_channel_bhattacharyya(n, crossover_p)
    info = sorted(zs)[:k]
    return min(1.0, sum(info))


@dataclass(frozen=True)
class PolarCodeModel:
    """Polar code proxy model for ECC coverage calculations."""

    n: int
    k: int
    adj_correlation: float = 1.35
    nonadj_correlation: float = 1.0

    @property
    def n_bits(self) -> int:
        return 2**self.n

    def effective_crossover(self, k_errors: int, *, word_bits: int, kind: str | None) -> float:
        """Convert a k-bit upset into an effective BSC crossover probability."""

        if word_bits <= 0:
            raise ValueError("word_bits must be positive")
        base = min(0.5, k_errors / float(word_bits))
        if kind == "adj":
            return min(0.5, base * self.adj_correlation)
        return min(0.5, base * self.nonadj_correlation)

    def coverage(self, k_errors: int, *, word_bits: int, kind: str | None) -> float:
        """Return probability of correct decoding for a k-bit upset pattern."""

        crossover = self.effective_crossover(k_errors, word_bits=word_bits, kind=kind)
        block_err = polar_block_error_bound(self.n, self.k, crossover)
        return max(0.0, 1.0 - block_err)

