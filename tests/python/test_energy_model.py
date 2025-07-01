import pytest
import numpy as np
import energy_model
from energy_model import estimate_energy, epc, gate_energy_vec, gate_energy


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


def test_gate_energy_vec_rounding(caplog):
    with caplog.at_level('WARNING'):
        val = gate_energy_vec(16, [0.75], "xor")[0]
    ref = gate_energy(16, 0.8, "xor")
    assert val == pytest.approx(ref)
    assert any('VDD rounded to nearest entry' in m for m in caplog.text.splitlines())


def test_gate_energy_vec_monotonic():
    e_small = gate_energy_vec(7, [0.6], "xor")[0]
    e_large = gate_energy_vec(28, [0.8], "xor")[0]
    assert e_small < e_large


def test_nearest_rounding():
    e_exact = gate_energy(16, 0.8, "xor")
    e_round = gate_energy(16, 0.75, "xor")
    assert e_exact == e_round


def test_vector_api():
    v = np.array([0.6, 0.75, 0.8])
    arr = energy_model.gate_energy_vec(28, v, "and")
    assert arr.shape == v.shape
