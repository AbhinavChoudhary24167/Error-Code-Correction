"""Feature helpers used by the optional ML layer."""

from __future__ import annotations

from typing import Mapping


NUMERIC_FEATURES = [
    "node",
    "vdd",
    "temp",
    "capacity_gib",
    "ci",
    "bitcell_um2",
    "scrub_s",
    "latency_ns",
    "area_logic_mm2",
    "area_macro_mm2",
]

CATEGORICAL_FEATURES = ["code"]

FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES

TARGET_COLUMNS = ["fit_true", "carbon_true", "energy_true", "label_code"]


DEFAULT_SCENARIO = {
    "node": 14.0,
    "vdd": 0.8,
    "temp": 75.0,
    "capacity_gib": 8.0,
    "ci": 0.55,
    "bitcell_um2": 0.04,
    "scrub_s": 10.0,
}


def as_float(value: object, default: float) -> float:
    """Coerce value to float with a deterministic default."""

    if value is None:
        return default
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def row_to_feature_dict(
    row: Mapping[str, object], scenario_defaults: Mapping[str, float] | None = None
) -> dict[str, float | str]:
    """Return feature dict from an artifact row.

    Missing fields are filled from defaults so prediction never hard-fails.
    """

    defaults = dict(DEFAULT_SCENARIO)
    if scenario_defaults:
        defaults.update(scenario_defaults)

    feature = {
        "code": str(row.get("code", "sec-ded-64")),
        "node": as_float(row.get("node"), defaults["node"]),
        "vdd": as_float(row.get("vdd"), defaults["vdd"]),
        "temp": as_float(row.get("temp"), defaults["temp"]),
        "capacity_gib": as_float(row.get("capacity_gib"), defaults["capacity_gib"]),
        "ci": as_float(row.get("ci"), defaults["ci"]),
        "bitcell_um2": as_float(row.get("bitcell_um2"), defaults["bitcell_um2"]),
        "scrub_s": as_float(row.get("scrub_s"), defaults["scrub_s"]),
        "latency_ns": as_float(row.get("latency_ns"), 0.0),
        "area_logic_mm2": as_float(row.get("area_logic_mm2"), 0.0),
        "area_macro_mm2": as_float(row.get("area_macro_mm2"), 0.0),
    }
    return feature


def row_targets(row: Mapping[str, object]) -> dict[str, float]:
    """Extract supervised targets from a row."""

    e_dyn = as_float(row.get("E_dyn_kWh"), 0.0)
    e_leak = as_float(row.get("E_leak_kWh"), 0.0)
    e_scrub = as_float(row.get("E_scrub_kWh"), 0.0)
    return {
        "fit_true": as_float(row.get("FIT"), 0.0),
        "carbon_true": as_float(row.get("carbon_kg"), 0.0),
        "energy_true": e_dyn + e_leak + e_scrub,
    }


def with_training_columns(
    row: Mapping[str, object], scenario_defaults: Mapping[str, float] | None = None
) -> dict[str, object]:
    """Merge features and targets into one training row."""

    out: dict[str, object] = {}
    out.update(row_to_feature_dict(row, scenario_defaults=scenario_defaults))
    out.update(row_targets(row))
    out["scenario_hash"] = str(row.get("scenario_hash", "unknown"))
    return out
