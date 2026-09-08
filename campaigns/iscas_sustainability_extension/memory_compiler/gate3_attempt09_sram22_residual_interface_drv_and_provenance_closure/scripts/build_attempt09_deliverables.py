#!/usr/bin/env python3
"""Build the final Attempt09 evidence package from frozen raw results."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT.parent / "gate3_attempt08_sram22_slew_provenance_and_drv_closure"
IMAGE = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
UPSTREAM = "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, payload: dict) -> None:
    (ROOT / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_md(name: str, body: str) -> None:
    (ROOT / name).write_text(body.strip() + "\n", encoding="utf-8")


def fmt(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:.9g}" if isinstance(value, float) else str(value)


def delta(a, b):
    return a - b


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() or "UNKNOWN"


def counterfactual_rows(design: str) -> list[dict]:
    path = ROOT / "raw" / "diagnostics" / "class_c_counterfactual" / f"{design.lower()}.log"
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"max slew\n\nPin\s+Limit\s+Slew\s+Slack\n-+\n(?P<body>.*?)(?:\n\n|\Z)", text, re.S)
    if not match:
        return []
    rows = []
    for line in match.group("body").splitlines():
        row = re.match(r"(?P<object>\S+)\s+(?P<limit>-?[\d.]+)\s+(?P<slew>-?[\d.]+)\s+(?P<slack>-?[\d.]+)\s+\(VIOLATED\)", line)
        if row:
            rows.append({"object": row["object"].replace("\\[", "[").replace("\\]", "]"), "limit_ns": float(row["limit"]), "slew_ns": float(row["slew"]), "slack_ns": float(row["slack"])})
    return rows


multi = load(ROOT / "MULTISEED_EXTERNAL_CLOSURE.json")
inventory = load(ROOT / "RESIDUAL_EXTERNAL_DRV_INVENTORY.json")
class_c = load(ROOT / "raw" / "class_c_output_measurements.json")
provenance = load(ROOT / "raw" / "sram22_output_provenance_audit.json")
experiments = load(ROOT / "raw" / "repair_experiments" / "experiment_summary.json")
diagnostic_manifest = load(ROOT / "raw" / "diagnostics" / "class_c_counterfactual" / "diagnostic_liberty_manifest.json")
prior_multi = load(PRIOR / "MULTISEED_DRV_STATUS.json")
regression_path = ROOT / "REGRESSION_STATUS.json"
regression = load(regression_path) if regression_path.is_file() else {"overall_status": "PENDING", "new_regression_count": None}
u0 = multi["seeds"][0]["U0"]
e0 = multi["seeds"][0]["E0"]
seed17_e0 = next(p for p in multi["seeds"] if p["seed"] == 17)["E0"]
pu0 = prior_multi["seeds"][0]["U0"]
pe0 = prior_multi["seeds"][0]["E0"]
residual = {(r["design"], r["object"]): r for r in inventory["records"]}
closed = {(r["design"], r["object"]): r for r in inventory["closed_target_records"]}
cf = {design: counterfactual_rows(design) for design in ("U0", "E0")}

environment = {
    "schema_version": 1,
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "campaign": ROOT.name,
    "repository_commit": git_value("rev-parse", "HEAD"),
    "repository_branch": git_value("branch", "--show-current"),
    "openroad_flow_image": IMAGE,
    "openroad_version": "26Q3-1080-gab6fd26351",
    "sram22_upstream_commit": UPSTREAM,
    "technology_pvt": "SKY130HD TT/25C/1.8V",
    "clock": {"period_ns": 10.0, "frequency_mhz": 100.0, "uncertainty_ns": 0.1},
    "routing_stack": ["met1", "met2", "met3", "met4", "met5"],
    "constraint_relaxation": False,
    "production_liberty_sha256": {path.name: sha(path) for path in sorted((ROOT / "raw" / "liberty").glob("*.lib"))},
}
write_json("ENVIRONMENT_MANIFEST.json", environment)

displacement = {
    "U0": {
        "standard_cell_area_um2": delta(u0["standard_cell_area_um2"], pu0["standard_cell_area_um2"]),
        "total_placed_design_area_um2": delta(u0["total_placed_design_area_um2"], pu0["total_placed_design_area_um2"]),
        "wirelength_um": delta(u0["wirelength_um"], pu0["wirelength_um"]),
        "vias": delta(u0["vias"], pu0["vias"]),
        "setup_wns_ns": delta(u0["setup_wns_ns"], pu0["setup_wns_ns"]),
        "worst_hold_slack_ns": delta(u0["worst_hold_slack_ns"], pu0["worst_hold_slack_ns"]),
        "power_w": delta(u0["power_w"]["total"], pu0["power_w"]["total"]),
    },
    "E0": {
        "standard_cell_area_um2": delta(e0["standard_cell_area_um2"], pe0["standard_cell_area_um2"]),
        "total_placed_design_area_um2": delta(e0["total_placed_design_area_um2"], pe0["total_placed_design_area_um2"]),
        "wirelength_um": delta(e0["wirelength_um"], pe0["wirelength_um"]),
        "vias": delta(e0["vias"], pe0["vias"]),
        "setup_wns_ns": delta(e0["setup_wns_ns"], pe0["setup_wns_ns"]),
        "worst_hold_slack_ns": delta(e0["worst_hold_slack_ns"], pe0["worst_hold_slack_ns"]),
        "power_w": delta(e0["power_w"]["total"], pe0["power_w"]["total"]),
    },
}
ppa = {
    "schema_version": 1,
    "canonical_seed": 11,
    "U0": u0,
    "E0": e0,
    "E0_minus_U0": {
        "standard_cell_area_um2": delta(e0["standard_cell_area_um2"], u0["standard_cell_area_um2"]),
        "total_placed_design_area_um2": delta(e0["total_placed_design_area_um2"], u0["total_placed_design_area_um2"]),
        "wirelength_um": delta(e0["wirelength_um"], u0["wirelength_um"]),
        "vias": delta(e0["vias"], u0["vias"]),
        "power_w": delta(e0["power_w"]["total"], u0["power_w"]["total"]),
    },
    "attempt09_minus_attempt08": displacement,
    "power_evidence_level": "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE",
    "energy_per_access": "NOT_QUALIFIED",
    "comparison_validity": "DIAGNOSTIC_ONLY_RESIDUAL_SRAM_INPUT_DRV_FAIL",
}
write_json("FINAL_MATCHED_PPA.json", ppa)

tt_files = [r for r in provenance["files"] if "_tt_025C_1v80.lib" in r["file"]]
prov_lines = [
    "# SRAM22 output-transition provenance", "",
    "Classification: `UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY`. Canonical disposition: `PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV`. This is neither a foundry waiver nor signoff certification; every original warning remains in production reports.", "",
    "Both production TT views contain `default_max_transition : 0.04`. All 72 selected macro output pins (64 + 8) inherit it: none has a pin-level `max_transition` override, while every output has `max_capacitance : 0.52`. Thresholds are 10–90% slew and 50% input/output switching thresholds.", "",
    "| Frozen view | Outputs | Output overrides | Transition tables | Minimum grid value (ns) | Min-load/fast-input range (ns) |", "|---|---:|---:|---:|---:|---:|",
]
for row in provenance["files"]:
    prov_lines.append(f"| `{Path(row['file']).name}` | {row['output_pin_count']} | {row['output_pin_max_transition_override_count']} | {row['transition_table_count']} | {row['minimum_transition_table_value_ns']:.6f} | {row['minimum_load_fastest_input_value_range_ns'][0]:.6f}–{row['minimum_load_fastest_input_value_range_ns'][1]:.6f} |")
prov_lines += [
    "", "The audit covers both locally frozen macros at FF/−40 C/1.95 V, TT/25 C/1.8 V, and SS/100 C/1.6 V: 6/6 published views and all four bus-scope output transition tables (`rise_transition`, `fall_transition`, `retain_rise_slew`, `retain_fall_slew`). In every table the value at the fastest input and minimum 0.007 pF characterized load is already greater than 0.04 ns. The causal contradiction therefore exists before routed external RC is added.", "",
]
for design in ("U0", "E0"):
    stat = class_c["statistics"][design]
    prov_lines.append(f"- {design}: {class_c['per_design_count'][design]} structural output rows; reported-transition/0.04 ratio min/median/max = {stat['transition_to_0p04_ratio']['minimum']:.6f}/{stat['transition_to_0p04_ratio']['median']:.6f}/{stat['transition_to_0p04_ratio']['maximum']:.6f}. Extracted parasitic load min/median/max = {stat['extracted_parasitic_capacitance_pf']['minimum']:.9g}/{stat['extracted_parasitic_capacitance_pf']['median']:.9g}/{stat['extracted_parasitic_capacitance_pf']['maximum']:.9g} pF; below/within/above the 0.007–0.52 pF characterized domain = {stat['loads_below_characterized_minimum']}/{stat['loads_within_characterized_domain']}/{stat['loads_above_characterized_maximum']}.")
prov_lines += ["", "The SPEF declares `PIN_CAP NONE`, so the load comparison deliberately reports extracted D_NET parasitic capacitance as a reproducible lower bound and does not invent receiver Liberty capacitance. Full per-output measurements are preserved in `raw/class_c_output_measurements.json`; full per-view table evidence is in `raw/sram22_output_provenance_audit.json`. Counts remain tied exactly to macro width across normal rerouting, while the same Liberty contradiction exists at minimum characterized load, so excessive external RC alone cannot explain Class C."]
write_md("SRAM22_OUTPUT_TRANSITION_PROVENANCE.md", "\n".join(prov_lines))

write_md("CLASS_C_COUNTERFACTUAL_DIAGNOSTIC.md", f"""
# Class-C counterfactual diagnostic

