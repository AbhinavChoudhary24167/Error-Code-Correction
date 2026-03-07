import json

from ml.drift import DRIFT_POLICY_THRESHOLDS, compute_drift_policy


def _base_report(*, max_psi: float = 0.0, confidence_shift: float = 0.0, ood_rate_delta: float = 0.0) -> dict:
    return {
        "population_stability_index": {},
        "ood_rate_delta": float(ood_rate_delta),
        "confidence_shift": float(confidence_shift),
        "summary": {
            "max_psi": float(max_psi),
            "mean_psi": float(max_psi),
            "reference_ood_rate": 0.0,
            "new_ood_rate": 0.0,
            "reference_confidence_mean": 0.6,
            "new_confidence_mean": 0.6,
        },
        "status": {"drift_detected": False, "severity": "none"},
    }


def test_drift_policy_no_drift_case():
    policy = compute_drift_policy(_base_report())
    assert policy["actions"]["action"] == "none"
    assert policy["actions"]["warn_threshold_hit"] is False
    assert policy["actions"]["fail_threshold_hit"] is False
    assert policy["actions"]["retrain_recommended"] is False


def test_drift_policy_warn_level_case_is_deterministic():
    psi_warn = float(DRIFT_POLICY_THRESHOLDS["psi"]["warn"])
    psi_fail = float(DRIFT_POLICY_THRESHOLDS["psi"]["fail"])
    report = _base_report(max_psi=(psi_warn + psi_fail) / 2.0)

    policy_a = compute_drift_policy(report)
    policy_b = compute_drift_policy(report)

    assert policy_a == policy_b
    assert policy_a["actions"]["action"] == "warn"
    assert policy_a["actions"]["warn_threshold_hit"] is True
    assert policy_a["actions"]["fail_threshold_hit"] is False
    assert policy_a["actions"]["retrain_recommended"] is True
    assert policy_a["triggered_metrics"]["warn"] == ["psi"]
    assert policy_a["triggered_metrics"]["fail"] == []


def test_drift_policy_fail_case_from_ood_delta():
    ood_fail = float(DRIFT_POLICY_THRESHOLDS["ood_rate_delta"]["fail"])
    report = _base_report(ood_rate_delta=ood_fail + 0.01)
    policy = compute_drift_policy(report)

    assert policy["actions"]["action"] == "fail"
    assert policy["actions"]["warn_threshold_hit"] is True
    assert policy["actions"]["fail_threshold_hit"] is True
    assert policy["actions"]["retrain_recommended"] is True
    assert "ood_rate_delta" in policy["triggered_metrics"]["fail"]


def test_drift_policy_json_stable_encoding_ordering():
    report = _base_report(max_psi=0.25)
    payload = compute_drift_policy(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    assert '"policy_version": 1' in text
