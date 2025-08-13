"""Telemetry parsing and validation utilities.

This module validates telemetry CSV files against ``docs/schema/telemetry.schema.json``
and can emit normalised CSV and JSON representations.  It also exposes a helper
for computing energy per correction from validated logs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd
from jsonschema import ValidationError, validate

from energy_model import estimate_energy

# Order of fields in the canonical schema/CSV
FIELDS: list[str] = [
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
]

_INT_FIELDS: Iterable[str] = {
    "node_nm",
    "xor_toggles",
    "and_toggles",
    "add_toggles",
    "corr_events",
    "words",
    "accesses",
}
_FLOAT_FIELDS: Iterable[str] = {
    "vdd",
    "tempC",
    "clk_MHz",
    "scrub_s",
    "capacity_gib",
    "runtime_s",
}

SCHEMA_PATH = Path(__file__).resolve().parent / "docs" / "schema" / "telemetry.schema.json"


def _load_schema(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_and_validate(csv_path: str | Path, schema_path: Path | None = None) -> pd.DataFrame:
    """Load ``csv_path`` and validate each row against the JSON schema."""
    schema = _load_schema(schema_path or SCHEMA_PATH)
    df = pd.read_csv(csv_path)

    missing = set(FIELDS) - set(df.columns)
    extra = set(df.columns) - set(FIELDS)
    if missing or extra:
        raise ValueError(
            f"CSV columns mismatch. Missing: {sorted(missing)}, Extra: {sorted(extra)}"
        )

    df = df[FIELDS].copy()
    for col in _INT_FIELDS:
        df[col] = pd.to_numeric(df[col], errors="raise", downcast="integer")
    for col in _FLOAT_FIELDS:
        df[col] = pd.to_numeric(df[col], errors="raise")

    for _, row in df.iterrows():
        try:
            validate(row.to_dict(), schema)
        except ValidationError as exc:  # pragma: no cover - jsonschema tested via ValueError
            field = "/".join(str(p) for p in exc.path) or "<root>"
            raise ValueError(f"{field}: {exc.message}") from exc

    return df


def write_normalized(
    df: pd.DataFrame, csv_out: str | Path, json_out: str | Path
) -> None:
    """Write ``df`` to ``csv_out`` and ``json_out`` in canonical order."""
    df[FIELDS].to_csv(csv_out, index=False)
    df[FIELDS].to_json(json_out, orient="records", indent=2)


def compute_epc(
    csv_path: str | Path, node_nm: int | None = None, vdd: float | None = None
) -> tuple[float, float]:
    """Return total energy and energy per correction for a validated log."""
    df = load_and_validate(csv_path)
    node = int(node_nm if node_nm is not None else df["node_nm"].iloc[0])
    voltage = float(vdd if vdd is not None else df["vdd"].iloc[0])
    xor_cnt = int(df["xor_toggles"].sum())
    and_cnt = int(df["and_toggles"].sum())
    corrections = int(df["corr_events"].sum())
    if corrections <= 0:
        raise ValueError("corr_events must be positive")
    total_energy = estimate_energy(xor_cnt, and_cnt, node_nm=node, vdd=voltage)
    return total_energy, total_energy / corrections


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate telemetry CSV and emit normalised CSV and JSON"
    )
    parser.add_argument("csv", help="Input telemetry CSV path")
    parser.add_argument("--out-csv", required=True, help="Path to write normalised CSV")
    parser.add_argument("--out-json", required=True, help="Path to write JSON")
    parser.add_argument("--schema", default=str(SCHEMA_PATH), help="JSON schema path")
    args = parser.parse_args()

    df = load_and_validate(args.csv, Path(args.schema))
    write_normalized(df, args.out_csv, args.out_json)


if __name__ == "__main__":
    main()
