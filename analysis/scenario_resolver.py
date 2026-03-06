from __future__ import annotations

"""Scenario parsing and strict filtering helpers for plot generation."""

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd


SCENARIO_ALIASES: dict[str, str] = {
    "tempc": "temp",
    "temperature": "temp",
    "temperature_c": "temp",
    "scrub_interval_s": "scrub_s",
    "scrub_interval": "scrub_s",
    "scrub-s": "scrub_s",
    "capacity-gib": "capacity_gib",
    "target-ber": "target_ber",
    "energy-budget-nj": "energy_budget_nj",
    "burst-length": "burst_length",
    "required-bits": "required_bits",
    "node-nm": "node",
    "code-set": "codes",
}


KNOWN_SCENARIO_FIELDS: tuple[str, ...] = (
    "codes",
    "node",
    "vdd",
    "temp",
    "scrub_s",
    "capacity_gib",
    "target_ber",
    "burst_length",
    "required_bits",
    "sustainability",
    "energy_budget_nj",
    "carbon_kg_max",
    "fit_max",
)


FLOAT_TOLERANCES: dict[str, float] = {
    "vdd": 1e-6,
    "temp": 1e-6,
    "scrub_s": 1e-9,
    "capacity_gib": 1e-9,
    "target_ber": 1e-15,
    "energy_budget_nj": 1e-9,
    "carbon_kg_max": 1e-9,
    "fit_max": 1e-9,
    "bitcell_um2": 1e-9,
    "ci": 1e-9,
}


@dataclass(frozen=True)
class ScenarioResolution:
    requested: dict[str, Any]
    applied: dict[str, Any]
    omitted_fields: list[str]
    missing_fields: list[str]
    matched_rows: int


class ScenarioFilterError(ValueError):
    """Raised when strict scenario filtering fails."""


def _canonical_field(name: str) -> str:
    key = str(name).strip().replace("-", "_").lower()
    return SCENARIO_ALIASES.get(key, key)


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def normalise_scenario_filters(raw: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if value is None:
            continue
        canon = _canonical_field(key)
        if canon == "codes":
            if isinstance(value, str):
                codes = [v.strip() for v in value.split(",") if v.strip()]
            elif isinstance(value, (list, tuple, set)):
                codes = [str(v).strip() for v in value if str(v).strip()]
            else:
                codes = [str(value).strip()]
            out[canon] = sorted(set(codes))
            continue
        if canon in {"node", "burst_length", "required_bits"}:
            out[canon] = int(value)
            continue
        if canon in {"sustainability"}:
            out[canon] = _parse_bool(value)
            continue
        if canon in {
            "vdd",
            "temp",
            "scrub_s",
            "capacity_gib",
            "target_ber",
            "energy_budget_nj",
            "carbon_kg_max",
            "fit_max",
            "ci",
            "bitcell_um2",
            "alt_km",
            "latitude_deg",
            "flux_rel",
            "lifetime_h",
        }:
            out[canon] = float(value)
            continue
        out[canon] = value
    return out


def _is_numeric_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _value_mask(series: pd.Series, value: Any, field: str) -> pd.Series:
    if _is_numeric_value(value):
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.isna().all():
            return pd.Series([False] * len(series), index=series.index)
        tol = FLOAT_TOLERANCES.get(field, 0.0)
        return (numeric - float(value)).abs() <= tol
    if isinstance(value, bool):
        lowered = series.astype(str).str.strip().str.lower()
        expected = "true" if value else "false"
        return lowered.isin({expected, "1" if value else "0"})
    target = str(value).strip().lower()
    return series.astype(str).str.strip().str.lower() == target


def _miss_detail(df: pd.DataFrame, applied: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for field, value in applied.items():
        col = "code" if field == "codes" else field
        if col not in df.columns:
            continue
        if field == "codes":
            hits = int(df[col].isin(set(value)).sum())
        else:
            hits = int(_value_mask(df[col], value, field).sum())
        parts.append(f"{field}={value!r} matched {hits}/{len(df)} rows")
    return "; ".join(parts)


def filter_by_scenario(
    df: pd.DataFrame,
    filters: Mapping[str, Any],
    *,
    strict: bool,
    error_on_empty: bool,
) -> tuple[pd.DataFrame, ScenarioResolution]:
    """Apply exact/tolerance-based scenario filters to a data frame."""

    requested = normalise_scenario_filters(filters)
    mask = pd.Series([True] * len(df), index=df.index)
    applied: dict[str, Any] = {}
    missing_fields: list[str] = []

    for field in sorted(requested):
        value = requested[field]
        if field == "codes":
            if "code" not in df.columns:
                missing_fields.append("code")
                continue
            mask &= df["code"].isin(set(value))
            applied[field] = value
            continue

        if field not in df.columns:
            missing_fields.append(field)
            continue

        mask &= _value_mask(df[field], value, field)
        applied[field] = value

    if strict and missing_fields:
        missing = ", ".join(sorted(set(missing_fields)))
        raise ScenarioFilterError(
            f"Scenario fields not available in dataset: {missing}. "
            "Provide source artifacts with these fields or relax strict scenario filtering."
        )

    filtered = df[mask].copy()
    omitted = [f for f in KNOWN_SCENARIO_FIELDS if f not in requested]
    resolution = ScenarioResolution(
        requested=requested,
        applied=applied,
        omitted_fields=omitted,
        missing_fields=sorted(set(missing_fields)),
        matched_rows=int(len(filtered)),
    )

    if error_on_empty and filtered.empty:
        detail = _miss_detail(df, applied)
        raise ScenarioFilterError(
            "No rows matched the requested scenario. "
            f"Applied filters: {applied}. "
            f"Details: {detail if detail else 'no evaluable filters'}"
        )

    return filtered, resolution


__all__ = [
    "FLOAT_TOLERANCES",
    "KNOWN_SCENARIO_FIELDS",
    "SCENARIO_ALIASES",
    "ScenarioFilterError",
    "ScenarioResolution",
    "filter_by_scenario",
    "normalise_scenario_filters",
]
