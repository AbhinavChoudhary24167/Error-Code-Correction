import math

import pytest

import ecc_selector
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
    assert emb["best_case_kgco2e"] != pytest.approx(emb["lower_bound_kgco2e"])


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


def test_node_mapping_metadata_for_uncalibrated_node():
    emb = estimate_embodied_carbon(node_nm=14, area_cm2=0.2)
    assumptions = emb["assumptions"]
    assert assumptions["requested_node_nm"] == 14
    assert assumptions["calibrated_node_nm"] == 16
    assert assumptions["node_mapping_mode"] == "nearest_calibrated"


def test_invalid_inputs_raise_clean_errors():
    with pytest.raises(ValueError, match="energy_joules must be non-negative"):
        estimate_operational_carbon(energy_joules=-1.0)
    with pytest.raises(ValueError, match="area_cm2 must be non-negative"):
        estimate_embodied_carbon(node_nm=16, area_cm2=-0.1)
    with pytest.raises(ValueError, match="years must be positive"):
        estimate_operational_carbon(energy_joules=1.0, years=0)
    with pytest.raises(ValueError, match="accesses_per_day must be positive"):
        estimate_operational_carbon(energy_joules=1.0, accesses_per_day=0)
    with pytest.raises(ValueError, match="Unknown grid_region=moon"):
        estimate_operational_carbon(energy_joules=1.0, grid_region="moon")
    with pytest.raises(ValueError, match="fab_intensity_kgco2e_per_cm2 must be positive"):
        estimate_embodied_carbon(node_nm=16, area_cm2=0.1, fab_intensity_kgco2e_per_cm2=0)
    with pytest.raises(ValueError, match="yield_loss_factor must be positive"):
        estimate_embodied_carbon(node_nm=16, area_cm2=0.1, yield_loss_factor=0)
    with pytest.raises(ValueError, match="Ambiguous workload specification"):
        estimate_operational_carbon(energy_joules=1.0, lifetime_energy_joules=10.0, total_accesses=2)


def test_uncertainty_separate_from_scenario_bounds():
    bounds = estimate_carbon_bounds(node_nm=16, area_cm2=0.1, energy_joules=1000.0, total_accesses=100)
    assert "uncertainty" in bounds
    assert bounds["uncertainty"]["static_carbon_kgco2e"]["lower_bound_kgco2e"] < bounds["nominal"]["static_carbon_kgco2e"]
    assert bounds["best_case"]["static_carbon_kgco2e"] <= bounds["worst_case"]["static_carbon_kgco2e"]
    assert bounds["uncertainty"]["static_carbon_kgco2e"]["lower_bound_kgco2e"] != pytest.approx(
        bounds["best_case"]["static_carbon_kgco2e"]
    )


def test_selector_default_behavior_unchanged_without_policy():
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    omitted = select(codes, **_selector_params())
    explicit_none = select(codes, carbon_policy=None, **_selector_params())
    assert omitted["best"]["code"] == explicit_none["best"]["code"]
    for rec in omitted["candidate_records"]:
        assert "dynamic_carbon_kgco2e" not in rec
        assert "static_carbon_kgco2e" not in rec


def test_selector_carbon_policy_routes_ranking_logic(monkeypatch):
    base = {
        "sram-secded-8": {
            "FIT": 10.0,
            "ESII": 1.0,
            "carbon_kg": 5.0,
            "E_dyn_kWh": 1.0,
            "E_leak_kWh": 0.0,
            "E_scrub_kWh": 0.0,
            "latency_ns": 1.0,
            "latency_base_ns": 0.0,
            "area_logic_mm2": 5.0,
            "area_macro_mm2": 0.0,
            "notes": "",
            "includes_scrub_energy": True,
            "fit_bit": 1.0,
            "fit_word_post": 1.0,
            "flux_rel": 1.0,
        },
        "sram-bch-32": {
            "FIT": 12.0,
            "ESII": 1.0,
            "carbon_kg": 4.0,
            "E_dyn_kWh": 3.0,
            "E_leak_kWh": 0.0,
            "E_scrub_kWh": 0.0,
            "latency_ns": 1.0,
            "latency_base_ns": 0.0,
            "area_logic_mm2": 1.0,
            "area_macro_mm2": 0.0,
            "notes": "",
            "includes_scrub_energy": True,
            "fit_bit": 1.0,
            "fit_word_post": 1.0,
            "flux_rel": 1.0,
        },
        "polar-128-96": {
            "FIT": 11.0,
            "ESII": 1.0,
            "carbon_kg": 6.0,
            "E_dyn_kWh": 2.0,
            "E_leak_kWh": 0.0,
            "E_scrub_kWh": 0.0,
            "latency_ns": 1.0,
            "latency_base_ns": 0.0,
            "area_logic_mm2": 2.0,
            "area_macro_mm2": 0.0,
            "notes": "",
            "includes_scrub_energy": True,
            "fit_bit": 1.0,
            "fit_word_post": 1.0,
            "flux_rel": 1.0,
        },
    }

    def _fake_metrics(code, **kwargs):
        return {"code": code, **base[code]}

    def _fake_bounds(*, area_cm2, energy_joules, **kwargs):
        return {
            "nominal": {
                "static_carbon_kgco2e": area_cm2 * 100.0,
                "dynamic_carbon_kgco2e": energy_joules / 3_600_000.0,
                "total_carbon_kgco2e": area_cm2 * 100.0 + energy_joules / 3_600_000.0,
            },
            "best_case": {"static_carbon_kgco2e": 0.0, "dynamic_carbon_kgco2e": 0.0, "total_carbon_kgco2e": 0.0},
            "worst_case": {"static_carbon_kgco2e": 1.0, "dynamic_carbon_kgco2e": 1.0, "total_carbon_kgco2e": 2.0},
            "assumptions": {},
        }

    monkeypatch.setattr(ecc_selector, "_compute_metrics", _fake_metrics)
    monkeypatch.setattr(ecc_selector, "_annotate_gs", lambda recs, weights: None)
    monkeypatch.setattr(ecc_selector, "estimate_carbon_bounds", _fake_bounds)
    codes = ["sram-secded-8", "sram-bch-32", "polar-128-96"]
    params = _selector_params()
    winners = {
        "minimum_dynamic_carbon": select(codes, carbon_policy="minimum_dynamic_carbon", **params)["best"]["code"],
        "minimum_static_carbon": select(codes, carbon_policy="minimum_static_carbon", **params)["best"]["code"],
        "minimum_total_carbon": select(codes, carbon_policy="minimum_total_carbon", **params)["best"]["code"],
        "balanced_carbon_energy": select(codes, carbon_policy="balanced_carbon_energy", **params)["best"]["code"],
    }
    assert len(set(winners.values())) >= 2


