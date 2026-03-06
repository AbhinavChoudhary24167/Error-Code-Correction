"""Dataset construction for optional ECC ML models."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .features import FEATURE_COLUMNS, TARGET_COLUMNS, DEFAULT_SCENARIO, with_training_columns


LABEL_POLICIES = {"carbon_min", "fit_min", "energy_min", "utility_balanced"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit(repo_root: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _iter_csv_rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield dict(row)


def _canonical_row(raw: dict[str, str], source_kind: str) -> dict[str, object]:
    """Map known aliases into canonical training columns."""

    def pick(*keys: str, default: str | None = None) -> str | None:
        for key in keys:
            if key in raw and raw[key] not in ("", None):
                return raw[key]
            low = key.lower()
            for rk, rv in raw.items():
                if rk.lower() == low and rv not in ("", None):
                    return rv
        return default

    row: dict[str, object] = {
        "code": pick("code", "ecc", default="sec-ded-64"),
        "FIT": pick("FIT", "fit", "fit_system", default="0"),
        "carbon_kg": pick("carbon_kg", "carbon", default="0"),
        "E_dyn_kWh": pick("E_dyn_kWh", "dynamic_kwh", default="0"),
        "E_leak_kWh": pick("E_leak_kWh", "leakage_kwh", default="0"),
        "E_scrub_kWh": pick("E_scrub_kWh", "scrub_energy_kwh", default="0"),
        "scrub_s": pick("scrub_s", "scrub_interval_s", default=str(DEFAULT_SCENARIO["scrub_s"])),
        "latency_ns": pick("latency_ns", default="0"),
        "area_logic_mm2": pick("area_logic_mm2", "logic_mm2", default="0"),
        "area_macro_mm2": pick("area_macro_mm2", "macro_mm2", default="0"),
        "node": pick("node", "node_nm", default=str(DEFAULT_SCENARIO["node"])),
        "vdd": pick("vdd", default=str(DEFAULT_SCENARIO["vdd"])),
        "temp": pick("temp", "tempC", default=str(DEFAULT_SCENARIO["temp"])),
        "capacity_gib": pick("capacity_gib", default=str(DEFAULT_SCENARIO["capacity_gib"])),
        "ci": pick("ci", "ci_kg_per_kwh", default=str(DEFAULT_SCENARIO["ci"])),
        "bitcell_um2": pick("bitcell_um2", default=str(DEFAULT_SCENARIO["bitcell_um2"])),
        "scenario_hash": pick("scenario_hash", default="unknown"),
        "source_kind": source_kind,
    }
    return row


def _source_kind(path: Path) -> str:
    name = path.name.lower()
    if name == "pareto.csv":
        return "pareto"
    if "candidate" in name:
        return "candidates"
    if "telemetry" in name:
        return "telemetry"
    if name == "feasible.csv":
        return "feasible"
    return "csv"


def _label_for_policy(
    scn_rows: list[dict[str, object]],
    *,
    label_policy: str,
    utility_weights: dict[str, float],
) -> str:
    if label_policy == "carbon_min":
        chosen = min(scn_rows, key=lambda r: (float(r["carbon_true"]), float(r["fit_true"]), str(r["code"])))
        return str(chosen["code"])
    if label_policy == "fit_min":
        chosen = min(scn_rows, key=lambda r: (float(r["fit_true"]), float(r["carbon_true"]), str(r["code"])))
        return str(chosen["code"])
    if label_policy == "energy_min":
        chosen = min(scn_rows, key=lambda r: (float(r["energy_true"]), float(r["carbon_true"]), str(r["code"])))
        return str(chosen["code"])

    fit_vals = [float(r["fit_true"]) for r in scn_rows]
    carbon_vals = [float(r["carbon_true"]) for r in scn_rows]
    energy_vals = [float(r["energy_true"]) for r in scn_rows]

    def _norm(v: float, lo: float, hi: float) -> float:
        if hi <= lo:
            return 0.0
        return (v - lo) / (hi - lo)

    fit_lo, fit_hi = min(fit_vals), max(fit_vals)
    carbon_lo, carbon_hi = min(carbon_vals), max(carbon_vals)
    energy_lo, energy_hi = min(energy_vals), max(energy_vals)

    alpha = float(utility_weights.get("alpha_fit", 1.0))
    beta = float(utility_weights.get("beta_carbon", 1.0))
    gamma = float(utility_weights.get("gamma_energy", 1.0))

    chosen = min(
        scn_rows,
        key=lambda r: (
            alpha * _norm(float(r["fit_true"]), fit_lo, fit_hi)
            + beta * _norm(float(r["carbon_true"]), carbon_lo, carbon_hi)
            + gamma * _norm(float(r["energy_true"]), energy_lo, energy_hi),
            str(r["code"]),
        ),
    )
    return str(chosen["code"])


def _collect_training_rows(
    from_dir: Path,
    *,
    label_policy: str,
    utility_weights: dict[str, float],
) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    sources: list[str] = []

    for path in sorted(from_dir.rglob("*.csv")):
        source_kind = _source_kind(path)
        local_rows = 0
        for raw in _iter_csv_rows(path):
            if not raw:
                continue
            canon = _canonical_row(raw, source_kind)
            out = with_training_columns(canon)
            out["source_kind"] = source_kind
            out["source_file"] = str(path)
            rows.append(out)
            local_rows += 1
        if local_rows:
            sources.append(str(path))

    if not rows:
        raise ValueError(f"No usable CSV rows found under {from_dir}")

    # Scenario-level label policy.
    groups: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(str(row["scenario_hash"]), []).append(row)

    for scn_rows in groups.values():
        label = _label_for_policy(scn_rows, label_policy=label_policy, utility_weights=utility_weights)
        for row in scn_rows:
            row["label_code"] = label

    return rows, sources


def build_dataset(
    from_dir: Path,
    out_dir: Path,
    seed: int = 1,
    *,
    label_policy: str = "carbon_min",
    utility_alpha_fit: float = 1.0,
    utility_beta_carbon: float = 1.0,
    utility_gamma_energy: float = 1.0,
    split_strategy: str = "scenario_hash",
) -> dict[str, Path]:
    """Build a training dataset from existing ECC artifacts.

    Outputs:
    - dataset.csv
    - dataset_schema.json
    - dataset_manifest.json
    """

    from_dir = from_dir.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if label_policy not in LABEL_POLICIES:
        raise ValueError(f"Unsupported label_policy: {label_policy}")

    utility_weights = {
        "alpha_fit": float(utility_alpha_fit),
        "beta_carbon": float(utility_beta_carbon),
        "gamma_energy": float(utility_gamma_energy),
    }

    rows, sources = _collect_training_rows(
        from_dir,
        label_policy=label_policy,
        utility_weights=utility_weights,
    )
    rows.sort(key=lambda r: (str(r["scenario_hash"]), str(r["code"]), str(r["source_file"])))
    random.Random(seed).shuffle(rows)

    dataset_path = out_dir / "dataset.csv"
    schema_path = out_dir / "dataset_schema.json"
    manifest_path = out_dir / "dataset_manifest.json"

    fieldnames = FEATURE_COLUMNS + TARGET_COLUMNS + ["scenario_hash", "source_kind", "source_file"]
    with dataset_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    schema = {
        "format": "csv",
        "columns": [
            {"name": col, "type": "string" if col in ("code", "label_code", "scenario_hash", "source_kind", "source_file") else "float"}
            for col in fieldnames
        ],
    }
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[1]
    tech_path = repo_root / "tech_calib.json"
    qcrit_path = repo_root / "data" / "qcrit_sram6t.json"

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": int(seed),
        "label_policy": label_policy,
        "utility_weights": utility_weights,
        "split_strategy": str(split_strategy),
        "feature_version": 1,
        "source_dir": str(from_dir),
        "source_files": sources,
        "row_count": len(rows),
        "dataset_file": str(dataset_path),
        "git_commit": _git_commit(repo_root),
        "configs": {
            "tech_calib_sha256": _sha256(tech_path) if tech_path.exists() else None,
            "qcrit_sram6t_sha256": _sha256(qcrit_path) if qcrit_path.exists() else None,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "dataset": dataset_path,
        "schema": schema_path,
        "manifest": manifest_path,
    }
