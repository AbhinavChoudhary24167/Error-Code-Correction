"""Physical accounting helpers for ECC reconfiguration granularity."""

from __future__ import annotations

import math
from typing import Mapping


GRANULARITIES = {"whole_memory", "bank", "page", "word"}


def metadata_protection_factor(policy: str) -> int:
    factors = {"none": 1, "parity": 2, "triplicated": 3}
    try:
        return factors[policy]
    except KeyError as exc:
        raise ValueError(f"unsupported metadata protection policy: {policy}") from exc


def evaluate_granularity(
    *,
    granularity: str,
    total_words: int,
    active_region_fraction: float,
    mode_count: int,
    metadata_protection: str,
    bank_count: int = 8,
    page_words: int = 512,
    mux_replication_regions: int | None = None,
    physical_word_selection_credible: bool = False,
) -> dict:
    """Return logical overheads without inventing per-cell physical data."""

    if granularity not in GRANULARITIES:
        raise ValueError(f"unsupported granularity: {granularity}")
    if total_words <= 0 or mode_count <= 0 or bank_count <= 0 or page_words <= 0:
        raise ValueError("word, mode, bank, and page counts must be positive")
    if not 0 <= active_region_fraction <= 1:
        raise ValueError("active_region_fraction must be in [0, 1]")
    if granularity == "word" and not physical_word_selection_credible:
        return {
            "granularity": granularity,
            "feasible": False,
            "reason": "word-level selection requires explicit credible metadata and routing characterization",
        }
    if granularity == "whole_memory":
        regions = 1
    elif granularity == "bank":
        regions = bank_count
    elif granularity == "page":
        regions = math.ceil(total_words / page_words)
    else:
        regions = total_words
    affected_regions = max(1, math.ceil(regions * active_region_fraction))
    words_per_region = math.ceil(total_words / regions)
    migrated_words = min(total_words, affected_regions * words_per_region)
    raw_mode_bits = max(1, math.ceil(math.log2(mode_count)))
    protection_factor = metadata_protection_factor(metadata_protection)
    stored_metadata_bits = regions * raw_mode_bits * protection_factor
    replicas = (
        int(mux_replication_regions)
        if mux_replication_regions is not None
        else (1 if granularity == "whole_memory" else regions)
    )
    return {
        "granularity": granularity,
        "feasible": True,
        "regions": regions,
        "affected_regions": affected_regions,
        "words_per_region": words_per_region,
        "migrated_words": migrated_words,
        "raw_mode_bits_per_region": raw_mode_bits,
        "metadata_protection": metadata_protection,
        "metadata_protection_factor": protection_factor,
        "stored_metadata_bits": stored_metadata_bits,
        "mux_replication_regions": replicas,
        "fanout_regions": regions,
        "physical_energy_area_latency_status": "requires_characterized_per-unit inputs",
    }


def scale_transition_for_granularity(
    base: Mapping[str, object], granularity: Mapping[str, object]
) -> dict:
    if not bool(granularity.get("feasible", False)):
        return {"allowed": False, "reason": granularity.get("reason")}
    migrated_words = int(granularity["migrated_words"])
    per_word_energy = base.get("migration_energy_j_per_word")
    per_word_latency = base.get("migration_latency_s_per_word")
    control_energy = base.get("control_energy_j")
    energy = (
        migrated_words * float(per_word_energy) + float(control_energy or 0.0)
        if per_word_energy is not None and control_energy is not None
        else None
    )
    latency = (
        migrated_words * float(per_word_latency) + float(base.get("control_latency_s", 0.0))
        if per_word_latency is not None
        else None
    )
    return {
        "allowed": bool(base.get("allowed", True)),
        "migrated_words": migrated_words,
        "migration_energy_j": energy,
        "transition_latency_s": latency,
        "one_time_carbon_kgco2e": (
            float(base["one_time_carbon_kgco2e"])
            if base.get("one_time_carbon_kgco2e") is not None
            else None
        ),
        "dual_format_temporary_words": (
            migrated_words if bool(base.get("dual_format_during_migration", True)) else 0
        ),
        "characterization_status": str(base.get("characterization_status", "synthetic_sensitivity")),
    }
