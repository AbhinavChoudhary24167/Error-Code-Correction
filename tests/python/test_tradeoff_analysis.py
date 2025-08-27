import json
from pathlib import Path

import numpy as np
import pandas as pd
import warnings
from numpy.exceptions import RankWarning

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
    assert result2["exchange"]["fit_vs_carbon"]["ci95"] == [lo, hi]

    prov = result["provenance"]
    assert prov["ci_method"] == "bootstrap"
    assert prov["seed"] == 1
    assert prov["n_resamples"] == 1000
    assert prov["filter"] is None

    quality = result["quality"]
    assert quality["ref_point_norm"] == [1.0, 1.0]
    assert quality["hypervolume"] > 0.0
    assert quality["spacing"] >= 0.0


def test_tradeoff_filter(tmp_path: Path) -> None:
    pareto = create_pareto(tmp_path)
    out = tmp_path / "trade.json"
    cfg = TradeoffConfig(n_resamples=1000, seed=1, filter_expr="carbon_kg > 1.5")
    result = analyze_tradeoffs(pareto, out, cfg)

    stats = result["exchange"]["fit_vs_carbon"]
    assert stats["N"] == 2
    assert len(stats["ci95"]) == 2
    assert "r" in stats and "p" in stats
    assert not np.isnan(stats["kg_per_decade"])
    assert result["provenance"]["filter"] == "carbon_kg > 1.5"


def test_tradeoff_bootstrap_no_rankwarning(tmp_path: Path) -> None:
    pareto = create_pareto(tmp_path)
    out = tmp_path / "trade.json"
    cfg = TradeoffConfig(n_resamples=1000, seed=2)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always", RankWarning)
        analyze_tradeoffs(pareto, out, cfg)
        assert not any(isinstance(w.message, RankWarning) for w in rec)


