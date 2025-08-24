from pathlib import Path

import pandas as pd

from analysis.archetype import classify_archetypes


def create_data(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "fit": [1e-16, 5e-13, 5e-12, 1e-12],
            "latency_ns": [3.5, 2.0, 1.0, 1.0],
            "carbon_kg": [0.9, 0.5, 0.2, 0.5],
        }
    )
    path = tmp_path / "pareto.csv"
    df.to_csv(path, index=False)
    return path


def test_archetype_classification(tmp_path: Path) -> None:
    pareto = create_data(tmp_path)
    out = tmp_path / "arch.json"
    result = classify_archetypes(pareto, out)
    assert result["counts"]["Fortress"] == 1
    assert result["counts"]["Efficiency"] == 1
    assert result["counts"]["Frugal"] == 1
    assert result["counts"]["SpeedDemon"] == 1

