import logging
import math

import pytest

from gs import GSInputs, compute_gs


def test_compute_gs_basic_bounded():
    inp = GSInputs(
        fit_base=1000, fit_ecc=100, carbon_kg=10.0, latency_ns=20.0, latency_base_ns=0.0
    )
    res = compute_gs(inp)
    assert 0.0 <= res["GS"] <= 100.0
    assert 0.0 <= res["Sr"] <= 1.0
    assert 0.0 <= res["Sc"] <= 1.0
    assert 0.0 <= res["Sl"] <= 1.0
    assert 0.0 <= res["So"] <= 1.0


def test_gs_monotone_reliability():
    inp_a = GSInputs(
        fit_base=1000, fit_ecc=500, carbon_kg=5.0, latency_ns=10.0, latency_base_ns=0.0
    )
    inp_b = GSInputs(
        fit_base=1000, fit_ecc=100, carbon_kg=5.0, latency_ns=10.0, latency_base_ns=0.0
    )
    assert compute_gs(inp_b)["GS"] > compute_gs(inp_a)["GS"]


def test_gs_monotone_energy_latency_burden():
    low = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=1.0, latency_ns=5.0)
    high = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=1.0, latency_ns=50.0)
    assert compute_gs(low)["GS"] > compute_gs(high)["GS"]


def test_gs_monotone_overhead_penalty():
    base = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=1.0, latency_ns=5.0, overhead_norm=0.0)
    heavy = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=1.0, latency_ns=5.0, overhead_norm=1.0)
    assert compute_gs(base)["GS"] > compute_gs(heavy)["GS"]


def test_gs_extreme_costs_stable_and_small():
    inp = GSInputs(
        fit_base=100, fit_ecc=10, carbon_kg=1e9, latency_ns=1e9, latency_base_ns=0.0, overhead_norm=1e6
    )
    res = compute_gs(inp)
    assert math.isfinite(res["GS"])
    assert res["GS"] < 0.1


def test_weight_hygiene_normalises(caplog):
    inp = GSInputs(
        fit_base=100, fit_ecc=10, carbon_kg=1.0, latency_ns=5.0, latency_base_ns=0.0
    )
    caplog.set_level(logging.WARNING)
    res = compute_gs(inp, weights=(0.5, 0.5, 0.5))
    exp = compute_gs(inp, weights=(1 / 3, 1 / 3, 1 / 3))
    assert res["GS"] == pytest.approx(exp["GS"])
    assert any("renormalizing" in r.message for r in caplog.records)


def test_missing_carbon_is_neutral_dimension():
    inp_none = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=None, latency_ns=5.0)
    inp_zero = GSInputs(fit_base=1000, fit_ecc=100, carbon_kg=0.0, latency_ns=5.0)
    res_none = compute_gs(inp_none)
    res_zero = compute_gs(inp_zero)
    assert res_none["Sc"] == 1.0
    assert 0.0 <= res_none["GS"] <= 100.0
    assert 0.0 <= res_zero["GS"] <= 100.0
