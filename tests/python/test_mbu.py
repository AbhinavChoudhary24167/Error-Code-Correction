from fit import compute_fit_post, ecc_coverage_factory
from mbu import pmf_adjacent


def _rates_from_pmf(pmf, totals):
    rates = {}
    for k, total in totals.items():
        p_adj = pmf[k]["adj"]
        rates[k] = {"adj": total * p_adj, "nonadj": total * (1 - p_adj)}
    return rates


def test_heavy_severity_penalises_sec_ded_more():
    word_bits = 64
    fit_bit = 0.0
    scrub = 0.0

    totals_light = {2: 10.0, 3: 1.0}
    totals_heavy = {2: 100.0, 3: 20.0}

    pmf_light = pmf_adjacent("light", word_bits, bitline_bits=64)
    pmf_heavy = pmf_adjacent("heavy", word_bits, bitline_bits=64)

    rates_light = _rates_from_pmf(pmf_light, totals_light)
    rates_heavy = _rates_from_pmf(pmf_heavy, totals_heavy)

    ded = ecc_coverage_factory("SEC-DED")
    daec = ecc_coverage_factory("SEC-DAEC")
    taec = ecc_coverage_factory("TAEC")

    ded_light = compute_fit_post(word_bits, fit_bit, rates_light, ded, scrub)
    ded_heavy = compute_fit_post(word_bits, fit_bit, rates_heavy, ded, scrub)
    daec_light = compute_fit_post(word_bits, fit_bit, rates_light, daec, scrub)
    daec_heavy = compute_fit_post(word_bits, fit_bit, rates_heavy, daec, scrub)
    taec_light = compute_fit_post(word_bits, fit_bit, rates_light, taec, scrub)
    taec_heavy = compute_fit_post(word_bits, fit_bit, rates_heavy, taec, scrub)

    diff_ded = ded_heavy.nominal - ded_light.nominal
    diff_daec = daec_heavy.nominal - daec_light.nominal
    diff_taec = taec_heavy.nominal - taec_light.nominal

    assert ded_heavy.nominal > ded_light.nominal
    assert diff_ded > diff_daec
    assert diff_ded > diff_taec
