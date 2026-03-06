from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "eccsim.py"


def _write_candidates(path: Path) -> None:
    df = pd.DataFrame(
        [
            {
                "code": "sec-ded-64",
                "FIT": 11.0,
                "carbon_kg": 1.0,
                "latency_ns": 1.0,
                "node": 7,
                "vdd": 0.8,
                "temp": 25.0,
            },
            {
                "code": "sec-daec-64",
                "FIT": 8.0,
                "carbon_kg": 1.5,
                "latency_ns": 1.2,
                "node": 7,
                "vdd": 0.8,
                "temp": 25.0,
            },
        ]
    )
    df.to_csv(path, index=False)


def test_plot_cli_generates_png_and_metadata(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.csv"
    out = tmp_path / "plots" / "pareto.png"
    _write_candidates(candidates)

    cmd = [
        sys.executable,
        str(SCRIPT),
        "plot",
        "pareto",
        "--from",
        str(tmp_path),
        "--node",
        "7",
        "--vdd",
        "0.8",
        "--temp",
        "25",
        "--x",
        "carbon_kg",
        "--y",
        "FIT",
        "--show-dominated",
        "--save-metadata",
        "--out",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert out.exists()
    meta_path = out.with_suffix(".json")
    assert meta_path.exists()

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["rows_after_filter"] == 2
    assert meta["rows_plotted"] == 2
    assert meta["axes"]["x"] == "carbon_kg"


def test_plot_cli_error_on_empty_scenario(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.csv"
    out = tmp_path / "pareto.png"
    _write_candidates(candidates)

    cmd = [
        sys.executable,
        str(SCRIPT),
        "plot",
        "pareto",
        "--from",
        str(tmp_path),
        "--node",
        "9",
        "--vdd",
        "0.8",
        "--temp",
        "25",
        "--error-on-empty",
        "--out",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "No rows matched the requested scenario" in res.stderr
