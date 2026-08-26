from __future__ import annotations

import json
from pathlib import Path

from scripts.gate03f.analyze_qualification import metric_statistics


ROOT = Path(__file__).parents[2]
CONTRACT = json.loads((ROOT / "scripts/gate03f/contract_v1.json").read_text(encoding="utf-8"))


def test_qualification_matrix_is_exactly_three_two_two() -> None:
    runs = CONTRACT["qualification_runs"]
    assert len(runs) == 7
    assert len({row["run_id"] for row in runs}) == 7
    counts = {}
    for row in runs:
        counts[row["design_family"]] = counts.get(row["design_family"], 0) + 1
    assert counts == {
        "gcd": 3,
        "representative_secded_72_64": 2,
        "bch_78_64_t2": 2,
    }


def test_environment_and_interpretation_are_frozen_result_blind() -> None:
    assert CONTRACT["contract_state"] == "RESULT_BLIND_FROZEN_BEFORE_QUALIFICATION"
    assert CONTRACT["flow"]["clock_period_ns"] == 10.0
    assert CONTRACT["flow"]["physical_seed"] == 11
    assert CONTRACT["flow"]["num_cores"] == 1
    assert CONTRACT["flow"]["core_utilization_percent"] == 35
    assert CONTRACT["flow"]["place_density"] == 0.55
    assert CONTRACT["statistics"]["interpretation_policy"] == (
        "A comparative ECC effect will be interpreted quantitatively only when its magnitude "
        "is at least 5× the measured reproducibility noise for that metric."
    )


def test_zero_variation_is_reported_without_inventing_tolerance() -> None:
    result = metric_statistics([0.0, 0.0, 0.0])
    assert result["zero_observed_variation"] is True
    assert result["range"] == 0.0
    assert result["maximum_relative_run_to_run_difference"] == 0.0
    assert result["five_x_noise_absolute_threshold"] == 0.0
    assert result["coefficient_of_variation"] is None


def test_power_uses_activity_and_never_arbitrary_toggle_rates() -> None:
    power = CONTRACT["power"]
    assert power["payload_operations_per_trace"] == 100000
    assert power["trace_classes"] == ["no_error", "single_error", "double_error"]
    assert power["arbitrary_toggle_rates"] is False
    assert power["field_rate_weighting"] is False
