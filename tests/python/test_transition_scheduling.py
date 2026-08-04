from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture.break_even import break_even_horizon, carbon_break_even, energy_break_even, overhead_ratio
from architecture.granularity import evaluate_granularity
from architecture.hysteresis import hysteresis_schedule
from architecture.scheduling import (
    EpochModeCost,
    brute_force_optimal_path,
    exact_dynamic_programming,
    robust_dynamic_programming,
)
from architecture.traces import generate_synthetic_trace, trace_family_names
from architecture.transitions import ArchitectureDesign, TransitionCost


def _design(modes=("a", "b")) -> ArchitectureDesign:
    return ArchitectureDesign(
        design_id="adaptive", architecture_mode="adaptive", topology="shared_reconfigurable",
        granularity="bank", supported_eccs=tuple(modes), metadata_protection="triplicated",
        total_words=1024, bank_count=4, adaptability_energy_j_per_access=0.0,
        metadata_lookup_energy_j_per_access=0.0, controller_energy_j_per_decision=0.0,
        inactive_engine_leakage_w=0.0, area_mm2=1.0, embodied_carbon_kgco2e=0.0,
        implementation_energy_j=0.0,
    )


def _cost(epoch: int, mode: str, value: float, *, feasible=True, probability=1.0) -> EpochModeCost:
    return EpochModeCost(
        epoch_id=f"e{epoch}", mode_id=f"adaptive:{mode}", ecc_id=mode,
        design_id="adaptive", objective_cost=value, operational_energy_j=value,
        operational_carbon_kgco2e=value / 3.6e6, latency_ns=1.0, fit=1.0,
        area_mm2=1.0, feasible=feasible, feasibility_probability=probability,
        objective_std=value * 0.1, constraint_margins={},
        violations=(() if feasible else ("fit",)), cost_breakdown={"accesses": 1},
    )


def _lookup(matrix):
    def lookup(index: int, old: str, new: str) -> TransitionCost:
        value = 0.0 if old == new else matrix[(old, new)]
        return TransitionCost(old, new, True, value, value / 3.6e6, 0.0, 0, 0, "test_fixture")

    return lookup


def test_dynamic_programming_matches_brute_force() -> None:
    costs = tuple(
        {"a": _cost(index, "a", a), "b": _cost(index, "b", b)}
        for index, (a, b) in enumerate(((1, 3), (4, 1), (4, 1), (1, 3)))
    )
    lookup = _lookup({("a", "b"): 0.7, ("b", "a"): 0.2})
    exact = exact_dynamic_programming(
        epoch_costs=costs, transition_lookup=lookup, design=_design(),
        objective="lifecycle_energy_j",
    )
    brute = brute_force_optimal_path(
        epoch_costs=costs, transition_lookup=lookup, objective="lifecycle_energy_j"
    )
    assert brute is not None
    assert exact.path == brute[0]
    assert exact.total_objective == pytest.approx(brute[1])


def test_zero_transition_cost_reduces_to_independent_selection() -> None:
    costs = (
        {"a": _cost(0, "a", 1), "b": _cost(0, "b", 2)},
        {"a": _cost(1, "a", 3), "b": _cost(1, "b", 1)},
        {"a": _cost(2, "a", 1), "b": _cost(2, "b", 3)},
    )
    result = exact_dynamic_programming(
        epoch_costs=costs,
        transition_lookup=_lookup({("a", "b"): 0, ("b", "a"): 0}),
        design=_design(), objective="lifecycle_energy_j",
    )
    assert result.path == ("a", "b", "a")


def test_prohibitively_large_and_asymmetric_transition_costs() -> None:
    costs = (
        {"a": _cost(0, "a", 1), "b": _cost(0, "b", 4)},
        {"a": _cost(1, "a", 3), "b": _cost(1, "b", 1)},
        {"a": _cost(2, "a", 3), "b": _cost(2, "b", 1)},
    )
    high = exact_dynamic_programming(
        epoch_costs=costs,
        transition_lookup=_lookup({("a", "b"): 100, ("b", "a"): 0}),
        design=_design(), objective="lifecycle_energy_j",
    )
    assert high.path == ("b", "b", "b")
    asymmetric = exact_dynamic_programming(
        epoch_costs=costs,
        transition_lookup=_lookup({("a", "b"): 0.1, ("b", "a"): 100}),
        design=_design(), objective="lifecycle_energy_j",
    )
    assert asymmetric.path == ("a", "b", "b")


def test_infeasible_mode_and_minimum_dwell() -> None:
    costs = (
        {"a": _cost(0, "a", 1), "b": _cost(0, "b", 5)},
        {"a": _cost(1, "a", 5), "b": _cost(1, "b", 1, feasible=False)},
        {"a": _cost(2, "a", 5), "b": _cost(2, "b", 1)},
        {"a": _cost(3, "a", 5), "b": _cost(3, "b", 1)},
    )
    result = exact_dynamic_programming(
        epoch_costs=costs,
        transition_lookup=_lookup({("a", "b"): 0, ("b", "a"): 0}),
        design=_design(), objective="lifecycle_energy_j", min_dwell_epochs=2,
    )
    assert result.path[:2] == ("a", "a")
    assert result.path[2:] == ("b", "b")


