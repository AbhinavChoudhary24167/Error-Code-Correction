#!/usr/bin/env python3
"""Render Attempt08's status, comparison, and narrative evidence from raw results."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
PRIOR = ROOT.parent / "gate3_attempt07_sram22_matched_physical_closure"
IMAGE = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
UPSTREAM = "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, payload: dict) -> None:
    (ROOT / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_md(name: str, text: str) -> None:
    (ROOT / name).write_text(text.strip() + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(*args: str) -> str:
    run = subprocess.run(["git", *args], cwd=REPO, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return run.stdout.strip() if run.returncode == 0 else "UNAVAILABLE"


def delta(after: float, before: float) -> float:
    return round(after - before, 12)


def fmt(value: float) -> str:
    return f"{value:.9g}"


inventory = load(ROOT / "SLEW_VIOLATION_INVENTORY.json")
multi = load(ROOT / "MULTISEED_DRV_STATUS.json")
prior_multi = load(PRIOR / "MULTISEED_STATUS.json")
u0 = multi["seeds"][0]["U0"]
e0 = multi["seeds"][0]["E0"]
pu0 = prior_multi["seeds"][0]["U0"]
pe0 = prior_multi["seeds"][0]["E0"]
regression_path = ROOT / "REGRESSION_STATUS.json"
regression = load(regression_path) if regression_path.is_file() else {
    "overall_status": "PENDING",
    "campaign_local_tests": {"status": "PENDING"},
    "make": {"status": "PENDING"},
    "make_test": {"status": "PENDING"},
    "full_pytest": {"status": "PENDING"},
    "protected_date_baseline": {"status": "PENDING", "protected_file_count": None},
    "prior_campaign_evidence": {"status": "PENDING"},
    "frozen_sram22_sources": {"status": "PENDING"},
    "new_regression_count": None,
}

environment = {
    "schema_version": 1,
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "campaign": ROOT.name,
    "repository_commit": git_value("rev-parse", "HEAD"),
    "repository_branch": git_value("branch", "--show-current"),
    "openroad_flow_image": IMAGE,
    "openroad_version": "26Q3-1080-gab6fd26351",
    "sram22_upstream_commit": UPSTREAM,
    "technology": "SKY130HD",
    "pvt": "TT / 25 C / 1.8 V",
    "clock": {"period_ns": 10.0, "frequency_mhz": 100.0, "uncertainty_ns": 0.1},
    "routing_stack": ["met1", "met2", "met3", "met4", "met5"],
    "rc_and_extraction": "sky130hd nominal setRC.tcl; final SPEF extraction corner X",
    "matched_policy": "Attempt07 floorplan, macro placement/halo, top-edge IO, PDN, synthesis, CTS, legalization and routing policy retained; one common repair decision rule",
    "constraint_relaxation": False,
    "liberty_sha256": {path.name: sha(path) for path in sorted((ROOT / "raw" / "liberty").glob("*.lib"))},
    "canonical_sdc_sha256": {
        design: sha(ROOT / "raw" / "openroad" / "work" / "results" / "sky130hd" / f"attempt08_{design.lower()}" / "seed11" / "6_final.sdc")
        for design in ("U0", "E0")
    },
}
write_json("ENVIRONMENT_MANIFEST.json", environment)

comparison = {
    "schema_version": 1,
    "classification": "SLEW_REPAIR_PARTIAL",
    "canonical_seed": 11,
    "U0": u0,
    "E0": e0,
    "attempt08_E0_minus_U0": {
        "macro_area_um2": delta(e0["macro_area_um2"], u0["macro_area_um2"]),
        "standard_cell_area_um2": delta(e0["standard_cell_area_um2"], u0["standard_cell_area_um2"]),
        "total_placed_design_area_um2": delta(e0["total_placed_design_area_um2"], u0["total_placed_design_area_um2"]),
        "wirelength_um": delta(e0["wirelength_um"], u0["wirelength_um"]),
        "vias": e0["vias"] - u0["vias"],
        "power_w": delta(e0["power_w"]["total"], u0["power_w"]["total"]),
    },
    "repair_displacement_vs_attempt07": {
        "U0": {
            "standard_cell_area_um2": delta(u0["standard_cell_area_um2"], pu0["standard_cell_area_um2"]),
            "total_placed_design_area_um2": delta(u0["total_placed_design_area_um2"], pu0["total_placed_design_area_um2"]),
            "wirelength_um": delta(u0["wirelength_um"], pu0["wirelength_um"]),
            "vias": u0["vias"] - pu0["vias"],
            "power_w": delta(u0["power_w"]["total"], pu0["power_w"]["total"]),
            "setup_wns_ns": delta(u0["setup_wns_ns"], pu0["setup_wns_ns"]),
            "worst_hold_slack_ns": delta(u0["worst_hold_slack_ns"], pu0["worst_hold_slack_ns"]),
        },
        "E0": {
            "standard_cell_area_um2": delta(e0["standard_cell_area_um2"], pe0["standard_cell_area_um2"]),
            "total_placed_design_area_um2": delta(e0["total_placed_design_area_um2"], pe0["total_placed_design_area_um2"]),
            "wirelength_um": delta(e0["wirelength_um"], pe0["wirelength_um"]),
            "vias": e0["vias"] - pe0["vias"],
            "power_w": delta(e0["power_w"]["total"], pe0["power_w"]["total"]),
            "setup_wns_ns": delta(e0["setup_wns_ns"], pe0["setup_wns_ns"]),
            "worst_hold_slack_ns": delta(e0["worst_hold_slack_ns"], pe0["worst_hold_slack_ns"]),
        },
    },
    "power_evidence_level": "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE",
    "energy_per_access": "NOT_QUALIFIED",
    "matched_comparison_validity": "DIAGNOSTIC_ONLY_SLEW_REPAIR_PARTIAL",
}
write_json("ATTEMPT08_MATCHED_COMPARISON.json", comparison)

dc = comparison["repair_displacement_vs_attempt07"]
write_md("ATTEMPT08_MATCHED_COMPARISON.md", f"""
# Attempt08 matched final-route comparison

