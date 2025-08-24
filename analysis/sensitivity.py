from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List

from ecc_selector import select


@dataclass
class SensitivityRun:
    value: float
    choice: str | None
    feasible: List[str]


def analyze_sensitivity(
    scenario_json: Path, factor: str, grid: List[float], out_json: Path
) -> Dict[str, Any]:
    """Analyse robustness of the ECC recommendation against a single factor."""

    scenario = json.loads(scenario_json.read_text())
    if "codes" not in scenario:
        raise KeyError("scenario missing 'codes'")
    codes = scenario["codes"]
    scenario_params = {k: v for k, v in scenario.items() if k != "codes" and k != "constraints"}
    constraints = dict(scenario.get("constraints", {}))

    runs: List[SensitivityRun] = []
    for val in grid:
        params = dict(scenario_params)
        cons = dict(constraints)
        if factor in params:
            params[factor] = val
        else:
            cons[factor] = val

        res = select(codes, constraints=cons if cons else None, **params)
        best = res.get("best")
        choice = best.get("code") if isinstance(best, dict) else None
        if factor == "fit_max":
            feasible = [
                r["code"] for r in res.get("candidate_records", []) if r.get("FIT", float("inf")) <= val
            ]
        else:
            feasible = [r["code"] for r in res.get("candidate_records", [])]
        runs.append(SensitivityRun(value=float(val), choice=choice, feasible=feasible))

    choices = {str(r.value): r.choice for r in runs}
    feasible_map = {str(r.value): r.feasible for r in runs}

    codes_list = [r.choice for r in runs]
    if codes_list:
        from collections import Counter

        cnt = Counter(codes_list)
        _, mode_count = cnt.most_common(1)[0]
        robustness = mode_count / len(codes_list)
    else:
        robustness = 0.0

    change_points: List[Dict[str, Any]] = []
    for prev, curr in zip(runs, runs[1:]):
        if prev.choice != curr.choice:
            change_points.append({
                "value": curr.value,
                "from": prev.choice,
                "to": curr.choice,
            })

    result = {
        "factor": factor,
        "grid": grid,
        "choices": choices,
        "feasible": feasible_map,
        "robustness": robustness,
        "change_points": change_points,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2))
    return result


__all__ = ["analyze_sensitivity"]
