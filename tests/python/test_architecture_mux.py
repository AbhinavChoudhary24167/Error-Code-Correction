from __future__ import annotations

import math

import pytest

from architecture.carbon import (
    EmbodiedCarbonAssumptions,
    embodied_carbon_kg,
    grams_to_kilograms,
    joules_to_kwh,
    kilograms_to_grams,
    operational_carbon_kg,
)
from architecture.mux import (
    MuxCellCharacterization,
    MuxPath,
    evaluate_mux_path,
    metadata_failure_probability,
    mux_2to1_count,
    mux_depth,
    physical_container_layout,
    protected_metadata_bits,
    system_failure_probability,
)
from architecture.types import ECCConfiguration


@pytest.mark.parametrize("modes", [1, 2, 3, 4, 5])
def test_pruned_mux_count_and_depth(modes: int) -> None:
    assert mux_2to1_count(8, modes, implementation="pruned") == 8 * (modes - 1)
    assert mux_depth(modes) == (0 if modes == 1 else math.ceil(math.log2(modes)))


@pytest.mark.parametrize(
    ("modes", "expected"),
    [(1, 0), (2, 8), (3, 24), (4, 24), (5, 56)],
)
def test_padded_mux_count_non_power_of_two(modes: int, expected: int) -> None:
    assert mux_2to1_count(8, modes, implementation="padded") == expected


def test_m1_mux_has_zero_physical_overhead_without_characterization() -> None:
    result = evaluate_mux_path(MuxPath("fixed", 128, 1), characterization=None)
    assert result["mux_2to1_count"] == 0
    assert result["area_um2"] == 0.0
    assert result["delay_ns"] == 0.0
    assert result["dynamic_energy_j_per_operation"] == 0.0
    assert result["leakage_power_w"] == 0.0
    assert result["physical_metrics_characterized"] is True


def test_characterized_mux_equations() -> None:
    characterization = MuxCellCharacterization(
        area_um2=2.0,
        delay_ns=0.1,
        switched_capacitance_f=1e-15,
        leakage_current_a=1e-9,
        switching_activity=0.25,
        source="test_fixture",
        node_nm=16,
        vdd=0.8,
        temperature_c=75,
        process_corner="tt",
        library="test-only",
        tool="test",
        tool_version="1",
        calibration_source="synthetic unit-test fixture",
    )
    result = evaluate_mux_path(
        MuxPath("data", 8, 3, wire_delay_ns=0.2, route_area_um2=4.0),
        characterization=characterization,
    )
    count = 8 * 2
    assert result["area_um2"] == pytest.approx(count * 2.0 + 4.0)
    assert result["delay_ns"] == pytest.approx(2 * 0.1 + 0.2)
    assert result["dynamic_energy_j_per_operation"] == pytest.approx(count * 0.25 * 1e-15 * 0.8**2)
    assert result["leakage_power_w"] == pytest.approx(count * 0.8 * 1e-9)


def test_variable_width_fixed_container_and_padding() -> None:
    candidates = [
        ECCConfiguration("secded", "SEC-DED", "72,64", "sec-ded-64", 72, 64, 1, 2),
        ECCConfiguration("bch", "BCH", "63,51", "bch-63", 63, 51, 2, 4),
        ECCConfiguration("polar", "POLAR", "64,48", "polar-64-48", 64, 48, 1, 1),
    ]
    layout = physical_container_layout(candidates, 64)
    entries = {item["config_id"]: item for item in layout["entries"]}
    assert layout["container_bits"] == 128
    assert entries["secded"]["padding_bits"] == 56
    assert entries["bch"]["physical_bits_used"] == 126
    assert entries["polar"]["codewords_per_logical_word"] == 2


def test_metadata_storage_and_fault_tree() -> None:
    metadata = protected_metadata_bits(5, "triplicated")
    assert metadata["mode_bits"] == 3
    assert metadata["stored_bits"] == 9
    probability = metadata_failure_probability(5, "triplicated", 1e-3)
    assert probability is not None
    assert probability < metadata_failure_probability(5, "none", 1e-3)
    combined = system_failure_probability(
        0.01,
        mux_failure_probability=0.02,
        controller_failure_probability=None,
        metadata_failure_probability_value=0.03,
    )
    assert combined["system_failure_probability"] == pytest.approx(1 - 0.99 * 0.98 * 0.97)
    assert "controller" not in combined["terms"]


def test_carbon_unit_conversions_and_embodied_assumptions() -> None:
    assert joules_to_kwh(3.6e6) == pytest.approx(1.0)
    assert grams_to_kilograms(1000.0) == pytest.approx(1.0)
    assert kilograms_to_grams(1.0) == pytest.approx(1000.0)
    assert operational_carbon_kg(3.6e6, 500.0, intensity_unit="gco2e_per_kwh") == pytest.approx(0.5)
    assumptions = EmbodiedCarbonAssumptions(100.0, 1.2, packaging_allocation_kgco2e=0.1)
    result = embodied_carbon_kg(1e8, assumptions)
    assert result["area_cm2"] == pytest.approx(1.0)
    assert result["total_embodied_kgco2e"] == pytest.approx(120.1)
