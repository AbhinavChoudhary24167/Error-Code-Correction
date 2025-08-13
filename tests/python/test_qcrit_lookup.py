import pytest
from ser_model import qcrit_lookup


def test_direct_lookup():
    val = qcrit_lookup("sram6t", 14, 0.80, 75, 50)
    assert val == pytest.approx(0.28, rel=1e-6)


def test_out_of_bounds_warns_and_clamps():
    with pytest.warns(RuntimeWarning):
        val = qcrit_lookup("sram6t", 14, 0.90, 75, 50)
    assert val == pytest.approx(0.28, rel=1e-6)
