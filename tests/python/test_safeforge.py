from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture.schedule_pipeline import _apply_certificate_gate
from architecture.scheduling import EpochModeCost
from architecture.traces import ScenarioTrace, TraceEpoch
from codeforge.ambiguity import build_support, solve_worst_case
from codeforge.certificates import verify_risk_certificate, verify_safety_certificate
from codeforge.confidence import simultaneous_category_intervals
from codeforge.equivalence import classify_code
from codeforge.experiments import attach_experiment_identity, assert_comparable, make_experiment_identity
from codeforge.faults import load_fault_distribution
from codeforge.robust import compile_safe_decoder, decoder_actions, execute_policy_losses
from codeforge.robust_synthesis import cosynthesize_exact_small


REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def safe_inputs():
    nominal = load_fault_distribution(
        "configs/fault_distributions/small_hotspot_8bit.json", repo_root=REPO
    )
    shifted = load_fault_distribution(
        "configs/fault_distributions/small_shifted_8bit.json", repo_root=REPO
    )
    support = build_support(nominal, [shifted])
    code = json.loads((REPO / "reports/code_synthesis/code.json").read_text(encoding="utf-8"))
    return nominal, shifted, support, code


def test_equivalence_audit_proves_existing_small_code_is_known(safe_inputs) -> None:
    _, _, _, code = safe_inputs
    reference = json.loads(
        (REPO / "reports/code_synthesis/baselines/odd_column_secded_code.json").read_text(
            encoding="utf-8"
        )
    )
    audit = classify_code(code, reference_code=reference, geometry={"rows": 2, "columns": 4})
    assert audit["minimum_distance"] == 4
    assert audit["weight_enumerators"]["primal"] == [1, 0, 0, 0, 14, 0, 0, 0, 1]
    assert audit["reference_equivalence"]["row_operations_plus_arbitrary_columns"]["equivalent"]
    assert not audit["reference_equivalence"]["geometry_preserving_automorphisms"]["equivalent"]
    assert audit["novel_code_status"] == "not_a_new_linear_code_family"


@pytest.mark.parametrize(
    "ambiguity",
    [
        {"type": "total_variation", "radius": 0.1},
        {
            "type": "geometry_wasserstein",
            "radius": 0.05,
            "geometry": {"sram_columns": 4},
        },
        {
            "type": "structured_interval",
            "radius": 1.0,
            "category_intervals": {
                "family": {
                    "sbu": {"lower": 0.35, "upper": 0.60},
                    "adjacent_dbu": {"lower": 0.25, "upper": 0.55},
                    "non_adjacent_dbu": {"lower": 0.01, "upper": 0.12},
                    "triple_adjacent": {"lower": 0.0, "upper": 0.15},
                    "general_mbu": {"lower": 0.0, "upper": 0.08},
                }
            },
        },
    ],
)
def test_all_ambiguity_certificates_are_tight_and_solver_free_verifiable(
    safe_inputs, ambiguity
) -> None:
    _, _, support, _ = safe_inputs
    losses = [int(index % 3 == 0) for index in range(len(support))]
    certificate = solve_worst_case(support, losses, ambiguity, bit_width=8)
    verification = verify_risk_certificate(certificate, support, bit_width=8)
    assert certificate["solver_status"] == "optimal"
    assert certificate["optimality_gap"] <= 1e-8
    assert verification["verification_status"] == "passed", verification["failures"]


def test_abstaining_policy_executes_every_error_and_stays_zero_sdc(safe_inputs) -> None:
    nominal, _, support, code = safe_inputs
    policy = compile_safe_decoder(
        code,
        support,
        {"type": "total_variation", "radius": 0.1, "maximum_radius": 0.5},
        sdc_limit=0.0,
        raw_fit=nominal.raw_fit,
    )
    actions = decoder_actions(policy["compiled_code"])
    executed = execute_policy_losses(code, support, actions)
    assert len(executed["outcomes"]) == len(support)
    assert not any(executed["sdc"])
    assert policy["metrics"]["worst_case"]["sdc"] == 0.0
    assert all(entry["correct"] != entry["abstain"] for entry in policy["entries"])


def test_checked_in_safety_certificate_reexecutes_and_verifies() -> None:
    document = json.loads(
        (REPO / "reports/safe_decoder/certificate.json").read_text(encoding="utf-8")
    )
    report = verify_safety_certificate(document)
    assert report["verification_status"] == "passed", report["failures"]


