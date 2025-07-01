import pytest
from energy_model import estimate_energy, ENERGY_PER_XOR, ENERGY_PER_AND


def test_estimate_energy_basic():
    assert estimate_energy(4, 2) == pytest.approx(4 * ENERGY_PER_XOR + 2 * ENERGY_PER_AND)


def test_estimate_energy_negative_inputs():
    with pytest.raises(ValueError):
        estimate_energy(-1, 0)
    with pytest.raises(ValueError):
        estimate_energy(0, -1)
