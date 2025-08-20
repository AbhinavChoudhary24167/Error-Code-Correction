import math

from ecc_selector import select
from energy_model import estimate_energy


def test_scrub_energy_included():
    params = {
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 1.0,
        "ci": 0.5,
        "bitcell_um2": 0.040,
        "lifetime_h": 1.0,
    }
    res = select(["sec-ded-64"], scrub_s=1.0, **params)
    rec = res["pareto"][0]

    e_per_read = estimate_energy(8, 0, node_nm=params["node"], vdd=params["vdd"])
    words = params["capacity_gib"] * (2**30 * 8) / 64
    expected = (params["lifetime_h"] * 3600 / 1.0) * words * e_per_read / 3_600_000.0

    assert math.isclose(rec["E_dyn_kWh"], expected, rel_tol=1e-9)
    assert rec["includes_scrub_energy"] is True
    assert res["includes_scrub_energy"] is True
