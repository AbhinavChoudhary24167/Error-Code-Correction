from __future__ import annotations

"""Feasible surface analysis utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

from ecc_selector import _pareto_front

import subprocess
import hashlib


def _git_hash() -> str:
    """Return the current git commit hash or ``unknown`` if unavailable."""
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


@dataclass
class SurfaceResult:
    df: pd.DataFrame
    frontier_codes: set[str]
    git: str
    tech_calib: str
    scenario_hash: str


def analyze_surface(
    cand_csv: Path, out_csv: Path, plot: Optional[Path] = None
) -> SurfaceResult:
    """Classify candidate points and optionally plot the feasible surface."""

    df = pd.read_csv(cand_csv)

    # Identify Pareto frontier
    recs = df[["code", "FIT", "carbon_kg", "latency_ns"]].to_dict("records")
    frontier = {r["code"] for r in _pareto_front(recs)}
    df["frontier"] = df["code"].isin(frontier)

    # NESII bounds check
    if "NESII" in df.columns:
        if not df["NESII"].between(0.0, 100.0, inclusive="both").all():
            raise ValueError("NESII outside [0,100]")

    # provenance
    repo_path = Path(__file__).resolve().parents[1]
    git = _git_hash()
    tech = _file_hash(repo_path / "tech_calib.json")
    df["git"] = git
    df["tech_calib"] = tech
    scen_hash = str(df.get("scenario_hash").iloc[0]) if "scenario_hash" in df else ""

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    if plot is not None:
        try:
            import matplotlib.pyplot as plt  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            plot.write_text("matplotlib not installed")
        else:
            dominated = df[~df["frontier"]]
            front = df[df["frontier"]]
            plt.figure()
            if not dominated.empty:
                plt.scatter(
                    dominated["carbon_kg"],
                    dominated["FIT"],
                    c=dominated["latency_ns"],
                    cmap="viridis",
                    alpha=0.3,
                    label="dominated",
                )
            if not front.empty:
                plt.scatter(
                    front["carbon_kg"],
                    front["FIT"],
                    c=front["latency_ns"],
                    cmap="viridis",
                    edgecolors="black",
                    label="frontier",
                )
            plt.xlabel("carbon_kg")
            plt.ylabel("FIT")
            plt.title("Feasible surface")
            plt.legend()
            plt.tight_layout()
            plt.savefig(plot)
            plt.close()

    return SurfaceResult(df=df, frontier_codes=frontier, git=git, tech_calib=tech, scenario_hash=scen_hash)


__all__ = ["analyze_surface", "SurfaceResult"]