This read-only diagnostic loaded the canonical final seed-11 ODB/SDC/SPEF and unchanged timing tables, propagation delays, loads, netlist, placement, and routing. Separately labelled diagnostic Liberty copies changed only the library-level `default_max_transition` from 0.04 to the standard-cell-level 1.50 ns, thereby excluding the inherited SRAM-output rule. Production Liberty remained byte-identical before/after, as recorded in `raw/diagnostics/class_c_counterfactual/diagnostic_liberty_manifest.json`; the copies were never used to generate production results.

U0 counterfactual residual rows: {len(cf['U0'])}, `{', '.join(r['object'] for r in cf['U0'])}`. E0 counterfactual residual rows: {len(cf['E0'])}, `{', '.join(r['object'] for r in cf['E0'])}`. Thus Class C disappears without any physical or timing-table change, but each design's genuine data-macro `rstb` violation remains. There are no other canonical external max-transition violations. This supports the Class-C causal disposition but cannot make Attempt09 pass.
""")

rstb_exps = [r for r in experiments["records"] if r["target"].endswith("/rstb")]
rstb_lines = [
    "# RSTB repair", "",
    "The 0.351 ns SRAM-input requirement was never relaxed. All candidates were legal external SKY130HD cells inserted close to the target on the frozen Attempt08 canonical ODB; two-stage candidates preserve reset polarity. Every nonpersistent experiment is listed below and its complete log remains under `raw/repair_experiments`.", "",
    "| Target | Candidate | Form | Before → after (ns) | Closes? | Log |", "|---|---|---|---:|:---:|---|",
]
for row in rstb_exps:
    rstb_lines.append(f"| `{row['target']}` | `{row['cell']}` | {row['experiment_kind']} | {row['before_slew_ns']:.9f} → {row['after_slew_ns']:.9f} | {'yes' if row['closes_target_at_placement_estimate'] else 'no'} | `{row['log']}` |")
u0rst = residual[("U0", "u_data/rstb")]
e0rst = residual[("E0", "u_protected_memory.u_data/rstb")]
eccrst = closed[("E0", "u_protected_memory.u_ecc/rstb")]
rstb_lines += [
    "", f"ECC `rstb` accepted the smallest ordinary phase-preserving repair that closed: two `sky130_fd_sc_hd__inv_16` stages. Its canonical final slew is {eccrst['transition_value_ns']:.9f}/0.351 ns. We rejected the larger clock-inverter solution even though it also closed.", "",
    f"The 256×64 data-macro load is infeasible with every legal single-output candidate tested: best U0 is {min(r['after_slew_ns'] for r in rstb_exps if r['design']=='U0'):.9f} ns; best E0 is {min(r['after_slew_ns'] for r in rstb_exps if r['design']=='E0' and '.u_data/' in r['target']):.9f} ns, but its opposite edge is the limiting failure. Parallel drivers were not used because they would create an electrically invalid multi-driver net. Canonical U0/E0 data `rstb` remain {u0rst['transition_value_ns']:.9f}/{e0rst['transition_value_ns']:.9f} ns against 0.351 ns.", "",
    f"Timing-path impact is measured at whole-design final STA: U0 setup WNS/hold slack moved {pu0['setup_wns_ns']:.9f}/{pu0['worst_hold_slack_ns']:.9f} → {u0['setup_wns_ns']:.9f}/{u0['worst_hold_slack_ns']:.9f} ns; E0 moved {pe0['setup_wns_ns']:.9f}/{pe0['worst_hold_slack_ns']:.9f} → {e0['setup_wns_ns']:.9f}/{e0['worst_hold_slack_ns']:.9f} ns. Setup/hold violation counts remain zero canonically.",
]
write_md("RSTB_REPAIR.md", "\n".join(rstb_lines))

clk = closed[("E0", "u_protected_memory.u_data/clk")]
clk_exps = [r for r in experiments["records"] if r["target"].endswith(".u_data/clk")]
clk8 = next(r for r in clk_exps if "clkinv_8" in r["cell"])
clk16 = next(r for r in clk_exps if "clkinv_16" in r["cell"])
write_md("CLOCK_INTERFACE_REPAIR.md", f"""
# Clock-interface repair

