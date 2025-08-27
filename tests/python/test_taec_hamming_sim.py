from taec_hamming_sim import simulate_both


def test_taec_covers_superset_of_sec_ded():
    results, _ = simulate_both(trials=200, seed=123)
    ded = results["SEC-DED"]["corrected"]
    taec = results["TAEC"]["corrected"]
    # TAEC corrects at least as many patterns as SEC-DED
    assert taec >= ded
    assert results["SEC-DED"]["trials"] == 200


def test_double_error_detection():
    results, patterns = simulate_both(trials=500, seed=1)

    # SEC-DED should detect all double errors and miss all triples
    double_total = patterns[(2, "adj")] + patterns[(2, "nonadj")]
    triple_total = patterns[(3, "adj")] + patterns[(3, "nonadj")]
    assert results["SEC-DED"]["corrected"] == patterns[(1, None)]
    assert results["SEC-DED"]["detected"] == double_total
    assert results["SEC-DED"]["undetected"] == triple_total

    # TAEC corrects single, double-adjacent and triple-adjacent errors
    assert results["TAEC"]["corrected"] == (
        patterns[(1, None)] + patterns[(2, "adj")] + patterns[(3, "adj")]
    )
    # Remaining patterns are detected-only
    assert results["TAEC"]["detected"] == (
        patterns[(2, "nonadj")] + patterns[(3, "nonadj")]
    )