def test_selector_policy_routing_uses_policy_specific_metrics(monkeypatch):
    def _fake_bounds(*, area_cm2, energy_joules, **kwargs):
        # Force a tradeoff so static/dynamic minima differ across candidates.
        static = area_cm2 * 100.0
        dynamic = 1000.0 / max(area_cm2, 1e-9)
        return {
            "nominal": {
                "static_carbon_kgco2e": static,
                "dynamic_carbon_kgco2e": dynamic,
                "total_carbon_kgco2e": static + dynamic,
            },
            "best_case": {
                "static_carbon_kgco2e": static,
                "dynamic_carbon_kgco2e": dynamic,
                "total_carbon_kgco2e": static + dynamic,
            },
            "worst_case": {
                "static_carbon_kgco2e": static,
                "dynamic_carbon_kgco2e": dynamic,
                "total_carbon_kgco2e": static + dynamic,
            },
            "assumptions": {},
        }

    monkeypatch.setattr(ecc_selector, "estimate_carbon_bounds", _fake_bounds)
    codes = ["sram-secded-8", "sram-bch-32", "polar-128-96"]
    params = _selector_params()

    dynamic_pick = select(codes, carbon_policy="minimum_dynamic_carbon", **params)
    static_pick = select(codes, carbon_policy="minimum_static_carbon", **params)

    assert dynamic_pick["best"]["code"] != static_pick["best"]["code"]


def test_zero_edge_cases_are_safe():
    op = estimate_operational_carbon(energy_joules=0.0, total_accesses=10)
    assert op["nominal_kgco2e"] == pytest.approx(0.0)
    emb = estimate_embodied_carbon(node_nm=16, area_cm2=0.0)
    assert emb["nominal_kgco2e"] == pytest.approx(0.0)
    bounds = estimate_carbon_bounds(node_nm=16, area_cm2=0.0, energy_joules=0.0, total_accesses=1)
    score = carbon_breakdown(bounds=bounds)
    assert score["total_carbon_kgco2e"] == pytest.approx(0.0)
    assert score["static_fraction"] == pytest.approx(0.0)
    assert score["dynamic_fraction"] == pytest.approx(0.0)


def test_unit_consistency_and_lifetime_scaling():
    assert JOULES_PER_KWH == pytest.approx(3.6e6)
    op_1kwh = estimate_operational_carbon(energy_joules=JOULES_PER_KWH, lifetime_energy_joules=JOULES_PER_KWH, grid_factor_kgco2e_per_kwh=1.0)
    assert op_1kwh["energy_kwh"] == pytest.approx(1.0)
    op_3600j = estimate_operational_carbon(energy_joules=3600.0, lifetime_energy_joules=3600.0, grid_factor_kgco2e_per_kwh=1.0)
    assert op_3600j["energy_kwh"] == pytest.approx(0.001)
    op_a = estimate_operational_carbon(energy_joules=20.0, total_accesses=10, grid_factor_kgco2e_per_kwh=1.0)
    op_b = estimate_operational_carbon(energy_joules=20.0, total_accesses=20, grid_factor_kgco2e_per_kwh=1.0)
    assert op_b["nominal_kgco2e"] == pytest.approx(op_a["nominal_kgco2e"] * 2.0)


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
