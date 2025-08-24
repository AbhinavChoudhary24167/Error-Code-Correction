import math

import pytest

from ecc_selector import select
from energy_model import scrub_energy_kwh


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
    codes = ["sec-ded-64", "sec-daec-64"]
    res_fast = select(codes, scrub_s=1.0, **params)
    rec_fast = next(r for r in res_fast["pareto"] if r["code"] == "sec-ded-64")

    expected = scrub_energy_kwh(
        8,
        params["capacity_gib"],
        params["lifetime_h"],
        1.0,
        node_nm=params["node"],
        vdd=params["vdd"],
    )

    assert math.isclose(rec_fast["E_scrub_kWh"], expected, rel_tol=1e-9)
    assert rec_fast["E_dyn_kWh"] == 0.0
    assert rec_fast["includes_scrub_energy"] is True
    assert res_fast["includes_scrub_energy"] is True

    res_slow = select(codes, scrub_s=0.5, **params)
    rec_slow = next(r for r in res_slow["pareto"] if r["code"] == "sec-ded-64")

    assert rec_slow["E_scrub_kWh"] == pytest.approx(rec_fast["E_scrub_kWh"] * 2, rel=1e-9)
    assert rec_slow["carbon_kg"] > rec_fast["carbon_kg"]
    assert rec_slow["ESII"] < rec_fast["ESII"]
