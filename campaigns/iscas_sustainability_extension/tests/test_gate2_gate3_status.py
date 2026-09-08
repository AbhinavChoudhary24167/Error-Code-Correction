import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MC = ROOT / "memory_compiler"


def test_gate2_matrix_is_field_complete_and_explicit():
    with (MC / "memory_compiler_matrix.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) >= 4
    required = {
        "name",
        "repository_project",
        "license",
        "maintenance_status",
        "supported_pdks",
        "supported_depths",
        "supported_word_widths",
        "banking_support",
        "muxing_support",
        "generated_lef",
        "generated_gds",
        "generated_liberty",
        "generated_spice",
        "generated_verilog",
        "characterization_support",
        "read_write_timing_support",
        "leakage_support",
        "read_write_energy_support",
        "openroad_compatibility",
        "opensta_compatibility",
        "reproducibility",
        "installation_complexity",
        "known_limitations",
        "comparability_to_date_sky130hd",
        "gate2_disposition",
    }
    assert required <= set(rows[0])
    assert all(all(row[field].strip() for field in required) for row in rows)


def test_gate2_selects_one_primary_without_admitting_false_comparison():
    status = json.loads((MC / "GATE2_STATUS.json").read_text(encoding="utf-8"))
    assert status["status"] == "CONDITIONAL_PASS"
    assert status["primary_candidate"]["name"] == "OpenRAM"
    assert status["numerical_cross_compiler_comparison_admitted"] is False
    assert status["gate3_first_attempt"]["stored_word_bits"] == 72


def test_gate3_preserves_attempt01_and_records_attempt02_scientific_failure():
    status = json.loads((MC / "GATE3_STATUS.json").read_text(encoding="utf-8"))
    assert status["status"] == "FAIL"
    assert (
        status["status_detail"]
        == "OPENRAM_256X72_PHYSICAL_VERIFICATION_INTERFACE_AND_CHARACTERIZATION_FAILED"
    )
    attempts = {row["attempt"]: row for row in status["attempt_history"]}
    assert attempts["attempt01_toolchain_setup"]["status"] == "NOT_ASSESSABLE"
    assert (
        attempts["attempt01_toolchain_setup"]["status_detail"]
        == "INFRASTRUCTURE_BLOCKED_STORAGE_UNSAFE"
    )
    assert attempts["gate3_openram_attempt02"]["status"] == "FAIL"
    assert status["scientific_measurements_produced"] == 0
    assert status["macro_artifacts_admitted"] == 0
    assert status["downstream_numeric_propagation_allowed"] is False
    assert status["gate4_authorized"] is False
    assert status["protected_integrity"]["status"] == "PASS"
    assert status["protected_integrity"]["protected_file_count"] == 7094


def test_gate3_attempt02_failure_is_complete_and_non_infrastructural():
    attempt = json.loads(
        (MC / "gate3_openram_attempt02" / "GATE3_ATTEMPT02_STATUS.json").read_text(
            encoding="utf-8"
        )
    )
    assert attempt["status"] == "FAIL"
    assert attempt["infrastructure_failure"] is False
    assert attempt["target"]["num_words"] == 256
    assert attempt["target"]["logical_data_bits"] == 72
    assert attempt["qualification"]["storage_environment"] == "PASS"
    assert attempt["qualification"]["reproducible_installation"] == "PASS"
    assert attempt["qualification"]["drc"] == "FAIL"
    assert attempt["qualification"]["drc_violation_count"] == 223312
    assert attempt["qualification"]["lvs"] == "FAIL"
    assert attempt["qualification"]["spice_characterization"] == "FAIL"
    assert attempt["qualified_macro_views"] == 0
    assert attempt["macro_artifacts_admitted"] == 0
    assert attempt["gate4_authorized"] is False


def test_gate3_attempt02_view_and_artifact_boundaries_are_explicit():
    root = MC / "gate3_openram_attempt02"
    views = json.loads((root / "view_consistency.json").read_text(encoding="utf-8"))
    artifacts = json.loads(
        (root / "generated_artifact_manifest.json").read_text(encoding="utf-8")
    )

    assert views["status"] == "FAIL"
    assert views["observed_interfaces"]["spice"]["logical_header_data_bits"] == 72
    assert views["observed_interfaces"]["spice"]["data_input_indices"] == "0..72"
    assert views["observed_interfaces"]["spice"]["address_indices"] == "0..8"
    assert views["downstream_interface_frozen"] is False

    assert artifacts["view_availability"] == {
        "gds": "AVAILABLE_UNQUALIFIED",
        "spice": "AVAILABLE_UNQUALIFIED",
        "lef": "UNAVAILABLE",
        "liberty": "UNAVAILABLE",
        "verilog": "UNAVAILABLE",
    }
    assert artifacts["qualified_macro_views"] == 0
    assert artifacts["macro_artifacts_admitted"] == 0
    assert all(len(row["sha256"]) == 64 for row in artifacts["artifacts"])
