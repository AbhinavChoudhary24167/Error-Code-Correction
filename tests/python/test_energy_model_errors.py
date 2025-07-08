import pytest
from energy_model import estimate_energy


def test_estimate_energy_negative_parity():
    with pytest.raises(ValueError):
        estimate_energy(-1, 0)


def test_estimate_energy_negative_errors():
    with pytest.raises(ValueError):
        estimate_energy(0, -1)
