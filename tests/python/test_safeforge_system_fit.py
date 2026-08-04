import math

import pytest

from codeforge.system_fit import derive_system_sdc_budget, project_system_sdc


def test_system_fit_conversion_and_tail_budget_are_unit_consistent():
    report = derive_system_sdc_budget(
        {
            "system_target_id": "server-engineering-sensitivity",
            "mission_hours": 10_000,
            "target": {"kind": "system_sdc_fit", "value": 1.0},
            "exposure": {"kind": "system_event_fit", "event_fit_upper": 1000.0},
            "tail": {"probability_upper": 1e-5, "sdc_probability_upper": 1.0},
        }
    )
    assert report["conditional_sdc_budget_total"] == pytest.approx(1e-3)
    assert report["conditional_sdc_budget_modeled_support"] == pytest.approx(
        (1e-3 - 1e-5) / (1.0 - 1e-5)
    )
    projected = project_system_sdc(
        report, support_conditional_sdc=report["conditional_sdc_budget_modeled_support"]
    )
    assert projected["system_sdc_fit_upper"] == pytest.approx(1.0)
    assert projected["meets_system_target"]


def test_per_word_and_mission_probability_models():
    report = derive_system_sdc_budget(
        {
            "mission_hours": 1000.0,
            "target": {"kind": "mission_sdc_probability", "value": 1e-6},
            "exposure": {
                "kind": "per_word_event_rate_per_hour",
                "protected_words": 1_000_000,
                "event_rate_upper_per_word_hour": 1e-12,
            },
            "tail": {"probability_upper": 0.0, "sdc_probability_upper": 1.0},
        }
    )
    expected_rate = -math.log1p(-1e-6) / 1000.0
    assert report["target"]["rate_upper_per_hour"] == pytest.approx(expected_rate)
    assert report["exposure"]["event_rate_upper_per_hour"] == pytest.approx(1e-6)


def test_unbounded_tail_is_fail_closed_and_projects_worst_case():
    report = derive_system_sdc_budget(
        {
            "mission_hours": 1.0,
            "target": {"kind": "system_sdc_fit", "value": 1.0},
            "exposure": {"kind": "system_event_fit", "event_fit_upper": 1000.0},
        }
    )
    assert report["conditional_sdc_budget_modeled_support"] is None
    assert not report["deployment_feasible_from_declared_bounds"]
    assert project_system_sdc(report, support_conditional_sdc=0.0)["system_sdc_fit_upper"] == pytest.approx(
        1000.0
    )


def test_decode_opportunity_model_rejects_possible_double_counting():
    with pytest.raises(ValueError, match="opportunities_are_disjoint"):
        derive_system_sdc_budget(
            {
                "mission_hours": 1,
                "target": {"kind": "system_sdc_fit", "value": 1},
                "exposure": {
                    "kind": "per_decode_opportunity",
                    "system_word_accesses_upper_per_hour": 100,
                    "system_word_scrubs_upper_per_hour": 10,
                    "event_probability_upper_per_opportunity": 1e-6,
                },
                "tail": {"probability_upper": 0, "sdc_probability_upper": 1},
            }
        )
