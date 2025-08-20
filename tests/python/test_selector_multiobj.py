import logging
import math

from ecc_selector import select, _pareto_front


def test_pareto_dominance():
    records = [
        {"code": "a", "FIT": 1.0, "carbon_kg": 1.0, "latency_ns": 2.0},
        {"code": "b", "FIT": 2.0, "carbon_kg": 1.5, "latency_ns": 1.0},
        {"code": "c", "FIT": 3.0, "carbon_kg": 2.0, "latency_ns": 3.0},
    ]
    front = _pareto_front(records)
    assert [r["code"] for r in front] == ["a", "b"]


def _default_params():
    return {
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.040,
    }


def test_constraint_pruning():
    res = select(
        ["sec-ded-64", "sec-daec-64", "taec-64"],
        constraints={"latency_ns_max": 1.2},
        **_default_params(),
    )
    assert [r["code"] for r in res["pareto"]] == ["sec-ded-64"]


def test_scenario_shift_mbu():
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    light = select(codes, mbu="light", **_default_params())
    heavy = select(codes, mbu="heavy", **_default_params())

    codes_light = {r["code"] for r in light["pareto"]}
    codes_heavy = {r["code"] for r in heavy["pareto"]}

    assert codes_light == {"sec-ded-64"}
    assert {"sec-daec-64", "taec-64"}.issubset(codes_heavy)


def test_nesii_normalisation():
    res = select(["sec-ded-64", "sec-daec-64", "taec-64"], **_default_params())
    norm = res["normalization"]
    assert norm["p5"] <= norm["p95"]
    assert norm["epsilon_on_normalized_axes"] == 1e-8
    assert norm["basis"] == "system"
    assert math.isnan(norm["lifetime_h"])
    assert norm["ci_kg_per_kwh"] == _default_params()["ci"]
    assert norm["ci_source"] == "unspecified"
    for rec in res["pareto"]:
        assert 0.0 <= rec["NESII"] <= 100.0
        assert rec["p5"] == norm["p5"]
        assert rec["p95"] == norm["p95"]
        assert rec["N_scale"] == norm["N"]


def test_nesii_fallback_logs_once(caplog):
    import ecc_selector

    ecc_selector._logged_fallback = False
    ecc_selector._logged_degenerate = False
    params = _default_params()
    caplog.set_level(logging.WARNING)
    select(["sec-ded-64"], **params)
    select(["sec-ded-64"], **params)
    msgs = [r.message for r in caplog.records if "NESII" in r.message]
    assert msgs == [
        "NESII normalization fallback to min-max",
        "NESII degenerate scale; forcing score 50",
    ]
