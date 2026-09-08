from __future__ import annotations

import inspect
import math
import random

import pytest

from campaigns.iscas_sustainability_extension.green_matrix_v3_imec_aligned.core import (
    BoundarySignature,
    BoundaryTerm,
    EvidenceRecord,
    EvidenceRequirement,
    EvidenceTier,
    ServiceConstraints,
    Objective,
    OperationalWorkload,
    ProcessGasUse,
    ProcessStep,
    QualificationRule,
    boundary_mismatches,
    convert_unit,
    correct_service_count,
    csci,
    csci_bit,
    exact_pareto_indices,
    evaluate_feasibility,
    good_die_carbon,
    good_dies_per_wafer,
    gross_dies_per_wafer,
    latin_hypercube,
    lifecycle_carbon,
    lifetime_energy_j,
    mrcc,
    murphy_yield,
    negative_binomial_yield,
    operational_carbon,
    physical_outcome_probability,
    poisson_yield,
    qualify,
    scenario_envelope,
    validate_coefficient_transfer,
    wafer_carbon,
    yield_fraction,
)


BOUNDARY = "SB_TEST_DECLARED"


def test_canonical_unit_conversions_are_explicit_and_dimension_safe() -> None:
    assert convert_unit(1.0, "kWh", "J") == 3_600_000.0
    assert convert_unit(1.0, "kgCO2e", "gCO2e") == 1_000.0
    assert convert_unit(1.0, "cm2", "mm2") == 100.0
    assert convert_unit(1.0, "mm2", "um2") == 1_000_000.0
    assert convert_unit(1.0, "ppm", "probability") == pytest.approx(1e-6)
    assert convert_unit(1.0, "FIT", "failures_per_hour") == pytest.approx(1e-9)
    with pytest.raises(ValueError, match="cannot convert"):
        convert_unit(1.0, "J", "kgCO2e")
    with pytest.raises(ValueError, match="unknown unit"):
        convert_unit(1.0, "mystery", "J")


def test_correct_service_count_domain_and_dimensions() -> None:
    assert correct_service_count(1_000.0, 0.99) == pytest.approx(990.0)
    with pytest.raises(ValueError):
        correct_service_count(-1.0, 0.5)
    with pytest.raises(ValueError):
        correct_service_count(1.0, 1.01)


def test_csci_zero_service_is_undefined_without_epsilon() -> None:
    result = csci(2.0, 100.0, 0.0, boundary_id=BOUNDARY)
    assert result.value is None
    assert result.status == "UNDEFINED_ZERO_CORRECT_SERVICE"
    assert "epsilon" in (result.reason or "")
    assert "epsilon" not in inspect.signature(csci).parameters


def test_csci_missing_inputs_remain_missing_not_zero() -> None:
    carbon = csci(None, 100.0, 0.9, boundary_id=BOUNDARY)
    reliability = csci(1.0, 100.0, None, boundary_id=BOUNDARY)
    assert carbon.value is None
    assert carbon.status == "BLOCKED_MISSING_LIFECYCLE_CARBON"
    assert reliability.value is None
    assert reliability.status == "BLOCKED_MISSING_CORRECT_SERVICE_PROBABILITY"


def test_csci_zero_carbon_and_monotonicity() -> None:
    assert csci(0.0, 100.0, 0.9, boundary_id=BOUNDARY).value == 0.0
    base = csci(2.0, 100.0, 0.9, boundary_id=BOUNDARY).value
    more_carbon = csci(4.0, 100.0, 0.9, boundary_id=BOUNDARY).value
    more_reliable = csci(2.0, 100.0, 0.99, boundary_id=BOUNDARY).value
    assert base is not None and more_carbon is not None and more_reliable is not None
    assert more_carbon > base
    assert more_reliable < base


def test_csci_is_candidate_set_independent() -> None:
    candidates = [(1.0, 100.0, 0.8), (2.0, 100.0, 0.99)]
    before = [csci(*row, boundary_id=BOUNDARY).value for row in candidates]
    candidates.append((1e9, 1e-9, 0.01))
    after = [csci(*row, boundary_id=BOUNDARY).value for row in candidates[:2]]
    assert before == after
    assert "candidates" not in inspect.signature(csci).parameters


def test_payload_normalization_can_reverse_access_ranking() -> None:
    a_access = csci(100.0, 100.0, 1.0, boundary_id=BOUNDARY).value
    b_access = csci(80.0, 100.0, 1.0, boundary_id=BOUNDARY).value
    a_bit = csci_bit(100.0, 64, 100.0, 1.0, boundary_id=BOUNDARY).value
    b_bit = csci_bit(80.0, 32, 100.0, 1.0, boundary_id=BOUNDARY).value
    assert b_access < a_access  # type: ignore[operator]
    assert a_bit < b_bit  # type: ignore[operator]


