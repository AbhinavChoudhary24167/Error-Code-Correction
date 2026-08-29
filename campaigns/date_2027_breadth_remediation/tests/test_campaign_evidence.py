"""Regression contracts for the additive DATE 2027 breadth campaign."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
SEEDS = {11, 13, 17, 19, 23}


def load_json(relative: str) -> dict:
    return json.loads((CAMPAIGN / relative).read_text(encoding="utf-8"))


def load_csv(relative: str) -> list[dict[str, str]]:
    with (CAMPAIGN / relative).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def check_hash_manifest(relative: str) -> None:
    for line in (CAMPAIGN / relative).read_text(encoding="utf-8").splitlines():
        expected, path = line.split(maxsplit=1)
        payload = (CAMPAIGN / path.strip()).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected


def assert_two_by_five(rows: list[dict[str, str]], architectures: set[str]) -> None:
    assert len(rows) == 10
    assert {int(row["seed"]) for row in rows} == SEEDS
    assert {row["architecture"] for row in rows} == architectures
    assert {(row["architecture"], int(row["seed"])) for row in rows} == {
        (architecture, seed) for architecture in architectures for seed in SEEDS
    }


def test_predeclared_plans_and_physical_contract_remain_frozen() -> None:
    check_hash_manifest("00_plan_freeze.sha256")
    check_hash_manifest("00_physical_contract_freeze.sha256")


def test_structural_formal_and_synthesis_gates_pass() -> None:
    formal = load_json("formal/results/A_formal_qualification.json")
    synthesis = load_json("synthesis/A_synthesis_structural_comparison.json")
    assert formal["formal_status"] == "PASS"
    assert formal["latency_alignment_cycles"] == 0
    assert formal["expected_request_latency_cycles"] == 1
    assert formal["expected_initiation_interval_cycles"] == 1
    assert all(proof["status"] == "PASS" for proof in formal["proofs"].values())
    assert synthesis["status"] == "PASS"
    assert not synthesis["differences"]["cell_type_histogram_equal"]
    assert not synthesis["differences"]["name_independent_graph_signature_equal"]
    assert synthesis["differences"]["register_count"] == 0


def test_structural_physical_matrix_is_exact_and_feasible() -> None:
    rows = load_csv("analysis/A_structural_pair_per_seed.csv")
    assert_two_by_five(rows, {"A_hsiao_flat", "A_hsiao_hierarchical"})
    assert all(row["routing_complete"] == "True" for row in rows)
    assert all(row["target_feasible"] == "True" for row in rows)
    assert all(int(row["setup_violation_count"]) == 0 for row in rows)
    assert all(int(row["hold_violation_count"]) == 0 for row in rows)
    summary = load_json("analysis/A_structural_pair_summary.json")
    assert summary["seed_set"] == sorted(SEEDS)
    assert summary["paired_effects"]["standard_cell_instance_area_um2"]["changed_lower_count"] == 5
    assert summary["paired_effects"]["energy_per_op_pj"]["changed_greater_count"] == 5


def test_historical_power_decomposition_reproduces_revision2() -> None:
    rows = load_csv("analysis/B_power_components_per_seed.csv")
    assert_two_by_five(rows, {"secded_comb", "secded_pipe"})
    summary = load_json("analysis/B_power_components_summary.json")
    assert summary["evidence_join_count"] == 10
    assert summary["published_total_power_reproduction_status"] == "PASS"
    assert summary["published_energy_reproduction_status"] == "PASS"
    assert summary["report_arithmetic_status"] == "PASS"
    assert summary["primary_component_by_absolute_mean_difference"] == "switching_power_w"
    assert summary["paired_effects"]["switching_power_w"]["pipelined_lower_count"] == 5
    assert summary["paired_effects"]["total_power_w"]["pipelined_lower_count"] == 5


def test_5ns_matrix_is_exact_feasible_and_preserves_ordering() -> None:
    rows = load_csv("analysis/C_5ns_per_seed.csv")
    assert_two_by_five(rows, {"C_secded_comb", "C_secded_pipe"})
    assert all(float(row["clock_period_ns"]) == 5.0 for row in rows)
    assert all(row["routing_complete"] == "True" for row in rows)
    assert all(row["target_feasible"] == "True" for row in rows)
    assert all(int(row["setup_violation_count"]) == 0 for row in rows)
    assert all(int(row["hold_violation_count"]) == 0 for row in rows)
    summary = load_json("analysis/C_5ns_summary.json")
    assert summary["historical_target_ns"] == 10.0
    assert summary["new_target_ns"] == 5.0
    assert summary["seed_set"] == sorted(SEEDS)
    assert all(
        ordering["same_direction_count"] == ordering["assessable_count"] == 5
        for ordering in summary["architecture_ordering_preservation"].values()
    )
    assert {item["relation"] for item in summary["pareto_5ns"]} == {"NON_DOMINATED"}


def test_descriptive_summaries_preserve_required_statistics() -> None:
    required = {
        "mean", "median", "sample_standard_deviation", "minimum", "maximum", "range", "values_by_seed"
    }
    a = load_json("analysis/A_structural_pair_summary.json")
    c = load_json("analysis/C_5ns_summary.json")
    for summary in (a["paired_effects"], c["within_5ns_paired_effects"]):
        for metric in summary.values():
            assert required <= metric["absolute_difference"].keys()
            assert required <= metric["percent_effect"].keys()


def test_final_repository_campaign_inventory_matches() -> None:
    manifest = CAMPAIGN / "FINAL_campaign_inventory.sha256"
    seen: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        relative = relative.strip()
        assert relative not in seen
        seen.add(relative)
        assert hashlib.sha256((CAMPAIGN / relative).read_bytes()).hexdigest() == expected
    assert "FINAL_campaign_inventory.sha256" not in seen