Canonical seed 11 was recomputed from fresh final ODB/DEF/GDS/SPEF results after the common repair policy. No Attempt07 physical metric is reused as an Attempt08 result.

| Metric | U0 | E0 | E0 - U0 |
|---|---:|---:|---:|
| Macro area (um^2) | {fmt(u0['macro_area_um2'])} | {fmt(e0['macro_area_um2'])} | {fmt(comparison['attempt08_E0_minus_U0']['macro_area_um2'])} |
| Standard/physical-cell area (um^2) | {fmt(u0['standard_cell_area_um2'])} | {fmt(e0['standard_cell_area_um2'])} | {fmt(comparison['attempt08_E0_minus_U0']['standard_cell_area_um2'])} |
| Total placed area (um^2) | {fmt(u0['total_placed_design_area_um2'])} | {fmt(e0['total_placed_design_area_um2'])} | {fmt(comparison['attempt08_E0_minus_U0']['total_placed_design_area_um2'])} |
| Core / die area (um^2) | {fmt(u0['core_area_um2'])} / {fmt(u0['die_area_um2'])} | {fmt(e0['core_area_um2'])} / {fmt(e0['die_area_um2'])} | — |
| Wirelength (um) | {u0['wirelength_um']} | {e0['wirelength_um']} | {comparison['attempt08_E0_minus_U0']['wirelength_um']} |
| Vias | {u0['vias']} | {e0['vias']} | {comparison['attempt08_E0_minus_U0']['vias']} |
| Clock buffers / inverters | {u0['clock_buffers']} / {u0['clock_inverters']} | {e0['clock_buffers']} / {e0['clock_inverters']} | — |
| Setup WNS/TNS (ns) | {fmt(u0['setup_wns_ns'])} / {fmt(u0['setup_tns_ns'])} | {fmt(e0['setup_wns_ns'])} / {fmt(e0['setup_tns_ns'])} | — |
| Worst hold slack (ns) | {fmt(u0['worst_hold_slack_ns'])} | {fmt(e0['worst_hold_slack_ns'])} | — |
| Vectorless post-route power (W) | {fmt(u0['power_w']['total'])} | {fmt(e0['power_w']['total'])} | {fmt(comparison['attempt08_E0_minus_U0']['power_w'])} |