Attempt08's data-SRAM clock endpoint was driven by `clkbuf_1_1__f_clk/X` (`sky130_fd_sc_hd__clkbuf_16`) at 0.511382282/0.351 ns, fanout 1, extracted D_NET capacitance 0.00726447 pF, and 64.28 um routed wire. This is a legitimate explicit macro clock-input rule and characterization-axis ceiling.

The phase-preserving `clkinv_8` pair produced {clk8['after_slew_ns']:.9f} ns and failed. The smallest closing clock-cell pair was two `sky130_fd_sc_hd__clkinv_16` stages at {clk16['after_slew_ns']:.9f} ns in the placement diagnostic. The production ECO applies that pair to the data branch and an identical pair to the ECC branch to preserve polarity and avoid unbalanced clock semantics. Canonical final data/ECC clock slew is {clk['transition_value_ns']:.9f}/{closed[('E0', 'u_protected_memory.u_ecc/clk')]['transition_value_ns']:.9f} ns, each against 0.351 ns.

Propagated clocks, timing checks, 10 ns period, 0.10 ns uncertainty, and the SRAM input rule remain enabled. Final canonical setup/hold are 0/0 violations, route DRC and antenna are 0/0, and max capacitance is 0.
""")

hold_rows = []
for pair in multi["seeds"]:
    hold_rows.append(f"| {pair['seed']} | {pair['E0']['hold_violations']} | {pair['E0']['worst_hold_slack_ns']:.9f} | {pair['E0']['setup_violations']} | {pair['E0']['setup_wns_ns']:.9f} |")
write_md("COMMON_HOLD_POLICY.md", f"""
# Common hold policy

