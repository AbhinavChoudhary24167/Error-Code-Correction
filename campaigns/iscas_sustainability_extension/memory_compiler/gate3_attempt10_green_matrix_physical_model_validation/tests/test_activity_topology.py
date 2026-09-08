from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import pytest

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "scripts"))
from activity_energy import FAMILIES, ROOT, codec, inspect_vcd, sha, workload
from topology_reliability import outcome, persistent_sequence, proposal_location, validate_geometry


def test_trace_reproducibility_and_fault_domains():
    for family in FAMILIES:
        assert workload(family, 64, 11) == workload(family, 64, 11)
        assert workload(family, 64, 11) != workload(family, 64, 13)
        for step in workload(family):
            assert not step["logical_payload_fault_bits"] or step["operation"] == "READ"
            assert len(set(step["logical_payload_fault_bits"])) == len(step["logical_payload_fault_bits"])
    assert {s["operation"] for s in workload("idle_leakage_dominated")} == {"IDLE"}


def test_retained_activity_window_scope_counts_and_qualification():
    manifest = json.loads((CAMPAIGN / "energy/WORKLOAD_MANIFEST.json").read_text())
    assert len(manifest["workloads"]) == 8
    for spec in manifest["workloads"]:
        assert sha(CAMPAIGN / spec["trace_file"]) == spec["trace_sha256"]
        for arch in ("U0", "E0"):
            activity = spec["activity"][arch]
            parsed = inspect_vcd(CAMPAIGN / activity["file"])
            assert parsed["unknown_value_events"] == 0
            assert parsed["window_ticks"] == spec["cycles"] * spec["clock_period_ns"] * 1000
            assert parsed["sha256"] == activity["sha256"]
            assert parsed["scope_check_pass"]
    rows = json.loads((CAMPAIGN / "energy/ENERGY_RESULTS.json").read_text())["rows"]
    assert len(rows) == 16
    assert all(r["energy_access_j"] == "NOT_QUALIFIED" for r in rows)


def test_exact_sbu_dbu_controls_and_miscorrection_detection():
    adapter = codec()
    for bit in range(72):
        assert outcome(adapter, 1234, 1 << bit, "E0")["outcome"] == "CORRECTED"
    for left in range(72):
        for right in range(left + 1, 72):
            assert outcome(adapter, 1234, (1 << left) | (1 << right), "E0")["outcome"] == "DUE"
    miscorr = outcome(adapter, 1234, 7, "E0")
    assert miscorr["correction_flag"] and miscorr["outcome"] == "SDC"


def test_scrub_uses_decoder_flag_and_cannot_undo_due():
    adapter = codec()
    no_scrub = persistent_sequence(adapter, "E0", [1, 2], "none")
    scrub = persistent_sequence(adapter, "E0", [1, 2], "scrub_on_correct")
    assert no_scrub[-1]["outcome"] == "DUE"
    assert [r["outcome"] for r in scrub] == ["CORRECTED", "CORRECTED"]
    mistaken = persistent_sequence(adapter, "E0", [7, 0], "scrub_on_correct")
    assert mistaken[0]["outcome"] == "SDC" and mistaken[0]["scrub_writeback"]
    assert mistaken[1]["outcome"] == "SDC"


def test_bank_proposal_bijections_and_pin_bounds():
    for mid in ("I0", "I1", "I2"):
        locations = set()
        for word in range(256):
            for bit in range(72):
                loc = proposal_location(mid, word, bit)
                identity = tuple(loc[k] for k in ("macro_kind", "bank", "macro_address", "macro_data_pin"))
                assert identity not in locations
                locations.add(identity)
                assert 0 <= loc["macro_data_pin"] < (64 if bit < 64 else 8)
        assert len(locations) == 256 * 72


def test_geometry_rejects_unproven_stale_duplicate_or_incomplete_map():
    with pytest.raises(ValueError, match="extracted"):
        validate_geometry({"units": "um", "evidence_level": "PROPOSAL"})
    source = "AGENTS.md"
    geometry = {"units": "um", "evidence_level": "EXTRACTED_BITCELL_ADDRESS_MAP", "stored_bits": 72,
                "placement_source": source, "bitcell_source": source, "address_mapping_source": source,
                "source_provenance": {source: sha(ROOT / source)},
                "cells": [{"bitcell_id": "test_fixture_only", "gds_instance_path": "test_fixture_only", "macro_instance": "m",
                           "bank": 0, "word_address": 0, "codeword_bit": 0, "x_um": 0, "y_um": 0}]}
    with pytest.raises(ValueError, match="full memory"):
        validate_geometry(geometry)
    assert len(validate_geometry(geometry, require_complete=False)) == 1
    duplicate = copy.deepcopy(geometry)
    duplicate["cells"].append(copy.deepcopy(duplicate["cells"][0]))
    with pytest.raises(ValueError, match="non-bijective"):
        validate_geometry(duplicate, require_complete=False)
    geometry["source_provenance"][source] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        validate_geometry(geometry, require_complete=False)


def test_no_physical_reliability_promotion():
    records = json.loads((CAMPAIGN / "green_matrix/GREEN_MATRIX_RELIABILITY.json").read_text())["rows"]
    assert len(records) == 72
    assert all(row["MBU_coverage"] == "NOT_QUALIFIED" for row in records)
    mapping = json.loads((CAMPAIGN / "interleaving/MBU_TO_CODEWORD_MAPPING.json").read_text())
    assert not mapping["physical_coverage_qualified"]
    assert mapping["physical_records"] == []


def test_partial_power_annotation_stays_unqualified():
    result = json.loads((CAMPAIGN / "energy/POSTROUTE_ACTIVITY_DIAGNOSTIC.json").read_text())
    for row in result["rows"]:
        assert row["unannotated_pin_count"] > 0
        assert row["energy_access_j"] == "NOT_QUALIFIED"
        assert 0 < row["annotated_pin_fraction"] < 1
        assert row["liberty_model"] == "UPSTREAM_ORIGINAL"
