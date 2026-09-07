from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
    / "carbon"
    / "model"
)
sys.path.insert(0, str(MODEL))

from semiconductor_carbon import (  # noqa: E402
    Evidence,
    EvidenceLabel,
    FabEnergyBoundary,
    PatterningRoute,
    PatterningStep,
    ProcessGasUse,
    WaferProcessInventory,
    act_compatible_logic_carbon_kgco2e,
    die_embodied_carbon,
    gross_dies_per_wafer,
    incremental_ecc_embodied_carbon,
    mask_nre_per_die_kgco2e,
    negative_binomial_yield,
    poisson_yield,
    wafer_carbon,
)


def _evidence() -> Evidence:
    return Evidence(
        EvidenceLabel.PARAMETRIC_EXTRAPOLATION,
        ("SRC_IMEC_IEDM_2023",),
        "Synthetic property-test point; not a node calibration.",
    )


def _inventory(**changes: object) -> WaferProcessInventory:
    values: dict[str, object] = {
        "node_name": "TEST_NODE",
        "process_route": "TEST_ROUTE",
        "maturity": "MATURE_NODE",
        "wafer_diameter_mm": 300.0,
        "fab_electricity_kwh": 500.0,
        "fab_ci_kgco2e_per_kwh": 0.4,
        "process_gases": (
            ProcessGasUse("CF4", 1e-3, 7_380.0, 0.5, 0.8),
        ),
        "upstream_kgco2e_per_wafer": 25.0,
        "evidence": _evidence(),
    }
    values.update(changes)
    return WaferProcessInventory(**values)  # type: ignore[arg-type]


def test_carbon_cannot_decrease_when_fab_ci_increases() -> None:
    low = wafer_carbon(_inventory(fab_ci_kgco2e_per_kwh=0.1))
    high = wafer_carbon(_inventory(fab_ci_kgco2e_per_kwh=0.8))
    assert high.scope2_kgco2e > low.scope2_kgco2e
    assert high.total_kgco2e > low.total_kgco2e


def test_carbon_cannot_increase_when_abatement_improves() -> None:
    base_gas = _inventory().process_gases[0]
    weak = wafer_carbon(
        _inventory(process_gases=(replace(base_gas, abatement_efficiency=0.1),))
    )
    strong = wafer_carbon(
        _inventory(process_gases=(replace(base_gas, abatement_efficiency=0.9),))
    )
    assert strong.scope1_kgco2e < weak.scope1_kgco2e
    assert strong.total_kgco2e < weak.total_kgco2e


@pytest.mark.parametrize("yield_model", ["poisson", "negative_binomial", "murphy"])
def test_good_die_carbon_increases_when_defect_density_increases(
    yield_model: str,
) -> None:
    kwargs = {"yield_alpha": 2.0} if yield_model == "negative_binomial" else {}
    high_yield = die_embodied_carbon(
        _inventory(), 100.0, 0.05, yield_model=yield_model, **kwargs
    )
    low_yield = die_embodied_carbon(
        _inventory(), 100.0, 0.5, yield_model=yield_model, **kwargs
    )
    assert low_yield.die_yield_fraction < high_yield.die_yield_fraction
    assert low_yield.process_kgco2e > high_yield.process_kgco2e


def test_incremental_ecc_embodied_carbon_is_nonnegative() -> None:
    result = incremental_ecc_embodied_carbon(
        _inventory(),
        host_area_mm2=50.0,
        baseline_ecc_area_mm2=0.1,
        candidate_ecc_area_mm2=0.2,
        defect_density_per_cm2=0.15,
        yield_model="murphy",
        line_yield_fraction=0.9,
    )
    assert result.incremental_kgco2e > 0.0
    assert result.candidate_kgco2e > result.baseline_kgco2e


def test_host_die_context_changes_same_ecc_area_consequence() -> None:
    small = incremental_ecc_embodied_carbon(
        _inventory(), 10.0, 0.0, 0.1, 0.15, yield_model="murphy"
    )
    large = incremental_ecc_embodied_carbon(
        _inventory(), 250.0, 0.0, 0.1, 0.15, yield_model="murphy"
    )
    assert small.incremental_kgco2e != pytest.approx(large.incremental_kgco2e)


