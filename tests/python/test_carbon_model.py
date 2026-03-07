import math

import pytest

from carbon_model import (
    JOULES_PER_KWH,
    estimate_embodied_carbon,
    estimate_operational_carbon,
    estimate_total_carbon,
    estimate_carbon_bounds,
    carbon_breakdown,
)
from ecc_selector import select


def _selector_params():
    return {
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.040,
    }


def test_embodied_monotonicity_by_intensity_and_node():
    base = estimate_embodied_carbon(node_nm=28, area_cm2=0.2)
    high_intensity = estimate_embodied_carbon(node_nm=28, area_cm2=0.2, fab_intensity_kgco2e_per_cm2=30.0)
    advanced_node = estimate_embodied_carbon(node_nm=7, area_cm2=0.2)

    assert high_intensity["nominal_kgco2e"] > base["nominal_kgco2e"]
    assert advanced_node["nominal_kgco2e"] > base["nominal_kgco2e"]


def test_operational_monotonicity_by_energy_and_grid():
    low = estimate_operational_carbon(energy_joules=1000.0, grid_region="iceland")
    high_energy = estimate_operational_carbon(energy_joules=2000.0, grid_region="iceland")
    high_grid = estimate_operational_carbon(energy_joules=1000.0, grid_region="india")

    assert high_energy["nominal_kgco2e"] > low["nominal_kgco2e"]
    assert high_grid["nominal_kgco2e"] > low["nominal_kgco2e"]


def test_lifetime_total_consistency():
    bounds = estimate_carbon_bounds(
        node_nm=16,
        area_cm2=0.1,
        energy_joules=3600.0,
        total_accesses=1000,
        grid_region="us",
    )
    nominal = bounds["nominal"]
    expected = estimate_total_carbon(
        embodied_kgco2e=nominal["static_carbon_kgco2e"],
        dynamic_kgco2e_lifetime=nominal["dynamic_carbon_kgco2e"],
    )
    assert nominal["total_carbon_kgco2e"] == pytest.approx(expected)


def test_uncertainty_bounds_correctness():
    emb = estimate_embodied_carbon(node_nm=16, area_cm2=0.5, uncertainty_margin=0.2)
    assert emb["lower_bound_kgco2e"] == pytest.approx(emb["nominal_kgco2e"] * 0.8)
    assert emb["upper_bound_kgco2e"] == pytest.approx(emb["nominal_kgco2e"] * 1.2)
    assert emb["best_case_kgco2e"] <= emb["worst_case_kgco2e"]


def test_region_override_correctness():
    op = estimate_operational_carbon(
        energy_joules=JOULES_PER_KWH,
        lifetime_energy_joules=JOULES_PER_KWH,
        grid_region="global_avg",
        grid_factor_kgco2e_per_kwh=0.4,
    )
    assert op["nominal_kgco2e"] == pytest.approx(0.4)


def test_selector_carbon_policy_integration():
    result = select(
        ["sec-ded-64", "sec-daec-64", "taec-64"],
        carbon_policy="minimum_dynamic_carbon",
        **_selector_params(),
    )
    best = result["best"]
    dynamic_vals = [r["dynamic_carbon_kgco2e"] for r in result["candidate_records"]]
    assert best["dynamic_carbon_kgco2e"] == pytest.approx(min(dynamic_vals))


def test_carbon_breakdown_schema_and_fractions():
    bounds = estimate_carbon_bounds(node_nm=16, area_cm2=0.05, energy_joules=1000.0)
    score = carbon_breakdown(bounds=bounds)
    assert set(score.keys()) == {
        "static_carbon_kgco2e",
        "dynamic_carbon_kgco2e",
        "total_carbon_kgco2e",
        "static_fraction",
        "dynamic_fraction",
        "nominal_score",
        "best_case_score",
        "worst_case_score",
        "assumptions",
    }
    assert math.isclose(score["static_fraction"] + score["dynamic_fraction"], 1.0, rel_tol=1e-9, abs_tol=1e-9)
