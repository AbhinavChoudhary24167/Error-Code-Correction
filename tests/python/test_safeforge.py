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
from codeforge.experiments import (
    attach_experiment_identity,
    assert_comparable,
    make_experiment_identity,
    validate_metric_rows,
)
from codeforge.faults import load_fault_distribution
from codeforge.robust import compile_safe_decoder, decoder_actions, execute_policy_losses
from codeforge.robust_synthesis import cosynthesize_exact_small
from codeforge.support_audit import (
    audit_finite_universe,
    complete_tail_bound,
    error_masks,
    support_from_masks,
)


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


def _epoch(radius: float, out_of_support: float | None = None) -> TraceEpoch:
    uncertainty = {"ambiguity_radius": radius}
    if out_of_support is not None:
        uncertainty["out_of_support_probability_upper"] = out_of_support
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
        uncertainty=uncertainty,
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


def _strict_envelope(mode: str, *, fallback: bool = False) -> dict:
    digest = "a" * 64 if mode == "specialized" else "b" * 64
    return {
        "mode_id": mode,
        "ambiguity_type": "total_variation",
        "support_identifier": "support-a",
        "certified_radius": 0.1 if mode == "specialized" else 1.0,
        "maximum_certified_sdc": 0.01,
        "maximum_certified_due": 1.0,
        "maximum_out_of_support_probability": 0.02,
        "fallback_mode": "fallback",
        "certificate_identifier": digest,
        "certificate_sha256": digest,
        "certificate_verification_status": "passed",
        "certificate_integrity_valid": True,
        "certificate_version": 3,
        "is_certified_fallback": fallback,
        "supported_fault_regimes": ["sbu"],
    }


def _strict_gate() -> dict:
    return {
        "enabled": True,
        "ambiguity_type": "total_variation",
        "maximum_sdc": 0.01,
        "strict_deployment_validation": True,
        "minimum_certificate_version": 3,
        "support_id_by_fault_regime": {"sbu": "support-a"},
    }


def test_strict_scheduler_gate_accepts_in_envelope_and_boundary() -> None:
    envelopes = [_strict_envelope("specialized"), _strict_envelope("fallback", fallback=True)]
    for radius, outside in ((0.09, 0.01), (0.1, 0.02)):
        gated = _apply_certificate_gate(
            trace=ScenarioTrace(
                trace_id="t", epochs=(_epoch(radius, outside),), source="user_supplied"
            ),
            costs=({"specialized": _cost("specialized"), "fallback": _cost("fallback")},),
            gate=_strict_gate(),
            envelopes=envelopes,
        )
        assert gated[0]["specialized"].feasible
        assert gated[0]["fallback"].feasible


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ({"certificate_version": 2}, "certificate_gate:stale_certificate"),
        ({"certificate_integrity_valid": False}, "certificate_gate:certificate_integrity_failure"),
        ({"certificate_sha256": "corrupted"}, "certificate_gate:certificate_identifier_hash_mismatch"),
    ],
)
def test_strict_scheduler_gate_rejects_stale_or_corrupt_certificate(mutation, expected) -> None:
    specialized = {**_strict_envelope("specialized"), **mutation}
    gated = _apply_certificate_gate(
        trace=ScenarioTrace(
            trace_id="t", epochs=(_epoch(0.05, 0.01),), source="user_supplied"
        ),
        costs=({"specialized": _cost("specialized")},),
        gate=_strict_gate(),
        envelopes=[specialized],
    )
    assert not gated[0]["specialized"].feasible
    assert expected in gated[0]["specialized"].violations


