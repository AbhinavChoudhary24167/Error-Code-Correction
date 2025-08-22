import pytest
from gs import GSInputs, compute_gs

import pytest

from gs import GSInputs, compute_gs


def _manual_gs(fit_base, fit_ecc, carbon, latency):
    sr_raw = max(fit_base - fit_ecc, 0.0) / fit_base
    sr = sr_raw / (sr_raw + 0.05)
    sc = 1.0 / (1.0 + carbon / 1.0)
    sl = 1.0 / (1.0 + latency / 10.0)
    denom = 0.6 / sr + 0.3 / sc + 0.1 / sl
    return {
        "Sr": sr,
        "Sc": sc,
        "Sl": sl,
        "GS": 100.0 * 1.0 / denom,
    }


def test_compute_gs_basic():
    inp = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=10.0, latency_ns=20.0)
    res = compute_gs(inp)
    exp = _manual_gs(1000, 100, 10.0, 20.0)
    assert res["Sr"] == pytest.approx(exp["Sr"])
    assert res["Sc"] == pytest.approx(exp["Sc"])
    assert res["Sl"] == pytest.approx(exp["Sl"])
    assert res["GS"] == pytest.approx(exp["GS"])
    assert 0.0 <= res["GS"] <= 100.0


def test_gs_monotone_reliability():
    inp_a = GSInputs(fit_base=1000, fit_ecc=500, carbon_kg=5.0, latency_ns=10.0)
    inp_b = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=5.0, latency_ns=10.0)
    assert compute_gs(inp_b)["GS"] > compute_gs(inp_a)["GS"]


def test_gs_extreme_costs():
    inp = GSInputs(fit_base=100, fit_ecc=10, carbon_kg=1e6, latency_ns=1e6)
    res = compute_gs(inp)
    assert res["GS"] < 1.0