Repair displacement versus Attempt07 is U0: {fmt(dc['U0']['standard_cell_area_um2'])} um^2 cells, {dc['U0']['wirelength_um']} um wire, {dc['U0']['vias']} vias, and {fmt(dc['U0']['power_w'])} W. E0: {fmt(dc['E0']['standard_cell_area_um2'])} um^2 cells, {dc['E0']['wirelength_um']} um wire, {dc['E0']['vias']} vias, and {fmt(dc['E0']['power_w'])} W. Power remains `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`; energy/access remains `NOT_QUALIFIED`.
""")

write_md("SLEW_INTERFACE_CORRELATION.md", """
# Slew/interface correlation

The counts are structural, not a random cloud of routed nets. In canonical U0, all 65/65 rows are SRAM interface pins: 64 data-macro outputs plus `rstb`. In canonical E0, 77/80 rows are SRAM interface pins: all 72 macro outputs, data-macro `rstb`, `clk`, `din[56]`, `din[57]`, and ECC-macro `rstb`. The other three report rows are three pins on one ordinary standard-cell electrical net.

| Design / macro | Input pins | Output pins | Pins with an applicable max-transition rule | Violating report rows |
|---|---:|---:|---:|---:|
| U0 `sram22_256x64m4w8` | 84 | 64 | 148 | 65 |
| E0 `sram22_256x64m4w8` | 84 | 64 | 148 | 68 |
| E0 `sram22_256x8m8w1` | 28 | 8 | 36 | 9 |

All inputs carry explicit pin-level 0.351 ns rules. All outputs inherit the explicit library-level 0.04 ns default. The E0 accepted repair eliminates `din[56]` and `din[57]`; it does not change either macro or hide any remaining row.
""")

write_md("SRAM22_LIBERTY_TRANSITION_AUDIT.md", """
# SRAM22 Liberty transition audit

The exact TT/25 C/1.8 V files used by OpenROAD are preserved under `raw/liberty`. Both libraries set input and output thresholds to 50%, slew lower thresholds to 10%, slew upper thresholds to 90%, and `default_max_transition : 0.04`. Every input pin has explicit `max_transition : 0.351`. The delay template input-transition axis is `[0.002, 0.008, 0.03, 0.073, 0.138, 0.231, 0.351]` ns and its output-capacitance axis is `[0.007, 0.013, 0.033, 0.065, 0.13, 0.26, 0.52]` pF. Output timing is related to rising `clk`; output pins have `max_capacitance : 0.52` but no pin-level max-transition override.

Thus macro-input rows have two distinct, aligned facts: `EXPLICIT_MAX_TRANSITION_DESIGN_RULE` at 0.351 ns and `LIBRARY_CHARACTERIZATION_RANGE_LIMIT` at 0.351 ns. They are not dismissed as mere extrapolation warnings.

Macro-output rows expose a different defect. The inherited 0.04 ns value is explicit, but each output's own characterized table already predicts a transition above it at the minimum 0.007 pF load and fastest 0.002 ns input. For `sram22_256x64m4w8`, representative `dout[0]` values are 0.137135 ns rise and 0.083310 ns fall. For `sram22_256x8m8w1`, they are 0.134220 ns rise and 0.081710 ns fall. Therefore 0.04 ns is self-incompatible with the delivered macro characterization. This is recorded as `EXPLICIT_MAX_TRANSITION_DESIGN_RULE_WITH_SELF_INCONSISTENT_OUTPUT_TABLE`, not silently removed and not confused with physical invalidity.

The characterization was not independently regenerated. The upstream library's physical validity beyond its documented axes remains unsupported.
""")

write_md("STANDARD_CELL_TRANSITION_AUDIT.md", """
# SKY130HD standard-cell transition audit

The preserved SKY130HD TT library declares `default_max_transition : 1.5000000000`; affected `sky130_fd_sc_hd__xnor2_1`, `sky130_fd_sc_hd__xnor3_1`, and `sky130_fd_sc_hd__xor2_1` pins do not create the 0.60 ns limit. The common top-level SDC does: `set_max_transition 0.60 [current_design]`.

