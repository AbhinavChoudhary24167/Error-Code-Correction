#!/usr/bin/env python3
"""Extract controlled U0/E0 metrics from pinned ORFS JSON and route logs."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "raw" / "openroad" / "work"


def load(design: str, stage: str) -> dict:
    path = BASE / "logs" / "sky130hd" / design / "base" / f"{stage}.json"
    return json.loads(path.read_text(encoding="utf-8"))


u0_grt = load("attempt06_u0", "5_1_grt")
e0_synth = load("attempt06_e0", "1_synth")
e0_grt = load("attempt06_e0", "5_1_grt")
e0_route = load("attempt06_e0", "5_2_route")
e0_finish = load("attempt06_e0", "6_report")
u0_route_log = (BASE / "logs" / "sky130hd" / "attempt06_u0" / "base" / "5_2_route.tmp.log").read_text(encoding="utf-8", errors="replace")
counts = [int(value) for value in re.findall(r"Number of violations = (\d+)", u0_route_log)]

u0_macro_area = 690.12 * 291.64
ecc_macro_area = 261.72 * 225.68
payload = {
    "schema_version": 1,
    "toolchain": {
        "image_id": "f05cee3219a0",
        "image_digest": "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e",
        "openroad_version": "26Q3-1080-gab6fd26351",
        "yosys_version": "0.68+post",
        "klayout_version": "0.30.7",
        "platform": "sky130hd",
        "corner": "TT_025C_1V80",
    },
    "u0": {
        "status": "DETAIL_ROUTE_NOT_CLEAN",
        "completed_stages": ["synthesis", "floorplan", "macro_placement", "pdn", "global_placement", "cts", "global_route"],
        "resize_carry_forward": "UNCHANGED_DATABASE_CARRY_FORWARD_AFTER_RSZ_0090",
        "global_route": {
            "macro_count": u0_grt["globalroute__design__instance__count__macros"],
            "macro_area_um2": u0_grt["globalroute__design__instance__area__macros"],
            "total_instance_area_um2": u0_grt["globalroute__design__instance__area"],
            "standard_cell_area_um2": u0_grt["globalroute__design__instance__area__stdcell"],
            "core_area_um2": u0_grt["globalroute__design__core__area"],
            "utilization_fraction": u0_grt["globalroute__design__instance__utilization"],
            "wirelength_um": u0_grt["globalroute__global_route__wirelength"],
            "vias": u0_grt["globalroute__global_route__vias"],
            "setup_worst_slack_ns": u0_grt["globalroute__timing__setup__ws"],
            "hold_worst_slack_ns": u0_grt["globalroute__timing__hold__ws"],
            "fmax_hz": u0_grt["globalroute__timing__fmax"],
            "max_slew_violations": u0_grt["globalroute__timing__drv__max_slew"],
            "max_cap_violations": u0_grt["globalroute__timing__drv__max_cap"],
            "vectorless_power_w": u0_grt["globalroute__power__total"],
        },
        "detailed_route": {
            "completed": False,
            "clean": False,
            "observed_violation_counts": counts,
            "best_observed_completed_iteration_count": min(counts),
            "last_observed_completed_iteration_count": counts[-1],
            "termination": "USER_OWNED_PROCESS_INTERRUPTED_AFTER_NONCONVERGENCE; iteration 18 had started",
        },
    },
    "e0": {
        "status": "FINAL_LAYOUT_GENERATED_ROUTE_DRC_CLEAN_TIMING_DRV_VIOLATIONS",
        "completed_stages": ["synthesis", "floorplan", "macro_placement", "pdn", "global_placement", "resize", "detailed_placement", "cts", "global_route", "detailed_route", "fill", "extraction", "final_report", "gds_merge"],
        "synthesis": {
            "ecc_logic_standard_cell_area_um2": e0_synth["synth__design__instance__area__stdcell"],
        },
        "global_route": {
            "macro_count": e0_grt["globalroute__design__instance__count__macros"],
            "macro_area_um2": e0_grt["globalroute__design__instance__area__macros"],
            "total_instance_area_um2": e0_grt["globalroute__design__instance__area"],
            "standard_cell_area_um2": e0_grt["globalroute__design__instance__area__stdcell"],
            "core_area_um2": e0_grt["globalroute__design__core__area"],
            "utilization_fraction": e0_grt["globalroute__design__instance__utilization"],
            "wirelength_um": e0_grt["globalroute__global_route__wirelength"],
            "vias": e0_grt["globalroute__global_route__vias"],
            "setup_worst_slack_ns": e0_grt["globalroute__timing__setup__ws"],
            "hold_worst_slack_ns": e0_grt["globalroute__timing__hold__ws"],
            "fmax_hz": e0_grt["globalroute__timing__fmax"],
            "max_slew_violations": e0_grt["globalroute__timing__drv__max_slew"],
            "vectorless_power_w": e0_grt["globalroute__power__total"],
        },
        "detailed_route": {
            "completed": True,
            "clean": e0_route["detailedroute__route__drc_errors"] == 0,
            "drc_errors": e0_route["detailedroute__route__drc_errors"],
            "wirelength_um": e0_route["detailedroute__route__wirelength"],
            "vias": e0_route["detailedroute__route__vias"],
        },
        "finish": {
            "macro_area_um2": e0_finish["finish__design__instance__area__macros"],
            "total_instance_area_um2": e0_finish["finish__design__instance__area"],
            "standard_cell_area_um2": e0_finish["finish__design__instance__area__stdcell"],
            "utilization_fraction": e0_finish["finish__design__instance__utilization"],
            "setup_worst_slack_ns": e0_finish["finish__timing__setup__ws"],
            "hold_worst_slack_ns": e0_finish["finish__timing__hold__ws"],
            "setup_violations": e0_finish["finish__timing__drv__setup_violation_count"],
            "hold_violations": e0_finish["finish__timing__drv__hold_violation_count"],
            "max_slew_violations": e0_finish["finish__timing__drv__max_slew"],
            "max_cap_violations": e0_finish["finish__timing__drv__max_cap"],
            "fmax_hz": e0_finish["finish__timing__fmax"],
            "vectorless_power_w": e0_finish["finish__power__total"],
            "final_gds": "raw/openroad/work/results/sky130hd/attempt06_e0/base/6_final.gds",
            "final_def": "raw/openroad/work/results/sky130hd/attempt06_e0/base/6_final.def",
            "final_spef": "raw/openroad/work/results/sky130hd/attempt06_e0/base/6_final.spef",
        },
    },
    "comparison": {
        "data_macro_area_um2": u0_macro_area,
        "ecc_macro_area_overhead_um2": ecc_macro_area,
        "ecc_macro_area_overhead_percent_of_u0_macro": 100.0 * ecc_macro_area / u0_macro_area,
        "ecc_logic_area_overhead_um2_at_synthesis": e0_synth["synth__design__instance__area__stdcell"],
        "common_global_route_setup_slack_displacement_ns_e0_minus_u0": e0_grt["globalroute__timing__setup__ws"] - u0_grt["globalroute__timing__setup__ws"],
        "common_global_route_fmax_displacement_hz_e0_minus_u0": e0_grt["globalroute__timing__fmax"] - u0_grt["globalroute__timing__fmax"],
        "common_global_route_vectorless_power_displacement_w_e0_minus_u0": e0_grt["globalroute__power__total"] - u0_grt["globalroute__power__total"],
        "comparison_limit": "U0 has no final clean routed result; common-stage global-route comparisons are diagnostic only.",
    },
    "overall": "PARTIAL",
}
target = ROOT / "raw" / "openroad" / "integration_metrics.json"
target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"overall": payload["overall"], "u0": payload["u0"]["status"], "e0": payload["e0"]["status"]}))
