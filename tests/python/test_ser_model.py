import pytest
from ser_model import ber

CALIBRATION_SER = 1e-6


def test_monotonic_ber():
    assert ber(0.7) < ber(0.6) < ber(0.5)


def test_voltage_boundary():
    with pytest.raises(ValueError):
        ber(0.3)


def test_calibration_point():
    assert ber(0.6, nodes=1) == pytest.approx(CALIBRATION_SER, rel=0.1)
