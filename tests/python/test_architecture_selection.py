from __future__ import annotations

from pathlib import Path

import pytest

from architecture.deployment import reconfiguration_overhead
from architecture.providers import MuxCharacterizationProvider
from architecture.plugins import PluginRegistry
from architecture.robustness import monte_carlo_robustness
from architecture.selection import (
    apply_hard_constraints,
    exact_pareto,
    score_diagnostics,
    select_baselines,
)
from architecture.types import Scenario, Workload
from ecc_selector import _nsga2_sort
from esii import ESIIInputs, compute_esii


def _record(config_id: str, fit: float, carbon: float, latency: float, energy: float) -> dict:
    return {
        "config_id": config_id,
        "family": "SEC-DED" if config_id == "a" else "BCH",
        "FIT": fit,
        "architecture_carbon_kg": carbon,
        "architecture_latency_ns": latency,
        "architecture_energy_j": energy,
        "capacity_efficiency": 0.8,
        "ESII": 0.8 if config_id == "a" else 0.6,
        "NESII": 80.0 if config_id == "a" else 60.0,
        "GS": 70.0 if config_id == "a" else 90.0,
    }


def test_hard_constraints_then_exact_pareto_and_baselines() -> None:
    records = [_record("a", 2.0, 1.0, 1.0, 3.0), _record("b", 1.0, 2.0, 2.0, 2.0)]
    feasible, infeasible = apply_hard_constraints(records, {"latency_ns_max": 1.5})
    assert [item["config_id"] for item in feasible] == ["a"]
    assert [item["config_id"] for item in infeasible] == ["b"]
    assert feasible[0]["constraint_margins"]["latency_ns_max"] == pytest.approx(0.5)
    assert infeasible[0]["constraint_margins"]["latency_ns_max"] == pytest.approx(-0.5)
    assert [item["config_id"] for item in exact_pareto(records)] == ["a", "b"]
    baselines = select_baselines(records, fault_regime="heavy", preference_weights={})
    assert baselines["selections"]["static_secded"] == "a"
    assert baselines["selections"]["fault_regime_lookup"] == "b"


def test_score_diagnostics_distinguish_equivalence_from_agreement() -> None:
    records = [_record("a", 2.0, 1.0, 1.0, 3.0), _record("b", 1.0, 2.0, 2.0, 2.0)]
    report = score_diagnostics(records)
    assert report["argmax_by_score"]["ESII"] == "a"
    assert report["argmax_by_score"]["NESII"] == "a"
    assert report["argmax_by_score"]["GS"] == "b"
    assert report["all_scores_same_winner"] is False
    assert report["rank_correlations"]["ESII_vs_NESII"] == pytest.approx(1.0)


def test_esii_monotonicity_in_reliability_and_carbon_burden() -> None:
    base = ESIIInputs(100.0, 10.0, 1.0, 1.0, 0.5, 0.1)
    better_reliability = ESIIInputs(100.0, 1.0, 1.0, 1.0, 0.5, 0.1)
    higher_carbon = ESIIInputs(100.0, 10.0, 1.0, 1.0, 0.5, 10.0)
    assert compute_esii(better_reliability)["ESII"] > compute_esii(base)["ESII"]
    assert compute_esii(higher_carbon)["ESII"] < compute_esii(base)["ESII"]


def test_nsga_sort_agrees_with_exact_enumeration_on_tractable_subset() -> None:
    records = [
        {"code": "a", "FIT": 2.0, "carbon_kg": 1.0, "latency_ns": 1.0},
        {"code": "b", "FIT": 1.0, "carbon_kg": 2.0, "latency_ns": 2.0},
        {"code": "c", "FIT": 3.0, "carbon_kg": 3.0, "latency_ns": 3.0},
    ]
    fronts, *_ = _nsga2_sort(records)
    exact = exact_pareto(
        [
            {
                "config_id": item["code"],
                "FIT": item["FIT"],
                "architecture_carbon_kg": item["carbon_kg"],
                "architecture_latency_ns": item["latency_ns"],
            }
            for item in records
        ]
    )
    assert {records[index]["code"] for index in fronts[0]} == {item["config_id"] for item in exact}


def test_robustness_is_deterministic() -> None:
    records = [_record("a", 2.0, 1.0, 1.0, 3.0), _record("b", 1.0, 2.0, 2.0, 2.0)]
    kwargs = dict(
        constraints={},
        preference_weights={"reliability": 1, "carbon": 1, "latency": 1},
        relative_intervals={"fit": 0.1, "energy": 0.1, "carbon": 0.1, "latency": 0.1},
        samples=50,
        seed=1723,
    )
    assert monte_carlo_robustness(records, **kwargs) == monte_carlo_robustness(records, **kwargs)
    robust = monte_carlo_robustness(records, **kwargs)
    assert all(
        0 <= item["robust_pareto_membership_probability"] <= 1
        for item in robust["candidates"].values()
    )


def test_reconfiguration_amortization() -> None:
    scenario = Scenario(
        "s",
        16,
        0.8,
        75,
        1.0,
        64,
        0.08,
        0.5,
        "moderate",
        1000,
        Workload(0.5, 0.5, 1000, decision_epochs=3, migrated_words_per_transition=10),
        memory_read_latency_ns=2.0,
        memory_write_latency_ns=3.0,
    )
    old = {"E_dyn_kWh": 1e-6, "E_leak_kWh": 0, "E_scrub_kWh": 0, "latency_ns": 1.0}
    new = {"E_dyn_kWh": 2e-6, "E_leak_kWh": 0, "E_scrub_kWh": 0, "latency_ns": 2.0}
    result = reconfiguration_overhead(
        old_record=old,
        new_record=new,
        scenario=scenario,
        container_bits=128,
        control_energy_j_per_transition=1e-9,
    )
    assert result["migrated_words_total"] == 20
    assert result["temporary_capacity_bits"] == 1280
    assert result["energy_j_total"] == pytest.approx(20 * (3.6 / 1000 + 7.2 / 1000) + 2e-9)
    assert result["amortized_energy_j_per_access"] == pytest.approx(result["energy_j_total"] / 1000)


def test_mux_provider_requires_exact_pvt_and_prefers_stronger_source(tmp_path: Path) -> None:
    common = {
        "area_um2": 1.0,
        "delay_ns": 0.1,
        "switched_capacitance_f": 1e-15,
        "leakage_current_a": 1e-9,
        "switching_activity": 0.2,
        "node_nm": 16,
        "vdd": 0.8,
        "temperature_c": 75,
        "process_corner": "tt",
        "library": "test-only",
        "tool": "test",
        "tool_version": "1",
        "calibration_source": "test fixture",
    }
    provider = MuxCharacterizationProvider(
        [{**common, "source": "analytical"}, {**common, "source": "synthesized", "area_um2": 2.0}]
    )
    exact = provider.resolve(node_nm=16, vdd=0.8, temperature_c=75, process_corner="tt")
    assert exact is not None and exact.source == "synthesized" and exact.area_um2 == 2.0
    assert provider.resolve(node_nm=16, vdd=0.81, temperature_c=75, process_corner="tt") is None
    assert provider.resolve(node_nm=16, vdd=0.8, temperature_c=85, process_corner="tt") is None


def test_plugin_registry_extends_without_central_selector_edits() -> None:
    registry: PluginRegistry[dict] = PluginRegistry()
    registry.register("test-technology", lambda **kwargs: dict(kwargs))
    assert registry.available() == ("test-technology",)
    assert registry.create("test-technology", node_nm=22) == {"node_nm": 22}
    with pytest.raises(ValueError, match="already registered"):
        registry.register("test-technology", dict)