On net `_055_`, `_513_/Y` drives `_518_/A` and `_540_/A` (fanout 2). Exact extracted STA gives a worst rising transition of 0.646700442 ns at the driver and 0.646702707/0.646722376 ns at the sinks, about 0.0467 ns above the top-level rule. This is one genuine Class-A electrical net represented by three report rows. Replacing only the legal driver `xnor2_1` with `xnor2_2` gives 0.394375741 ns in the non-persistent candidate experiment and removes all three rows in final route.
""")

write_md("SLEW_PROVENANCE_CLASSIFICATION.md", """
# Slew provenance classification

| Design | A | B | C | D | E | F | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| U0 original | 0 | 1 | 64 | 0 | 0 | 0 | 65 |
| E0 original | 3 | 4 | 72 | 0 | 1 | 0 | 80 |

Class A is the single E0 standard-cell net `_055_` reported at three pins. Class B is U0 data `rstb`, E0 data `rstb`, data `din[56:57]`, and ECC `rstb`. Class C is every SRAM output (64 U0; 64 data plus 8 ECC in E0). Class E is the E0 data-macro clock input. There are no Class-D primary-IO rows and no Class-F rows whose rule source cannot be located.

The 136 original Class-C rows also carry a secondary upstream provenance defect: the explicit inherited 0.04 ns rule contradicts their own output tables. They remain Class C because the violating object is an SRAM output; no warning is waived. After repair E0 has B2/C72/E1 and U0 remains B1/C64. The explicit, out-of-characterization-range B/E rows prevent the provenance-limited exception.
""")

e0d = dc["E0"]
write_md("DRV_REPAIR_SEQUENCE.md", f"""
# DRV repair sequence

All candidate swaps were first evaluated non-persistently against the frozen Attempt07 seed-11 ODB/SDC/SPEF. The accepted common decision rule is: resize a legal external driver only when constrained STA proves the target row closes; never edit macros or constraints. U0 had no target satisfying that rule. E0 received three legal replacements before global routing, followed by ordinary detailed placement and routing.

| Repair | Reason | Rows before -> after | Candidate result |
|---|---|---:|---|
| `_513_`: `xnor2_1` -> `xnor2_2` | Class-A fanout/RC driver | 3 -> 0 | 0.646700442 -> 0.394375741 ns |
| `din[56]` driver: `buf_4` -> `buf_8` | Long extracted route to macro input | 1 -> 0 | 0.367528468 -> 0.226246253 ns |
| `din[57]` driver: `buf_4` -> `buf_8` | Long extracted route to macro input | 1 -> 0 | 0.393737197 -> 0.243002206 ns |

Applied together, E0 goes 80 -> {e0['max_slew_violations']} rows. Setup remains 0 violations (WNS {fmt(pe0['setup_wns_ns'])} -> {fmt(e0['setup_wns_ns'])} ns), hold remains 0 (worst slack {fmt(pe0['worst_hold_slack_ns'])} -> {fmt(e0['worst_hold_slack_ns'])} ns), route DRC/capacitance/antenna remain 0, standard-cell area changes by {fmt(e0d['standard_cell_area_um2'])} um^2, total placed area by {fmt(e0d['total_placed_design_area_um2'])} um^2, wirelength by {e0d['wirelength_um']} um, vias by {e0d['vias']}, and vectorless estimated power by {fmt(e0d['power_w'])} W. Legalization moved 5.4 um total/max with 0% HPWL change in the canonical repair log.

Rejected experiments are also preserved. A `clkbuf_16` on data `rstb` only improves 0.615880728 -> 0.602424264 ns; ECC `rstb` reaches 0.351614386 ns at best, still above 0.351; alternative data-clock `buf_16`/`bufbuf_16` cells worsen 0.511382282 ns to 0.519892454/0.519068480 ns. None was applied. No per-seed tuning occurred.
""")

write_md("U0_FINAL_DRV_CLOSURE.md", f"""
# U0 final DRV closure

