"""Simulate SEC-DED and TAEC ECC schemes on random error patterns.

This utility compares the correction, double-error detection and miss
rates of a traditional Hamming SEC-DED code against a hypothetical
Triple Adjacent Error Correction (TAEC) code.  A Monte Carlo approach
draws random error patterns and checks whether each code corrects,
merely detects or completely misses them using simplified coverage
models from :mod:`fit`.

Usage:
    python taec_hamming_sim.py --trials 10000 --seed 1
"""
from __future__ import annotations

import argparse
import random
from collections import Counter
from typing import Dict, Set, Tuple

from fit import ecc_coverage_factory

Pattern = Tuple[int, str | None]

# Enumerate the patterns we want to exercise.
PATTERNS: Tuple[Pattern, ...] = (
    (1, None),
    (2, "adj"),
    (2, "nonadj"),
    (3, "adj"),
    (3, "nonadj"),
)

# Patterns that are *detected* but not corrected.
DETECTABLE_ONLY: Dict[str, Set[Pattern]] = {
    "SEC-DED": {(2, "adj"), (2, "nonadj")},
    "TAEC": {(2, "nonadj"), (3, "nonadj")},
}


def _correctable(code: str) -> Set[Pattern]:
    """Return the subset of :data:`PATTERNS` corrected by ``code``."""

    cov = ecc_coverage_factory(code)
    return {p for p in PATTERNS if cov(p) == 1.0}


def simulate_code(code: str, trials: int = 10000, seed: int | None = None) -> Dict[str, int]:
    """Run a Monte Carlo simulation for ``code``.

    Parameters
    ----------
    code:
        ECC scheme name (e.g. ``"SEC-DED"`` or ``"TAEC"``).
    trials:
        Number of random error patterns to sample.
    seed:
        Optional seed for deterministic runs.

    Returns
    -------
    Mapping with counts of corrected, detected and undetected errors.
    """
    rng = random.Random(seed)
    correctable = _correctable(code)
    detectable = DETECTABLE_ONLY.get(code, set())
    stats = Counter()
    for _ in range(trials):
        pattern = rng.choice(PATTERNS)
        if pattern in correctable:
            stats["corrected"] += 1
        elif pattern in detectable:
            stats["detected"] += 1
        else:
            stats["undetected"] += 1
    stats["uncorrected"] = stats["detected"] + stats["undetected"]
    stats["trials"] = trials
    return dict(stats)


def simulate_both(trials: int = 10000, seed: int | None = None) -> Tuple[Dict[str, Dict[str, int]], Counter]:
    """Simulate SEC-DED and TAEC on the same error patterns."""
    rng = random.Random(seed)
    correctable = {code: _correctable(code) for code in ("SEC-DED", "TAEC")}
    detectable = {code: DETECTABLE_ONLY.get(code, set()) for code in ("SEC-DED", "TAEC")}
    stats = {code: Counter() for code in correctable}
    patterns = Counter()
    for _ in range(trials):
        pattern = rng.choice(PATTERNS)
        patterns[pattern] += 1
        for code in stats:
            if pattern in correctable[code]:
                stats[code]["corrected"] += 1
            elif pattern in detectable[code]:
                stats[code]["detected"] += 1
            else:
                stats[code]["undetected"] += 1
    for code in stats:
        stats[code]["uncorrected"] = stats[code]["detected"] + stats[code]["undetected"]
        stats[code]["trials"] = trials
    return {code: dict(cnt) for code, cnt in stats.items()}, patterns


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=10000, help="number of random patterns to simulate")
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducibility")
    args = parser.parse_args()

    results, patterns = simulate_both(args.trials, args.seed)

    print("Pattern distribution:")
    for (k, kind), count in sorted(patterns.items()):
        label = f"{k}-bit {'adjacent' if kind == 'adj' else 'nonadjacent' if kind == 'nonadj' else 'single'}"
        print(f"  {label:20s}: {count}")

    print("\nECC results:")
    for code, stat in results.items():
        corr = stat["corrected"]
        det = stat["detected"]
        und = stat.get("undetected", 0)
        print(
            f"  {code:7s} -> corrected: {corr} ({corr/args.trials:.2%}), "
            f"detected-only: {det} ({det/args.trials:.2%}), "
            f"undetected: {und} ({und/args.trials:.2%})"
        )


if __name__ == "__main__":
    main()
