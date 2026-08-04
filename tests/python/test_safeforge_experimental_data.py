import csv

import pytest

from codeforge.experimental_data import REQUIRED_COLUMNS, ingest_fault_map_csv, leave_one_group_out_splits


def _campaign():
    return {
        "schema_version": 1,
        "campaign_id": "campaign-a",
        "evidence_level": "A_raw_bit_exact_experimental",
        "bit_width": 72,
        "word_mapping": {
            "physical_to_logical_map_source": "map.csv",
            "interleaving": "none",
            "word_address_definition": "72-bit row",
        },
        "experiment": {
            "device": "device",
            "memory": "BRAM",
            "procedure": "write-read-compare",
            "repeated_trials": 3,
            "event_association_rule": "one read",
        },
        "licensing": {
            "data_owner": "test",
            "license": "CC0-1.0",
            "redistribution_allowed": True,
        },
    }


def _write(path):
    rows = []
    for trial, device, event, bits in [
        ("t1", "d1", "e1", [1, 2]),
        ("t2", "d2", "e2", [3]),
        ("t3", "d1", "e3", [1, 2]),
    ]:
        for bit in bits:
            row = {name: "0" for name in REQUIRED_COLUMNS}
            row.update(
                {
                    "campaign_id": "campaign-a",
                    "trial_id": trial,
                    "event_id": event,
                    "device_id": device,
                    "source_group": "v1" if device == "d1" else "v2",
                    "independence_group": device,
                    "timestamp_utc": "2026-01-01T00:00:00Z",
                    "memory_kind": "BRAM",
                    "technology_nm": "16",
                    "voltage_v": "0.7",
                    "temperature_c": "25",
                    "radiation_source": "none",
                    "word_address": "0x1",
                    "physical_bit": str(bit),
                    "logical_bit": str(bit),
                    "expected_value": "0",
                    "observed_value": "1",
                    "repetition": "1",
                }
            )
            rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_raw_adapter_hashes_vectors_and_builds_empirical_pmf(tmp_path):
    source = tmp_path / "faults.csv"
    _write(source)
    package = ingest_fault_map_csv(source, _campaign())
    assert package["manifest"]["event_word_sample_count"] == 3
    probabilities = sorted(item["probability"] for item in package["fault_distribution"]["patterns"])
    assert probabilities == pytest.approx([1 / 3, 2 / 3])
    splits = leave_one_group_out_splits(package["injection_vectors"], field="device_id")
    assert len(splits) == 2
    assert all(not item["retuning_allowed"] for item in splits)


def test_raw_adapter_rejects_aggregate_evidence(tmp_path):
    source = tmp_path / "faults.csv"
    _write(source)
    campaign = _campaign()
    campaign["evidence_level"] = "C_literature_aggregate"
    with pytest.raises(ValueError, match="evidence_level"):
        ingest_fault_map_csv(source, campaign)