def test_comparison_identity_rejects_different_fault_pmfs(safe_inputs) -> None:
    nominal, shifted, _, _ = safe_inputs
    first = make_experiment_identity(k=4, r=4, distribution=nominal)
    second = make_experiment_identity(k=4, r=4, distribution=shifted)
    with pytest.raises(ValueError, match="mismatched experiment identities"):
        assert_comparable(
            [
                attach_experiment_identity({"strategy_id": "a"}, first),
                attach_experiment_identity({"strategy_id": "b"}, second),
            ]
        )


def test_exact_small_cosynthesis_reports_complete_search(safe_inputs) -> None:
    nominal, shifted, _, _ = safe_inputs
    # A compact (5,2) instance exercises the same exhaustive ordered-column method.
    compact_nominal = type(nominal)(
        distribution_id="compact",
        bit_width=5,
        patterns=tuple(
            type(nominal.patterns[0])(
                pattern_id=f"sbu-{index}",
                positions=(index,),
                probability=0.2,
                family="sbu",
                metadata={},
            )
            for index in range(5)
        ),
        provenance={"kind": "synthetic"},
        raw_fit=100.0,
    )
    support = build_support(compact_nominal)
    result = cosynthesize_exact_small(
        k=2,
        r=3,
        support=support,
        ambiguity={"type": "total_variation", "radius": 0.1},
        code_id="compact-safe",
    )
    assert result["status"] == "optimal"
    assert result["optimality_proven"] is True
    assert result["candidate_matrices_evaluated"] == result["theoretical_candidate_matrices"] == 12
    assert result["verification"]["worst_case"]["sdc"] == 0.0


def test_sample_bounds_are_declared_statistical_and_simultaneous() -> None:
    report = simultaneous_category_intervals(
        {"family": {"sbu": 80, "mbu": 20}, "adjacency_class": {"adjacent": 15}},
        sample_count=100,
        confidence=0.95,
    )
    assert report["calibration_kind"] == "statistically_calibrated"
    assert report["declared_simultaneous_coverage"] == 0.95
    assert report["per_interval_alpha"] == pytest.approx(0.05 / 3)


def _epoch(radius: float) -> TraceEpoch:
    return TraceEpoch(
        epoch_id="e0",
        duration_s=1,
        accesses=1,
        active_words=1,
        fault_regime="sbu",
        fit_multiplier=1,
        vdd_volts=.8,
        temperature_c=75,
        read_fraction=.5,
        write_fraction=.5,
        latency_limit_ns=2,
        fit_limit=100,
        grid_carbon_intensity_kgco2e_per_kwh=.5,
        uncertainty={"ambiguity_radius": radius},
    )


def _cost(mode: str) -> EpochModeCost:
    return EpochModeCost(
        epoch_id="e0",
        mode_id=mode,
        ecc_id=mode,
        design_id="d",
        objective_cost=1,
        operational_energy_j=1,
        operational_carbon_kgco2e=1,
        latency_ns=1,
        fit=1,
        area_mm2=1,
        feasible=True,
        feasibility_probability=1,
        objective_std=0,
        constraint_margins={},
        violations=(),
        cost_breakdown={},
    )


def test_scheduler_certificate_gate_rejects_out_of_envelope_specialization() -> None:
    envelopes = [
        {
            "mode_id": "specialized",
            "ambiguity_type": "total_variation",
            "support_identifier": "support-a",
            "certified_radius": 0.1,
            "maximum_certified_sdc": 0.0,
            "maximum_certified_due": 0.5,
            "fallback_mode": "fallback",
            "certificate_identifier": "abc",
            "supported_fault_regimes": ["sbu"],
        },
        {
            "mode_id": "fallback",
            "ambiguity_type": "total_variation",
            "support_identifier": "support-a",
            "certified_radius": 1.0,
            "maximum_certified_sdc": 0.0,
            "maximum_certified_due": 1.0,
            "fallback_mode": "fallback",
            "certificate_identifier": "def",
            "supported_fault_regimes": ["sbu"],
        },
    ]
    trace = ScenarioTrace(trace_id="t", epochs=(_epoch(0.2),), source="user_supplied")
    gated = _apply_certificate_gate(
        trace=trace,
        costs=({"specialized": _cost("specialized"), "fallback": _cost("fallback")},),
        gate={
            "enabled": True,
            "ambiguity_type": "total_variation",
            "maximum_sdc": 0.0,
            "support_id_by_fault_regime": {"sbu": "support-a"},
        },
        envelopes=envelopes,
    )
    assert not gated[0]["specialized"].feasible
    assert "certificate_gate:confidence_region_outside_envelope" in gated[0]["specialized"].violations
    assert gated[0]["fallback"].feasible