def test_robust_chance_constraint_filters_uncertain_nominal_winner() -> None:
    costs = (
        {"a": _cost(0, "a", 1, probability=0.8), "b": _cost(0, "b", 2)},
        {"a": _cost(1, "a", 1, probability=0.8), "b": _cost(1, "b", 2)},
    )
    result = robust_dynamic_programming(
        epoch_costs=costs,
        transition_lookup=_lookup({("a", "b"): 0, ("b", "a"): 0}),
        design=_design(), objective="lifecycle_energy_j",
        chance_constraint_epsilon=0.05, risk_aversion_z=1.645,
        min_dwell_epochs=1, max_transitions=None,
    )
    assert result.path == ("b", "b")


def test_hysteresis_suppresses_low_value_switches() -> None:
    costs = tuple(
        {"a": _cost(index, "a", a), "b": _cost(index, "b", b)}
        for index, (a, b) in enumerate(((1, 1.1), (1.1, 1), (1, 1.1), (1.1, 1)))
    )
    result = hysteresis_schedule(
        epoch_costs=costs,
        transition_lookup=_lookup({("a", "b"): 0.5, ("b", "a"): 0.5}),
        design=_design(), objective="lifecycle_energy_j", prediction_horizon_epochs=2,
        min_dwell_epochs=1, minimum_benefit_margin=0.1, max_transitions=2,
        confidence_threshold=0.8, uncertainty_z=1.0, safe_fallback="a",
    )
    assert result.path == ("a", "a", "a", "a")
    assert result.transitions == 0


def test_break_even_statuses_and_unit_consistency() -> None:
    finite = energy_break_even(
        current_energy_j_per_access=3e-9, new_energy_j_per_access=1e-9,
        adaptive_energy_j_per_access=0.5e-9, migration_energy_j=1e-3,
        control_energy_j=0.0,
    )
    assert finite.status == "finite"
    assert finite.horizon_accesses == 666667
    never = break_even_horizon(
        current_cost_per_access=1, new_cost_per_access=1,
        continuing_adaptive_overhead_per_access=0,
        one_time_transition_cost=1, units="J and J/access",
    )
    assert never.status == "never_beneficial"
    immediate = carbon_break_even(
        current_carbon_kg_per_access=2e-12, new_carbon_kg_per_access=1e-12,
        adaptive_carbon_kg_per_access=0.0, migration_carbon_kg=0.0,
        allocated_embodied_carbon_kg=0.0,
    )
    assert immediate.status == "immediate_benefit"
    missing = energy_break_even(
        current_energy_j_per_access=1e-9, new_energy_j_per_access=0.5e-9,
        adaptive_energy_j_per_access=None, migration_energy_j=1e-3,
        control_energy_j=0,
    )
    assert missing.status == "insufficient_characterization"
    assert overhead_ratio(1.0, 0.0) == {
        "status": "no_gross_benefit", "ratio": None, "beneficial": False
    }


def test_granularity_changes_migration_and_metadata() -> None:
    whole = evaluate_granularity(
        granularity="whole_memory", total_words=4096, active_region_fraction=0.125,
        mode_count=3, metadata_protection="triplicated",
    )
    bank = evaluate_granularity(
        granularity="bank", total_words=4096, active_region_fraction=0.125,
        mode_count=3, metadata_protection="triplicated", bank_count=8,
    )
    page = evaluate_granularity(
        granularity="page", total_words=4096, active_region_fraction=0.125,
        mode_count=3, metadata_protection="triplicated", page_words=256,
    )
    assert whole["migrated_words"] == 4096
    assert bank["migrated_words"] == page["migrated_words"] == 512
    assert whole["stored_metadata_bits"] < bank["stored_metadata_bits"] < page["stored_metadata_bits"]
    word = evaluate_granularity(
        granularity="word", total_words=64, active_region_fraction=0.1,
        mode_count=3, metadata_protection="triplicated",
    )
    assert word["feasible"] is False


def test_all_synthetic_trace_families_are_seeded_and_deterministic() -> None:
    assert len(trace_family_names()) == 10
    spec = {"family": "uncertain_transitions", "seed": 17, "epoch_count": 8}
    first = generate_synthetic_trace(spec)
    second = generate_synthetic_trace(spec)
    assert first.to_dict() == second.to_dict()
    assert first.source == "generated_synthetic"
    assert first.seed == 17


def test_transition_controller_declares_safe_sequence() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "asic" / "rtl" / "common" / "green_ecc_transition_controller.sv").read_text()
    for state in (
        "ST_STABLE", "ST_QUIESCE", "ST_READ_OLD", "ST_DECODE", "ST_RE_ENCODE",
        "ST_WRITE_NEW", "ST_VERIFY", "ST_COMMIT_MODE", "ST_RESUME", "ST_RECOVERY",
    ):
        assert state in text
    assert "metadata_commit_o" in text
    assert "verify_ok_i" in text
