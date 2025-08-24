from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from ecc_selector import select


@dataclass
class SensitivityRun:
    value: float
    choice: str | None
    feasible: List[str]


def analyze_sensitivity(
    scenario_json: Path,
    factor: str,
    grid: List[float],
    out_json: Path,
    factor2: str | None = None,
    grid2: List[float] | None = None,
    out_csv: Path | None = None,
) -> Dict[str, Any]:
    """Analyse robustness of the ECC recommendation.

    When ``factor2``/``grid2`` are provided a two-factor matrix analysis is
    performed; otherwise the behaviour matches the original one-factor mode.
    """

    scenario = json.loads(scenario_json.read_text())
    if "codes" not in scenario:
        raise KeyError("scenario missing 'codes'")
    codes = scenario["codes"]
    scenario_params = {k: v for k, v in scenario.items() if k != "codes" and k != "constraints"}
    constraints = dict(scenario.get("constraints", {}))

    if factor2 is not None and grid2 is not None:
        # Two-factor matrix analysis
        from collections import Counter

        choices: Dict[str, Dict[str, str | None]] = {}
        feasible_map: Dict[str, Dict[str, List[str]]] = {}
        row_robust: Dict[str, float] = {}

        for val1 in grid:
            choices[str(val1)] = {}
            feasible_map[str(val1)] = {}
            row_codes: List[str | None] = []

            for val2 in grid2:
                params = dict(scenario_params)
                cons = dict(constraints)

                if factor in params:
                    params[factor] = val1
                else:
                    cons[factor] = val1
                if factor2 in params:
                    params[factor2] = val2
                else:
                    cons[factor2] = val2

                res = select(codes, constraints=cons if cons else None, **params)
                best = res.get("best")
                choice = best.get("code") if isinstance(best, dict) else None

                fit_bound = None
                if factor == "fit_max":
                    fit_bound = val1
                if factor2 == "fit_max":
                    fit_bound = (
                        min(fit_bound, val2)
                        if fit_bound is not None
                        else val2
                    )
                cand = res.get("candidate_records", [])
                if fit_bound is None:
                    feasible = [r["code"] for r in cand]
                else:
                    feasible = [
                        r["code"]
                        for r in cand
                        if r.get("FIT", float("inf")) <= fit_bound
                    ]

                choices[str(val1)][str(val2)] = choice
                feasible_map[str(val1)][str(val2)] = feasible
                row_codes.append(choice)

            if row_codes:
                cnt = Counter(row_codes)
                _, mode_count = cnt.most_common(1)[0]
                row_robust[str(val1)] = mode_count / len(row_codes)
            else:
                row_robust[str(val1)] = 0.0

        col_robust: Dict[str, float] = {}
        for val2 in grid2:
            col_codes = [choices[str(v1)][str(val2)] for v1 in grid]
            if col_codes:
                cnt = Counter(col_codes)
                _, mode_count = cnt.most_common(1)[0]
                col_robust[str(val2)] = mode_count / len(col_codes)
            else:
                col_robust[str(val2)] = 0.0

        result = {
            "factor": factor,
            "grid": grid,
            "factor2": factor2,
            "grid2": grid2,
            "choices": choices,
            "feasible": feasible_map,
            "robustness": row_robust,
            "robustness2": col_robust,
        }

        if out_csv is not None:
            out_csv.parent.mkdir(parents=True, exist_ok=True)
            with out_csv.open("w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow([f"{factor}\\{factor2}"] + [str(v) for v in grid2])
                for v1 in grid:
                    row = [str(v1)] + [choices[str(v1)][str(v2)] or "" for v2 in grid2]
                    writer.writerow(row)

        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(result, indent=2))
        return result

    # One-factor analysis (original behaviour)
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
                r["code"]
                for r in res.get("candidate_records", [])
                if r.get("FIT", float("inf")) <= val
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
            change_points.append(
                {
                    "value": curr.value,
                    "from": prev.choice,
                    "to": curr.choice,
                }
            )

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
