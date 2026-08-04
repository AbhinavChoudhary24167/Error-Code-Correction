"""Transparent synthetic SRAM fault-PMF benchmark generators."""

from __future__ import annotations

from collections import defaultdict
import math
import random
from typing import Any, Iterable


BENCHMARK_FAMILIES = (
    "uniform_sbu",
    "adjacent_dbu",
    "adjacent_triple_bit_upset",
    "variable_length_bursts",
    "non_adjacent_mbu",
    "mixed_sbu_dbu_mbu",
    "spatial_hot_spots",
    "bit_position_asymmetry",
    "voltage_sensitive",
    "temperature_sensitive",
    "geometry_filtered",
    "distribution_shift",
)


def _add_uniform(
    weights: dict[tuple[int, ...], float],
    families: dict[tuple[int, ...], set[str]],
    patterns: Iterable[tuple[int, ...]],
    total_weight: float,
    family: str,
) -> None:
    unique = sorted(set(tuple(sorted(pattern)) for pattern in patterns))
    if not unique or total_weight == 0:
        return
    each = total_weight / len(unique)
    for pattern in unique:
        weights[pattern] += each
        families[pattern].add(family)


def _non_adjacent_patterns(bit_width: int, rng: random.Random, count: int) -> list[tuple[int, ...]]:
    patterns: set[tuple[int, ...]] = set()
    attempts = 0
    while len(patterns) < count and attempts < count * 100:
        attempts += 1
        multiplicity = 2 if rng.random() < 0.65 else 3
        positions = tuple(sorted(rng.sample(range(bit_width), multiplicity)))
        if all(right - left > 1 for left, right in zip(positions, positions[1:])):
            patterns.add(positions)
    return sorted(patterns)


def build_benchmark(
    family: str,
    *,
    bit_width: int = 72,
    seed: int = 5200,
) -> dict[str, Any]:
    if family not in BENCHMARK_FAMILIES:
        raise ValueError(f"unknown benchmark family {family!r}")
    if bit_width < 8:
        raise ValueError("benchmark bit_width must be at least 8")
    rng = random.Random(seed)
    weights: dict[tuple[int, ...], float] = defaultdict(float)
    families: dict[tuple[int, ...], set[str]] = defaultdict(set)
    sbu = [(position,) for position in range(bit_width)]
    adjacent_dbu = [(position, position + 1) for position in range(bit_width - 1)]
    adjacent_tbu = [(position, position + 1, position + 2) for position in range(bit_width - 2)]

    if family == "uniform_sbu":
        _add_uniform(weights, families, sbu, 1.0, "sbu")
    elif family == "adjacent_dbu":
        _add_uniform(weights, families, adjacent_dbu, 1.0, "adjacent_dbu")
    elif family == "adjacent_triple_bit_upset":
        _add_uniform(weights, families, adjacent_tbu, 1.0, "adjacent_tbu")
    elif family == "variable_length_bursts":
        for length, mass in ((2, 0.45), (3, 0.35), (4, 0.20)):
            _add_uniform(
                weights,
                families,
                [tuple(range(start, start + length)) for start in range(bit_width - length + 1)],
                mass,
                f"burst_{length}",
            )
    elif family == "non_adjacent_mbu":
        _add_uniform(
            weights,
            families,
            _non_adjacent_patterns(bit_width, rng, min(160, bit_width * 2)),
            1.0,
            "non_adjacent_mbu",
        )
    elif family == "mixed_sbu_dbu_mbu":
        _add_uniform(weights, families, sbu, 0.55, "sbu")
        _add_uniform(weights, families, adjacent_dbu, 0.30, "adjacent_dbu")
        _add_uniform(
            weights,
            families,
            _non_adjacent_patterns(bit_width, rng, min(96, bit_width)),
            0.15,
            "non_adjacent_mbu",
        )
    elif family == "spatial_hot_spots":
        _add_uniform(weights, families, sbu, 0.35, "sbu")
        center = (bit_width - 1) / 2.0
        raw = [math.exp(-abs((left + 0.5) - center) / max(1.0, bit_width / 16)) for left in range(bit_width - 1)]
        scale = 0.65 / math.fsum(raw)
        for pattern, value in zip(adjacent_dbu, raw):
            weights[pattern] += value * scale
            families[pattern].add("adjacent_dbu")
    elif family == "bit_position_asymmetry":
        raw = [1.0 + 9.0 * (position / max(1, bit_width - 1)) ** 2 for position in range(bit_width)]
        scale = 1.0 / math.fsum(raw)
        for pattern, value in zip(sbu, raw):
            weights[pattern] += value * scale
            families[pattern].add("sbu")
    elif family == "voltage_sensitive":
        _add_uniform(weights, families, sbu, 0.25, "sbu")
        _add_uniform(weights, families, adjacent_dbu, 0.30, "adjacent_dbu")
        _add_uniform(weights, families, adjacent_tbu, 0.45, "adjacent_tbu")
    elif family == "temperature_sensitive":
        _add_uniform(weights, families, sbu, 0.45, "sbu")
        _add_uniform(weights, families, adjacent_dbu, 0.40, "adjacent_dbu")
        _add_uniform(
            weights,
            families,
            _non_adjacent_patterns(bit_width, rng, min(96, bit_width)),
            0.15,
            "non_adjacent_mbu",
        )
    elif family == "geometry_filtered":
        _add_uniform(weights, families, sbu, 0.30, "sbu")
        same_column = [(position, position + 8) for position in range(bit_width - 8)]
        _add_uniform(weights, families, same_column, 0.50, "geometry_filtered_mbu")
        _add_uniform(weights, families, adjacent_dbu, 0.20, "adjacent_dbu")
    elif family == "distribution_shift":
        _add_uniform(weights, families, sbu, 0.20, "sbu")
        _add_uniform(weights, families, adjacent_dbu, 0.25, "adjacent_dbu")
        _add_uniform(weights, families, adjacent_tbu, 0.25, "adjacent_tbu")
        _add_uniform(
            weights,
            families,
            _non_adjacent_patterns(bit_width, rng, min(160, bit_width * 2)),
            0.30,
            "non_adjacent_mbu",
        )

    total = math.fsum(weights.values())
    patterns = []
    for index, positions in enumerate(sorted(weights, key=lambda item: (len(item), item))):
        labels = sorted(families[positions])
        patterns.append(
            {
                "pattern_id": f"{family}-{index:04d}",
                "positions": list(positions),
                "probability": weights[positions] / total,
                "family": labels[0] if len(labels) == 1 else "mixed",
                "metadata": {"component_families": labels},
            }
        )
    probability_sum = math.fsum(item["probability"] for item in patterns)
    return {
        "schema_version": 1,
        "distribution_id": f"{family}-{bit_width}bit-seed{seed}-v1",
        "bit_width": bit_width,
        "raw_fit": 1000.0,
        "provenance": {
            "kind": "synthetic",
            "description": f"Modeled {family.replace('_', ' ')} conditional error-pattern PMF; not silicon measurement.",
            "source": None,
            "derivation": "Deterministic open benchmark generator in codeforge/benchmarks.py",
            "seed": seed,
            "generator_family": family,
            "parameters": {"bit_width": bit_width},
            "supported_bit_width": bit_width,
        },
        "normalization": {
            "probability_sum": probability_sum,
            "tolerance": 1e-12,
            "valid": math.isclose(probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-12),
        },
        "patterns": patterns,
    }
