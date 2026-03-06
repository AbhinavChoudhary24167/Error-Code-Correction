from __future__ import annotations

"""Strict factual plotting pipeline for scenario-bound Pareto plots."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from analysis.pareto import pareto_partition
from analysis.plot_metadata import git_hash, utc_timestamp, write_metadata
from analysis.scenario_resolver import (
    ScenarioFilterError,
    ScenarioResolution,
    filter_by_scenario,
    normalise_scenario_filters,
)


COLUMN_ALIASES: dict[str, str] = {
    "fit": "FIT",
    "esii": "ESII",
    "nesii": "NESII",
    "n_scale": "N_scale",
    "e_dyn_kwh": "E_dyn_kWh",
    "e_leak_kwh": "E_leak_kWh",
    "e_scrub_kwh": "E_scrub_kWh",
    "scrub_interval_s": "scrub_s",
    "tempc": "temp",
    "node_nm": "node",
    "latitude": "latitude_deg",
}


AXIS_LABELS: dict[str, str] = {
    "FIT": "FIT (failures / 1e9 h)",
    "fit_word_post": "UWER",
    "fit_bit": "Bit error rate proxy",
    "carbon_kg": "Carbon (kg CO2e)",
    "latency_ns": "Latency (ns)",
    "ESII": "ESII",
    "NESII": "NESII",
    "energy_per_access_nj": "Energy per access (nJ)",
    "E_scrub_kWh": "Scrub energy (kWh)",
}


REQUIRED_SCENARIO_KEYS = {"codes", "node", "vdd", "temp", "capacity_gib", "ci", "bitcell_um2"}


@dataclass(frozen=True)
class LoadedDataset:
    rows: pd.DataFrame
    source_files: list[str]
    source_kind_counts: dict[str, int]
    reduced_only: bool
    recomputed_from_scenarios: list[str]
    rows_loaded_before_dedup: int


@dataclass(frozen=True)
class PlotRequest:
    from_path: Path
    out_path: Path
    x: str
    y: str
    scenario_filters: dict[str, Any] = field(default_factory=dict)
    show_dominated: bool = False
    save_metadata: bool = True
    strict_scenario: bool = True
    error_on_empty: bool = True
    log_x: bool = False
    log_y: bool = False
    x_objective: str = "min"
    y_objective: str = "min"
    allow_recompute: bool = True


@dataclass(frozen=True)
class PlotResult:
    out_path: Path
    metadata_path: Path | None
    rows_loaded: int
    rows_filtered: int
    rows_plotted: int
    frontier_rows: int


def _canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {}
    for col in df.columns:
        low = str(col).strip().lower()
        rename[col] = COLUMN_ALIASES.get(low, str(col))
    return df.rename(columns=rename)


def _kind_for_file(path: Path, columns: set[str]) -> str:
    name = path.name.lower()
    if "candidate" in name:
        return "candidates"
    if name == "pareto.csv":
        return "pareto"
    if "surface" in name:
        return "surface"
    if "feasible" in name:
        return "feasible"
    if "frontier" in columns and "violations" in columns:
        return "surface"
    return "csv"


def _scenario_path_for_csv(path: Path, root: Path) -> Path | None:
    cur = path.parent.resolve()
    root = root.resolve()
    while True:
        candidate = cur / "scenario.json"
        if candidate.exists():
            return candidate
        if cur == root:
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _load_scenario_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Scenario file must contain an object: {path}")
    return normalise_scenario_filters(payload)


def _augment_with_scenario(df: pd.DataFrame, scenario: dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    for key, value in scenario.items():
        if key == "codes":
            continue
        if key not in out.columns:
            out[key] = value
    return out


def _stable_row_fingerprint(row: pd.Series, cols: Iterable[str]) -> str:
    payload = {c: row[c] for c in cols}
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha1(encoded.encode()).hexdigest()


def _load_csv_files(root: Path) -> tuple[list[pd.DataFrame], list[str], dict[str, int]]:
    files: list[Path]
    if root.is_file():
        files = [root]
    else:
        files = sorted(root.rglob("*.csv"))

    frames: list[pd.DataFrame] = []
    source_files: list[str] = []
    kind_counts: dict[str, int] = {}

    for csv_path in files:
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            raise ValueError(f"Failed to read CSV {csv_path}: {exc}") from exc
        if df.empty:
            continue
        df = _canonical_columns(df)
        kind = _kind_for_file(csv_path, {str(c).lower() for c in df.columns})
        scenario_path = _scenario_path_for_csv(csv_path, root if root.is_dir() else csv_path.parent)
        if scenario_path is not None:
            scenario = _load_scenario_json(scenario_path)
            df = _augment_with_scenario(df, scenario)
            df["scenario_file"] = str(scenario_path.resolve())
        df["source_file"] = str(csv_path.resolve())
        df["source_row_index"] = list(range(len(df)))
        df["source_kind"] = kind
        frames.append(df)
        source_files.append(str(csv_path.resolve()))
        kind_counts[kind] = kind_counts.get(kind, 0) + len(df)

    return frames, sorted(set(source_files)), kind_counts


def _discover_scenario_files(root: Path) -> list[Path]:
    if root.is_file():
        maybe = root.parent / "scenario.json"
        return [maybe] if maybe.exists() else []
    return sorted(root.rglob("scenario.json"))


def _recompute_from_scenarios(scenario_files: list[Path]) -> tuple[pd.DataFrame, list[str]]:
    from ecc_selector import select

    rows: list[dict[str, Any]] = []
    used: list[str] = []

    for path in scenario_files:
        scenario_raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(scenario_raw, dict):
            continue
        scenario = normalise_scenario_filters(scenario_raw)
        if not REQUIRED_SCENARIO_KEYS.issubset(set(scenario.keys())):
            continue
        codes = scenario.get("codes")
        if not isinstance(codes, list) or not codes:
            continue
        constraints = scenario_raw.get("constraints")
        if constraints is not None and not isinstance(constraints, dict):
            raise ValueError(f"Invalid constraints in scenario file: {path}")
        params = {
            "node": scenario["node"],
            "vdd": scenario["vdd"],
            "temp": scenario["temp"],
            "capacity_gib": scenario["capacity_gib"],
            "ci": scenario["ci"],
            "bitcell_um2": scenario["bitcell_um2"],
            "lifetime_h": scenario.get("lifetime_h", float("nan")),
            "ci_source": scenario.get("ci_source", "unspecified"),
        }
        result = select(
            codes,
            constraints=constraints,
            mbu=scenario.get("mbu", "moderate"),
            scrub_s=scenario.get("scrub_s", 10.0),
            alt_km=scenario.get("alt_km", 0.0),
            latitude_deg=scenario.get("latitude_deg", scenario.get("latitude", 45.0)),
            flux_rel=scenario.get("flux_rel", None),
            **params,
        )
        for idx, rec in enumerate(result.get("candidate_records", [])):
            row = dict(rec)
            for key, value in scenario.items():
                if key == "codes":
                    continue
                row[key] = value
            row["source_file"] = str(path.resolve())
            row["source_row_index"] = idx
            row["source_kind"] = "recomputed"
            row["scenario_file"] = str(path.resolve())
            rows.append(row)
        used.append(str(path.resolve()))

    if not rows:
        return pd.DataFrame(), []

    return pd.DataFrame(rows), used


def load_plot_dataset(from_path: Path, *, allow_recompute: bool = True) -> LoadedDataset:
    root = from_path.resolve()
    frames, source_files, kind_counts = _load_csv_files(root)
    rows_loaded = int(sum(len(f) for f in frames))
    if frames:
        df = pd.concat(frames, ignore_index=True, sort=False)
    else:
        df = pd.DataFrame()

    reduced_only = bool(not df.empty and set(df["source_kind"]).issubset({"pareto"}))
    recomputed_files: list[str] = []

    if reduced_only:
        if not allow_recompute:
            raise ScenarioFilterError(
                "Only reduced Pareto rows were found and recompute is disabled. "
                "Provide candidate/surface artifacts or enable recompute."
            )
        scenario_files = _discover_scenario_files(root)
        recomputed_df, used = _recompute_from_scenarios(scenario_files)
        if recomputed_df.empty:
            raise ScenarioFilterError(
                "Only reduced Pareto rows were found and no resolvable scenario.json was available "
                "to recompute full candidate rows."
            )
        df = pd.concat([df, recomputed_df], ignore_index=True, sort=False)
        recomputed_files = used
        source_files = sorted(set(source_files + used))
        kind_counts["recomputed"] = kind_counts.get("recomputed", 0) + len(recomputed_df)

    if df.empty:
        raise ScenarioFilterError(f"No rows were loaded from {root}")

    provenance_cols = {"row_id", "row_fingerprint", "source_file", "source_row_index", "source_kind", "scenario_file"}
    sorted_cols = sorted(c for c in df.columns if c not in provenance_cols)
    df = df.sort_values(by=["source_file", "source_row_index"], kind="mergesort").reset_index(drop=True)
    df["row_fingerprint"] = [
        _stable_row_fingerprint(df.iloc[i], sorted_cols) for i in range(len(df))
    ]
    df = df.drop_duplicates(subset=["row_fingerprint"], keep="first").reset_index(drop=True)
    df["row_id"] = [
        hashlib.sha1(f"{r.source_file}:{r.source_row_index}:{r.row_fingerprint}".encode()).hexdigest()
        for r in df.itertuples(index=False)
    ]

    return LoadedDataset(
        rows=df,
        source_files=source_files,
        source_kind_counts={k: int(v) for k, v in kind_counts.items()},
        reduced_only=reduced_only,
        recomputed_from_scenarios=recomputed_files,
        rows_loaded_before_dedup=rows_loaded,
    )


def _axis_label(name: str) -> str:
    return AXIS_LABELS.get(name, name)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ScenarioFilterError(f"Dataset is missing required columns: {missing}")


def _validate_plot_values(df: pd.DataFrame, col: str, *, log_scale: bool) -> None:
    values = pd.to_numeric(df[col], errors="coerce")
    if values.isna().any():
        raise ScenarioFilterError(f"Column {col!r} contains non-numeric or NaN values")
    if log_scale and (values <= 0).any():
        raise ScenarioFilterError(f"Column {col!r} has non-positive values incompatible with log scale")


def _render_plot(
    filtered: pd.DataFrame,
    part_frontier: list[int],
    *,
    request: PlotRequest,
    resolution: ScenarioResolution,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("matplotlib is required for plotting") from exc

    idx_map = {row_idx: pos for pos, row_idx in enumerate(filtered.index.tolist())}
    frontier_pos = {idx_map[filtered.index[i]] for i in part_frontier}

    front = filtered.iloc[sorted(frontier_pos)].copy()
    dominated = filtered.drop(front.index)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    if request.show_dominated and not dominated.empty:
        ax.scatter(
            pd.to_numeric(dominated[request.x], errors="coerce"),
            pd.to_numeric(dominated[request.y], errors="coerce"),
            c="#bfbfbf",
            s=40,
            alpha=0.6,
            label="Dominated",
        )

    ax.scatter(
        pd.to_numeric(front[request.x], errors="coerce"),
        pd.to_numeric(front[request.y], errors="coerce"),
        c="#1f77b4",
        edgecolors="black",
        s=60,
        alpha=0.9,
        label="Pareto frontier",
    )

    for row in front.itertuples(index=False):
        ax.annotate(
            str(getattr(row, "code", "")),
            (float(getattr(row, request.x)), float(getattr(row, request.y))),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
        )

    if request.log_x:
        ax.set_xscale("log")
    if request.log_y:
        ax.set_yscale("log")

    scenario_bits = ", ".join(f"{k}={v}" for k, v in sorted(resolution.applied.items()))
    ax.set_title(f"Pareto plot ({scenario_bits})" if scenario_bits else "Pareto plot")
    ax.set_xlabel(_axis_label(request.x))
    ax.set_ylabel(_axis_label(request.y))
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="best", frameon=False)
    fig.tight_layout()

    request.out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(request.out_path, dpi=300)
    plt.close(fig)


def generate_pareto_plot(request: PlotRequest) -> PlotResult:
    loaded = load_plot_dataset(request.from_path, allow_recompute=request.allow_recompute)
    filtered, resolution = filter_by_scenario(
        loaded.rows,
        request.scenario_filters,
        strict=request.strict_scenario,
        error_on_empty=request.error_on_empty,
    )

    _require_columns(filtered, ["code", request.x, request.y, "row_id", "source_file", "source_row_index"])
    _validate_plot_values(filtered, request.x, log_scale=request.log_x)
    _validate_plot_values(filtered, request.y, log_scale=request.log_y)

    records = filtered[[request.x, request.y]].to_dict("records")
    partition = pareto_partition(
        records,
        objectives={request.x: request.x_objective, request.y: request.y_objective},
    )

    _render_plot(filtered, partition.frontier_indices, request=request, resolution=resolution)

    idx_map = {pos: int(filtered.index[pos]) for pos in range(len(filtered))}
    frontier_global = {idx_map[pos] for pos in partition.frontier_indices}
    filtered_with_front = filtered.copy()
    filtered_with_front["frontier"] = [idx in frontier_global for idx in filtered.index]

    rows_plotted = int(len(filtered_with_front[filtered_with_front["frontier"]]))
    if request.show_dominated:
        rows_plotted = int(len(filtered_with_front))

    metadata_path: Path | None = None
    if request.save_metadata:
        metadata_path = request.out_path.with_suffix(".json")
        transformations: list[str] = []
        if request.log_x:
            transformations.append(f"log10({request.x})")
        if request.log_y:
            transformations.append(f"log10({request.y})")
        write_metadata(
            metadata_path,
            {
                "scenario": {
                    "requested": resolution.requested,
                    "applied": resolution.applied,
                    "omitted_scope_fields": resolution.omitted_fields,
                    "missing_fields": resolution.missing_fields,
                },
                "source_files": loaded.source_files,
                "source_kind_counts": loaded.source_kind_counts,
                "rows_loaded_before_dedup": loaded.rows_loaded_before_dedup,
                "rows_loaded": int(len(loaded.rows)),
                "rows_after_filter": int(len(filtered)),
                "rows_plotted": rows_plotted,
                "rows_frontier": int(len(partition.frontier_indices)),
                "frontier_reduction_applied": True,
                "timestamp_utc": utc_timestamp(),
                "git": git_hash(),
                "axes": {
                    "x": request.x,
                    "y": request.y,
                    "x_objective": request.x_objective,
                    "y_objective": request.y_objective,
                    "log_x": request.log_x,
                    "log_y": request.log_y,
                },
                "transformations": transformations,
                "recomputed_from_scenarios": loaded.recomputed_from_scenarios,
                "plotted_rows": [
                    {
                        "row_id": str(row.row_id),
                        "source_file": str(row.source_file),
                        "source_row_index": int(row.source_row_index),
                        "code": str(row.code),
                        "x": float(row.__getattribute__(request.x)),
                        "y": float(row.__getattribute__(request.y)),
                        "frontier": bool(row.frontier),
                    }
                    for row in filtered_with_front.itertuples(index=False)
                ],
            },
        )

    return PlotResult(
        out_path=request.out_path,
        metadata_path=metadata_path,
        rows_loaded=int(len(loaded.rows)),
        rows_filtered=int(len(filtered)),
        rows_plotted=rows_plotted,
        frontier_rows=int(len(partition.frontier_indices)),
    )



def generate_pareto_plot_from_records(
    records: list[dict[str, Any]],
    *,
    out_path: Path,
    x: str = "carbon_kg",
    y: str = "FIT",
    x_objective: str = "min",
    y_objective: str = "min",
    show_dominated: bool = True,
    save_metadata: bool = True,
    log_x: bool = False,
    log_y: bool = False,
    scenario: dict[str, Any] | None = None,
    source_files: list[str] | None = None,
) -> PlotResult:
    """Render a factual Pareto plot directly from in-memory records."""

    if not records:
        raise ScenarioFilterError("No records available for plotting")

    df = pd.DataFrame(records)
    _require_columns(df, ["code", x, y])
    _validate_plot_values(df, x, log_scale=log_x)
    _validate_plot_values(df, y, log_scale=log_y)

    df = df.reset_index(drop=True)
    if "source_file" not in df.columns:
        fallback_source = source_files[0] if source_files else "<in-memory>"
        df["source_file"] = fallback_source
    if "source_row_index" not in df.columns:
        df["source_row_index"] = list(range(len(df)))
    if "row_id" not in df.columns:
        df["row_id"] = [
            hashlib.sha1(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest()
            for row in df.to_dict("records")
        ]

    partition = pareto_partition(
        df[[x, y]].to_dict("records"),
        objectives={x: x_objective, y: y_objective},
    )

    resolution = ScenarioResolution(
        requested=dict(scenario or {}),
        applied=dict(scenario or {}),
        omitted_fields=[],
        missing_fields=[],
        matched_rows=int(len(df)),
    )
    _render_plot(
        df,
        partition.frontier_indices,
        request=PlotRequest(
            from_path=Path("."),
            out_path=out_path,
            x=x,
            y=y,
            show_dominated=show_dominated,
            save_metadata=save_metadata,
            strict_scenario=True,
            error_on_empty=True,
            log_x=log_x,
            log_y=log_y,
            x_objective=x_objective,
            y_objective=y_objective,
        ),
        resolution=resolution,
    )

    idx_map = {pos: int(df.index[pos]) for pos in range(len(df))}
    frontier_global = {idx_map[pos] for pos in partition.frontier_indices}
    plotted = df.copy()
    plotted["frontier"] = [idx in frontier_global for idx in df.index]

    rows_plotted = int(plotted["frontier"].sum())
    if show_dominated:
        rows_plotted = int(len(plotted))

    metadata_path: Path | None = None
    if save_metadata:
        metadata_path = out_path.with_suffix(".json")
        transformations: list[str] = []
        if log_x:
            transformations.append(f"log10({x})")
        if log_y:
            transformations.append(f"log10({y})")
        write_metadata(
            metadata_path,
            {
                "scenario": {
                    "requested": dict(scenario or {}),
                    "applied": dict(scenario or {}),
                    "omitted_scope_fields": [],
                    "missing_fields": [],
                },
                "source_files": sorted(set(source_files or [str(s) for s in plotted["source_file"].tolist()])),
                "source_kind_counts": {"in_memory": int(len(df))},
                "rows_loaded_before_dedup": int(len(df)),
                "rows_loaded": int(len(df)),
                "rows_after_filter": int(len(df)),
                "rows_plotted": rows_plotted,
                "rows_frontier": int(len(partition.frontier_indices)),
                "frontier_reduction_applied": True,
                "timestamp_utc": utc_timestamp(),
                "git": git_hash(),
                "axes": {
                    "x": x,
                    "y": y,
                    "x_objective": x_objective,
                    "y_objective": y_objective,
                    "log_x": log_x,
                    "log_y": log_y,
                },
                "transformations": transformations,
                "recomputed_from_scenarios": [],
                "plotted_rows": [
                    {
                        "row_id": str(row.row_id),
                        "source_file": str(row.source_file),
                        "source_row_index": int(row.source_row_index),
                        "code": str(row.code),
                        "x": float(row.__getattribute__(x)),
                        "y": float(row.__getattribute__(y)),
                        "frontier": bool(row.frontier),
                    }
                    for row in plotted.itertuples(index=False)
                ],
            },
        )

    return PlotResult(
        out_path=out_path,
        metadata_path=metadata_path,
        rows_loaded=int(len(df)),
        rows_filtered=int(len(df)),
        rows_plotted=rows_plotted,
        frontier_rows=int(len(partition.frontier_indices)),
    )
__all__ = [
    "LoadedDataset",
    "PlotRequest",
    "PlotResult",
    "generate_pareto_plot",
    "generate_pareto_plot_from_records",
    "load_plot_dataset",
]









