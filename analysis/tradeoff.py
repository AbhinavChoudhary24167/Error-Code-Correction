from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
from statistics import NormalDist
import warnings
from numpy.exceptions import RankWarning

from analysis.hv import normalize, hypervolume, schott_spacing


@dataclass
class TradeoffConfig:
    """Configuration for trade-off analysis."""

    n_resamples: int = 20000
    seed: int = 0
    filter_expr: Optional[str] = None
    basis: str = "per_gib"
    lifetime_h: Optional[float] = None


def _pearsonr_p(x: np.ndarray, y: np.ndarray) -> float:
    """Return an approximate two-sided p-value for Pearson correlation.

    This implementation avoids dependencies outside the standard library by
    approximating the distribution of the test statistic with a normal
    distribution. It is sufficiently accurate for large ``n`` which is
    adequate for our unit tests.
    """

    n = len(x)
    if n < 3:
        return float("nan")
    r = np.corrcoef(x, y)[0, 1]
    if abs(r) == 1.0:
        return 0.0
    t = r * np.sqrt((n - 2) / (1 - r ** 2))
    p = 2 * (1 - NormalDist().cdf(abs(t)))
    return float(p)


def _bootstrap_slopes(x: np.ndarray, y: np.ndarray, cfg: TradeoffConfig) -> np.ndarray:
    rng = np.random.default_rng(cfg.seed)
    n = len(x)
    slopes = np.empty(cfg.n_resamples)
    for i in range(cfg.n_resamples):
        while True:
            idx = rng.integers(0, n, size=n)
            xs = x[idx]
            ys = y[idx]
            # Skip samples with effectively no variation which would
            # make the fit ill-conditioned.
            if np.var(xs) < 1e-12 or np.var(ys) < 1e-12:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("error", category=RankWarning)
                    slope = np.polyfit(xs, ys, 1)[0]
            except RankWarning:
                # Add a tiny amount of noise to break perfect collinearity and
                # retry the fit once.
                xs = xs + rng.normal(scale=1e-12, size=n)
                ys = ys + rng.normal(scale=1e-12, size=n)
                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("error", category=RankWarning)
                        slope = np.polyfit(xs, ys, 1)[0]
                except RankWarning:
                    # If the data are still ill-conditioned, draw a new
                    # bootstrap sample.
                    continue
            slopes[i] = slope
            break
    return slopes


def analyze_tradeoffs(pareto_csv: Path, out_json: Path, cfg: TradeoffConfig) -> Dict[str, Any]:
    """Compute trade-off statistics from a Pareto frontier CSV."""

    df = pd.read_csv(pareto_csv)
    if cfg.filter_expr:
        df = df.query(cfg.filter_expr)
    df = df.sort_values("carbon_kg")

    logfit = np.log10(df["fit"])
    carbon = df["carbon_kg"].to_numpy()

    slope = float(np.polyfit(logfit, carbon, 1)[0])
    r = float(np.corrcoef(logfit, carbon)[0, 1])
    p = _pearsonr_p(logfit, carbon)

    slopes = _bootstrap_slopes(logfit.to_numpy(), carbon, cfg)
    mean = float(np.mean(slopes))
    std = float(np.std(slopes, ddof=1))
    lo, hi = np.percentile(slopes, [2.5, 97.5])

    pts = df[["fit", "carbon_kg"]].to_numpy()
    norm_pts = normalize(pts)

    # Remove dominated points before computing quality metrics
    nd: list[np.ndarray] = []
    for i, pt in enumerate(norm_pts):
        dominated = False
        for j, other in enumerate(norm_pts):
            if i == j:
                continue
            if np.all(other <= pt) and np.any(other < pt):
                dominated = True
                break
        if not dominated:
            nd.append(pt)
    nd_pts = np.array(nd)

    hv = float(hypervolume(nd_pts))
    spacing = float(schott_spacing(nd_pts))

    result = {
        "provenance": {
            "basis": cfg.basis,
            "ci_method": "bootstrap",
            "seed": cfg.seed,
            "n_resamples": cfg.n_resamples,
            "filter": cfg.filter_expr,
            "notes": [],
        },
        "exchange": {
            "fit_vs_carbon": {
                "kg_per_decade": slope,
                "mean": mean,
                "std": std,
                "ci95": [float(lo), float(hi)],
                "r": r,
                "p": p,
                "N": int(len(df)),
            }
        },
        "quality": {
            "hypervolume": hv,
            "ref_point_norm": [1.0, 1.0],
            "spacing": spacing,
        },
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2))
    return result
