import pytest
from ser_model import qcrit_lookup


def test_interpolation_within_grid():
    val = qcrit_lookup("sram6t", 22, 0.7, 0.0, 10)
    expected = 1.0 + 0.5 * 0.7 + 0.01 * 0.0
    assert val == pytest.approx(expected, rel=1e-5)


def test_out_of_bounds_warning():
    with pytest.warns(RuntimeWarning):
        qcrit_lookup("sram6t", 22, 1.2, 0.0, 10)