def test_strict_scheduler_gate_rejects_tail_unknown_support_and_no_fallback() -> None:
    specialized = _strict_envelope("specialized")
    fallback = {**_strict_envelope("fallback", fallback=True), "certificate_verification_status": "failed"}
    unknown_tail = _apply_certificate_gate(
        trace=ScenarioTrace(
            trace_id="t", epochs=(_epoch(0.05),), source="user_supplied"
        ),
        costs=({"specialized": _cost("specialized")},),
        gate=_strict_gate(),
        envelopes=[specialized],
    )
    assert "certificate_gate:out_of_support_probability_missing" in unknown_tail[0]["specialized"].violations
    unknown_support_gate = {**_strict_gate(), "support_id_by_fault_regime": {}}
    no_mode = _apply_certificate_gate(
        trace=ScenarioTrace(
            trace_id="t", epochs=(_epoch(0.05, 0.03),), source="user_supplied"
        ),
        costs=({"specialized": _cost("specialized"), "fallback": _cost("fallback")},),
        gate=unknown_support_gate,
        envelopes=[specialized, fallback],
    )
    assert not any(item.feasible for item in no_mode[0].values())
    assert "certificate_gate:current_support_identifier_missing" in no_mode[0]["specialized"].violations


def test_support_audit_expands_to_complete_8bit_universe_and_bounds_tail(safe_inputs) -> None:
    nominal, _, support, code = safe_inputs
    full = support_from_masks(
        range(1, 256), bit_width=8, nominal_support=support, universe_id="full-8bit"
    )
    report = audit_finite_universe(
        code,
        decoder_actions(code),
        full,
        universe_id="full-8bit",
        ambiguity={"type": "total_variation", "radius": 0.1},
    )
    assert report["pattern_count"] == 255
    assert sum(report["outcome_counts"][key] for key in ("correct", "due", "sdc_miscorrection", "undetected")) == 255
    assert len(tuple(error_masks(8, maximum_weight=3))) == 92
    bound = complete_tail_bound(0.02, outside_probability_upper=0.01)
    assert bound["total_sdc_upper"] == pytest.approx(0.0298)
    tighter = complete_tail_bound(
        0.4, outside_probability_upper=0.5, outside_sdc_upper=0.0
    )
    assert tighter["total_sdc_upper"] == pytest.approx(0.4)


def test_aggregate_literature_constraint_certificate_is_solver_independently_verified(
    safe_inputs,
) -> None:
    _, _, support, code = safe_inputs
    losses = execute_policy_losses(code, support, decoder_actions(code))["sdc"]
    ambiguity = {
        "type": "structured_interval",
        "radius": 1.0,
        "aggregate_intervals": [
            {
                "name": "multiplicity_ge_2",
                "members": [
                    {"dimension": "multiplicity", "category": "2"},
                    {"dimension": "multiplicity", "category": "3"},
                ],
                "lower": 0.1,
                "upper": 0.9,
            }
        ],
    }
    certificate = solve_worst_case(support, losses, ambiguity, bit_width=8)
    aggregate = certificate["category_constraints"][0]
    assert aggregate["name"] == "aggregate:multiplicity_ge_2"
    verified = verify_risk_certificate(certificate, support, bit_width=8)
    assert verified["verification_status"] == "passed"


def test_metric_context_validation_rejects_scope_and_identity_mixing() -> None:
    row = {
        "experiment_id": "a",
        "matrix_id": "m",
        "decoder_policy_id": "p",
        "pmf_id": "q",
        "ambiguity_set_type": "total_variation",
        "ambiguity_radius": 0.1,
        "error_pattern_universe": "u",
        "parity_budget": 4,
        "physical_mapping": list(range(8)),
        "metric_scope": "nominal",
        "metrics": {"corrected": 0.8, "due": 0.1, "sdc": 0.1},
    }
    assert validate_metric_rows([row]) == "a"
    worst = {
        **row,
        "pmf_id": "separate-adversarial-pmfs-by-risk",
        "metric_scope": "worst_case",
        "metrics": {"due": 0.3, "sdc": 0.2},
        "adversarial_pmf_ids": {"due": "adv-due", "sdc": "adv-sdc"},
    }
    assert validate_metric_rows([worst]) == "a"
    with pytest.raises(ValueError, match="mismatched experiment identities"):
        validate_metric_rows([row, {**row, "experiment_id": "b"}])
    with pytest.raises(ValueError, match="must not mix"):
        validate_metric_rows(
            [{**row, "metric_scope": "worst_case", "metrics": {"corrected": 0.8, "due": 0.2, "sdc": 0.1}}]
        )
