"""Canonical schema helpers with backward-compatible aliases.

This module centralizes semantic field names used across ECC selection,
energy/carbon scoring, telemetry parsing, and ML advisory outputs.

The canonical schema is additive-only: existing field names remain valid via
aliases so external callers and CLI outputs stay backward compatible.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Mapping, Any


CANONICAL_FIELDS: tuple[str, ...] = (
    "code",
    "ber",
    "uwer",
    "parity_bits",
    "correction_capability",
    "fit",
    "fit_base",
    "fit_word_post",
    "esii",
    "nesii",
    "green_score",
    "energy_dynamic_kwh",
    "energy_leakage_kwh",
    "energy_scrub_kwh",
    "energy_total_j",
    "carbon_embodied_kgco2e",
    "carbon_operational_kgco2e",
    "carbon_total_kgco2e",
    "confidence",
    "confidence_threshold",
    "ood_score",
    "ood_threshold",
)


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "fit": ("FIT",),
    "fit_base": ("fit_base",),
    "fit_word_post": ("fit_word_post",),
    "esii": ("ESII",),
    "nesii": ("NESII",),
    "green_score": ("GS", "GREEN_score", "green_score"),
    "energy_dynamic_kwh": ("E_dyn_kWh", "energy_kWh"),
    "energy_leakage_kwh": ("E_leak_kWh",),
    "energy_scrub_kwh": ("E_scrub_kWh",),
    "energy_total_j": ("total_J", "total_energy_j", "energy_j", "total_J"),
    "carbon_embodied_kgco2e": (
        "embodied_kgCO2e",
        "embodied_kgco2e",
        "static_carbon_kgco2e",
    ),
    "carbon_operational_kgco2e": (
        "operational_kgCO2e",
        "operational_kgco2e",
        "dynamic_carbon_kgco2e",
    ),
    "carbon_total_kgco2e": (
        "total_kgCO2e",
        "total_kgco2e",
        "total_carbon_kgco2e",
        "carbon_kg",
    ),
    "confidence": ("confidence", "confidence_score", "advisory_confidence"),
    "confidence_threshold": ("confidence_threshold",),
    "ood_score": ("ood_score", "advisory_ood_score", "ood_max_abs_z"),
    "ood_threshold": ("ood_threshold",),
    "ber": ("ber", "target_ber"),
    "uwer": ("uwer", "target_uwer"),
    "parity_bits": ("parity_bits",),
    "correction_capability": ("correction_capability",),
}


TELEMETRY_FIELDS: tuple[str, ...] = (
    "workload_id",
    "node_nm",
    "vdd",
    "tempC",
    "clk_MHz",
    "xor_toggles",
    "and_toggles",
    "add_toggles",
    "corr_events",
    "words",
    "accesses",
    "scrub_s",
    "capacity_gib",
    "runtime_s",
)

SELECT_CANDIDATE_CSV_FIELDS: tuple[str, ...] = (
    "code",
    "scrub_s",
    "FIT",
    "carbon_kg",
    "latency_ns",
    "ESII",
    "NESII",
    "GS",
    "areas",
    "energies",
    "violations",
    "scenario_hash",
)

TARGET_FEASIBLE_CSV_FIELDS: tuple[str, ...] = (
    "code",
    "fit_bit",
    "fit_word_post",
    "FIT",
    "carbon_kg",
    "ESII",
    "NESII",
    "GS",
    "scrub_s",
    "area_logic_mm2",
    "area_macro_mm2",
    "E_dyn_kWh",
    "E_leak_kWh",
    "E_scrub_kWh",
)


def canonical_name(field_name: str) -> str | None:
    for canonical, aliases in FIELD_ALIASES.items():
        if field_name == canonical or field_name in aliases:
            return canonical
    return None


def get_semantic_value(mapping: Mapping[str, Any], canonical: str, default: Any = None) -> Any:
    if canonical in mapping:
        return mapping[canonical]
    for alias in FIELD_ALIASES.get(canonical, ()):  # pragma: no branch
        if alias in mapping:
            return mapping[alias]
    return default


def canonical_projection(mapping: Mapping[str, Any]) -> OrderedDict[str, Any]:
    out: OrderedDict[str, Any] = OrderedDict()
    for field in CANONICAL_FIELDS:
        value = get_semantic_value(mapping, field, None)
        if value is not None:
            out[field] = value
    return out


def infer_schema_aliases(field_names: Iterable[str]) -> dict[str, set[str]]:
    inferred: dict[str, set[str]] = {}
    for name in field_names:
        canonical = canonical_name(name)
        if canonical is None:
            continue
        inferred.setdefault(canonical, set()).add(name)
    return inferred