Canonical seed 11 completed final ODB/DEF/GDS/SPEF with setup 0, hold 0, integration DRC 0, capacitance 0, antenna 0, and unconstrained endpoints 0. Setup WNS/TNS is {fmt(u0['setup_wns_ns'])}/{fmt(u0['setup_tns_ns'])} ns and worst hold slack is {fmt(u0['worst_hold_slack_ns'])} ns.

The final slew count is {u0['max_slew_violations']}: 64 Class-C data-macro outputs governed by the self-inconsistent inherited 0.04 ns macro-library rule and one genuine Class-B data-macro `rstb` at about 0.62 ns against its explicit 0.351 ns input rule/range. The strongest legitimate external substitution does not close `rstb`. U0 is therefore not externally timing/DRV clean and is not eligible for the provenance-limited exception.
""")

write_md("E0_FINAL_DRV_CLOSURE.md", f"""
# E0 final DRV closure

Canonical seed 11 completed final ODB/DEF/GDS/SPEF with setup 0, hold 0, integration DRC 0, capacitance 0, antenna 0, and unconstrained endpoints 0. Setup WNS/TNS is {fmt(e0['setup_wns_ns'])}/{fmt(e0['setup_tns_ns'])} ns and worst hold slack is {fmt(e0['worst_hold_slack_ns'])} ns.

The accepted repairs remove every ordinary standard-cell row and both long-route `din[56:57]` rows, reducing slew 80 -> {e0['max_slew_violations']}. The residual distribution is B2/C72/E1: data `rstb`, ECC `rstb`, all 72 macro outputs, and the data-macro clock input. Because the clock and two input rows violate explicit 0.351 ns macro-input rules and lie outside the characterized input axis, E0 is neither fully clean nor provenance-limited-only.
""")

write_md("GATE3_REASSESSMENT_READINESS.md", """
# Gate-3 reassessment readiness

Recommendation: `KEEP_GATE3_FAILED`.

Attempt08 does not establish either qualifying classification. Genuine repairable integration DRVs were reduced, but explicit SRAM-input and clock transition violations remain, so `SLEW_REPAIR_PARTIAL` applies. The matched pair is not externally timing/DRV clean and the macro-provenance exception is unavailable. Gate-3 reassessment is not started, the historical Gate-3 state remains `FAIL`, and Gate 4 remains `NOT_STARTED_UNAUTHORIZED`.

