import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MC = ROOT / "memory_compiler"
ATTEMPT = MC / "gate3_openram_attempt03_target_diagnosis"


REQUIRED = {
    "ATTEMPT03_STATUS.json",
    "STORAGE_PREFLIGHT.md",
    "storage_preflight.json",
    "baseline_integrity.json",
    "prior_evidence_integrity.json",
    "environment_manifest.json",
    "command_manifest.json",
    "CONFIG_DERIVATION.md",
    "config_derivation.json",
    "INTERFACE_ROOT_CAUSE.md",
    "interface_trace.json",
    "CONTROL_EXPERIMENT.md",
    "dimensional_bisection.csv",
    "DIMENSIONAL_BISECTION.md",
    "drc_rule_histogram.csv",
    "DRC_ROOT_CAUSE.md",
    "LVS_ROOT_CAUSE.md",
    "lvs_mismatch_summary.json",
    "CHARACTERIZATION_ROOT_CAUSE.md",
    "characterization_net_trace.json",
    "RECOVERY_RECOMMENDATION.md",
    "generated_artifact_manifest.json",
    "execution.log",
    "ATTEMPT03_EVIDENCE_MANIFEST.json",
}


def load(name):
    return json.loads((ATTEMPT / name).read_text(encoding="utf-8"))


def test_attempt03_required_evidence_is_complete():
    assert REQUIRED <= {path.name for path in ATTEMPT.iterdir() if path.is_file()}


def test_attempt03_is_diagnostic_only_and_gate3_gate4_boundaries_hold():
    status = load("ATTEMPT03_STATUS.json")
    gate3 = json.loads((MC / "GATE3_STATUS.json").read_text(encoding="utf-8"))

    assert status["status"] == "PASS"
    assert status["status_scope"] == "DIAGNOSTIC_OBJECTIVE_ONLY"
    assert status["scientific_macro_qualification"] == "FAIL_UNCHANGED"
    assert gate3["status"] == "FAIL"
    assert gate3["status_detail"] == (
        "OPENRAM_256X72_PHYSICAL_VERIFICATION_INTERFACE_AND_CHARACTERIZATION_FAILED"
    )
    assert status["qualified_macro_views"] == 0
    assert status["macro_artifacts_admitted"] == 0
    assert status["gate4_started"] is False
    assert status["gate4_authorized"] is False


def test_attempt03_geometry_and_interface_derivation_are_exact():
    config = load("config_derivation.json")
    interface = load("interface_trace.json")

    assert config["input"]["word_size"] == 72
    assert config["input"]["num_words"] == 256
    assert config["result"]["emitted_data_indices"] == "0..72"
    assert config["result"]["emitted_address_indices"] == "0..8"
    assert config["result"]["frozen_plain_256x72_interface_matched"] is False
    assert interface["data_interface"]["cause"] == "spare-column support"
    assert interface["address_interface"]["rows_used_for_address_width"] == 129
    assert interface["address_interface"]["bank_addr_size"] == 9
    assert interface["repair_control"]["pin"] == "spare_wen0"
    assert "scalar/vector" in interface["repair_control"]["observed_defect"]


def test_control_failure_closes_dimensional_bisection_gate():
    status = load("ATTEMPT03_STATUS.json")
    with (ATTEMPT / "dimensional_bisection.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = {row["target"]: row for row in csv.DictReader(stream)}

    assert status["control"]["classification"] == "CONTROL_FAIL"
    assert status["control"]["drc_violation_count"] == 2140
    assert status["dimensional_bisection"]["status"] == "NOT_RUN_CONTROL_FAIL"
    assert rows["control_16x8"]["execution_status"] == "RUN_CONTROL_FAIL"
    assert rows["256x8"]["execution_status"] == "NOT_RUN_CONTROL_FAIL"
    assert rows["256x64"]["execution_status"] == "NOT_RUN_CONTROL_FAIL"
    assert rows["256x72"]["execution_status"] == "NOT_RUN_CONTROL_FAIL"


def test_lvs_and_characterization_root_causes_are_structural():
    lvs = load("lvs_mismatch_summary.json")
    char = load("characterization_net_trace.json")

    assert lvs["attempt02_counts"]["device_count_delta"] == 0
    assert lvs["attempt02_counts"]["extracted_net_excess"] == 584
    assert lvs["single_fanout_error"] is False
    assert lvs["connectivity_failure_supported"] is True
    assert char["attempt02"]["decoded_row"] == 255
    assert char["attempt02"]["valid_row_range"] == "0..128"
    assert char["attempt02"]["all_bitcells_excluded"] is True
    assert char["generated_spice_names"]["expected_bl_exists_in_netlist"] is True
    assert char["generated_spice_names"][
        "expected_bl_retained_in_filtered_timing_graph"
    ] is False


def test_attempt03_evidence_manifest_hashes_all_listed_local_files():
    manifest = load("ATTEMPT03_EVIDENCE_MANIFEST.json")
    assert manifest["preserved_manifest_modified"] is False
    for artifact in manifest["artifacts"]:
        path = ATTEMPT / artifact["path"]
        assert path.is_file()
        assert path.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
