"""Deterministic interval-ensemble uncertainty utilities.

The sampler covers declared epistemic intervals.  It does not claim that the
intervals form fitted probability distributions.  Quantiles computed from the
ensemble are therefore scenario quantiles, not statistical confidence limits.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import statistics
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class IntervalParameter:
    name: str
    low: float
    high: float
    scale: str = "linear"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("interval name must be non-empty")
        if not math.isfinite(self.low) or not math.isfinite(self.high):
            raise ValueError("interval endpoints must be finite")
        if self.low > self.high:
            raise ValueError("interval low must not exceed high")
        if self.scale not in {"linear", "log"}:
            raise ValueError("scale must be linear or log")
        if self.scale == "log" and self.low <= 0.0:
            raise ValueError("log interval endpoints must be strictly positive")

    def from_unit(self, unit_value: float) -> float:
        if not 0.0 <= unit_value <= 1.0:
            raise ValueError("unit value must be in [0, 1]")
        if self.scale == "linear":
            return self.low + unit_value * (self.high - self.low)
        return math.exp(
            math.log(self.low)
            + unit_value * (math.log(self.high) - math.log(self.low))
        )


def latin_hypercube_samples(
    parameters: Sequence[IntervalParameter], sample_count: int, seed: int
) -> list[dict[str, float]]:
    """Return deterministic, independently permuted interval strata."""
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 2:
        raise ValueError("sample_count must be an integer >= 2")
    names = [parameter.name for parameter in parameters]
    if len(names) != len(set(names)):
        raise ValueError("parameter names must be unique")
    samples: list[dict[str, float]] = [dict() for _ in range(sample_count)]
    rng = random.Random(seed)
    for parameter in parameters:
        # Mid-stratum locations make the interval coverage deterministic; only
        # their cross-parameter pairing is shuffled by the declared seed.
        unit_values = [(index + 0.5) / sample_count for index in range(sample_count)]
        rng.shuffle(unit_values)
        for row, unit_value in zip(samples, unit_values):
            row[parameter.name] = parameter.from_unit(unit_value)
    return samples


def percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("at least one value is required")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0, 1]")
    ordered = sorted(float(value) for value in values)
    if not all(math.isfinite(value) for value in ordered):
        raise ValueError("all values must be finite")
    if len(ordered) == 1:
        return ordered[0]
    location = probability * (len(ordered) - 1)
    lower = math.floor(location)
    upper = math.ceil(location)
    if lower == upper:
        return ordered[lower]
    fraction = location - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def scenario_quantile_summary(values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ValueError("at least one value is required")
    finite = [float(value) for value in values]
    if not all(math.isfinite(value) for value in finite):
        raise ValueError("all values must be finite")
    return {
        "mean": statistics.fmean(finite),
        "median": statistics.median(finite),
        "p05": percentile(finite, 0.05),
        "p95": percentile(finite, 0.95),
        "minimum": min(finite),
        "maximum": max(finite),
    }


def _average_ranks(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(indexed):
        end = start + 1
        while end < len(indexed) and indexed[end][1] == indexed[start][1]:
            end += 1
        average = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[indexed[position][0]] = average
        start = end
    return ranks


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("paired vectors of length >= 2 are required")
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right)
    )
    left_norm = math.sqrt(sum((x - left_mean) ** 2 for x in left))
    right_norm = math.sqrt(sum((y - right_mean) ** 2 for y in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def spearman_sensitivity(
    samples: Sequence[Mapping[str, float]], outputs: Sequence[float]
) -> list[dict[str, float | str]]:
    """Rank-correlation screening, normalized by absolute correlation sum."""
    if len(samples) != len(outputs) or len(samples) < 2:
        raise ValueError("samples and outputs must have equal length >= 2")
    names = list(samples[0])
    if any(set(sample) != set(names) for sample in samples):
        raise ValueError("all samples must contain identical parameters")
    output_ranks = _average_ranks(outputs)
    raw: list[tuple[str, float]] = []
    for name in names:
        input_ranks = _average_ranks([float(sample[name]) for sample in samples])
        raw.append((name, _pearson(input_ranks, output_ranks)))
    denominator = sum(abs(coefficient) for _, coefficient in raw)
    rows = [
        {
            "parameter": name,
            "spearman_rho": coefficient,
            "normalized_absolute_influence": (
                abs(coefficient) / denominator if denominator else 0.0
            ),
        }
        for name, coefficient in raw
    ]
    return sorted(
        rows,
        key=lambda row: float(row["normalized_absolute_influence"]),
        reverse=True,
    )


def murphy_yield_from_area_cm2(defect_density_per_cm2: float, area_cm2: float) -> float:
    product = defect_density_per_cm2 * area_cm2
    if product == 0.0:
        return 1.0
    return ((1.0 - math.exp(-product)) / product) ** 2


def normalized_good_die_carbon_index(sample: Mapping[str, float]) -> float:
    """Parametric normalized model for uncertainty-path verification.

    The baseline component split (0.07 Scope 1, 0.58 Scope 2, 0.35 upstream)
    is a constructed point within imec's reported share ranges, not a measured
    node coefficient.  The index equals one at all baseline factors.
    """
    required = {
        "fab_grid_CI_factor",
        "fab_energy_factor",
        "gas_use_factor",
        "abatement_efficiency",
        "upstream_factor",
        "defect_density_per_cm2",
        "line_yield_fraction",
    }
    if set(sample) != required:
        raise ValueError(f"normalized model requires parameters {sorted(required)}")
    abatement = sample["abatement_efficiency"]
    line_yield = sample["line_yield_fraction"]
    if not 0.0 <= abatement <= 1.0 or not 0.0 < line_yield <= 1.0:
        raise ValueError("abatement and line yield are invalid")
    scope2 = (
        0.58 * sample["fab_grid_CI_factor"] * sample["fab_energy_factor"]
    )
    scope1 = (
        0.07 * sample["gas_use_factor"] * (1.0 - abatement) / (1.0 - 0.90)
    )
    upstream = 0.35 * sample["upstream_factor"]
    baseline_die_yield = murphy_yield_from_area_cm2(0.15, 1.0)
    scenario_die_yield = murphy_yield_from_area_cm2(
        sample["defect_density_per_cm2"], 1.0
    )
    yield_allocation_factor = (baseline_die_yield * 0.90) / (
        scenario_die_yield * line_yield
    )
    return (scope1 + scope2 + upstream) * yield_allocation_factor


def evaluate_ensemble(
    parameters: Sequence[IntervalParameter],
    sample_count: int,
    seed: int,
    model: Callable[[Mapping[str, float]], float],
) -> tuple[list[dict[str, float]], list[float]]:
    samples = latin_hypercube_samples(parameters, sample_count, seed)
    outputs = [float(model(sample)) for sample in samples]
    if not all(math.isfinite(output) for output in outputs):
        raise OverflowError("uncertainty model produced a non-finite output")
    return samples, outputs
