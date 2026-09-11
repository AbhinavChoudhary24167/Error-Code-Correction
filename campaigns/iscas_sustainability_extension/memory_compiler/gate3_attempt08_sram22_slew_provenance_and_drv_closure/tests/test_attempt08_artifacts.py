import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT.parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_required_deliverables_exist():
    names = [
        "ATTEMPT08_STATUS.json", "ATTEMPT08_SUMMARY.md", "ENVIRONMENT_MANIFEST.json",
        "SLEW_VIOLATION_INVENTORY.json", "SLEW_VIOLATION_INVENTORY.md",
        "SLEW_INTERFACE_CORRELATION.md", "SRAM22_LIBERTY_TRANSITION_AUDIT.md",
        "STANDARD_CELL_TRANSITION_AUDIT.md", "SLEW_PROVENANCE_CLASSIFICATION.md",
        "DRV_REPAIR_SEQUENCE.md", "U0_FINAL_DRV_CLOSURE.md", "E0_FINAL_DRV_CLOSURE.md",
        "MULTISEED_DRV_STATUS.json", "ATTEMPT08_MATCHED_COMPARISON.json",
        "ATTEMPT08_MATCHED_COMPARISON.md", "GATE3_REASSESSMENT_READINESS.md",
        "REGRESSION_STATUS.json", "ATTEMPT08_EVIDENCE_MANIFEST.json",
    ]
    assert all((ROOT / name).is_file() for name in names)


def test_inventory_is_exhaustive_and_single_classed():
    inv = load("SLEW_VIOLATION_INVENTORY.json")
    assert inv["record_count"] == 145
    assert inv["per_design"]["U0"]["violation_count"] == 65
    assert inv["per_design"]["E0"]["violation_count"] == 80
    assert inv["per_design"]["U0"]["class_distribution_A_through_F"] == {"A": 0, "B": 1, "C": 64, "D": 0, "E": 0, "F": 0}
    assert inv["per_design"]["E0"]["class_distribution_A_through_F"] == {"A": 3, "B": 4, "C": 72, "D": 0, "E": 1, "F": 0}
    required = {
        "design", "seed", "violating_object", "net", "driver", "driver_cell",
        "driver_pin", "receivers", "receiver_pins", "transition_value_ns",
        "maximum_permitted_transition_ns", "violation_magnitude_ns",
        "limiting_transition", "fanout", "capacitance_pf",
        "estimated_parasitic_wire_length_um", "route_layers", "driver_type",
        "sink_types", "source_of_max_transition_requirement",
        "liberty_file_cell_pin_or_sdc", "requirement_origin", "primary_class",
    }
    assert all(required <= row.keys() and row["primary_class"] in "ABCDEF" for row in inv["records"])


def test_primary_classification_and_gate_boundaries():
    status = load("ATTEMPT08_STATUS.json")
    assert status["final_attempt08_classification"] == "SLEW_REPAIR_PARTIAL"
    assert status["gate3_recommendation"] == "KEEP_GATE3_FAILED"
    assert status["gate3_historical_state"] == "FAIL"
    assert status["gate3_reassessment_started"] is False
    assert status["gate4_state"] == "NOT_STARTED_UNAUTHORIZED"
    assert status["attempt09_started"] is False
    assert status["constraint_relaxed_to_force_pass"] is False
    assert status["macro_internals_changed"] is False


def test_canonical_repairs_reduce_e0_without_regressing_other_checks():
    status = load("ATTEMPT08_STATUS.json")
    assert len(status["accepted_repairs"]) == 3
    assert status["canonical"]["U0"]["max_slew_violations"] == 65
    assert status["canonical"]["E0"]["max_slew_violations"] == 75
    for design in ("U0", "E0"):
        row = status["canonical"][design]
        assert row["flow_completed"] is True
        assert row["setup_violations"] == 0
        assert row["hold_violations"] == 0
        assert row["integration_drc"] == 0
        assert row["max_capacitance_violations"] == 0
        assert row["antenna_violating_nets"] == 0
    assert status["canonical_pair_externally_timing_drv_clean"] is False
    assert status["provenance_limited_exception_eligible"] is False


def test_five_seed_policy_and_seed17_are_reported_exactly():
    multi = load("MULTISEED_DRV_STATUS.json")
    assert multi["seed_policy"] == [11, 13, 17, 19, 23]
    assert multi["per_seed_tuning"] is False
    assert multi["all_u0_route_clean"] is True
    assert multi["all_e0_route_clean"] is True
    assert multi["matched_setup_hold_clean_count"] == 4
    assert multi["matched_external_timing_drv_closure_count"] == 0
    seed17 = next(row for row in multi["seeds"] if row["seed"] == 17)
    assert seed17["E0"]["hold_violations"] == 1
    assert seed17["E0"]["worst_hold_slack_ns"] < 0


def test_final_artifacts_match_registered_hashes():
    multi = load("MULTISEED_DRV_STATUS.json")
    for pair in multi["seeds"]:
        for design, flow in (("U0", "attempt08_u0"), ("E0", "attempt08_e0")):
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


def test_constraints_are_unrelaxed_and_common():
    for design in ("u0", "e0"):
        sdc = (ROOT / f"openroad/{design}/constraint.sdc").read_text(encoding="utf-8")
        assert "create_clock -name core_clk -period 10.0" in sdc
        assert "set_clock_uncertainty 0.10" in sdc
        assert "set_max_transition 0.60 [current_design]" in sdc
    repair = (ROOT / "openroad/pre_global_route_drv_repair.tcl").read_text(encoding="utf-8")
    assert "set_max_transition" not in repair
    assert "constraints_relaxed=0" in repair


def test_preserved_hard_macro_and_power_limits():
    status = load("ATTEMPT08_STATUS.json")
    assert status["sram_internal_drc_disposition"] == "MACRO_INTERNAL_DRC_NOT_INDEPENDENTLY_SIGNOFF_QUALIFIED"
    assert status["physical_lvs"] == "NOT_INDEPENDENTLY_REPRODUCED"
    assert status["power_evidence_level"] == "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE"
    assert status["energy_per_access"] == "NOT_QUALIFIED"
