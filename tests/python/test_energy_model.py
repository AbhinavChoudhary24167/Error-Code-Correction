import pytest
from energy_model import estimate_energy, epc


def test_estimate_energy_basic():
    e = estimate_energy(4, 2, node_nm=28, vdd=0.8)
    ref = estimate_energy(4, 2, node_nm=28, vdd=0.6)
    assert ref < e


def test_energy_monotonicity():
    e_28_08 = estimate_energy(1, 1, node_nm=28, vdd=0.8)
    e_28_06 = estimate_energy(1, 1, node_nm=28, vdd=0.6)
    e_16_08 = estimate_energy(1, 1, node_nm=16, vdd=0.8)
    e_16_06 = estimate_energy(1, 1, node_nm=16, vdd=0.6)
    e_7_06 = estimate_energy(1, 1, node_nm=7, vdd=0.6)

    assert e_28_06 < e_28_08  # lower VDD
    assert e_16_08 < e_28_08  # smaller node
    assert e_16_06 < e_16_08  # lower VDD
    assert e_7_06 < e_16_06  # smaller node


def test_epc():
    assert epc(2, 2, 1, node_nm=16, vdd=0.6) == pytest.approx(
        estimate_energy(2, 2, node_nm=16, vdd=0.6)
    )


def test_tech_calibration_schema():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent.parent / "tech_calib.json"
    data = json.loads(path.read_text())

    assert set(data.keys()) == {"28", "16", "7"}
    for node_data in data.values():
        assert set(node_data.keys()) == {"0.8", "0.6"}
        for entry in node_data.values():
            assert set(entry.keys()) == {"xor", "and"}
