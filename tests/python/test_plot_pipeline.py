from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from analysis.plot_pipeline import PlotRequest, generate_pareto_plot, load_plot_dataset
from analysis.scenario_resolver import ScenarioFilterError


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def test_exact_scenario_filtering_and_metadata(tmp_path: Path) -> None:
    a = tmp_path / "candidates_a.csv"
    b = tmp_path / "candidates_b.csv"

    rows_a = [
        {
            "code": "sec-ded-64",
            "FIT": 10.0,
            "carbon_kg": 1.0,
            "latency_ns": 1.0,
            "node": 7,
            "vdd": 0.8,
            "temp": 25.0,
            "scrub_s": 5.0,
            "capacity_gib": 1.0,
        },
        {
            "code": "sec-daec-64",
            "FIT": 8.0,
            "carbon_kg": 1.3,
            "latency_ns": 1.2,
            "node": 7,
            "vdd": 0.8,
            "temp": 25.0,
            "scrub_s": 5.0,
            "capacity_gib": 1.0,
        },
    ]
    rows_b = [
        rows_a[0],
        {
            "code": "taec-64",
            "FIT": 7.0,
            "carbon_kg": 1.6,
            "latency_ns": 1.5,
            "node": 14,
            "vdd": 0.8,
            "temp": 25.0,
            "scrub_s": 10.0,
            "capacity_gib": 8.0,
        },
    ]
    _write_csv(a, rows_a)
    _write_csv(b, rows_b)

    out = tmp_path / "plots" / "pareto.png"
    req = PlotRequest(
        from_path=tmp_path,
        out_path=out,
        x="carbon_kg",
        y="FIT",
        show_dominated=True,
        log_x=True,
        scenario_filters={"node": 7, "vdd": 0.8, "temp": 25.0},
    )
    result = generate_pareto_plot(req)
    assert out.exists()
    assert result.rows_filtered == 2
    assert result.rows_loaded == 3

    metadata = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert metadata["rows_loaded"] == 3
    assert metadata["rows_after_filter"] == 2
    assert metadata["axes"]["x"] == "carbon_kg"
    assert metadata["axes"]["y"] == "FIT"
    assert "log10(carbon_kg)" in metadata["transformations"]
    assert metadata["scenario"]["applied"]["node"] == 7


def test_empty_scenario_failure(tmp_path: Path) -> None:
    _write_csv(
        tmp_path / "candidates.csv",
        [
            {
                "code": "sec-ded-64",
                "FIT": 10.0,
                "carbon_kg": 1.0,
                "latency_ns": 1.0,
                "node": 14,
                "vdd": 0.8,
                "temp": 75.0,
            }
        ],
    )

    req = PlotRequest(
        from_path=tmp_path,
        out_path=tmp_path / "pareto.png",
        x="carbon_kg",
        y="FIT",
        scenario_filters={"node": 7, "vdd": 0.8},
        error_on_empty=True,
    )
    with pytest.raises(ScenarioFilterError, match="No rows matched the requested scenario"):
        generate_pareto_plot(req)


def test_reduced_only_auto_recompute_from_scenario_json(tmp_path: Path) -> None:
    pareto_csv = tmp_path / "pareto.csv"
    _write_csv(
        pareto_csv,
        [
            {
                "code": "sec-ded-64",
                "FIT": 11.0,
                "carbon_kg": 2.0,
                "latency_ns": 1.0,
            }
        ],
    )

    scenario = {
        "codes": ["sec-ded-64", "sec-daec-64", "taec-64"],
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.04,
        "mbu": "moderate",
        "scrub_s": 10.0,
    }
    (tmp_path / "scenario.json").write_text(json.dumps(scenario), encoding="utf-8")

    loaded = load_plot_dataset(tmp_path)
    assert loaded.reduced_only is True
    assert loaded.source_kind_counts.get("recomputed", 0) >= 3

    req = PlotRequest(
        from_path=tmp_path,
        out_path=tmp_path / "recomputed_plot.png",
        x="carbon_kg",
        y="FIT",
        scenario_filters={"node": 14, "vdd": 0.8, "temp": 75.0},
    )
    result = generate_pareto_plot(req)
    assert result.rows_filtered >= 3


def test_load_dataset_is_deterministic_with_dedup(tmp_path: Path) -> None:
    rows = [
        {
            "code": "sec-ded-64",
            "FIT": 10.0,
            "carbon_kg": 1.0,
            "latency_ns": 1.0,
            "node": 14,
            "vdd": 0.8,
            "temp": 75.0,
        },
        {
            "code": "sec-ded-64",
            "FIT": 10.0,
            "carbon_kg": 1.0,
            "latency_ns": 1.0,
            "node": 14,
            "vdd": 0.8,
            "temp": 75.0,
        },
    ]
    _write_csv(tmp_path / "candidates.csv", rows)

    a = load_plot_dataset(tmp_path)
    b = load_plot_dataset(tmp_path)
    assert list(a.rows["row_id"]) == list(b.rows["row_id"])
    assert len(a.rows) == 1