Attempt08 E0 seed 17 had one hold violation at −0.000169975 ns. Attempt09 first evaluated unbalanced-clock and no/zero-margin repairs; both produced hold failures and are preserved under `raw/rejected_runs`. A common 20 ps post-interface hold-repair margin fixed seed 17 but yielded only 2/5 hold-clean seeds (seed 13 −0.00000272005 ns, seed 19 −0.000328404 ns, seed 23 −0.00484013 ns). A 30 ps worst-seed trial closed hold but reduced seed-23 setup WNS to 0.0214699 ns and increased area, so it was rejected. The retained physically standard policy is:

`repair_timing -setup_margin 0 -hold_margin 0.025 -repair_tns 100 -match_cell_footprint`

It is applied after the fixed interface ECO identically to every E0 seed; there is no seed-specific branch or tuning.

| Seed | Hold violations | Worst hold slack (ns) | Setup violations | Setup WNS (ns) |
|---:|---:|---:|---:|---:|
{chr(10).join(hold_rows)}

Final E0 hold-clean robustness is {sum(p['E0']['hold_violations']==0 for p in multi['seeds'])}/5. Seed 17 finishes with {seed17_e0['hold_violations']} violations and {seed17_e0['worst_hold_slack_ns']:.9f} ns worst slack.
""")

write_md("CANONICAL_EXTERNAL_CLOSURE.md", f"""
# Canonical external closure

