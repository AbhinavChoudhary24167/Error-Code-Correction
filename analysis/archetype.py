from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
import yaml


@dataclass
class Archetype:
    name: str
    fit_lo: float
    fit_hi: float
    lat_lo: float
    lat_hi: float
    carbon_lo: float
    carbon_hi: float

    @property
    def center(self) -> Dict[str, float]:
        return {
            "fit": np.sqrt(self.fit_lo * self.fit_hi),
            "latency_ns": (self.lat_lo + self.lat_hi) / 2,
            "carbon_kg": (self.carbon_lo + self.carbon_hi) / 2,
        }

    def matches(self, row: pd.Series) -> float:
        if not (self.fit_lo <= row.fit <= self.fit_hi):
            return -1.0
        if not (self.lat_lo <= row.latency_ns <= self.lat_hi):
            return -1.0
        if not (self.carbon_lo <= row.carbon_kg <= self.carbon_hi):
            return -1.0

        if self.fit_hi <= self.fit_lo or self.lat_hi <= self.lat_lo or self.carbon_hi <= self.carbon_lo:
            return -1.0

        fit_dist = 0.0
        if np.isfinite(self.fit_lo) and np.isfinite(self.fit_hi):
            if self.fit_lo > 0 and self.fit_hi > 0:
                fit_span = (np.log10(self.fit_hi) - np.log10(self.fit_lo)) / 2
                fit_center_log = (np.log10(self.fit_lo) + np.log10(self.fit_hi)) / 2
                fit_dist = abs(np.log10(max(row.fit, 1e-300)) - fit_center_log) / fit_span
            else:
                fit_span = (self.fit_hi - self.fit_lo) / 2
                fit_center = (self.fit_lo + self.fit_hi) / 2
                fit_dist = abs(row.fit - fit_center) / fit_span

        lat_dist = 0.0
        if np.isfinite(self.lat_lo) and np.isfinite(self.lat_hi):
            lat_span = (self.lat_hi - self.lat_lo) / 2
            lat_center = (self.lat_lo + self.lat_hi) / 2
            lat_dist = abs(row.latency_ns - lat_center) / lat_span

        carb_dist = 0.0
        if np.isfinite(self.carbon_lo) and np.isfinite(self.carbon_hi):
            carb_span = (self.carbon_hi - self.carbon_lo) / 2
            carb_center = (self.carbon_lo + self.carbon_hi) / 2
            carb_dist = abs(row.carbon_kg - carb_center) / carb_span

        return max(0.0, 1 - max(fit_dist, lat_dist, carb_dist))



CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "archetypes.yaml"


def _load_archetypes(cfg_path: Path = CONFIG_PATH) -> Tuple[str, Dict[str, Archetype], Dict[str, Any]]:
    """Load archetype definitions from ``cfg_path``.

    Returns a tuple of (version, archetype map, raw thresholds).
    """

    cfg = yaml.safe_load(cfg_path.read_text())
    arcs: Dict[str, Archetype] = {}
    for name, vals in cfg["archetypes"].items():
        arcs[name] = Archetype(
            name,
            float(vals["fit_lo"]),
            float(vals["fit_hi"]),
            float(vals["lat_lo"]),
            float(vals["lat_hi"]),
            float(vals["carbon_lo"]),
            float(vals["carbon_hi"]),
        )
    return str(cfg.get("version", "")), arcs, cfg["archetypes"]


def classify_archetypes(
    pareto_csv: Path, out_json: Path, cfg_path: Path | None = None
) -> Dict[str, Any]:
    df = pd.read_csv(pareto_csv)
    version, arcs, thresholds = _load_archetypes(cfg_path or CONFIG_PATH)

    archetype_names = []
    confidences = []
    alternates = []

    for _, row in df.iterrows():
        best_name = "Unknown"
        best_conf = -1.0
        alts = []
        for name, arc in arcs.items():
            conf = arc.matches(row)
            if conf >= 0:
                alts.append((conf, name))
                if conf > best_conf:
                    best_conf = conf
                    best_name = name
        alts_sorted = [n for _, n in sorted(alts, reverse=True) if n != best_name]
        archetype_names.append(best_name)
        confidences.append(max(best_conf, 0.0))
        alternates.append(alts_sorted)

    df["archetype"] = archetype_names
    df["archetype_confidence"] = confidences
    df["archetype_alternates"] = alternates

    counts = df["archetype"].value_counts().to_dict()
    exemplars = {
        name: df[df["archetype"] == name].iloc[0].to_dict()
        for name in counts
    }

    def _ser(val: Any) -> Any:
        if isinstance(val, float) and math.isinf(val):
            return "inf"
        return val

    thr_serial = {
        name: {k: _ser(v) for k, v in vals.items()} for name, vals in thresholds.items()
    }

    result = {
        "provenance": {"version": version, "thresholds": thr_serial},
        "counts": counts,
        "exemplars": exemplars,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2))
    return result
