from __future__ import annotations

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
    WaferProcessInventory,
    lifecycle_carbon_kgco2e,
    operational_carbon_kgco2e,
    wafer_carbon,
)


def _evidence() -> Evidence:
    return Evidence(
        EvidenceLabel.PARAMETRIC_EXTRAPOLATION,
        (),
        "Synthetic accounting test.",
    )


def test_patterning_diagnostic_is_not_added_twice_to_total_scope2() -> None:
    route = PatterningRoute(
        "route", "EUV", (PatterningStep("lithography", 2, 5.0),), _evidence()
    )
    result = wafer_carbon(
        WaferProcessInventory(
            "node",
            "route",
            "MATURE_NODE",
            300.0,
            100.0,
            0.5,
            (),
            10.0,
            _evidence(),
            FabEnergyBoundary.TOTAL_INCLUDING_PATTERNING,
            route,
        )
    )
    assert result.patterning_scope2_kgco2e_diagnostic == 5.0
    assert result.scope2_kgco2e == 50.0
    assert result.total_kgco2e == 60.0


def test_non_patterning_boundary_adds_patterning_exactly_once() -> None:
    route = PatterningRoute(
        "route", "DUV", (PatterningStep("lithography", 2, 5.0),), _evidence()
    )
    result = wafer_carbon(
        WaferProcessInventory(
            "node",
            "route",
            "MATURE_NODE",
            300.0,
            100.0,
            0.5,
            (),
            0.0,
            _evidence(),
            FabEnergyBoundary.NON_PATTERNING_ONLY,
            route,
        )
    )
    assert result.total_energy_kwh == 110.0
    assert result.scope2_kgco2e == 55.0


def test_operational_carbon_scales_linearly_with_use_phase_ci() -> None:
    low = operational_carbon_kgco2e(1e-6, 1e9, 0.1)
    high = operational_carbon_kgco2e(1e-6, 1e9, 0.8)
    assert high == pytest.approx(8.0 * low)


def test_recovery_energy_is_counted_once_inside_operational_carbon() -> None:
    base = operational_carbon_kgco2e(2.0, 10.0, 0.5)
    recovered = operational_carbon_kgco2e(
        2.0, 10.0, 0.5, recovery_energy_j=1.0
    )
    assert recovered == pytest.approx(1.5 * base)
    lifecycle = lifecycle_carbon_kgco2e(3.0, recovered)
    assert lifecycle == pytest.approx(3.0 + recovered)


def test_external_replacement_is_separate_and_never_implicit() -> None:
    assert lifecycle_carbon_kgco2e(1.0, 2.0) == 3.0
    assert (
        lifecycle_carbon_kgco2e(
            1.0, 2.0, replacement_or_external_recovery_kgco2e=4.0
        )
        == 7.0
    )
