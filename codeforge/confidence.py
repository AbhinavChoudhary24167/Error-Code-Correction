"""Finite-sample confidence intervals for structured fault-distribution masses."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


def clopper_pearson_interval(successes: int, trials: int, alpha: float) -> tuple[float, float]:
    """Return an exact two-sided binomial interval (coverage at least 1-alpha)."""

    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("require 0 <= successes <= trials and trials > 0")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0,1)")
    try:
        from scipy.stats import beta
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("sample confidence intervals require scipy.stats") from exc
    lower = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
    return lower, upper


def simultaneous_category_intervals(
    category_counts: Mapping[str, Mapping[str, int]],
    *,
    sample_count: int,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Bonferroni simultaneous intervals for multiplicity/geometry categories."""

    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be in (0,1)")
    flattened = [
        (dimension, category, int(count))
        for dimension, categories in category_counts.items()
        for category, count in categories.items()
    ]
    if not flattened:
        raise ValueError("at least one category count is required")
    family_alpha = 1.0 - confidence
    per_interval_alpha = family_alpha / len(flattened)
    intervals: dict[str, dict[str, Any]] = {}
    for dimension, category, count in flattened:
        lower, upper = clopper_pearson_interval(count, sample_count, per_interval_alpha)
        intervals.setdefault(str(dimension), {})[str(category)] = {
            "count": count,
            "estimate": count / sample_count,
            "lower": lower,
            "upper": upper,
        }
    return {
        "schema_version": 1,
        "calibration_kind": "statistically_calibrated",
        "method": "Bonferroni simultaneous Clopper-Pearson binomial intervals",
        "sample_count": sample_count,
        "declared_simultaneous_coverage": confidence,
        "family_alpha": family_alpha,
        "per_interval_alpha": per_interval_alpha,
        "interval_count": len(flattened),
        "category_intervals": intervals,
        "assumptions": [
            "samples are independent draws from a stationary categorical fault process",
            "each reported category is a predeclared binary event for its interval",
            "coverage applies to the listed masses, not to unobserved bit-exact support completeness",
        ],
    }


def pattern_intervals(
    pattern_counts: Mapping[str, int], *, sample_count: int, confidence: float = 0.95
) -> dict[str, Any]:
    records = simultaneous_category_intervals(
        {"pattern": {str(key): int(value) for key, value in pattern_counts.items()}},
        sample_count=sample_count,
        confidence=confidence,
    )
    return {
        **records,
        "pattern_intervals": records["category_intervals"].pop("pattern"),
        "category_intervals": {},
    }


def ambiguity_from_confidence_report(report: Mapping[str, Any], *, ambiguity_id: str) -> dict[str, Any]:
    if report.get("calibration_kind") != "statistically_calibrated":
        raise ValueError("only a statistically calibrated confidence report may be converted")
    category_intervals = {
        dimension: {
            category: {"lower": values["lower"], "upper": values["upper"]}
            for category, values in categories.items()
        }
        for dimension, categories in report.get("category_intervals", {}).items()
    }
    pattern_bounds = {
        pattern_id: {"lower": values["lower"], "upper": values["upper"]}
        for pattern_id, values in report.get("pattern_intervals", {}).items()
    }
    return {
        "schema_version": 1,
        "ambiguity_id": ambiguity_id,
        "type": "structured_interval",
        "radius": 1.0,
        "calibration": {
            "kind": "statistically_calibrated",
            "method": report["method"],
            "sample_count": report["sample_count"],
            "declared_coverage": report["declared_simultaneous_coverage"],
        },
        "category_intervals": category_intervals,
        "pattern_intervals": pattern_bounds,
    }
