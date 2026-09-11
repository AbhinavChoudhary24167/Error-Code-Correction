from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
CARBON = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
    / "carbon"
)
sys.path.insert(0, str(CARBON / "scenarios"))
sys.path.insert(0, str(CARBON / "validation"))

from fab_scenarios import (  # noqa: E402
    FabScenario,
    FactorInterval,
    apply_fab_scenario,
)
from act_cross_validation import (  # noqa: E402
    act_2022_logic_path,
    green_matched_areal_path,
)


def _scenario(identifier: str, s1: tuple[float, float], s2: tuple[float, float]) -> FabScenario:
    return FabScenario(
        identifier,
        FactorInterval(*s1),
        FactorInterval(*s2),
        FactorInterval(1.0, 1.0),
        "PARAMETRIC",
        ("TEST",),
    )


def test_decarbonization_cannot_raise_matched_wafer_carbon() -> None:
    baseline = apply_fab_scenario(
        current_scope1_kgco2e=10.0,
        current_scope2_kgco2e=80.0,
        current_upstream_kgco2e=10.0,
        scenario=_scenario("F0", (1.0, 1.0), (1.0, 1.0)),
    )
    lower = apply_fab_scenario(
        current_scope1_kgco2e=10.0,
        current_scope2_kgco2e=80.0,
        current_upstream_kgco2e=10.0,
        scenario=_scenario("F3", (0.1, 0.5), (0.1, 0.5)),
    )
    assert baseline.total_lower == baseline.total_upper == 100.0
    assert lower.total_upper < baseline.total_lower


def test_scope_terms_are_scaled_once_and_remain_disjoint() -> None:
    result = apply_fab_scenario(
        current_scope1_kgco2e=4.0,
        current_scope2_kgco2e=8.0,
        current_upstream_kgco2e=2.0,
        scenario=_scenario("X", (0.25, 0.5), (0.5, 0.75)),
    )
    assert result.total_lower == pytest.approx(1.0 + 4.0 + 2.0)
    assert result.total_upper == pytest.approx(2.0 + 6.0 + 2.0)


def test_fab_scenarios_are_explicitly_parametric_not_forecasts() -> None:
    data = json.loads((CARBON / "scenarios" / "FAB_SCENARIOS.json").read_text("utf-8"))
    assert data["classification"] == "PARAMETRIC_SCENARIOS_NOT_FORECASTS"
    assert [row["scenario_id"] for row in data["scenarios"]] == [
        "F0_CURRENT",
        "F1_LOW_CARBON_ELECTRICITY",
        "F2_HIGH_ABATEMENT",
        "F3_LOW_CARBON_PLUS_HIGH_ABATEMENT",
        "F4_2030_STYLE_DECARBONIZED_SCENARIO",
    ]


@pytest.mark.parametrize(
    "case",
    [
        (1.0, 0.454, 1.64, 0.0, 0.0, 0.86),
        (1.0, 0.454, 4.30, 0.0, 0.0, 0.86),
        (0.5, 0.454, 2.0, 0.2, 0.3, 0.9),
    ],
)
def test_independent_act_and_green_paths_match(case: tuple[float, ...]) -> None:
    names = (
        "area_cm2",
        "fab_ci_kgco2e_per_kwh",
        "energy_per_area_kwh_per_cm2",
        "gas_per_area_kgco2e_per_cm2",
        "materials_per_area_kgco2e_per_cm2",
        "yield_fraction",
    )
    inputs = dict(zip(names, case))
    act = act_2022_logic_path(**inputs)
    green, terms = green_matched_areal_path(**inputs)
    assert act == pytest.approx(green)
    assert green == pytest.approx(sum(terms.values()))


def test_checked_act_comparison_rows_reproduce() -> None:
    path = CARBON / "validation" / "ACT_COMPARISON.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        inputs = {
            "area_cm2": float(row["area_cm2"]),
            "fab_ci_kgco2e_per_kwh": float(row["fab_ci_kgco2e_per_kwh"]),
            "energy_per_area_kwh_per_cm2": float(row["energy_per_area_kwh_per_cm2"]),
            "gas_per_area_kgco2e_per_cm2": float(row["gas_per_area_kgco2e_per_cm2"]),
            "materials_per_area_kgco2e_per_cm2": float(row["materials_per_area_kgco2e_per_cm2"]),
            "yield_fraction": float(row["yield_fraction"]),
        }
        assert act_2022_logic_path(**inputs) == pytest.approx(float(row["act_2022_kgco2e"]))
        green, _ = green_matched_areal_path(**inputs)
        assert green == pytest.approx(float(row["green_matched_kgco2e"]))


def test_sky130_has_no_fabricated_carbon_coefficient() -> None:
    status = json.loads(
        (CARBON / "validation" / "SKY130_TRANSLATION_STATUS.json").read_text("utf-8")
    )
    assert status["exact_kgco2e_per_wafer"] == "NOT_AVAILABLE"
    assert status["exact_kwh_per_wafer"] == "NOT_AVAILABLE"
    assert status["manufacturing_carbon_evidence_class"] == "BOUND_ONLY_OR_PARAMETRIC_EXTRAPOLATION"
