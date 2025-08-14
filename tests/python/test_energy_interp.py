import pytest
import energy_model


def test_boundary_exactness():
    e_lo = energy_model.gate_energy(28, 0.6, "xor")
    assert e_lo == pytest.approx(2.5e-12, rel=1e-9)
    e_hi = energy_model.gate_energy(28, 0.8, "xor")
    assert e_hi == pytest.approx(3.0e-12, rel=1e-9)


def test_interior_linearity():
    e_lo = energy_model.gate_energy(28, 0.6, "xor")
    e_hi = energy_model.gate_energy(28, 0.8, "xor")
    e_mid = energy_model.gate_energy(28, 0.7, "xor")
    assert e_mid == pytest.approx((e_lo + e_hi) / 2, rel=1e-9)


def test_oob_warn_clamp(caplog):
    with caplog.at_level("WARNING"):
        e = energy_model.gate_energy(28, 0.5, "xor")
    assert e == pytest.approx(2.5e-12, rel=1e-9)
    assert any("clamped" in m for m in caplog.text.splitlines())
