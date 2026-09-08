import hashlib
import json
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]
MEMORY = CAMPAIGN.parent


def load(relative):
    return json.loads((CAMPAIGN / relative).read_text(encoding="utf-8"))


def test_primary_classification_and_gate_boundaries():
    status = load("ATTEMPT07_STATUS.json")
    assert status["final_attempt07_classification"] == "MATCHED_ROUTE_PASS_TIMING_LIMITED"
    assert status["gate3_recommendation"] == "KEEP_GATE3_FAILED"
    assert status["gate3_historical_state"] == "FAIL"
    assert status["gate4_state"] == "NOT_STARTED_UNAUTHORIZED"


def test_multiseed_route_and_setup_hold_results_are_preserved():
    status = load("MULTISEED_STATUS.json")
    assert status["seed_policy"] == [11, 13, 17, 19, 23]
    assert status["matched_route_timing_closure_count"] == 4
    assert status["at_least_three_matched_seeds_closed"] is True
    for pair in status["seeds"]:
        for design in ("U0", "E0"):
            row = pair[design]
            assert row["flow_completed"] is True
            assert row["integration_drc"] == 0
            assert row["setup_violations"] == 0
            assert row["drc_report_bytes"] == 0
    seed17 = next(row for row in status["seeds"] if row["seed"] == 17)
    assert seed17["E0"]["hold_violations"] == 2
    assert seed17["matched_route_timing_closure"] is False
    assert all(
        row["matched_route_timing_closure"]
        for row in status["seeds"]
        if row["seed"] != 17
    )


def test_final_artifacts_match_registered_hashes():
    status = load("MULTISEED_STATUS.json")
    for pair in status["seeds"]:
        for design, flow_name in (("U0", "attempt07_u0"), ("E0", "attempt07_e0")):
            row = pair[design]
            base = CAMPAIGN / "raw/openroad/work/results/sky130hd" / flow_name / f"seed{pair['seed']}"
            for extension, digest in row["final_artifact_sha256"].items():
                path = base / f"6_final.{extension}"
                assert path.is_file()
                assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_sram22_sources_are_byte_identical_to_attempt06_manifest():
    prior = json.loads(
        (MEMORY / "gate3_attempt06_replacement_sram_backend_qualification/SRAM22_SOURCE_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    assert prior["upstream_commit"] == "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05"
    rows = [row for row in prior["artifacts"] if row["role"] == "macro_source_artifact"]
    assert len(rows) == 14
    for row in rows:
        path = CAMPAIGN / "source_checkout" / row["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_hardened_drc_policy_is_not_overclaimed():
    comparison = (CAMPAIGN / "MATCHED_FINAL_ROUTE_COMPARISON.md").read_text(encoding="utf-8")
    required = (
        "The clean-route criterion concerns integration-generated geometry outside immutable SRAM22 internals. "
        "The SRAM22 macro internals retain the Attempt06 classification "
        "`DRC_NOT_INDEPENDENTLY_REPRODUCIBLE`; no foundry waiver or leaf-level signoff claim is made."
    )
    assert required in comparison
    status = load("ATTEMPT07_STATUS.json")
    assert status["sram_internal_drc_disposition"] == "MACRO_INTERNAL_DRC_NOT_INDEPENDENTLY_SIGNOFF_QUALIFIED"


def test_common_policy_and_clock_are_symmetric():
    constraints = load("MATCHED_FLOW_CONSTRAINTS.json")
    assert constraints["common_clock"]["period_ns"] == 10.0
    assert constraints["common_clock"]["frequency_mhz"] == 100.0
    assert constraints["asymmetric_tuning"] is False
    assert constraints["routing_layers"] == ["met1", "met2", "met3", "met4", "met5"]


def test_residual_drv_is_reported_not_suppressed():
    comparison = load("MATCHED_FINAL_ROUTE_COMPARISON.json")
    assert comparison["U0"]["timing"]["max_slew_violations"] > 0
    assert comparison["E0"]["timing"]["max_slew_violations"] > 0
    assert comparison["matched_comparison_validity"] == "DIAGNOSTIC_ONLY_TIMING_DRV_LIMITED"
    assert comparison["energy_per_access"] == "NOT_QUALIFIED"
