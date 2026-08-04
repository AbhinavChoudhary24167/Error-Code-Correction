"""Strict adapter for raw bit-exact SRAM/BRAM campaign CSV files."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .confidence import pattern_intervals, simultaneous_category_intervals


REQUIRED_COLUMNS = (
    "campaign_id",
    "trial_id",
    "event_id",
    "device_id",
    "source_group",
    "independence_group",
    "timestamp_utc",
    "memory_kind",
    "technology_nm",
    "voltage_v",
    "temperature_c",
    "radiation_source",
    "fluence_cm2",
    "word_address",
    "physical_x",
    "physical_y",
    "physical_bit",
    "logical_bit",
    "expected_value",
    "observed_value",
    "repetition",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def ingest_fault_map_csv(
    path: str | Path,
    campaign: Mapping[str, Any],
    *,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Validate raw flip rows and create replay vectors plus a conditional PMF."""

    source = Path(path)
    if str(campaign.get("evidence_level")) != "A_raw_bit_exact_experimental":
        raise ValueError("raw adapter requires evidence_level=A_raw_bit_exact_experimental")
    required_sections = {
        "word_mapping": ("physical_to_logical_map_source", "interleaving", "word_address_definition"),
        "experiment": ("device", "memory", "procedure", "repeated_trials", "event_association_rule"),
        "licensing": ("data_owner", "license", "redistribution_allowed"),
    }
    for section, keys in required_sections.items():
        values = campaign.get(section)
        if not isinstance(values, Mapping):
            raise ValueError(f"campaign manifest requires object {section}")
        missing = [key for key in keys if key not in values]
        if missing:
            raise ValueError(f"campaign {section} is missing: {', '.join(missing)}")
    bit_width = int(campaign["bit_width"])
    if bit_width <= 0:
        raise ValueError("campaign bit_width must be positive")
    rows: list[dict[str, str]] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"fault-map CSV is missing columns: {', '.join(missing)}")
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError("fault-map CSV contains no upset rows")
    campaign_ids = {row["campaign_id"] for row in rows}
    if campaign_ids != {str(campaign["campaign_id"])}:
        raise ValueError("CSV campaign_id differs from campaign manifest")

    events: dict[tuple[str, str, str], dict[str, Any]] = {}
    seen_cells: set[tuple[str, str, str, int]] = set()
    for row_number, row in enumerate(rows, start=2):
        logical = int(row["logical_bit"])
        if not 0 <= logical < bit_width:
            raise ValueError(f"row {row_number}: logical_bit is outside [0,{bit_width})")
        expected, observed = int(row["expected_value"]), int(row["observed_value"])
        if expected not in (0, 1) or observed not in (0, 1) or expected == observed:
            raise ValueError(f"row {row_number}: expected/observed must describe a bit flip")
        key = (row["trial_id"], row["event_id"], row["word_address"])
        cell_key = (*key, logical)
        if cell_key in seen_cells:
            raise ValueError(f"row {row_number}: duplicate logical bit within event/word")
        seen_cells.add(cell_key)
        record = events.setdefault(
            key,
            {
                "trial_id": row["trial_id"],
                "event_id": row["event_id"],
                "word_address": row["word_address"],
                "device_id": row["device_id"],
                "source_group": row["source_group"],
                "independence_group": row["independence_group"],
                "voltage_v": float(row["voltage_v"]),
                "temperature_c": float(row["temperature_c"]),
                "radiation_source": row["radiation_source"],
                "repetition": int(row["repetition"]),
                "positions": [],
                "physical_coordinates": [],
            },
        )
        stable_fields = ("device_id", "source_group", "independence_group", "radiation_source")
        if any(str(record[name]) != row[name] for name in stable_fields):
            raise ValueError(f"row {row_number}: event metadata changes within an event/word")
        record["positions"].append(logical)
        record["physical_coordinates"].append(
            {
                "x": int(row["physical_x"]),
                "y": int(row["physical_y"]),
                "physical_bit": int(row["physical_bit"]),
                "logical_bit": logical,
            }
        )

    replay = []
    pattern_counts: Counter[tuple[int, ...]] = Counter()
    for index, record in enumerate(events.values()):
        positions = tuple(sorted(int(value) for value in record.pop("positions")))
        pattern_counts[positions] += 1
        replay.append(
            {
                "vector_id": f"{campaign['campaign_id']}-event-{index:06d}",
                **record,
                "positions": list(positions),
                "error_mask_hex": hex(sum(1 << position for position in positions)),
            }
        )
    sample_count = len(replay)
    patterns = []
    pattern_id_by_positions: dict[tuple[int, ...], str] = {}
    for index, (positions, count) in enumerate(sorted(pattern_counts.items())):
        pattern_id = f"{campaign['campaign_id']}-pattern-{index:05d}"
        pattern_id_by_positions[positions] = pattern_id
        patterns.append(
            {
                "pattern_id": pattern_id,
                "positions": list(positions),
                "probability": count / sample_count,
                "family": f"measured_weight_{len(positions)}",
                "metadata": {"event_count": count, "evidence_level": campaign["evidence_level"]},
            }
        )
    pattern_count_report = {
        pattern_id_by_positions[positions]: count for positions, count in pattern_counts.items()
    }
    multiplicity_counts = Counter(str(len(tuple(item["positions"]))) for item in replay)
    confidence_report = simultaneous_category_intervals(
        {"multiplicity": multiplicity_counts}, sample_count=sample_count, confidence=confidence
    )
    confidence_report["bit_exact_patterns"] = pattern_intervals(
        pattern_count_report, sample_count=sample_count, confidence=confidence
    )
    distribution = {
        "schema_version": 1,
        "distribution_id": f"{campaign['campaign_id']}-conditional-pmf-v1",
        "bit_width": bit_width,
        "raw_fit": None,
        "provenance": {
            "kind": "measured",
            "description": "Empirical conditional PMF from validated raw bit-exact event rows.",
            "source": str(source),
            "derivation": "Group trial_id,event_id,word_address; aggregate identical logical-bit vectors.",
            "seed": None,
            "evidence_level": campaign["evidence_level"],
        },
        "normalization": {"kind": "conditional_on_recorded_nonzero_word_event", "sample_count": sample_count},
        "patterns": patterns,
    }
    manifest = {
        "schema_version": 1,
        "campaign": dict(campaign),
        "input_csv": str(source),
        "input_csv_sha256": _sha256(source),
        "row_count": len(rows),
        "event_word_sample_count": sample_count,
        "device_ids": sorted({item["device_id"] for item in replay}),
        "source_groups": sorted({item["source_group"] for item in replay}),
        "independence_groups": sorted({item["independence_group"] for item in replay}),
        "distribution_sha256": _canonical_hash(distribution),
        "replay_vectors_sha256": _canonical_hash(replay),
        "tail_status": "not_estimated_by_conditional_nonzero_event_adapter",
    }
    manifest["manifest_sha256"] = _canonical_hash(manifest)
    return {
        "manifest": manifest,
        "fault_distribution": distribution,
        "injection_vectors": replay,
        "confidence": confidence_report,
    }


def leave_one_group_out_splits(
    injection_vectors: Sequence[Mapping[str, Any]], *, field: str
) -> list[dict[str, Any]]:
    groups = sorted({str(item[field]) for item in injection_vectors})
    if len(groups) < 2:
        raise ValueError(f"leave-one-{field}-out requires at least two groups")
    return [
        {
            "split_id": f"holdout-{field}-{group}",
            "held_out_group": group,
            "train_vector_ids": [
                str(item["vector_id"]) for item in injection_vectors if str(item[field]) != group
            ],
            "test_vector_ids": [
                str(item["vector_id"]) for item in injection_vectors if str(item[field]) == group
            ],
            "retuning_allowed": False,
        }
        for group in groups
    ]


def write_campaign_package(package: Mapping[str, Any], outdir: str | Path) -> None:
    output = Path(outdir)
    output.mkdir(parents=True, exist_ok=True)
    for name in ("manifest", "fault_distribution", "injection_vectors", "confidence"):
        (output / f"{name}.json").write_text(
            json.dumps(package[name], indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
