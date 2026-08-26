from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[2]
DOC = ROOT / "docs/date2027/rigour_gate_03f"


def load(name: str):
    return json.loads((DOC / name).read_text(encoding="utf-8"))


def test_final_environment_was_frozen_before_qualification() -> None:
    environment = load("DATE_FINAL_PHYSICAL_ENVIRONMENT.json")
    assert environment["state"] == "DATE_FINAL_PHYSICAL_ENVIRONMENT_FROZEN"
    assert environment["frozen_before_qualification"] is True
    assert environment["docker"]["image_id"] == (
        "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
    )
    assert environment["tools"]["openroad_git_commit"] == (
        "ab6fd26351dc449e69059684dc6aa9ae9046eb36"
    )


def test_single_gate03f_verdict_and_gate04_readiness() -> None:
    verdict = load("GATE_03F_VERDICT.json")
    assert verdict["verdict"] == "GATE_03F_PASS"
    assert verdict["gate04_state"] == "GATE_04_READY"
    assert verdict["power_status"] == "ACTIVITY_BASED_POWER_QUALIFIED"
    assert verdict["physical_run_count"] == 7
    assert all(verdict["conditions"].values())


def test_exact_three_two_two_matrix_completed_with_zero_drc() -> None:
    runs = load("QUALIFICATION_RUN_METRICS.json")["runs"]
    assert len(runs) == 7
    assert Counter(row["design_family"] for row in runs) == {
        "gcd": 3,
        "representative_secded_72_64": 2,
        "bch_78_64_t2": 2,
    }
    assert all(row["physical_exit_status"] == 0 for row in runs)
    assert all(row["routing_complete"] is True for row in runs)
    assert all(row["metrics"]["drc_count"] == 0 for row in runs)


def test_every_repeated_metric_has_the_full_noise_summary() -> None:
    payload = load("REPRODUCIBILITY_STATISTICS.json")
    required = {
        "mean",
        "sample_standard_deviation",
        "coefficient_of_variation",
        "minimum",
        "maximum",
        "range",
        "maximum_relative_run_to_run_difference",
        "zero_observed_variation",
        "five_x_noise_absolute_threshold",
    }
    for group in (payload["physical"], payload["power"]):
        for metrics in group.values():
            for summary in metrics.values():
                assert required <= summary.keys()
                assert summary["range"] == 0
                assert summary["zero_observed_variation"] is True


def test_common_activity_power_is_complete_and_non_arbitrary() -> None:
    power = load("POWER_RESULTS.json")
    assert power["status"] == "ACTIVITY_BASED_POWER_QUALIFIED"
    assert len(power["rows"]) == 12
    assert {row["trace_class"] for row in power["rows"]} == {
        "no_error",
        "single_error",
        "double_error",
    }
    for row in power["rows"]:
        assert row["useful_operations"] == 100000
        assert row["metrics"]["total_power_w"] > 0
        assert row["metrics"]["total_energy_pj_per_operation"] > 0


def test_published_sealed_evidence_hashes_match() -> None:
    for line in (DOC / "QUALIFICATION_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = DOC / relative.removeprefix("./")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
