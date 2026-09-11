from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
UNCERTAINTY = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
    / "carbon"
    / "uncertainty"
)
sys.path.insert(0, str(UNCERTAINTY))

from uncertainty import (  # noqa: E402
    IntervalParameter,
    evaluate_ensemble,
    latin_hypercube_samples,
    normalized_good_die_carbon_index,
    percentile,
    scenario_quantile_summary,
    spearman_sensitivity,
)


def _parameters() -> list[IntervalParameter]:
    config = json.loads((UNCERTAINTY / "UNCERTAINTY_MODEL.json").read_text("utf-8"))
    return [
        IntervalParameter(item["name"], item["low"], item["high"], item["scale"])
        for item in config["parameters"]
    ]


def test_latin_hypercube_is_seed_deterministic() -> None:
    parameters = _parameters()
    assert latin_hypercube_samples(parameters, 64, 17) == latin_hypercube_samples(
        parameters, 64, 17
    )
    assert latin_hypercube_samples(parameters, 64, 17) != latin_hypercube_samples(
        parameters, 64, 18
    )


def test_every_parameter_stratum_is_covered_once() -> None:
    parameter = IntervalParameter("x", 0.0, 1.0)
    samples = latin_hypercube_samples([parameter], 8, 5)
    observed = sorted(sample["x"] for sample in samples)
    assert observed == pytest.approx([(index + 0.5) / 8 for index in range(8)])


def test_scenario_quantiles_are_ordered_and_finite() -> None:
    _, outputs = evaluate_ensemble(
        _parameters(), 256, 20260908, normalized_good_die_carbon_index
    )
    summary = scenario_quantile_summary(outputs)
    assert all(math.isfinite(value) for value in summary.values())
    assert summary["minimum"] <= summary["p05"] <= summary["median"]
    assert summary["median"] <= summary["p95"] <= summary["maximum"]


def test_percentile_uses_linear_interpolation() -> None:
    assert percentile([0.0, 10.0], 0.25) == pytest.approx(2.5)


def test_expected_monotonic_directions_hold_in_normalized_model() -> None:
    base = {
        "fab_grid_CI_factor": 1.0,
        "fab_energy_factor": 1.0,
        "gas_use_factor": 1.0,
        "abatement_efficiency": 0.90,
        "upstream_factor": 1.0,
        "defect_density_per_cm2": 0.15,
        "line_yield_fraction": 0.90,
    }
    assert normalized_good_die_carbon_index(base) == pytest.approx(1.0)
    higher_ci = dict(base, fab_grid_CI_factor=1.1)
    higher_abatement = dict(base, abatement_efficiency=0.95)
    worse_defects = dict(base, defect_density_per_cm2=0.3)
    assert normalized_good_die_carbon_index(higher_ci) > 1.0
    assert normalized_good_die_carbon_index(higher_abatement) < 1.0
    assert normalized_good_die_carbon_index(worse_defects) > 1.0


def test_sensitivity_is_ranked_and_normalized() -> None:
    samples, outputs = evaluate_ensemble(
        _parameters(), 256, 7, normalized_good_die_carbon_index
    )
    rows = spearman_sensitivity(samples, outputs)
    assert {row["parameter"] for row in rows} == {
        parameter.name for parameter in _parameters()
    }
    assert sum(float(row["normalized_absolute_influence"]) for row in rows) == pytest.approx(1.0)
    influences = [float(row["normalized_absolute_influence"]) for row in rows]
    assert influences == sorted(influences, reverse=True)


def test_checked_in_results_are_reproducible(tmp_path: Path) -> None:
    # The generator writes next to itself. Snapshot bytes, run, compare, and
    # leave the canonical files unchanged.
    result_paths = [
        UNCERTAINTY / "UNCERTAINTY_RESULTS.csv",
        UNCERTAINTY / "UNCERTAINTY_SENSITIVITY.csv",
    ]
    before = [path.read_bytes() for path in result_paths]
    subprocess.run(
        [sys.executable, "-B", str(UNCERTAINTY / "run_uncertainty.py")],
        cwd=UNCERTAINTY,
        check=True,
    )
    after = [path.read_bytes() for path in result_paths]
    assert after == before
    with result_paths[0].open("r", encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["evidence_label"] == "PARAMETRIC_UNCERTAIN"
    assert row["quantile_semantics"] == "SCENARIO_ENSEMBLE_NOT_CONFIDENCE"