def test_csci_embodied_amortization_and_operational_asymptote() -> None:
    embodied = 10.0
    energy_carbon_per_request = 0.01
    low_n = 100.0
    high_n = 1_000_000.0
    low = csci(embodied + low_n * energy_carbon_per_request, low_n, 1.0, boundary_id=BOUNDARY).value
    high = csci(embodied + high_n * energy_carbon_per_request, high_n, 1.0, boundary_id=BOUNDARY).value
    assert low is not None and high is not None
    assert high < low
    assert high == pytest.approx(energy_carbon_per_request + embodied / high_n)


def test_randomized_csci_properties() -> None:
    rng = random.Random(20260908)
    for _ in range(300):
        carbon = 10 ** rng.uniform(-12, 12)
        requests = 10 ** rng.uniform(-3, 20)
        q = 10 ** rng.uniform(-9, 0)
        value = csci(carbon, requests, q, boundary_id=BOUNDARY).value
        assert value is not None and math.isfinite(value) and value >= 0.0
        assert csci(carbon * 2, requests, q, boundary_id=BOUNDARY).value == pytest.approx(value * 2)


def test_mrcc_domain_and_no_epsilon() -> None:
    defined = mrcc(12.0, 10.0, 110.0, 100.0, boundary_id=BOUNDARY)
    zero = mrcc(12.0, 10.0, 100.0, 100.0, boundary_id=BOUNDARY)
    negative = mrcc(12.0, 10.0, 90.0, 100.0, boundary_id=BOUNDARY)
    assert defined.value == pytest.approx(0.2)
    assert zero.value is None and zero.status == "UNDEFINED_ZERO_SERVICE_IMPROVEMENT"
    assert negative.value is None and negative.status == "NOT_AN_INCREMENTAL_RELIABILITY_GAIN"
    assert "epsilon" not in inspect.signature(mrcc).parameters


def test_mrcc_carbon_saving_service_gain_is_valid_negative() -> None:
    result = mrcc(9.0, 10.0, 110.0, 100.0, boundary_id=BOUNDARY)
    assert result.value == pytest.approx(-0.1)
    assert result.status == "DEFINED_CARBON_SAVING_AND_SERVICE_GAIN"


def test_mrcc_missing_matched_inputs_blocks() -> None:
    result = mrcc(None, 1.0, 2.0, 1.0, boundary_id=BOUNDARY)
    assert result.value is None
    assert result.status == "BLOCKED_MISSING_MATCHED_BASELINE_INPUT"


def test_boundary_terms_distinguish_excluded_zero_missing_and_parametric() -> None:
    defined = lifecycle_carbon(
        BOUNDARY,
        [
            BoundaryTerm("process", 2.0, "kgCO2e", "INCLUDED_VALUE"),
            BoundaryTerm("package", None, "kgCO2e", "EXCLUDED_BY_BOUNDARY"),
            BoundaryTerm("other", 0.0, "kgCO2e", "INCLUDED_ZERO"),
        ],
    )
    missing = lifecycle_carbon(
        BOUNDARY, [BoundaryTerm("upstream", None, "kgCO2e", "UNAVAILABLE")]
    )
    parametric = lifecycle_carbon(
        BOUNDARY, [BoundaryTerm("fab", 2.0, "kgCO2e", "PARAMETRIC")]
    )
    assert defined.value == 2.0 and defined.status == "DEFINED"
    assert missing.value is None and missing.status == "BLOCKED_INCLUDED_TERM_UNAVAILABLE"
    assert parametric.value == 2.0 and parametric.status == "PARAMETRIC"


def test_process_gas_abatement_and_scope_accounting() -> None:
    gas = ProcessGasUse("CF4", 1.0, 0.5, 0.8, 100.0, "TEST_GWP100")
    steps = (
        ProcessStep("L1", "LITHOGRAPHY", 10.0, (), True),
        ProcessStep("E1", "DRY_ETCH", 5.0, (gas,), True),
        ProcessStep("C1", "WET_CLEAN", 5.0),
    )
    result = wafer_carbon(
        steps,
        0.5,
        [BoundaryTerm("materials", 3.0, "kgCO2e", "INCLUDED_VALUE")],
        boundary_id=BOUNDARY,
    )
    assert gas.scope1_kgco2e == pytest.approx(10.0)
    assert result.scope1_kgco2e == pytest.approx(10.0)
    assert result.scope2_kgco2e == pytest.approx(10.0)
    assert result.patterning_scope2_diagnostic_kgco2e == pytest.approx(7.5)
    assert result.total_kgco2e == pytest.approx(23.0)


