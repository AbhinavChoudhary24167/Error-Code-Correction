import pytest

from ecc_mux import compute_ecc_mux_params


def test_compute_ecc_mux_params_taec_28nm():
    latency, energy, area, fanin = compute_ecc_mux_params("TAEC", "28nm")
    assert latency == pytest.approx(0.07)
    assert energy == pytest.approx(0.03)
    assert area == pytest.approx(1.4)
    assert fanin == 8


def test_compute_ecc_mux_params_taec_16nm_scaled():
    latency, energy, area, fanin = compute_ecc_mux_params("TAEC", "16nm")
    assert latency == pytest.approx(0.07 * 0.85)
    assert energy == pytest.approx(0.03 * 0.8)
    assert area == pytest.approx(1.4 * 0.7)
    assert fanin == 8


def test_compute_ecc_mux_params_unknown_node():
    with pytest.raises(ValueError, match="No mux calibration"):
        compute_ecc_mux_params("TAEC", "3nm")
