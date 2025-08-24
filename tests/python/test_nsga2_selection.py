import math

from ecc_selector import select, _pareto_front, _nsga2_sort


def _default_params():
    return {
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.040,
    }


def test_frontier_equivalence():
    records = [
        {"code": "a", "FIT": 1.0, "carbon_kg": 1.0, "latency_ns": 1.0},
        {"code": "b", "FIT": 0.5, "carbon_kg": 1.5, "latency_ns": 1.2},
        {"code": "c", "FIT": 1.2, "carbon_kg": 0.8, "latency_ns": 1.1},
        {"code": "d", "FIT": 2.0, "carbon_kg": 2.0, "latency_ns": 0.9},
    ]
    fronts, *_ = _nsga2_sort(records)
    f1_codes = {records[i]["code"] for i in fronts[0]}
    enum_codes = {r["code"] for r in _pareto_front(records)}
    assert f1_codes == enum_codes


def test_seed_determinism():
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    params = _default_params()
    r1 = select(codes, **params)
    r2 = select(codes, **params)
    assert r1["best"]["code"] == r2["best"]["code"]
    assert [p["code"] for p in r1["pareto"]] == [p["code"] for p in r2["pareto"]]
    assert r1["nsga2"]["seed"] == r2["nsga2"]["seed"]


def test_epsilon_constraint_min_carbon():
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    params = _default_params()
    res = select(codes, constraints={"fit_max": 1000.0}, **params)
    best = res["best"]
    assert best["FIT"] <= 1000.0
    feasible = [r for r in res["pareto"] if r["FIT"] <= 1000.0]
    assert best["carbon_kg"] == min(r["carbon_kg"] for r in feasible)
    assert res["decision"]["mode"] == "epsilon-constraint"


def test_knee_stability():
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    params = _default_params()
    r1 = select(codes, **params)
    params2 = dict(params)
    params2["ci"] = params["ci"] * 1.001
    r2 = select(codes, **params2)
    assert r1["decision"]["mode"] == "knee"
    assert r1["best"]["code"] == r2["best"]["code"]


def test_pareto_antidominance():
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    res = select(codes, **_default_params())
    keys = ("FIT", "carbon_kg", "latency_ns")
    for i, p in enumerate(res["pareto"]):
        for j, q in enumerate(res["pareto"]):
            if i == j:
                continue
            le = all(p[k] <= q[k] + 1e-8 for k in keys)
            lt = any(p[k] < q[k] - 1e-8 for k in keys)
            assert not (le and lt)
