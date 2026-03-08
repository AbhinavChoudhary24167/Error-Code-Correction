import math

from esii import ESIIInputs, compute_esii, normalise_esii
from gs import GSInputs, compute_gs


def _inp(fit_ecc: float, energy_j: float, embodied: float = 0.1) -> ESIIInputs:
    return ESIIInputs(
        fit_base=1e4,
        fit_ecc=fit_ecc,
        e_dyn=energy_j,
        e_leak=0.0,
        e_scrub=0.0,
        ci_kgco2e_per_kwh=0.5,
        embodied_kgco2e=embodied,
        basis="system",
    )


def test_esii_and_gs_finite_across_ber_like_decades():
    vals = []
    for fit_ecc in [1e-11, 1e-9, 1e-7, 1e-5, 1e-3, 1e-1, 1, 10, 1e2, 1e4]:
        e = compute_esii(_inp(fit_ecc=fit_ecc, energy_j=1.0))
        g = compute_gs(GSInputs(fit_base=1e4, fit_ecc=fit_ecc, carbon_kg=e["total_kgCO2e"], latency_ns=1.0))
        assert math.isfinite(e["ESII"])
        assert math.isfinite(g["GS"])
        assert 0.0 <= e["ESII"] <= 1.0
        assert 0.0 <= g["GS"] <= 100.0
        vals.append(e["ESII"])
    nesii, _, _ = normalise_esii(vals)
    assert all(0.0 <= x <= 100.0 for x in nesii)


def test_monotonicity_energy_and_reliability():
    better_rel = compute_esii(_inp(fit_ecc=1.0, energy_j=1.0))["ESII"]
    worse_rel = compute_esii(_inp(fit_ecc=100.0, energy_j=1.0))["ESII"]
    assert better_rel >= worse_rel

    low_energy = compute_esii(_inp(fit_ecc=1.0, energy_j=1.0))["ESII"]
    high_energy = compute_esii(_inp(fit_ecc=1.0, energy_j=1e7))["ESII"]
    assert low_energy >= high_energy


def test_tradeoff_sanity_no_marginal_gain_domination():
    modest = compute_gs(
        GSInputs(
            fit_base=1e4,
            fit_ecc=10.0,
            carbon_kg=0.2,
            latency_ns=1.0,
            overhead_norm=0.1,
        )
    )["GS"]
    costly_marginal = compute_gs(
        GSInputs(
            fit_base=1e4,
            fit_ecc=9.5,
            carbon_kg=20.0,
            latency_ns=30.0,
            overhead_norm=2.0,
        )
    )["GS"]
    assert modest > costly_marginal


def test_identical_inputs_equal_scores():
    a = compute_esii(_inp(fit_ecc=10.0, energy_j=123.0))["ESII"]
    b = compute_esii(_inp(fit_ecc=10.0, energy_j=123.0))["ESII"]
    assert a == b

    ga = compute_gs(GSInputs(fit_base=1e4, fit_ecc=10.0, carbon_kg=0.2, latency_ns=1.0))["GS"]
    gb = compute_gs(GSInputs(fit_base=1e4, fit_ecc=10.0, carbon_kg=0.2, latency_ns=1.0))["GS"]
    assert ga == gb
