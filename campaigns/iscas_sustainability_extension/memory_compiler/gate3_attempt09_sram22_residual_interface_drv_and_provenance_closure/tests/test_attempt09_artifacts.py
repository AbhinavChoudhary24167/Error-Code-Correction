import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT.parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_required_deliverables_exist():
    names = [
        "ATTEMPT09_STATUS.json", "ATTEMPT09_SUMMARY.md",
        "RESIDUAL_EXTERNAL_DRV_INVENTORY.md", "RESIDUAL_EXTERNAL_DRV_INVENTORY.json",
        "SRAM22_OUTPUT_TRANSITION_PROVENANCE.md", "CLASS_C_COUNTERFACTUAL_DIAGNOSTIC.md",
        "RSTB_REPAIR.md", "CLOCK_INTERFACE_REPAIR.md", "COMMON_HOLD_POLICY.md",
        "CANONICAL_EXTERNAL_CLOSURE.md", "MULTISEED_EXTERNAL_CLOSURE.json",
        "FINAL_MATCHED_PPA.json", "GATE3_REASSESSMENT_READINESS.md",
        "REGRESSION_STATUS.json", "ATTEMPT09_EVIDENCE_MANIFEST.json",
    ]
    assert all((ROOT / name).is_file() for name in names)


def test_failure_class_and_gate_boundaries_are_explicit():
    status = load("ATTEMPT09_STATUS.json")
    assert status["final_attempt09_classification"] == "RESIDUAL_SRAM_INPUT_DRV_FAIL"
    assert status["gate3_recommendation"] == "KEEP_GATE3_FAILED"
    assert status["gate3_historical_state"] == "FAIL"
    assert status["gate3_reassessment_started"] is False
    assert status["gate4_state"] == "NOT_STARTED_UNAUTHORIZED"
    assert status["carbon_modeling_started"] is False
    assert status["attempt10_started"] is False
    assert status["constraint_relaxed_to_force_pass"] is False
    assert status["production_liberty_modified"] is False
    assert status["macro_internals_changed"] is False


def test_canonical_counts_separate_external_and_class_c():
    status = load("ATTEMPT09_STATUS.json")
    for design, class_c in (("U0", 64), ("E0", 72)):
        row = status["canonical"][design]
        assert row["genuine_external_slew_violations"] == 1
        assert row["class_c_sram_output_rows"] == class_c
        assert row["max_slew_violations_reported"] == class_c + 1
        assert row["setup_violations"] == row["hold_violations"] == 0
        assert row["max_capacitance_violations"] == 0
        assert row["integration_drc"] == 0
        assert row["antenna_violating_nets"] == 0


def test_class_c_provenance_and_counterfactual_are_causal():
    status = load("ATTEMPT09_STATUS.json")
    cls = status["class_c"]
    assert cls["classification"] == "UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY"
    assert cls["disposition"] == "PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV"
    assert cls["counts"] == {"U0": 64, "E0": 72}
    assert cls["production_warnings_preserved"] is True
    assert cls["provenance_established"] is True
    assert [r["object"] for r in status["counterfactual"]["U0_rows"]] == ["u_data/rstb"]
    assert [r["object"] for r in status["counterfactual"]["E0_rows"]] == ["u_protected_memory.u_data/rstb"]


def test_common_multiseed_policy_has_no_per_seed_tuning():
    multi = load("MULTISEED_EXTERNAL_CLOSURE.json")
    assert multi["seed_policy"] == [11, 13, 17, 19, 23]
    assert multi["per_seed_tuning"] is False
    assert multi["same_interface_repair_and_common_hold_policy_all_e0_seeds"] is True
    assert all(pair["matched_route_clean"] for pair in multi["seeds"])
    assert multi["matched_setup_hold_clean_count"] >= 4
    assert multi["matched_external_timing_drv_closure_count"] == 0
    seed17 = next(pair for pair in multi["seeds"] if pair["seed"] == 17)
    assert seed17["E0"]["hold_violations"] == 0
    assert seed17["E0"]["worst_hold_slack_ns"] >= 0


def test_final_artifacts_match_registered_hashes():
    multi = load("MULTISEED_EXTERNAL_CLOSURE.json")
    for pair in multi["seeds"]:
        for design, flow in (("U0", "attempt09_u0"), ("E0", "attempt09_e0")):
            base = ROOT / "raw/openroad/work/results/sky130hd" / flow / f"seed{pair['seed']}"
            for suffix, digest in pair[design]["final_artifact_sha256"].items():
                path = base / f"6_final.{suffix}"
                assert path.is_file()
                assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_sram_sources_match_frozen_attempt06_manifest():
    manifest = json.loads((MEMORY / "gate3_attempt06_replacement_sram_backend_qualification/SRAM22_SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["upstream_commit"] == "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05"
    rows = [row for row in manifest["artifacts"] if row["role"] == "macro_source_artifact"]
    assert len(rows) == 14
    for row in rows:
        path = ROOT / "source_checkout" / row["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_constraints_and_repair_policy_are_common_and_unrelaxed():
    for design in ("u0", "e0"):
        sdc = (ROOT / f"openroad/{design}/constraint.sdc").read_text(encoding="utf-8")
        assert "create_clock -name core_clk -period 10.0" in sdc
        assert "set_clock_uncertainty 0.10" in sdc
        assert "set_max_transition 0.60 [current_design]" in sdc
    repair = (ROOT / "openroad/pre_global_route_drv_repair.tcl").read_text(encoding="utf-8")
    assert "-hold_margin 0.025" in repair
    assert "set_max_transition" not in repair
    assert "constraints_relaxed=0" in repair
