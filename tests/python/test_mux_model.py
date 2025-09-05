import pytest

from mux_model import evaluate_mux_configs


def test_mux_metrics_table():
    res = evaluate_mux_configs()
    assert set(res) == {4, 8, 16}

    m4 = res[4]
    assert m4.sense_amps == 64
    assert m4.total_area_um2 == pytest.approx(1792.0)
    assert m4.latency_ns == pytest.approx(0.8)
    assert m4.dyn_energy_pj == pytest.approx(1.2)
    assert m4.esii == pytest.approx(0.96)
    assert m4.nesii == pytest.approx(1.0)
    assert m4.green_score == pytest.approx(100.0)
    assert m4.operational_energy_kj == pytest.approx(1.2)
    assert m4.operational_footprint_g == pytest.approx(0.1332, rel=1e-3)
    assert m4.embodied_footprint_g == pytest.approx(0.00896, rel=1e-3)

    m8 = res[8]
    assert m8.sense_amps == 32
    assert m8.total_area_um2 == pytest.approx(1254.4)
    assert m8.latency_ns == pytest.approx(1.0)
    assert m8.dyn_energy_pj == pytest.approx(1.0)
    assert m8.esii == pytest.approx(1.0)
    assert m8.nesii == pytest.approx(1.04, rel=1e-2)
    assert m8.green_score == pytest.approx(96.0, rel=1e-2)
    assert m8.operational_energy_kj == pytest.approx(1.0)
    assert m8.operational_footprint_g == pytest.approx(0.111, rel=1e-3)
    assert m8.embodied_footprint_g == pytest.approx(0.00627, rel=1e-3)

    m16 = res[16]
    assert m16.sense_amps == 16
    assert m16.total_area_um2 == pytest.approx(1088.0)
    assert m16.latency_ns == pytest.approx(1.3)
    assert m16.dyn_energy_pj == pytest.approx(1.1)
    assert m16.esii == pytest.approx(1.43)
    assert m16.nesii == pytest.approx(1.49, rel=1e-2)
    assert m16.green_score == pytest.approx(67.11, rel=1e-2)
    assert m16.operational_energy_kj == pytest.approx(1.1)
    assert m16.operational_footprint_g == pytest.approx(0.1221, rel=1e-3)
    assert m16.embodied_footprint_g == pytest.approx(0.00544, rel=1e-3)
