from __future__ import annotations

import inspect
import math
from pathlib import Path
import random
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
    / "metric_refoundation"
)
sys.path.insert(0, str(METRICS))

from green_service import (  # noqa: E402
    FeasibilityThresholds,
    ServiceOutcomes,
    dominates_service_carbon,
    evaluate_feasibility,
    exact_pareto_indices,
    gci,
    gse,
    gse_relative,
    matched_gse_relative,
    summarize_gse_samples,
    useful_service_bits,
)


def _outcomes(**changes: float) -> ServiceOutcomes:
    values = {
        "success_normal": 0.96,
        "success_corrected": 0.02,
        "success_after_retry": 0.01,
        "detected_failure": 0.005,
        "silent_data_corruption": 0.004,
        "timeout_or_sla_failure": 0.001,
    }
    values.update(changes)
    return ServiceOutcomes(**values)


def test_p1_dimensional_and_p7_unit_scaling_consistency() -> None:
    value_bits_per_kg = gse(8_000.0, 2.0)
    value_bytes_per_kg = gse(1_000.0, 2.0)
    value_bits_per_g = gse(8_000.0, 2_000.0)
    assert value_bits_per_kg == 8.0 * value_bytes_per_kg
    assert value_bits_per_kg == 1_000.0 * value_bits_per_g


def test_p2_positive_domain_and_reciprocity() -> None:
    assert gse(0.0, 2.0) == 0.0
    with pytest.raises(ValueError):
        gse(1.0, 0.0)
    with pytest.raises(ValueError):
        gci(0.0, 1.0)
    assert gse(10.0, 2.0) * gci(10.0, 2.0) == pytest.approx(1.0)


def test_p3_service_monotonicity_and_p4_carbon_monotonicity_randomized() -> None:
    rng = random.Random(0x475245454E)
    for _ in range(500):
        service = 10 ** rng.uniform(-9, 30)
        carbon = 10 ** rng.uniform(-12, 12)
        service_gain = 1.0 + rng.random() * 10.0
        carbon_gain = 1.0 + rng.random() * 10.0
        assert gse(service * service_gain, carbon) > gse(service, carbon)
        assert gse(service, carbon * carbon_gain) < gse(service, carbon)


def test_p5_dominance_consistency_randomized() -> None:
    rng = random.Random(20260908)
    for _ in range(500):
        sb = 10 ** rng.uniform(-6, 12)
        cb = 10 ** rng.uniform(-6, 6)
        sa = sb * (1.0 + rng.random())
        ca = cb / (1.0 + rng.random())
        assert dominates_service_carbon(sa, ca, sb, cb)
        assert gse(sa, ca) > gse(sb, cb)


def test_p6_candidate_set_independence_and_p10_no_percentiles() -> None:
    candidates = [(10.0, 2.0), (9.0, 1.0)]
    before = [gse(*item) for item in candidates]
    candidates.append((1e30, 1e-12))
    after = [gse(*item) for item in candidates[:2]]
    assert before == after
    assert "weights" not in inspect.signature(gse).parameters
    assert "candidates" not in inspect.signature(gse).parameters


def test_p8_baseline_relative_interpretability_and_matched_form() -> None:
    ratio = gse_relative(1_200.0, 2.0, 1_000.0, 2.0)
    assert ratio == pytest.approx(1.2)
    assert ratio > 1.0
    matched = matched_gse_relative(0.99, 2.0, 0.90, 2.2)
    explicit = gse_relative(64 * 100 * 0.99, 2.0, 64 * 100 * 0.90, 2.2)
    assert matched == pytest.approx(explicit)


def test_p9_no_arbitrary_weights() -> None:
    assert set(inspect.signature(gse).parameters) == {
        "useful_service_bits_value",
        "lifecycle_carbon_kgco2e_value",
    }


def test_p11_asymptotic_behavior() -> None:
    assert gse(1e30, 1.0) > gse(1e20, 1.0)
    assert gse(1.0, 1e30) < gse(1.0, 1e20)
    assert gse(0.0, 1e-30) == 0.0


def test_p12_uncertainty_summary_is_deterministic_and_ordered() -> None:
    samples = [gse(service, carbon) for service, carbon in [(9, 2), (10, 2), (11, 2), (12, 2)]]
    first = summarize_gse_samples(samples)
    second = summarize_gse_samples(list(reversed(samples)))
    assert first == second
    assert first["worst_case_interval_lower"] <= first["p05"] <= first["median"]
    assert first["median"] <= first["p95"] <= first["worst_case_interval_upper"]


def test_p13_pareto_compatibility() -> None:
    rows = [
        {"service": 10.0, "carbon": 2.0},
        {"service": 9.0, "carbon": 3.0},
        {"service": 12.0, "carbon": 4.0},
    ]
    assert exact_pareto_indices(rows, maximize=["service"], minimize=["carbon"]) == [0, 2]
    assert gse(10.0, 2.0) > gse(9.0, 3.0)


def test_service_outcome_semantics_count_recovered_due_as_success() -> None:
    outcomes = _outcomes()
    assert outcomes.service_success_probability == pytest.approx(0.99)
    assert useful_service_bits(64, 1_000, outcomes) == pytest.approx(63_360.0)
    assert outcomes.unrecovered_due_probability == pytest.approx(0.005)
    assert outcomes.sdc_probability == pytest.approx(0.004)


def test_outcomes_must_be_mutually_exclusive_and_complete() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        ServiceOutcomes(0.9, 0.1, 0.1, 0.0, 0.0)
    with pytest.raises(ValueError, match="non-negative"):
        ServiceOutcomes(1.1, -0.1, 0.0, 0.0, 0.0)


def test_no_threshold_is_invented_and_declared_constraint_is_hard() -> None:
    outcomes = _outcomes()
    absent = evaluate_feasibility(
        outcomes, thresholds=None, latency_ns=2.0, physical_feasible=True
    )
    assert absent["feasible"] is None
    assert absent["pareto_dimensions"] == ["GCI", "SDC", "DUE", "latency"]
    constrained = evaluate_feasibility(
        outcomes,
        thresholds=FeasibilityThresholds(max_sdc_probability=0.001),
        latency_ns=2.0,
        physical_feasible=True,
    )
    assert constrained["feasible"] is False
    assert constrained["violations"] == ["SDC_THRESHOLD"]


def test_legacy_harmonic_weakest_component_bound_is_false() -> None:
    scores = (0.1, 1.0, 1.0)
    weights = (0.6, 0.3, 0.1)
    harmonic = 1.0 / sum(weight / score for weight, score in zip(weights, scores))
    assert harmonic == pytest.approx(0.15625)
    assert harmonic > min(scores)


def test_large_reliability_does_not_guarantee_better_service_per_carbon() -> None:
    assert gse(0.999999, 100.0) < gse(0.99, 1.0)


def test_math_is_finite_across_wide_valid_domain() -> None:
    for exponent in range(-150, 151, 25):
        service = 10.0 ** exponent
        carbon = 10.0 ** -exponent
        assert math.isfinite(gse(service, carbon))


def test_ratio_outside_float_range_is_rejected_not_silently_infinite() -> None:
    with pytest.raises(OverflowError, match="finite float range"):
        gse(1e250, 1e-250)
