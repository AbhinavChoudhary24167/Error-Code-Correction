import math

from fit import (
    compute_fit_post,
    compute_fit_pre,
    ecc_coverage_factory,
    fit_system,
    mttf_from_fit,
)


def test_sec_daec_benefits_from_adjacent_bursts():
    word_bits = 64
    fit_bit = 0.0
    scrub = 0.0
    total_double = 100.0

    rates_low = {2: {"adj": total_double * 0.1, "nonadj": total_double * 0.9}}
    rates_high = {2: {"adj": total_double * 0.9, "nonadj": total_double * 0.1}}

    ded = ecc_coverage_factory("SEC-DED")
    daec = ecc_coverage_factory("SEC-DAEC")

    sys_ded_low = fit_system(1.0, compute_fit_post(word_bits, fit_bit, rates_low, ded, scrub))
    sys_daec_low = fit_system(1.0, compute_fit_post(word_bits, fit_bit, rates_low, daec, scrub))
    sys_ded_high = fit_system(1.0, compute_fit_post(word_bits, fit_bit, rates_high, ded, scrub))
    sys_daec_high = fit_system(1.0, compute_fit_post(word_bits, fit_bit, rates_high, daec, scrub))

    diff_low = sys_ded_low - sys_daec_low
    diff_high = sys_ded_high - sys_daec_high

    assert sys_daec_high < sys_ded_high
    assert sys_daec_high < sys_daec_low
    assert diff_high > diff_low


def test_scrub_interval_increases_residual_doubles():
    word_bits = 64
    fit_bit = 1_000.0
    rates = {}
    ded = ecc_coverage_factory("SEC-DED")

    short = compute_fit_post(word_bits, fit_bit, rates, ded, scrub_interval_s=3600)
    long = compute_fit_post(word_bits, fit_bit, rates, ded, scrub_interval_s=3600 * 10)

    assert long > short

    sys_short = fit_system(1.0, short)
    sys_long = fit_system(1.0, long)

    assert sys_long > sys_short


def test_mttf_from_fit():
    assert math.isinf(mttf_from_fit(0.0))
    assert mttf_from_fit(1000.0) == 1_000_000.0


def test_compute_fit_pre():
    fit_bit = 10.0
    mbu = {2: {"adj": 5.0, "nonadj": 5.0}, 3: 1.0}
    assert compute_fit_pre(64, fit_bit, mbu) == 64 * 10.0 + 5.0 + 5.0 + 1.0
