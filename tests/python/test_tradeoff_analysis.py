import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.tradeoff import analyze_tradeoffs, TradeoffConfig


def create_pareto(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "fit": [1e-12, 1e-11, 1e-10],
            "carbon_kg": [1.0, 2.0, 3.0],
        }
    )
    path = tmp_path / "pareto.csv"
    df.to_csv(path, index=False)
    return path


def test_tradeoff_slope_and_ci(tmp_path: Path) -> None:
    pareto = create_pareto(tmp_path)
    out = tmp_path / "trade.json"
    cfg = TradeoffConfig(n_resamples=1000, seed=1)
    result = analyze_tradeoffs(pareto, out, cfg)

    slope = result["exchange"]["fit_vs_carbon"]["kg_per_decade"]
    assert abs(slope - 1.0) < 1e-6
    lo, hi = result["exchange"]["fit_vs_carbon"]["ci95"]
    assert lo <= slope <= hi

    out2 = tmp_path / "trade2.json"
    result2 = analyze_tradeoffs(pareto, out2, cfg)
    assert result2["exchange"]["fit_vs_carbon"]["kg_per_decade"] == slope

    quality = result["quality"]
    assert quality["ref_point_norm"] == [1.0, 1.0]
    assert quality["hypervolume"] > 0.0
    assert quality["spacing"] >= 0.0


