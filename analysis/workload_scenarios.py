"""Scenario studies for mixed workloads and adaptive scrubbing."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from carbon import operational_kgco2e
import ecc_selector as selector
from gs import GSInputs, compute_gs


SCENARIO = dict(
    node=28,
    vdd=0.8,
    capacity_gib=32.0,
    bitcell_um2=0.09,
    lifetime_h=5 * 365 * 24,
)

CODES = ["sec-ded-64", "sec-daec-64", "taec-64"]


@dataclass(frozen=True)
class Phase:
    """Workload phase for a composite scenario."""

    name: str
    fraction: float
    temp: float
    scrub_s: float
    ci: float
    mbu: str


def _aggregate_code(code: str, phases: Sequence[Phase]) -> dict:
    embodied = None
    total_oper = 0.0
    fit_base = 0.0
    fit_ecc = 0.0
    latency = None
    area_logic = None
    area_macro = None
    total_scrub = 0.0
    details: List[dict[str, float]] = []

    for phase in phases:
        rec = selector._compute_metrics(
            code,
            node=SCENARIO["node"],
            vdd=SCENARIO["vdd"],
            temp=phase.temp,
            ci=phase.ci,
            capacity_gib=SCENARIO["capacity_gib"],
            bitcell_um2=SCENARIO["bitcell_um2"],
            alt_km=0.0,
            latitude_deg=45.0,
            flux_rel=None,
            mbu=phase.mbu,
            scrub_s=phase.scrub_s,
            lifetime_h=SCENARIO["lifetime_h"] * phase.fraction,
        )
        op = operational_kgco2e(
            rec["E_dyn_kWh"],
            rec["E_leak_kWh"],
            phase.ci,
            rec["E_scrub_kWh"],
        )
        if embodied is None:
            embodied = rec["carbon_kg"] - op
            latency = rec["latency_ns"]
            area_logic = rec["area_logic_mm2"]
            area_macro = rec["area_macro_mm2"]
        fit_base += phase.fraction * rec["fit_base"]
        fit_ecc += phase.fraction * rec["FIT"]
        total_oper += op
        total_scrub += rec["E_scrub_kWh"]
        details.append(
            {
                "phase": phase.name,
                "fraction": phase.fraction,
                "temp_C": phase.temp,
                "scrub_s": phase.scrub_s,
                "ci_kg_per_kwh": phase.ci,
                "mbu": phase.mbu,
                "FIT": rec["FIT"],
                "fit_base": rec["fit_base"],
                "carbon_operational_kg": op,
            }
        )

    carbon_total = (embodied or 0.0) + total_oper
    delta_fit = max(fit_base - fit_ecc, 0.0)
    esii = 0.0 if carbon_total <= 0 else delta_fit / carbon_total
    gs = compute_gs(
        GSInputs(
            fit_base=fit_base,
            fit_ecc=fit_ecc,
            carbon_kg=carbon_total,
            latency_ns=latency or 0.0,
        )
    )

    return {
        "code": code,
        "FIT": fit_ecc,
        "fit_base": fit_base,
        "ESII": esii,
        "carbon_kg": carbon_total,
        "E_scrub_kWh": total_scrub,
        "latency_ns": latency,
        "area_logic_mm2": area_logic,
        "area_macro_mm2": area_macro,
        "GS": gs["GS"],
        "Sr": gs["Sr"],
        "Sc": gs["Sc"],
        "Sl": gs["Sl"],
        "phase_details": details,
    }


def aggregate_records(phases: Sequence[Phase]) -> List[dict]:
    return [_aggregate_code(code, phases) for code in CODES]


def choose_best(records: Iterable[dict], fit_max: float | None = None) -> dict:
    recs = list(records)
    feasible = [rec for rec in recs if fit_max is None or rec["FIT"] <= fit_max]
    if feasible:
        return min(feasible, key=lambda rec: (rec["carbon_kg"], -rec["ESII"]))
    return min(recs, key=lambda rec: (rec["carbon_kg"], -rec["ESII"]))


DUTY_CYCLE_PHASES = (
    Phase("Hot peak", 0.4, 90.0, 5.0, 0.65, "heavy"),
    Phase("Cool cruise", 0.6, 30.0, 45.0, 0.2, "light"),
)

ADAPTIVE_SCRUB_PHASES = (
    Phase("Baseline", 0.85, 40.0, 120.0, 0.3, "moderate"),
    Phase("Storm", 0.15, 70.0, 10.0, 0.5, "heavy"),
)


def main(out_path: Path | None = None) -> dict:
    fit_budget = 1.0e4

    static = selector.select(
        CODES,
        node=SCENARIO["node"],
        vdd=SCENARIO["vdd"],
        temp=45.0,
        ci=0.35,
        capacity_gib=SCENARIO["capacity_gib"],
        bitcell_um2=SCENARIO["bitcell_um2"],
        mbu="moderate",
        scrub_s=40.0,
        lifetime_h=SCENARIO["lifetime_h"],
        constraints={"fit_max": fit_budget},
    )

    duty_records = aggregate_records(DUTY_CYCLE_PHASES)
    duty_best = choose_best(duty_records, fit_max=fit_budget)

    adaptive_records = aggregate_records(ADAPTIVE_SCRUB_PHASES)
    adaptive_best = choose_best(adaptive_records, fit_max=fit_budget)

    result = {
        "fit_budget": fit_budget,
        "static_reference": {
            "scenario": {
                "temp_C": 45.0,
                "scrub_s": 40.0,
                "ci_kg_per_kwh": 0.35,
                "mbu": "moderate",
            },
            "best": static.get("best"),
        },
        "duty_cycle": {
            "phases": [asdict(phase) for phase in DUTY_CYCLE_PHASES],
            "records": duty_records,
            "best": duty_best,
        },
        "adaptive_scrub": {
            "phases": [asdict(phase) for phase in ADAPTIVE_SCRUB_PHASES],
            "records": adaptive_records,
            "best": adaptive_best,
        },
    }

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    default_out = ROOT / "reports" / "analysis" / "workload_scenarios.json"
    main(default_out)