Canonical seed 11 remains a failure because one genuine 256×64 data-macro `rstb` input violation remains in each design. Original immutable-Liberty report counts remain visible: U0 {u0['max_slew_violations_reported']} = 64 Class C + {u0['genuine_external_slew_violations']} genuine external; E0 {e0['max_slew_violations_reported']} = 72 Class C + {e0['genuine_external_slew_violations']} genuine external. Class C is separately classified `UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY` / `PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV`; it is not counted as closed or deleted.

| Design | Setup / hold violations | Cap violations | Integration DRC | Antenna | Unconstrained | WNS / TNS (ns) | Worst hold (ns) |
|---|---:|---:|---:|---:|---:|---:|---:|
| U0 | {u0['setup_violations']} / {u0['hold_violations']} | {u0['max_capacitance_violations']} | {u0['integration_drc']} | {u0['antenna_violating_nets']} | {u0['unconstrained_endpoints']} | {u0['setup_wns_ns']:.9f} / {u0['setup_tns_ns']:.9f} | {u0['worst_hold_slack_ns']:.9f} |
| E0 | {e0['setup_violations']} / {e0['hold_violations']} | {e0['max_capacitance_violations']} | {e0['integration_drc']} | {e0['antenna_violating_nets']} | {e0['unconstrained_endpoints']} | {e0['setup_wns_ns']:.9f} / {e0['setup_tns_ns']:.9f} | {e0['worst_hold_slack_ns']:.9f} |

The exact residual driver, sink, slew, fanout, extracted capacitance, route length/layers, strength and original/final timing context are in `RESIDUAL_EXTERNAL_DRV_INVENTORY.json`. Classification is `RESIDUAL_SRAM_INPUT_DRV_FAIL`, not an external-closure pass.
""")

gate_evidence = {
    "immutable_sram22_hardened_macros": True,
    "upstream_reported_silicon_functionality": True,
    "gds_lef_spice_liberty_verilog_consistency": True,
    "exhaustive_secded_functional_validation": True,
    "clean_external_macro_integration": False,
    "clean_detailed_route": multi["all_u0_route_clean"] and multi["all_e0_route_clean"],
    "zero_external_integration_drc": True,
    "clean_setup": all(p[d]["setup_violations"] == 0 for p in multi["seeds"] for d in ("U0", "E0")),
    "clean_hold_or_quantified_multiseed_robustness": multi["matched_setup_hold_clean_count"] >= 4,
    "zero_genuine_external_drvs": False,
    "explicit_sram_output_liberty_provenance_limitation": True,
    "macro_internal_drc_limitation_visible": True,
    "physical_lvs_limitation_visible": True,
    "independently_unregenerated_liberty_limitation_visible": True,
}
write_md("GATE3_REASSESSMENT_READINESS.md", f"""
# Gate-3 reassessment readiness

