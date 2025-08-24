from analysis.knee import max_perp_norm


def test_extremes_not_selected():
    records = [
        {"FIT": 0.0, "carbon_kg": 0.0, "latency_ns": 0.0},
        {"FIT": 0.1, "carbon_kg": 0.2, "latency_ns": 0.1},
        {"FIT": 0.2, "carbon_kg": 0.25, "latency_ns": 0.15},
        {"FIT": 1.0, "carbon_kg": 1.0, "latency_ns": 1.0},
    ]
    idx, dist = max_perp_norm(records)
    assert idx not in (0, len(records) - 1)
    assert dist >= 0.0