The hard-macro provenance limitations remain explicit: `MACRO_INTERNAL_DRC_NOT_INDEPENDENTLY_SIGNOFF_QUALIFIED`, `PHYSICAL_LVS = NOT_INDEPENDENTLY_REPRODUCED`, Liberty not independently regenerated, and physical bitcell interleaving unavailable. Macro sources and internals are unchanged. Because external STA/DRV has not reached clean or provenance-limited-only status, the Gate-3 reassessment philosophy's prerequisite has not been reached.
""")

status = {
    "schema_version": 1,
    "campaign": f"campaigns/iscas_sustainability_extension/memory_compiler/{ROOT.name}",
    "final_attempt08_classification": "SLEW_REPAIR_PARTIAL",
    "sram22_upstream_commit": UPSTREAM,
    "technology_pvt": "SKY130HD TT/25C/1.8V",
    "common_clock": {"period_ns": 10.0, "frequency_mhz": 100.0, "uncertainty_ns": 0.1},
    "original_slew": {
        "U0": {"count": 65, "class_distribution_A_through_F": inventory["per_design"]["U0"]["class_distribution_A_through_F"]},
        "E0": {"count": 80, "class_distribution_A_through_F": inventory["per_design"]["E0"]["class_distribution_A_through_F"]},
    },
    "accepted_repairs": [
        {"design": "E0", "instance": "_513_", "from": "sky130_fd_sc_hd__xnor2_1", "to": "sky130_fd_sc_hd__xnor2_2"},
        {"design": "E0", "target": "u_protected_memory.u_data/din[56]", "from": "sky130_fd_sc_hd__buf_4", "to": "sky130_fd_sc_hd__buf_8"},
        {"design": "E0", "target": "u_protected_memory.u_data/din[57]", "from": "sky130_fd_sc_hd__buf_4", "to": "sky130_fd_sc_hd__buf_8"},
    ],
    "constraint_relaxed_to_force_pass": False,
    "macro_internals_changed": False,
    "canonical": {"U0": u0, "E0": e0},
    "canonical_remaining_slew_distribution": {
        "U0": {"A": 0, "B": 1, "C": 64, "D": 0, "E": 0, "F": 0},
        "E0": {"A": 0, "B": 2, "C": 72, "D": 0, "E": 1, "F": 0},
    },
    "canonical_pair_externally_timing_drv_clean": False,
    "provenance_limited_exception_eligible": False,
    "multiseed": {
        "seeds": multi["seed_policy"],
        "all_u0_route_clean": multi["all_u0_route_clean"],
        "all_e0_route_clean": multi["all_e0_route_clean"],
        "matched_setup_hold_clean_count": multi["matched_setup_hold_clean_count"],
        "matched_external_timing_drv_closure_count": multi["matched_external_timing_drv_closure_count"],
        "e0_seed17_hold_violations": next(row for row in multi["seeds"] if row["seed"] == 17)["E0"]["hold_violations"],
    },
    "power_evidence_level": "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE",
    "energy_per_access": "NOT_QUALIFIED",
    "sram_internal_drc_disposition": "MACRO_INTERNAL_DRC_NOT_INDEPENDENTLY_SIGNOFF_QUALIFIED",
    "physical_lvs": "NOT_INDEPENDENTLY_REPRODUCED",
    "remaining_unsupported_claims": [
        "SRAM22 macro-internal foundry signoff DRC",
        "independently reproduced physical LVS",
        "independently regenerated SRAM22 Liberty characterization",
        "physical bitcell interleaving",
        "activity-qualified power and energy per access",
    ],
    "regression": regression,
    "gate3_recommendation": "KEEP_GATE3_FAILED",
    "gate3_historical_state": "FAIL",
    "gate3_reassessment_started": False,
    "gate4_state": "NOT_STARTED_UNAUTHORIZED",
    "attempt09_started": False,
}
write_json("ATTEMPT08_STATUS.json", status)

seed17 = next(row for row in multi["seeds"] if row["seed"] == 17)
write_md("ATTEMPT08_SUMMARY.md", f"""
# Attempt08 summary

Attempt08 is classified `SLEW_REPAIR_PARTIAL`; recommendation is `KEEP_GATE3_FAILED`. The frozen original inventory is U0 65 = A0/B1/C64/D0/E0/F0 and E0 80 = A3/B4/C72/D0/E1/F0. The population is structurally tied to SRAM interfaces (65/65 U0 and 77/80 E0), with E0's other three report rows representing one repairable standard-cell net.

Three legal E0 driver upgrades remove that standard-cell net and `din[56:57]`, producing canonical U0/E0 slew counts {u0['max_slew_violations']}/{e0['max_slew_violations']}. No constraint or macro was changed. Setup, hold, integration DRC, capacitance and antenna remain zero in both canonical designs. U0 WNS/TNS is {fmt(u0['setup_wns_ns'])}/{fmt(u0['setup_tns_ns'])} ns; E0 is {fmt(e0['setup_wns_ns'])}/{fmt(e0['setup_tns_ns'])} ns.

The 0.04 ns macro-output default is explicit but contradicts the delivered output tables, so those Class-C rows have documented upstream provenance limitations. The remaining macro-input and clock rows are different: explicit 0.351 ns pin rules coincide with the maximum characterized input-transition axis and are genuinely exceeded. Consequently the canonical pair cannot use the provenance-limited exception.

All five matched seeds completed. U0/E0 route-clean status is {multi['all_u0_route_clean']}/{multi['all_e0_route_clean']}; matched setup/hold-clean pairs are {multi['matched_setup_hold_clean_count']}/5; matched external timing/DRV-closure pairs are {multi['matched_external_timing_drv_closure_count']}/5. E0 seed 17 now has {seed17['E0']['hold_violations']} hold violations and worst hold slack {fmt(seed17['E0']['worst_hold_slack_ns'])} ns. Historical Gate 3 remains failed; reassessment, Attempt09, Gate 4, and carbon work were not started.
""")
