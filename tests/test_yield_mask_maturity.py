from __future__ import annotations

import csv
import json
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
    GasAbatementOverride,
    MaturityScenario,
    PatterningRoute,
    PatterningStep,
    ProcessGasUse,
    WaferProcessInventory,
    apply_maturity_scenario,
    die_embodied_carbon,
    mask_nre_per_die_kgco2e,
    wafer_carbon,
)


def _evidence(label: EvidenceLabel = EvidenceLabel.PARAMETRIC_EXTRAPOLATION) -> Evidence:
    return Evidence(label, ("SRC_IMEC_IEDM_2023",), "Declared test scenario.")


def _inventory() -> WaferProcessInventory:
    route = PatterningRoute(
        "TEST_ROUTE",
        "EUV",
        (PatterningStep("lithography", 4, 2.0),),
        _evidence(),
    )
    return WaferProcessInventory(
        "TEST",
        "TEST_ROUTE",
        "BASE",
        300.0,
        100.0,
        0.4,
        (ProcessGasUse("CF4", 0.001, 7_380.0, 0.5, 0.5),),
        10.0,
        _evidence(),
        patterning_route=route,
    )


def _scenario(name: str, **changes: object) -> MaturityScenario:
    values: dict[str, object] = {
        "name": name,
        "defect_density_per_cm2": 0.15,
        "line_yield_fraction": 0.9,
        "fab_electricity_factor": 1.0,
        "process_gas_use_factor": 1.0,
        "upstream_factor": 1.0,
        "patterning_energy_factor": 1.0,
        "abatement_overrides": (),
        "evidence": _evidence(),
    }
    values.update(changes)
    return MaturityScenario(**values)  # type: ignore[arg-type]


def test_maturity_application_changes_every_declared_axis() -> None:
    early = apply_maturity_scenario(
        _inventory(),
        _scenario(
            "EARLY_NODE",
            defect_density_per_cm2=0.3,
            line_yield_fraction=0.8,
            fab_electricity_factor=1.2,
            process_gas_use_factor=1.1,
            upstream_factor=1.05,
            patterning_energy_factor=1.1,
            abatement_overrides=(GasAbatementOverride("CF4", 0.25),),
        ),
    )
    assert early.inventory.maturity == "EARLY_NODE"
    assert early.inventory.fab_electricity_kwh == pytest.approx(120.0)
    assert early.inventory.process_gases[0].mass_kg_per_wafer == pytest.approx(0.0011)
    assert early.inventory.process_gases[0].abatement_efficiency == 0.25
    assert early.inventory.upstream_kgco2e_per_wafer == pytest.approx(10.5)
    assert early.inventory.patterning_route is not None
    assert early.inventory.patterning_route.electricity_kwh_per_wafer == pytest.approx(8.8)


def test_declared_early_scenario_can_raise_good_die_carbon() -> None:
    inventory = _inventory()
    mature = apply_maturity_scenario(inventory, _scenario("MATURE_NODE"))
    early = apply_maturity_scenario(
        inventory,
        _scenario(
            "EARLY_NODE",
            defect_density_per_cm2=0.4,
            line_yield_fraction=0.8,
            fab_electricity_factor=1.2,
            process_gas_use_factor=1.2,
            upstream_factor=1.1,
            patterning_energy_factor=1.0,
        ),
    )
    mature_die = die_embodied_carbon(
        mature.inventory,
        100.0,
        mature.defect_density_per_cm2,
        yield_model="murphy",
        line_yield_fraction=mature.line_yield_fraction,
    )
    early_die = die_embodied_carbon(
        early.inventory,
        100.0,
        early.defect_density_per_cm2,
        yield_model="murphy",
        line_yield_fraction=early.line_yield_fraction,
    )
    assert early_die.total_kgco2e > mature_die.total_kgco2e


def test_maturity_scenario_is_not_derived_from_name() -> None:
    same_a = apply_maturity_scenario(_inventory(), _scenario("EARLY_NODE"))
    same_b = apply_maturity_scenario(_inventory(), _scenario("MATURE_NODE"))
    assert wafer_carbon(same_a.inventory) == wafer_carbon(same_b.inventory)


def test_mask_nre_has_no_value_without_explicit_carbon_and_volume() -> None:
    die = die_embodied_carbon(
        _inventory(), 100.0, 0.15, yield_model="murphy"
    )
    assert die.mask_nre_kgco2e is None


def test_mask_nre_conserves_total_maskset_allocation() -> None:
    allocated = mask_nre_per_die_kgco2e(1_000.0, 20.0, 500.0)
    assert allocated * 20.0 * 500.0 == pytest.approx(1_000.0)


def test_duplicate_gas_abatement_overrides_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        _scenario(
            "BAD",
            abatement_overrides=(
                GasAbatementOverride("CF4", 0.5),
                GasAbatementOverride("CF4", 0.6),
            ),
        )


def test_zero_maturity_factor_is_rejected() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        _scenario("BAD", fab_electricity_factor=0.0)


def test_maturity_envelopes_are_explicitly_parametric_intervals() -> None:
    path = (
        ROOT
        / "campaigns"
        / "iscas_sustainability_extension"
        / "green_refoundation_node_aware_carbon"
        / "carbon"
        / "maturity"
        / "MATURITY_SCENARIOS.json"
    )
    payload = json.loads(path.read_text("utf-8"))
    assert payload["evidence_label"] == "PARAMETRIC_UNCERTAIN"
    for scenario in payload["scenarios"]:
        assert scenario["provenance"].startswith("PARAMETRIC")
        for name, interval in scenario.items():
            if name.endswith("factor") or name.endswith("fraction") or name.endswith("per_cm2") or name == "abatement_efficiency":
                assert len(interval) == 2
                assert interval[0] <= interval[1]


def test_yield_sensitivity_covers_every_host_context_and_model() -> None:
    path = (
        ROOT
        / "campaigns"
        / "iscas_sustainability_extension"
        / "green_refoundation_node_aware_carbon"
        / "carbon"
        / "yield"
        / "YIELD_SENSITIVITY.csv"
    )
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {float(row["host_area_mm2"]) for row in rows} == {10, 25, 50, 100, 250}
    assert {row["yield_model"] for row in rows} == {
        "poisson",
        "negative_binomial",
        "murphy",
    }
    assert all(row["evidence_label"] == "PARAMETRIC_SENSITIVITY" for row in rows)


def test_mask_sensitivity_is_never_mislabeled_as_measured() -> None:
    path = (
        ROOT
        / "campaigns"
        / "iscas_sustainability_extension"
        / "green_refoundation_node_aware_carbon"
        / "carbon"
        / "mask"
        / "MASK_NRE_SENSITIVITY.csv"
    )
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows
    assert {row["evidence_label"] for row in rows} == {"PARAMETRIC_UNCERTAIN"}
