import math

import pytest

from esii import ESIIInputs, compute_esii, normalise_esii
from gs import GSInputs, compute_gs
from scores import compute_scores


def test_compute_scores_matches_components():
    inp = ESIIInputs(
        fit_base=500.0,
        fit_ecc=50.0,
        e_dyn=2_000_000.0,
        e_leak=1_000_000.0,
        ci_kgco2e_per_kwh=0.3,
        embodied_kgco2e=2.0,
    )
    ref = [10.0, 20.0, 30.0]
    res = compute_scores(inp, latency_ns=1.0, esii_reference=ref)

    esii_expected = compute_esii(inp)
    gs_expected = compute_gs(
        GSInputs(
            fit_base=inp.fit_base,
            fit_ecc=inp.fit_ecc,
            carbon_kg=esii_expected["total_kgCO2e"],
            latency_ns=1.0,
        )
    )
    _, p5_exp, p95_exp = normalise_esii(ref + [res["ESII"]])
    assert math.isclose(res["ESII"], esii_expected["ESII"])
    assert math.isclose(res["GS"], gs_expected["GS"])
    assert 0.0 <= res["NESII"] <= 100.0
    assert res["p5"] == pytest.approx(p5_exp)
    assert res["p95"] == pytest.approx(p95_exp)
