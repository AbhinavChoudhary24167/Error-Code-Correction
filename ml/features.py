"""Feature helpers used by the optional ML layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping


CORE_NUMERIC_FEATURES = [
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

CORE_CATEGORICAL_FEATURES = ["code"]

OPTIONAL_NUMERIC_FEATURES = [
    "mbu_class_idx",
    "scrub_log10_s",
    "fit_per_watt_proxy",
    "ser_slope_vdd",
    "telemetry_retry_rate",
]

OPTIONAL_FEATURE_DEFAULTS = {
    "mbu_class_idx": -1.0,
    "scrub_log10_s": 0.0,
    "fit_per_watt_proxy": 0.0,
    "ser_slope_vdd": 0.0,
    "telemetry_retry_rate": 0.0,
}

FEATURE_PACK_DEFAULTS: dict[str, tuple[str, ...]] = {
    "core": (),
    "core+telemetry": ("telemetry_retry_rate",),
    "core+telemetry+workload": tuple(OPTIONAL_NUMERIC_FEATURES),
}

CATEGORICAL_FEATURES = list(CORE_CATEGORICAL_FEATURES)
NUMERIC_FEATURES = list(CORE_NUMERIC_FEATURES)
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


def _ordered_unique(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        name = str(raw).strip()
        if not name or name in seen:
            continue
        out.append(name)
        seen.add(name)
    return out


def _normalize_optional_features(
    names: Iterable[str] | None,
    *,
    strict: bool,
) -> list[str]:
    if not names:
        return []
    normalized = _ordered_unique(names)
    unknown = [name for name in normalized if name not in OPTIONAL_NUMERIC_FEATURES]
    if unknown and strict:
        allowed = ", ".join(OPTIONAL_NUMERIC_FEATURES)
        unknown_msg = ", ".join(unknown)
        raise ValueError(f"Unknown optional feature(s): {unknown_msg}. Allowed: {allowed}")
    return [name for name in normalized if name in OPTIONAL_NUMERIC_FEATURES]


def resolve_feature_selection(
    *,
    feature_pack: str = "core",
    enable_features: Iterable[str] | None = None,
    disable_features: Iterable[str] | None = None,
    strict: bool = True,
) -> dict[str, object]:
    """Resolve optional features with precedence: pack defaults -> enable -> disable."""

    if feature_pack not in FEATURE_PACK_DEFAULTS:
        valid = ", ".join(FEATURE_PACK_DEFAULTS.keys())
        raise ValueError(f"Unknown feature_pack: {feature_pack!r}. Expected one of: {valid}")

    enabled = list(FEATURE_PACK_DEFAULTS[feature_pack])
    for name in _normalize_optional_features(enable_features, strict=strict):
        if name not in enabled:
            enabled.append(name)

    disabled = _normalize_optional_features(disable_features, strict=strict)
    disabled_set = set(disabled)
    enabled_final = [name for name in OPTIONAL_NUMERIC_FEATURES if name in enabled and name not in disabled_set]

    return {
        "feature_pack": feature_pack,
        "enabled_features": enabled_final,
        "disabled_features": disabled,
    }


def feature_lists_from_optional(enabled_optional: Iterable[str] | None) -> tuple[list[str], list[str]]:
    enabled_set = set(_normalize_optional_features(enabled_optional, strict=False))
    ordered_optional = [name for name in OPTIONAL_NUMERIC_FEATURES if name in enabled_set]
    return list(CORE_CATEGORICAL_FEATURES), list(CORE_NUMERIC_FEATURES) + ordered_optional


def resolve_dataset_feature_spec(
    dataset_dir: Path,
    *,
    dataframe_columns: Iterable[str] | None = None,
) -> dict[str, object]:
    """Resolve active feature lists from dataset_schema.json with compatibility fallback."""

    enabled_optional: list[str] = []
    feature_pack = "core"
    schema_path = dataset_dir / "dataset_schema.json"

    if schema_path.is_file():
        try:
            payload = json.loads(schema_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                feature_pack = str(payload.get("feature_pack", "core"))
                maybe_enabled = payload.get("enabled_features", [])
                if isinstance(maybe_enabled, list):
                    enabled_optional = _normalize_optional_features(maybe_enabled, strict=False)
        except Exception:
            # Keep backward-compatible defaults if schema is missing or malformed.
            enabled_optional = []
            feature_pack = "core"

    if not enabled_optional and dataframe_columns is not None:
        cols = {str(col) for col in dataframe_columns}
        enabled_optional = [name for name in OPTIONAL_NUMERIC_FEATURES if name in cols]

    categorical, numeric = feature_lists_from_optional(enabled_optional)
    return {
        "categorical": categorical,
        "numeric": numeric,
        "enabled_features": [name for name in OPTIONAL_NUMERIC_FEATURES if name in set(enabled_optional)],
        "feature_pack": feature_pack,
    }


def resolve_model_feature_spec(bundle: Mapping[str, object]) -> dict[str, list[str]]:
    """Resolve active feature lists from model bundle, fallback to core lists."""

    features = bundle.get("features", {}) if isinstance(bundle.get("features"), Mapping) else {}
    categorical = features.get("categorical", []) if isinstance(features, Mapping) else []
    numeric = features.get("numeric", []) if isinstance(features, Mapping) else []
    if isinstance(categorical, list) and isinstance(numeric, list) and categorical and numeric:
        return {"categorical": [str(v) for v in categorical], "numeric": [str(v) for v in numeric]}
    return {"categorical": list(CORE_CATEGORICAL_FEATURES), "numeric": list(CORE_NUMERIC_FEATURES)}


def _default_for_numeric_feature(name: str, defaults: Mapping[str, float]) -> float:
    if name == "node":
        return defaults["node"]
    if name == "vdd":
        return defaults["vdd"]
    if name == "temp":
        return defaults["temp"]
    if name == "capacity_gib":
        return defaults["capacity_gib"]
    if name == "ci":
        return defaults["ci"]
    if name == "bitcell_um2":
        return defaults["bitcell_um2"]
    if name == "scrub_s":
        return defaults["scrub_s"]
    if name in OPTIONAL_FEATURE_DEFAULTS:
        return float(OPTIONAL_FEATURE_DEFAULTS[name])
    return 0.0


def row_to_feature_dict(
    row: Mapping[str, object],
    scenario_defaults: Mapping[str, float] | None = None,
    *,
    categorical_features: Iterable[str] | None = None,
    numeric_features: Iterable[str] | None = None,
) -> dict[str, float | str]:
    """Return feature dict from an artifact row.

    Missing fields are filled from defaults so prediction never hard-fails.
    """

    defaults = dict(DEFAULT_SCENARIO)
    if scenario_defaults:
        defaults.update(scenario_defaults)

    categorical = list(categorical_features) if categorical_features else list(CORE_CATEGORICAL_FEATURES)
    numeric = list(numeric_features) if numeric_features else list(CORE_NUMERIC_FEATURES)

    feature: dict[str, float | str] = {}
    for key in categorical:
        if key == "code":
            feature[key] = str(row.get("code", "sec-ded-64"))
        else:
            feature[key] = str(row.get(key, ""))
    for key in numeric:
        feature[key] = as_float(row.get(key), _default_for_numeric_feature(key, defaults))
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