Recommendation: `KEEP_GATE3_FAILED`. Attempt09 is `RESIDUAL_SRAM_INPUT_DRV_FAIL`: the canonical and multiseed pairs retain a genuine explicit 0.351 ns SRAM data-`rstb` violation. The Class-C contradiction is proven, but that does not waive Class B. Gate-3 reassessment is not started; historical Gate 3 remains `FAIL`; Gate 4 and carbon work remain not started.

The evidence package establishes immutable SRAM22 hardened macros, upstream reported silicon functionality, previously frozen GDS/LEF/SPICE/Liberty/Verilog consistency and exhaustive SECDED functional validation, clean detailed routing and external integration DRC, clean canonical setup/hold, explicit Class-C provenance, and visible limitations. It does **not** establish clean external macro integration or zero genuine external DRVs. Macro-internal DRC remains `MACRO_INTERNAL_DRC_NOT_INDEPENDENTLY_SIGNOFF_QUALIFIED`, physical LVS remains `NOT_INDEPENDENTLY_REPRODUCED`, and Liberty remains independently unregenerated. Therefore the prerequisite for reassessment authorization is absent.
""")

remaining_unsupported = [
    "SRAM22 macro-internal foundry signoff DRC",
    "independently reproduced physical LVS",
    "independently regenerated SRAM22 Liberty characterization or a corrected output max-transition rule",
    "physical bitcell interleaving",
    "activity-qualified power and energy per access",
]
status = {
    "schema_version": 1,
    "campaign": f"campaigns/iscas_sustainability_extension/memory_compiler/{ROOT.name}",
    "final_attempt09_classification": "RESIDUAL_SRAM_INPUT_DRV_FAIL",
    "sram22_upstream_commit": UPSTREAM,
    "technology_pvt": "SKY130HD TT/25C/1.8V",
    "common_clock": {"period_ns": 10.0, "frequency_mhz": 100.0, "uncertainty_ns": 0.1},
    "original_attempt08_residual": {"U0": {"B": 1, "C": 64}, "E0": {"B": 2, "C": 72, "E": 1}},
    "original_exact_target_slew_ns": {
        "U0_data_rstb": {"actual": 0.619147718, "required": 0.351},
        "E0_data_rstb": {"actual": 0.615880728, "required": 0.351},
        "E0_ecc_rstb": {"actual": 0.358998388, "required": 0.351},
        "E0_data_clock": {"actual": 0.511382282, "required": 0.351},
    },
    "accepted_repairs": [
        {"scope": "retained Attempt08", "repair": "E0 _513_ xnor2_1 -> xnor2_2; data din[56]/din[57] buf_4 -> buf_8"},
        {"scope": "Attempt09 E0 all seeds", "target": "ECC rstb", "repair": "phase-preserving two-stage sky130_fd_sc_hd__inv_16 close to macro pin"},
        {"scope": "Attempt09 E0 all seeds", "target": "data and ECC clocks", "repair": "balanced phase-preserving two-stage sky130_fd_sc_hd__clkinv_16 on each branch"},
        {"scope": "Attempt09 E0 all seeds", "repair": "common post-interface repair_timing hold margin 0.025 ns; no per-seed tuning"},
    ],
    "data_rstb_repair_feasibility": "NO_SINGLE_OUTPUT_SKY130HD_CANDIDATE_CLOSED",
    "constraint_relaxed_to_force_pass": False,
    "production_liberty_modified": False,
    "macro_internals_changed": False,
    "canonical": {"U0": u0, "E0": e0},
    "canonical_remaining_slew_distribution": {"U0": {"A": 0, "B": 1, "C": 64, "D": 0, "E": 0, "F": 0}, "E0": {"A": 0, "B": 1, "C": 72, "D": 0, "E": 0, "F": 0}},
    "class_c": {
        "classification": "UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY",
        "disposition": "PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV",
        "upstream_constraint_ns": 0.04,
        "counts": {"U0": 64, "E0": 72},
        "production_warnings_preserved": True,
        "provenance_established": provenance["global_findings"]["all_output_transition_tables_exceed_0p04_at_min_load_fastest_input"],
    },
    "counterfactual": {"U0_rows": cf["U0"], "E0_rows": cf["E0"], "production_liberty_immutable": diagnostic_manifest["production_liberty_immutable"]},
    "canonical_pair_externally_timing_drv_clean": False,
    "provenance_limited_pass_eligible": False,
    "multiseed": {
        "seeds": multi["seed_policy"],
        "route_clean_pairs": sum(p["matched_route_clean"] for p in multi["seeds"]),
        "setup_hold_clean_pairs": multi["matched_setup_hold_clean_count"],
        "genuine_external_drv_clean_pairs": multi["matched_external_timing_drv_closure_count"],
        "seed17_e0": seed17_e0,
    },
    "final_ppa": ppa,
    "power_evidence_level": "COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE",
    "energy_per_access": "NOT_QUALIFIED",
    "sram_internal_drc_disposition": "MACRO_INTERNAL_DRC_NOT_INDEPENDENTLY_SIGNOFF_QUALIFIED",
    "physical_lvs": "NOT_INDEPENDENTLY_REPRODUCED",
    "liberty_provenance": "UPSTREAM_MODEL_INCONSISTENCY_PROVEN_BUT_LIBERTY_NOT_INDEPENDENTLY_REGENERATED",
    "macro_source_integrity": "FROZEN_14_ARTIFACTS_PASS",
    "remaining_unsupported_claims": remaining_unsupported,
    "gate3_reassessment_evidence": gate_evidence,
    "regression": regression,
    "gate3_recommendation": "KEEP_GATE3_FAILED",
    "gate3_historical_state": "FAIL",
    "gate3_reassessment_started": False,
    "gate4_state": "NOT_STARTED_UNAUTHORIZED",
    "carbon_modeling_started": False,
    "attempt10_started": False,
}
write_json("ATTEMPT09_STATUS.json", status)

write_md("ATTEMPT09_SUMMARY.md", f"""
# Attempt09 summary

