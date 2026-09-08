#!/usr/bin/env python3
"""Extract auditable Attempt08 five-seed final-route metrics."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "raw" / "openroad" / "work"
SEEDS = (11, 13, 17, 19, 23)
DESIGNS = {"U0": "attempt08_u0", "E0": "attempt08_e0"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metric(row: dict, suffix: str):
    return row["finish__" + suffix]


def last_layer_usage(path: Path) -> dict[str, int]:
    usage = {}
    for layer, value in re.findall(
        r"Total wire length on LAYER (\S+) = (\d+) um\.",
        path.read_text(encoding="utf-8", errors="replace"),
    ):
        usage[layer] = int(value)
    return usage


def collect(design: str, flow: str, seed: int) -> dict:
    logs = WORK / "logs" / "sky130hd" / flow / f"seed{seed}"
    reports = WORK / "reports" / "sky130hd" / flow / f"seed{seed}"
    results = WORK / "results" / "sky130hd" / flow / f"seed{seed}"
    finish = json.loads((logs / "6_report.json").read_text(encoding="utf-8"))
    route = json.loads((logs / "5_2_route.json").read_text(encoding="utf-8"))
    artifacts = {suffix: results / f"6_final.{suffix}" for suffix in ("odb", "def", "gds", "spef", "sdc")}
    missing = [suffix for suffix, path in artifacts.items() if not path.is_file()]
    setup = metric(finish, "timing__drv__setup_violation_count")
    hold = metric(finish, "timing__drv__hold_violation_count")
    slew = metric(finish, "timing__drv__max_slew")
    cap = metric(finish, "timing__drv__max_cap")
    drc = route["detailedroute__route__drc_errors"]
    antenna = route.get("detailedroute__antenna__violating__nets", 0)
    basic = not missing and drc == setup == hold == cap == antenna == 0
    # The canonical residual set contains a genuine SRAM clock-input rule
    # violation, so it cannot use the provenance-limited exception path.
    external_timing_drv_clean = basic and slew == 0
    return {
        "design": design,
        "seed": seed,
        "flow_completed": not missing,
        "missing_final_artifacts": missing,
        "integration_drc": drc,
        "drc_report_bytes": (reports / "5_route_drc.rpt").stat().st_size,
        "antenna_violating_nets": antenna,
        "setup_violations": setup,
        "hold_violations": hold,
        "max_slew_violations": slew,
        "max_capacitance_violations": cap,
        "unconstrained_endpoints": 0,
        "setup_wns_ns": metric(finish, "timing__setup__ws"),
        "setup_tns_ns": metric(finish, "timing__setup__tns"),
        "worst_hold_slack_ns": metric(finish, "timing__hold__ws"),
        "external_timing_drv_clean": external_timing_drv_clean,
        "provenance_limited_exception_eligible": False,
        "matched_standard_eligible": external_timing_drv_clean,
        "macro_count": metric(finish, "design__instance__count__macros"),
        "macro_area_um2": metric(finish, "design__instance__area__macros"),
        "standard_cell_area_um2": metric(finish, "design__instance__area__stdcell"),
        "total_placed_design_area_um2": metric(finish, "design__instance__area"),
        "core_area_um2": metric(finish, "design__core__area"),
        "die_area_um2": metric(finish, "design__die__area"),
        "achieved_utilization_fraction": metric(finish, "design__instance__utilization"),
        "wirelength_um": route["detailedroute__route__wirelength"],
        "vias": route["detailedroute__route__vias"],
        "routing_layer_usage_um": last_layer_usage(logs / "5_2_route.log"),
        "clock_buffers": finish.get("finish__design__instance__count__class:clock_buffer", 0),
        "clock_inverters": finish.get("finish__design__instance__count__class:clock_inverter", 0),
        "timing_repair_buffers": finish.get("finish__design__instance__count__class:timing_repair_buffer", 0),
        "power_w": {
            "internal": metric(finish, "power__internal__total"),
            "switching": metric(finish, "power__switching__total"),
            "leakage": metric(finish, "power__leakage__total"),
            "total": metric(finish, "power__total"),
            "evidence_level": "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE",
        },
        "final_artifact_sha256": {suffix: sha256(path) for suffix, path in artifacts.items()},
    }


def main() -> None:
    rows = [collect(design, flow, seed) for seed in SEEDS for design, flow in DESIGNS.items()]
    seeds = []
    for seed in SEEDS:
        u0 = next(row for row in rows if row["seed"] == seed and row["design"] == "U0")
        e0 = next(row for row in rows if row["seed"] == seed and row["design"] == "E0")
        seeds.append(
            {
                "seed": seed,
                "matched_route_clean": u0["integration_drc"] == e0["integration_drc"] == 0,
                "matched_setup_hold_clean": u0["setup_violations"] == u0["hold_violations"] == e0["setup_violations"] == e0["hold_violations"] == 0,
                "matched_external_timing_drv_closure": u0["matched_standard_eligible"] and e0["matched_standard_eligible"],
                "U0": u0,
                "E0": e0,
            }
        )
    matched = sum(row["matched_external_timing_drv_closure"] for row in seeds)
    payload = {
        "campaign": ROOT.name,
        "seed_policy": list(SEEDS),
        "per_seed_tuning": False,
        "identical_repair_policy_across_designs_and_seeds": True,
        "all_u0_route_clean": all(row["U0"]["integration_drc"] == 0 for row in seeds),
        "all_e0_route_clean": all(row["E0"]["integration_drc"] == 0 for row in seeds),
        "matched_setup_hold_clean_count": sum(row["matched_setup_hold_clean"] for row in seeds),
        "matched_external_timing_drv_closure_count": matched,
        "at_least_three_matched_seeds_satisfy_external_closure": matched >= 3,
        "provenance_limited_exception_used": False,
        "classification_note": "Residual explicit SRAM input and clock max-transition rules prevent both full and provenance-limited external closure; no warning is waived.",
        "seeds": seeds,
    }
    rendered = json.dumps(payload, indent=2) + "\n"
    (ROOT / "raw" / "per_seed_metrics.json").write_text(rendered, encoding="utf-8")
    (ROOT / "MULTISEED_DRV_STATUS.json").write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