def test_high_power_euv_can_reduce_total_patterning_energy() -> None:
    duv = PatterningRoute(
        "DUV_MULTI_PATTERN",
        "193i",
        (
            PatterningStep("lithography", 4, 1.0),
            PatterningStep("deposition", 3, 1.0),
            PatterningStep("etch", 3, 1.0),
        ),
        _evidence(),
    )
    euv = PatterningRoute(
        "EUV_SINGLE_PATTERN",
        "EUV",
        (
            PatterningStep("lithography", 1, 3.0),
            PatterningStep("deposition", 0, 1.0),
            PatterningStep("etch", 1, 1.0),
        ),
        _evidence(),
    )
    assert euv.steps[0].electricity_kwh_per_step > duv.steps[0].electricity_kwh_per_step
    assert euv.electricity_kwh_per_wafer < duv.electricity_kwh_per_wafer
    duv_carbon = wafer_carbon(
        _inventory(
            fab_electricity_kwh=20.0,
            fab_ci_kgco2e_per_kwh=1.0,
            process_gases=(),
            upstream_kgco2e_per_wafer=0.0,
            energy_boundary=FabEnergyBoundary.NON_PATTERNING_ONLY,
            patterning_route=duv,
        )
    )
    euv_carbon = wafer_carbon(
        _inventory(
            fab_electricity_kwh=20.0,
            fab_ci_kgco2e_per_kwh=1.0,
            process_gases=(),
            upstream_kgco2e_per_wafer=0.0,
            energy_boundary=FabEnergyBoundary.NON_PATTERNING_ONLY,
            patterning_route=euv,
        )
    )
    assert euv_carbon.total_kgco2e < duv_carbon.total_kgco2e


def test_gross_die_geometry_decreases_with_die_area() -> None:
    assert gross_dies_per_wafer(300.0, 25.0) > gross_dies_per_wafer(300.0, 100.0)


def test_poisson_and_negative_binomial_have_valid_limits() -> None:
    assert poisson_yield(0.0, 100.0) == 1.0
    assert negative_binomial_yield(0.0, 100.0, 2.0) == 1.0
    assert 0.0 < poisson_yield(0.2, 100.0) < 1.0
    assert 0.0 < negative_binomial_yield(0.2, 100.0, 2.0) < 1.0


def test_mask_nre_allocation_falls_with_volume() -> None:
    low_volume = mask_nre_per_die_kgco2e(1_000.0, 100.0, 500.0)
    high_volume = mask_nre_per_die_kgco2e(1_000.0, 10_000.0, 500.0)
    assert high_volume < low_volume


def test_mask_constant_is_never_implicit() -> None:
    result = die_embodied_carbon(
        _inventory(), 100.0, 0.15, yield_model="murphy"
    )
    assert result.mask_nre_kgco2e is None
    with pytest.raises(ValueError, match="both be supplied"):
        die_embodied_carbon(
            _inventory(),
            100.0,
            0.15,
            yield_model="murphy",
            maskset_kgco2e=1.0,
        )


def test_act_compatible_equation_matches_hand_calculation() -> None:
    actual = act_compatible_logic_carbon_kgco2e(
        area_cm2=2.0,
        fab_ci_kgco2e_per_kwh=0.5,
        energy_per_area_kwh_per_cm2=3.0,
        gas_per_area_kgco2e_per_cm2=0.2,
        materials_per_area_kgco2e_per_cm2=0.3,
        yield_fraction=0.8,
    )
    assert actual == pytest.approx(2.0 * (0.5 * 3.0 + 0.2 + 0.3) / 0.8)


def test_source_calibrated_evidence_requires_sources() -> None:
    with pytest.raises(ValueError, match="requires source IDs"):
        Evidence(EvidenceLabel.SOURCE_CALIBRATED, (), "Missing provenance test")