Attempt09 is `RESIDUAL_SRAM_INPUT_DRV_FAIL`; recommendation is `KEEP_GATE3_FAILED`. The fixed E0 interface ECO closes the ECC `rstb` and data-SRAM clock violations, retains balanced clock polarity, and a common 25 ps hold-repair policy is used across all E0 seeds. No constraint, macro, or production Liberty changed.

Canonical seed 11 reports U0 {u0['max_slew_violations_reported']} warnings = 64 Class C + 1 genuine data-`rstb`; E0 {e0['max_slew_violations_reported']} = 72 Class C + 1 genuine data-`rstb`. Setup/hold/capacitance/integration-DRC/antenna are 0/0/0/0/0 in both. U0 WNS/TNS is {u0['setup_wns_ns']:.9f}/{u0['setup_tns_ns']:.9f} ns; E0 is {e0['setup_wns_ns']:.9f}/{e0['setup_tns_ns']:.9f} ns.

The 136 Class-C warnings are causally classified `UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY` and `PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV`: six frozen macro/corner views inherit 0.04 ns on every output without pin override, while their own output tables exceed 0.04 ns at minimum load/fastest input. The diagnostic exclusion removes Class C while leaving one genuine `rstb` row per design. This classification does not repair or waive those input rows.

Across seeds 11/13/17/19/23, route-clean pairs are {sum(p['matched_route_clean'] for p in multi['seeds'])}/5, setup/hold-clean pairs are {multi['matched_setup_hold_clean_count']}/5, and genuine-external-DRV-clean pairs are {multi['matched_external_timing_drv_closure_count']}/5. Seed 17 E0 finishes at {seed17_e0['worst_hold_slack_ns']:.9f} ns with {seed17_e0['hold_violations']} violations. Power is only `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`; energy/access is `NOT_QUALIFIED`. Gate-3 reassessment, Attempt10, carbon work, and Gate 4 were not started.
""")