def test_process_route_and_scope_double_counting_are_rejected_or_avoided() -> None:
    duplicate = (ProcessStep("X", "ETCH", 1.0), ProcessStep("X", "CLEAN", 2.0))
    with pytest.raises(ValueError, match="double count"):
        wafer_carbon(duplicate, 0.5, [], boundary_id=BOUNDARY)
    result = wafer_carbon(
        (ProcessStep("X", "LITHOGRAPHY", 10.0, (), True),),
        0.5,
        [],
        boundary_id=BOUNDARY,
    )
    assert result.scope2_kgco2e == 5.0
    assert result.patterning_scope2_diagnostic_kgco2e == 5.0
    assert result.total_kgco2e == 5.0


def test_missing_upstream_blocks_total_but_preserves_scope_subtotals() -> None:
    result = wafer_carbon(
        (ProcessStep("X", "ETCH", 10.0),),
        0.5,
        [BoundaryTerm("upstream", None, "kgCO2e", "UNAVAILABLE")],
        boundary_id=BOUNDARY,
    )
    assert result.scope2_kgco2e == 5.0
    assert result.upstream_kgco2e is None
    assert result.total_kgco2e is None


def test_yield_models_and_explicit_parameters() -> None:
    p = poisson_yield(0.2, 100.0)
    n = negative_binomial_yield(0.2, 100.0, 2.0)
    m = murphy_yield(0.2, 100.0)
    assert 0.0 < p <= 1.0
    assert 0.0 < n <= 1.0
    assert 0.0 < m <= 1.0
    assert yield_fraction("MEASURED", None, 100.0, measured_yield=0.8) == 0.8
    with pytest.raises(ValueError, match="defect density"):
        yield_fraction("POISSON", None, 100.0)
    with pytest.raises(ValueError, match="alpha"):
        yield_fraction("NEGATIVE_BINOMIAL", 0.2, 100.0)


def test_good_die_and_mask_nre_asymptotic_volume_behavior() -> None:
    gross = gross_dies_per_wafer(300.0, 100.0)
    good = good_dies_per_wafer(gross, 0.8, 0.9)
    package = BoundaryTerm("package", None, "kgCO2e", "EXCLUDED_BY_BOUNDARY")
    other = BoundaryTerm("other", None, "kgCO2e", "EXCLUDED_BY_BOUNDARY")
    low_volume = good_die_carbon(
        100.0,
        good,
        maskset_kgco2e=1_000.0,
        production_wafers=10.0,
        package_term=package,
        other_term=other,
        boundary_id=BOUNDARY,
    ).value
    high_volume = good_die_carbon(
        100.0,
        good,
        maskset_kgco2e=1_000.0,
        production_wafers=1_000_000.0,
        package_term=package,
        other_term=other,
        boundary_id=BOUNDARY,
    ).value
    process_only = 100.0 / good
    assert low_volume is not None and high_volume is not None
    assert high_volume < low_volume
    assert high_volume == pytest.approx(process_only, rel=1e-4)


def _workload(**changes: object) -> OperationalWorkload:
    values: dict[str, object] = {
        "read_count": 10.0,
        "write_count": 2.0,
        "correction_count": 1.0,
        "retry_count": 1.0,
        "scrub_count": 1.0,
        "read_energy_j": 2.0,
        "write_energy_j": 3.0,
        "correction_incremental_energy_j": 1.0,
        "retry_incremental_energy_j": 2.0,
        "scrub_energy_j": 4.0,
        "idle_power_w": 0.5,
        "idle_time_s": 2.0,
        "read_energy_includes_correction": False,
    }
    values.update(changes)
    return OperationalWorkload(**values)  # type: ignore[arg-type]


def test_operational_energy_components_and_grid_scaling() -> None:
    energy = lifetime_energy_j(_workload())
    assert energy == pytest.approx(34.0)
    low = operational_carbon(energy, 0.1)
    high = operational_carbon(energy, 0.8)
    assert high == pytest.approx(8.0 * low)
    assert operational_carbon(0.0, 0.8) == 0.0


def test_correction_energy_double_counting_rejected() -> None:
    with pytest.raises(ValueError, match="counted twice"):
        lifetime_energy_j(_workload(read_energy_includes_correction=True))
    no_increment = lifetime_energy_j(
        _workload(
            read_energy_includes_correction=True,
            correction_incremental_energy_j=0.0,
        )
    )
    assert no_increment == pytest.approx(33.0)


