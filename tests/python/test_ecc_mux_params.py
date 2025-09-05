import pytest

from ecc_mux import compute_ecc_mux_params


def test_compute_ecc_mux_params_taec():
    latency, energy, area = compute_ecc_mux_params("TAEC")
    assert latency == pytest.approx(0.07)
    assert energy == pytest.approx(0.03)
    assert area == pytest.approx(1.4)
