"""Reliability helpers for FIT aggregation and ECC coverage.

This module models the Failure In Time (FIT) rate of memory words both
before and after error correcting codes (ECC) are applied.  It also
provides helpers to scale word level FITs to system level metrics and to
derive mean time to failure (MTTF).
"""
from __future__ import annotations

from math import comb
from typing import Callable, Mapping, Tuple

Pattern = Tuple[int, str | None]
"""Tuple identifying an error pattern.

The first element is the number of flipped bits.  The optional second
string indicates whether the bits are ``"adj"``acent or ``"nonadj"``acent.
"""

WORD_BITS = 64
"""Default word width used when aggregating to system level FIT."""


def compute_fit_pre(
    word_bits: int, fit_bit_single: float, mbu_rates_by_k: Mapping[int, Mapping[str, float] | float]
) -> float:
    """Return the raw FIT per word before ECC protection.

    Parameters
    ----------
    word_bits:
        Number of bits in the protected word.
    fit_bit_single:
        FIT for a single bit experiencing an upset.
    mbu_rates_by_k:
        Mapping from upset multiplicity ``k`` to a FIT rate.  Values may be a
        float (total rate for that ``k``) or a nested mapping distinguishing
        ``{"adj": rate, "nonadj": rate}`` for adjacent and non-adjacent bursts.
    """

    fit = word_bits * fit_bit_single
    for rates in mbu_rates_by_k.values():
        if isinstance(rates, Mapping):
            fit += sum(rates.values())
        else:
            fit += float(rates)
    return fit


def compute_fit_post(
    word_bits: int,
    fit_bit_single: float,
    mbu_rates_by_k: Mapping[int, Mapping[str, float]],
    ecc_coverage: Callable[[Pattern], float],
    scrub_interval_s: float,
) -> float:
    """Return residual FIT per word after ECC with periodic scrubbing.

    Residual FIT accounts for two mechanisms:

    * *Instantaneous* multi-bit upsets (MBUs) that the ECC cannot correct.
      Adjacency of the affected bits is considered when computing ECC
      coverage.
    * *Accumulated* double-bit errors that arise between scrub operations
      from two independent single-bit upsets.  This follows
      ``C(w,2)*λ1^2*τ*(1 - C_ECC(2_nonadj))`` where ``λ1`` is the per-bit
      upset rate and ``τ`` the scrub interval in hours.
    """

    # Rate of single bit upsets (λ1) per hour
    lambda1 = fit_bit_single / 1_000_000_000
    tau_hr = scrub_interval_s / 3600.0

    accum = (
        comb(word_bits, 2)
        * (lambda1**2)
        * tau_hr
        * 1_000_000_000
        * (1 - ecc_coverage((2, "nonadj")))
    )

    instant = 0.0
    for k, patterns in mbu_rates_by_k.items():
        for kind, rate in patterns.items():
            instant += rate * (1 - ecc_coverage((k, kind)))

    return accum + instant


def ecc_coverage_factory(code: str) -> Callable[[Pattern], float]:
    """Return a coverage function for the requested ECC ``code``.

    Supported codes are ``"SEC-DED"``, ``"SEC-DAEC"``, and ``"TAEC"``.
    The returned callable accepts a :class:`Pattern` tuple and returns the
    probability that the ECC corrects that pattern.
    """

    code = code.upper()

    def coverage(pattern: Pattern) -> float:
        k, kind = pattern
        if code == "SEC-DED":
            return 1.0 if k == 1 else 0.0
        if code == "SEC-DAEC":
            if k == 1:
                return 1.0
            if k == 2 and kind == "adj":
                return 1.0
            return 0.0
        if code == "TAEC":
            if k == 1:
                return 1.0
            if k == 2 and kind == "adj":
                return 1.0
            if k == 3 and kind == "adj":
                return 1.0
            return 0.0
        raise ValueError(f"Unsupported ECC code '{code}'")

    return coverage


def fit_system(capacity_gib: float, fit_word: float) -> float:
    """Return system level FIT for a memory of ``capacity_gib`` GiB."""

    words = capacity_gib * (2**30 * 8) / WORD_BITS
    return words * fit_word


def mttf_from_fit(fit_system: float) -> float:
    """Return mean time to failure in hours from a FIT value."""

    if fit_system <= 0:
        return float("inf")
    return 1_000_000_000 / fit_system