def test_physical_outcome_requires_external_probability_distribution() -> None:
    conditional = {"SBU": 0.0, "DBU": 0.5, "MBU": 1.0}
    physical = {"SBU": 0.8, "DBU": 0.15, "MBU": 0.05}
    assert physical_outcome_probability(conditional, physical) == pytest.approx(0.125)
    with pytest.raises(ValueError, match="sum to one"):
        physical_outcome_probability(conditional, {"SBU": 1.0, "DBU": 1.0, "MBU": 1.0})
    with pytest.raises(ValueError, match="domains"):
        physical_outcome_probability(conditional, {"SBU": 1.0})


def test_metric_specific_qualification_preserves_partial_results() -> None:
    records = {
        "area": EvidenceRecord("area", EvidenceTier.E4, "DIAGNOSTIC", BOUNDARY),
        "logical": EvidenceRecord("logical", EvidenceTier.E3, "LOGICAL_CONTROL", BOUNDARY),
        "energy": EvidenceRecord("energy", EvidenceTier.E0, "UNQUALIFIED", BOUNDARY, blocking_reason="missing"),
    }
    logical_rule = QualificationRule(
        "LOGICAL_DIAGNOSTIC",
        (
            EvidenceRequirement("area", EvidenceTier.E4, ("DIAGNOSTIC",)),
            EvidenceRequirement("logical", EvidenceTier.E3, ("LOGICAL_CONTROL",)),
        ),
    )
    energy_rule = QualificationRule(
        "ENERGY_FRONT",
        (EvidenceRequirement("energy", EvidenceTier.E5, ("ABSOLUTE_QUALIFIED",)),),
    )
    assert qualify(logical_rule, records).status == "QUALIFIED"
    blocked = qualify(energy_rule, records)
    assert blocked.status == "BLOCKED"
    assert any("BELOW_E5" in reason for reason in blocked.reasons)


def test_reliability_latency_and_throughput_are_hard_external_constraints() -> None:
    absent = evaluate_feasibility(
        constraints=None,
        sdc_probability=0.0,
        due_probability=0.0,
        latency_s=1e-9,
        throughput_services_per_s=1e9,
    )
    assert absent.feasible is None
    assert absent.status == "NO_DECLARED_CONSTRAINTS"
    constraints = ServiceConstraints(
        max_sdc_probability=1e-9,
        max_due_probability=1e-6,
        max_latency_s=2e-9,
        min_throughput_services_per_s=1e8,
    )
    failed = evaluate_feasibility(
        constraints=constraints,
        sdc_probability=1e-8,
        due_probability=1e-7,
        latency_s=None,
        throughput_services_per_s=1e7,
    )
    assert failed.feasible is False
    assert failed.violations == (
        "SDC_CONSTRAINT",
        "LATENCY_MISSING",
        "THROUGHPUT_CONSTRAINT",
    )


def test_exact_pareto_is_deterministic_and_candidate_values_do_not_change() -> None:
    rows = [
        {"carbon": 1.0, "sdc": 0.2},
        {"carbon": 2.0, "sdc": 0.1},
        {"carbon": 3.0, "sdc": 0.3},
    ]
    objectives = [Objective("carbon", "min"), Objective("sdc", "min")]
    assert exact_pareto_indices(rows, objectives) == [0, 1]
    before = [dict(row) for row in rows]
    rows.append({"carbon": 100.0, "sdc": 1.0})
    assert rows[:3] == before
    assert exact_pareto_indices(rows, objectives) == [0, 1]


def test_uncertainty_scenarios_are_reproducible_and_not_confidence_intervals() -> None:
    first = latin_hypercube({"ci": (0.1, 0.9), "yield": (0.7, 0.99)}, 32, 42)
    second = latin_hypercube({"yield": (0.7, 0.99), "ci": (0.1, 0.9)}, 32, 42)
    assert first == second
    assert first != latin_hypercube({"ci": (0.1, 0.9), "yield": (0.7, 0.99)}, 32, 43)
    interval = scenario_envelope(row["ci"] for row in first)
    assert interval.uncertainty_kind == "EPISTEMIC"
    assert 0.1 <= interval.lower <= interval.upper <= 0.9


def test_boundary_mismatch_and_sky130_translation_rejection() -> None:
    imec = BoundarySignature("IMEC", "A14", 300.0, "cradle-to-gate", False, False, "PARTIAL")
    sky = BoundarySignature("SKY", "SKY130", None, "cradle-to-gate", False, False, "UNAVAILABLE")
    mismatches = boundary_mismatches(imec, sky)
    assert "technology" in mismatches
    assert "wafer_diameter_mm" in mismatches
    assert "upstream_scope3" in mismatches
    with pytest.raises(ValueError, match="NOT_TRANSFERABLE_TO_SKY130"):
        validate_coefficient_transfer("A14", "SKY130", "ABSOLUTE_CALIBRATION")
    validate_coefficient_transfer("A14", "SKY130", "TREND_ONLY")
