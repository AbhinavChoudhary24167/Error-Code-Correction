from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd


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
        c = self.center
        fit_span = (np.log10(self.fit_hi) - np.log10(self.fit_lo)) / 2
        fit_dist = abs(np.log10(row.fit) - np.log10(c["fit"])) / fit_span
        lat_span = (self.lat_hi - self.lat_lo) / 2
        lat_dist = abs(row.latency_ns - c["latency_ns"]) / lat_span
        carb_span = (self.carbon_hi - self.carbon_lo) / 2
        carb_dist = abs(row.carbon_kg - c["carbon_kg"]) / carb_span
        return max(0.0, 1 - max(fit_dist, lat_dist, carb_dist))


def _archetypes() -> Dict[str, Archetype]:
    return {
        "Fortress": Archetype("Fortress", 0.0, 1e-15, 3.0, float("inf"), 0.8, 1.2),
        "Efficiency": Archetype("Efficiency", 1e-13, 1e-12, 1.5, 2.5, 0.3, 0.6),
        "Frugal": Archetype("Frugal", 1e-12, 1e-11, 0.0, 2.0, 0.0, 0.3),
        "SpeedDemon": Archetype("SpeedDemon", 0.0, float("inf"), 0.0, 1.5, 0.4, float("inf")),
    }


def classify_archetypes(pareto_csv: Path, out_json: Path) -> Dict[str, Any]:
    df = pd.read_csv(pareto_csv)
    arcs = _archetypes()

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

    result = {"counts": counts, "exemplars": exemplars}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2))
    return result
