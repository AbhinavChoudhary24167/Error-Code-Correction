from __future__ import annotations

import csv
import json
from pathlib import Path


CAMPAIGN = Path(__file__).resolve().parents[1]


def load_json(name: str) -> dict:
    return json.loads((CAMPAIGN / name).read_text(encoding="utf-8"))


def load_results() -> list[dict[str, str]]:
    with (CAMPAIGN / "baseline_results.csv").open(
        "r", encoding="utf-8", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


def test_gate0_status_and_protected_scope() -> None:
    status = load_json("GATE0_STATUS.json")
    manifest = load_json("baseline_integrity_manifest.json")
    integrity = load_json("GATE0_INTEGRITY_CHECK.json")
    assert status["status"] == "PASS"
    assert status["baseline_commit"] == manifest["baseline_commit"]
    assert manifest["repository"]["file_count"] == 2327
    assert manifest["external_evidence"]["date2027_revision2_raw"]["file_count"] == 2366
    assert manifest["external_evidence"]["date2027_breadth_raw"]["file_count"] == 2401
    assert status["protected_file_count"] == 7094
    assert integrity["status"] == "PASS"
    assert all(scope["status"] == "PASS" for scope in integrity["scopes"].values())


def test_all_reconstructed_claims_match_qualified_sources() -> None:
    provenance = load_json("baseline_provenance.json")
    assert provenance["status"] == "PASS"
    assert len(provenance["reconstruction_checks"]) == 13
    assert all(row["status"] == "PASS" for row in provenance["reconstruction_checks"])
    assert all(row["source_absolute_error"] <= 1e-9 for row in provenance["reconstruction_checks"])


def test_run_records_are_complete_and_missing_bch_power_is_explicit() -> None:
    rows = load_results()
    assert len(rows) == 40
    required = (
        "rtl_sha256",
        "formal_evidence",
        "raw_artifact_root",
        "raw_artifacts_manifest_sha256",
        "final_odb_sha256",
        "final_netlist_sha256",
        "final_sdc_sha256",
        "final_spef_sha256",
    )
    assert all(all(row[field] for field in required) for row in rows)
    bch = [row for row in rows if row["architecture"] == "bch78"]
    assert len(bch) == 5
    assert all(row["target_feasible"] == "False" for row in bch)
    assert all(not row["total_power_w"] and not row["energy_per_useful_op_pj"] for row in bch)
    assert all("TIMING_INELIGIBLE" in row["activity_power_status"] for row in bch)


def test_activity_evidence_boundary_is_not_overstated() -> None:
    activity = load_json("baseline_provenance.json")["activity_evidence"]
    assert activity["trace_count"] == 9
    assert activity["post_route_power_measured_classes"] == ["no_error"]
    assert activity["available_but_not_power_measured_classes"] == [
        "single_error",
        "double_error",
    ]
    assert {row["useful_operations"] for row in activity["traces"]} == {100000}


def test_sram_and_interleaving_gaps_are_precise() -> None:
    sram = load_json("baseline_provenance.json")["sram_infrastructure"]
    assert sram["logical_intra_word_placement_candidates_present"] is True
    assert sram["physical_cross_codeword_bit_interleaving_model_present"] is False
    assert sram["sram_macro_lef_gds_liberty_spice_views_present"] is False
    assert sram["openram_installed"] is False
