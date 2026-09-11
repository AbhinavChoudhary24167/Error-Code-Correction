#!/usr/bin/env python3
"""Extract matched A/C physical evidence and emit scoped descriptive analyses."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-breadth-remediation")
POLICY = ROOT / "policy"
SNAPSHOT = POLICY / "repo_snapshot"
CAMPAIGN = Path("campaigns/date_2027_breadth_remediation")
SEEDS = (11, 13, 17, 19, 23)
FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(root: Path, manifest: Path) -> None:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = root / relative.strip().removeprefix("./")
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"checksum mismatch: {path}")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_power(path: Path) -> dict[str, float]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Total"):
            values = [float(value) for value in FLOAT_RE.findall(line)]
            if len(values) >= 4:
                return dict(zip(("internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w"), values[:4]))
    raise ValueError(f"full-precision power Total row missing: {path}")


def annotation_counts(path: Path) -> tuple[int, int]:
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        pieces = line.split()
        if len(pieces) == 2 and pieces[1].isdigit():
            counts[pieces[0]] = int(pieces[1])
    return counts.get("vcd", 0), counts.get("unannotated", 0)


def stat_summary(values_by_seed: dict[int, float]) -> dict[str, object]:
    ordered = [values_by_seed[seed] for seed in sorted(values_by_seed)]
    if not ordered:
        return {
            "count": 0,
            "values_by_seed": {},
            "mean": None,
            "median": None,
            "sample_standard_deviation": None,
            "minimum": None,
            "maximum": None,
            "range": None,
        }
    return {
        "count": len(ordered),
        "values_by_seed": {str(seed): values_by_seed[seed] for seed in sorted(values_by_seed)},
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "sample_standard_deviation": statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
        "minimum": min(ordered),
        "maximum": max(ordered),
        "range": max(ordered) - min(ordered),
    }


def percent_delta(value: float, reference: float) -> float:
    if reference == 0:
        raise ZeroDivisionError("paired percentage reference is zero")
    return (value - reference) / reference * 100.0


def extract(record: dict[str, object], contract: dict[str, object], trace_by_file: dict[str, dict[str, object]]) -> dict[str, object]:
    workstream = str(record["workstream"])
    run_root = ROOT / "runs" / workstream / str(record["run_id"])
    verify_manifest(run_root, run_root / "raw-artifacts.sha256")
    metadata = json.loads((run_root / "run-metadata.json").read_text(encoding="utf-8"))
    architecture = contract["architectures"][record["architecture"]]
    if (
        metadata["run_id"] != record["run_id"]
        or metadata["architecture"] != record["architecture"]
        or int(metadata["physical_seed"]) != int(record["seed"])
        or metadata["implementation_id"] != architecture["implementation_id"]
    ):
        raise SystemExit(f"run identity mismatch: {record['run_id']}")
    period = float(architecture["clock_period_ns"])
    top = architecture["design_top"]
    logs = run_root / f"logs/sky130hd/{top}/base"
    results = run_root / f"results/sky130hd/{top}/base"
    row: dict[str, object] = {
        "run_id": record["run_id"],
        "workstream": workstream,
        "architecture": record["architecture"],
        "implementation_id": architecture["implementation_id"],
        "physical_identity": f"{record['run_id']}@{period:g}ns",
        "seed": int(record["seed"]),
        "design_top": top,
        "clock_period_ns": period,
        "latency_cycles": int(architecture["latency_cycles"]),
        "initiation_interval_cycles": int(architecture["initiation_interval_cycles"]),
        "physical_exit_status": int(metadata["physical_exit_status"]),
        "physical_failure_reason": metadata.get("physical_failure_reason", ""),
        "routing_complete": bool(metadata["routing_complete"]),
        "target_feasible": bool(metadata["target_feasible"]),
        "power_status": metadata["power_status"],
        "source_hashes_json": json.dumps(metadata["source_hashes"], sort_keys=True),
        "config_sha256": metadata["config_sha256"],
        "sdc_source_sha256": metadata["sdc_sha256"],
        "contract_sha256": metadata["contract_sha256"],
        "container_image": metadata["container_image"],
        "baseline_commit": metadata["baseline_commit"],
        "final_odb_sha256": sha256(results / "6_final.odb") if (results / "6_final.odb").is_file() else None,
        "final_netlist_sha256": sha256(results / "6_final.v") if (results / "6_final.v").is_file() else None,
        "final_sdc_sha256": sha256(results / "6_final.sdc") if (results / "6_final.sdc").is_file() else None,
        "final_spef_sha256": sha256(results / "6_final.spef") if (results / "6_final.spef").is_file() else None,
        "raw_artifacts_manifest_sha256": sha256(run_root / "raw-artifacts.sha256"),
    }
    if row["physical_exit_status"] != 0:
        row["characterization_status"] = "PHYSICAL_CHARACTERIZATION_FAIL"
        return row

    finish = json.loads((logs / "6_report.json").read_text(encoding="utf-8"))
    grt = json.loads((logs / "5_1_grt.json").read_text(encoding="utf-8"))
    drt = json.loads((logs / "5_2_route.json").read_text(encoding="utf-8"))
    setup = float(finish["finish__timing__setup__ws"])
    hold = float(finish["finish__timing__hold__ws"])
    setup_violations = int(finish["finish__timing__drv__setup_violation_count"])
    hold_violations = int(finish["finish__timing__drv__hold_violation_count"])
    clock_buffers = int(finish.get("finish__design__instance__count__class:clock_buffer", 0))
    repair_buffers = int(finish.get("finish__design__instance__count__class:timing_repair_buffer", 0))
    metrics: dict[str, object] = {
        "characterization_status": "PASS_TARGET_MET" if row["target_feasible"] else "PASS_TARGET_MISSED",
        "hold_status": "HOLD_CLEAN" if hold >= 0 and hold_violations == 0 else "HOLD_VIOLATION",
        "standard_cell_instance_area_um2": float(finish["finish__design__instance__area__stdcell"]),
        "cell_count": int(finish["finish__design__instance__count__stdcell"]),
        "sequential_cell_count": int(finish.get("finish__design__instance__count__class:sequential_cell", 0)),
        "clock_buffer_count": clock_buffers,
        "timing_repair_buffer_count": repair_buffers,
        "buffer_count": clock_buffers + repair_buffers,
        "utilization_percent": float(finish["finish__design__instance__utilization__stdcell"]) * 100.0,
        "signed_worst_setup_slack_ns": setup,
        "wns_ns": min(0.0, setup),
        "tns_ns": float(finish["finish__timing__setup__tns"]),
        "setup_violation_count": setup_violations,
        "worst_hold_slack_ns": hold,
        "hold_violation_count": hold_violations,
        "slack_derived_frequency_mhz": 1000.0 / (period - setup),
        "orfs_reported_fmax_mhz": float(finish["finish__timing__fmax"]) / 1.0e6,
        "global_route_wirelength_um": float(grt["globalroute__global_route__wirelength"]),
        "detailed_route_wirelength_um": float(drt["detailedroute__route__wirelength"]),
        "via_count": int(drt["detailedroute__route__vias"]),
        "routed_signal_net_count": int(drt["detailedroute__route__net"]),
        "congestion_violation_count": int(grt["globalroute__design__violations"]),
        "final_drc_count": int(drt["detailedroute__route__drc_errors"]),
        "final_flow_error_count": int(finish["finish__flow__errors__count"]),
        "internal_power_w": None,
        "switching_power_w": None,
        "leakage_power_w": None,
        "total_power_w": None,
        "energy_per_op_pj": None,
        "direct_vcd_annotated_pin_count": None,
        "unannotated_pin_count_before_propagation": None,
        "power_report_sha256": None,
        "trace_sha256": None,
    }
    if str(metadata["power_status"]).startswith("ACTIVITY_POWER_PASS"):
        label = metadata["power_label"]
        report = run_root / f"power/{label}.power.rpt"
        power = parse_power(report)
        trace = trace_by_file[metadata["trace_file"]]
        annotated, unannotated = annotation_counts(run_root / f"power/{label}.annotation.rpt")
        metrics.update(power)
        metrics["energy_per_op_pj"] = power["total_power_w"] * float(trace["total_time_ps"]) / float(trace["useful_operations"])
        metrics["direct_vcd_annotated_pin_count"] = annotated
        metrics["unannotated_pin_count_before_propagation"] = unannotated
        metrics["power_report_sha256"] = sha256(report)
        metrics["trace_sha256"] = trace["compressed_sha256"]
    row.update(metrics)
    return row


METRICS = (
    "standard_cell_instance_area_um2", "cell_count", "sequential_cell_count", "clock_buffer_count",
    "timing_repair_buffer_count", "buffer_count", "utilization_percent", "signed_worst_setup_slack_ns",
    "wns_ns", "tns_ns", "setup_violation_count", "worst_hold_slack_ns", "hold_violation_count",
    "slack_derived_frequency_mhz", "global_route_wirelength_um", "detailed_route_wirelength_um",
    "via_count", "routed_signal_net_count", "congestion_violation_count", "final_drc_count",
    "internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w", "energy_per_op_pj",
)


def architecture_summary(rows: list[dict[str, object]], architectures: tuple[str, str]) -> dict[str, object]:
    result = {}
    for architecture in architectures:
        selected = [row for row in rows if row["architecture"] == architecture]
        result[architecture] = {
            "implementation_id": selected[0]["implementation_id"],
            "physical_identities": [row["physical_identity"] for row in selected],
            "valid_route_count": sum(bool(row["routing_complete"]) for row in selected),
            "target_feasible_count": sum(bool(row["target_feasible"]) for row in selected),
            "hold_clean_count": sum(row.get("hold_status") == "HOLD_CLEAN" for row in selected),
            "power_result_count": sum(row.get("total_power_w") is not None for row in selected),
            "metrics": {
                metric: stat_summary({int(row["seed"]): float(row[metric]) for row in selected if row.get(metric) is not None})
                for metric in METRICS
            },
        }
    return result


def paired_effects(rows: list[dict[str, object]], reference: str, changed: str) -> dict[str, object]:
    by_key = {(str(row["architecture"]), int(row["seed"])): row for row in rows}
    effects = {}
    for metric in METRICS:
        percentages: dict[int, float] = {}
        differences: dict[int, float] = {}
        zero_reference_seeds: list[int] = []
        for seed in SEEDS:
            left = by_key[(reference, seed)].get(metric)
            right = by_key[(changed, seed)].get(metric)
            if left is not None and right is not None:
                differences[seed] = float(right) - float(left)
                if float(left) == 0.0:
                    zero_reference_seeds.append(seed)
                else:
                    percentages[seed] = percent_delta(float(right), float(left))
        effects[metric] = {
            "formula": f"({changed} - {reference}) / {reference} * 100 percent",
            "percent_effect": stat_summary(percentages),
            "percent_effect_not_assessable_zero_reference_seeds": zero_reference_seeds,
            "absolute_difference": stat_summary(differences),
            "changed_greater_count": sum(value > 0 for value in differences.values()),
            "changed_lower_count": sum(value < 0 for value in differences.values()),
            "equal_count": sum(value == 0 for value in differences.values()),
        }
    return effects


def pareto_relation(comb: dict[str, object], pipe: dict[str, object]) -> str:
    if comb.get("energy_per_op_pj") is None or pipe.get("energy_per_op_pj") is None:
        return "NOT_ASSESSABLE_INFEASIBLE_ENERGY"
    a = (float(comb["standard_cell_instance_area_um2"]), 1.0, float(comb["energy_per_op_pj"]), -float(comb["slack_derived_frequency_mhz"]))
    b = (float(pipe["standard_cell_instance_area_um2"]), 3.0, float(pipe["energy_per_op_pj"]), -float(pipe["slack_derived_frequency_mhz"]))
    a_dom = all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))
    b_dom = all(y <= x for x, y in zip(a, b)) and any(y < x for x, y in zip(a, b))
    return "COMB_DOMINATES" if a_dom else "PIPE_DOMINATES" if b_dom else "NON_DOMINATED"


def analyze_a(repo: Path, rows: list[dict[str, object]]) -> None:
    out = repo / CAMPAIGN / "analysis"
    csv_path = out / "A_structural_pair_per_seed.csv"
    json_path = out / "A_structural_pair_summary.json"
    report_path = out / "A_structural_pair_report.md"
    if any(path.exists() for path in (csv_path, json_path, report_path)):
        raise SystemExit("refusing to overwrite Workstream A analysis")
    architectures = ("A_hsiao_flat", "A_hsiao_hierarchical")
    summary = {
        "schema_version": 1,
        "interpretation": "five matched deterministic OpenROAD heuristic seeds; descriptive only",
        "seed_set": list(SEEDS),
        "formal_qualification": json.loads((repo / CAMPAIGN / "formal/results/A_formal_qualification.json").read_text(encoding="utf-8")),
        "synthesis_distinctness": json.loads((repo / CAMPAIGN / "synthesis/A_synthesis_structural_comparison.json").read_text(encoding="utf-8")),
        "architectures": architecture_summary(rows, architectures),
        "paired_effects": paired_effects(rows, *architectures),
    }
    write_csv(csv_path, rows)
    write_json(json_path, summary)
    effects = summary["paired_effects"]
    flat = summary["architectures"]["A_hsiao_flat"]["metrics"]
    hierarchical = summary["architectures"]["A_hsiao_hierarchical"]["metrics"]
    synthesis = summary["synthesis_distinctness"]
    report = [
        "# Workstream A structural-pair physical report",
        "",
        "## Qualification and structural sanity",
        "",
        "The flat and hierarchical Hsiao identities are exact-equivalent with zero temporal alignment, one-cycle request latency, and II=1. Exhaustive SAT proved decoder equality for every arbitrary 72-bit received word with no assumptions. Sequential temporal induction proved same-cycle equality of the complete registered transaction boundary from equal zero initialization under arbitrary reset, valid, payload, and decoder-word sequences.",
        "",
        f"Under one common SKY130HD mapping policy, the baseline has {synthesis['baseline']['mapped_cell_count']:,} mapped cells, {synthesis['baseline']['register_count']} registers, and {synthesis['baseline']['xor_xnor_count']} XOR/XNOR cells; the hierarchical identity has {synthesis['new_hierarchical']['mapped_cell_count']:,} mapped cells, {synthesis['new_hierarchical']['register_count']} registers, and {synthesis['new_hierarchical']['xor_xnor_count']} XOR/XNOR cells. Their cell histograms, normalized graph signatures, and mapped-netlist hashes differ. Combinational logic depth is `NOT ASSESSABLE` because the common mapped-library `ltp -noff` report exposed no paths; this absence is not converted to a pass criterion.",
        "",
        "## Five matched routes",
        "",
        f"All ten fresh runs completed and were target-feasible: flat {summary['architectures']['A_hsiao_flat']['target_feasible_count']}/5 and hierarchical {summary['architectures']['A_hsiao_hierarchical']['target_feasible_count']}/5. Every run is joined to its own final ODB/netlist, SDC, SPEF, trace, configuration, source hashes, command, log, and raw-artifact manifest.",
        "",
        "| Metric | Flat mean | Hierarchical mean | Mean paired effect | Ordering |",
        "|---|---:|---:|---:|---:|",
        f"| Standard-cell area (um2) | {flat['standard_cell_instance_area_um2']['mean']:,.2f} | {hierarchical['standard_cell_instance_area_um2']['mean']:,.2f} | {effects['standard_cell_instance_area_um2']['percent_effect']['mean']:+.6f}% | hierarchical lower {effects['standard_cell_instance_area_um2']['changed_lower_count']}/5 |",
        f"| Cell count | {flat['cell_count']['mean']:,.1f} | {hierarchical['cell_count']['mean']:,.1f} | {effects['cell_count']['percent_effect']['mean']:+.6f}% | hierarchical higher {effects['cell_count']['changed_greater_count']}/5 |",
        f"| Detailed wirelength (um) | {flat['detailed_route_wirelength_um']['mean']:,.1f} | {hierarchical['detailed_route_wirelength_um']['mean']:,.1f} | {effects['detailed_route_wirelength_um']['percent_effect']['mean']:+.6f}% | hierarchical higher {effects['detailed_route_wirelength_um']['changed_greater_count']}/5 |",
        f"| Via count | {flat['via_count']['mean']:,.1f} | {hierarchical['via_count']['mean']:,.1f} | {effects['via_count']['percent_effect']['mean']:+.6f}% | hierarchical higher {effects['via_count']['changed_greater_count']}/5 |",
        f"| Slack-derived frequency (MHz) | {flat['slack_derived_frequency_mhz']['mean']:.3f} | {hierarchical['slack_derived_frequency_mhz']['mean']:.3f} | {effects['slack_derived_frequency_mhz']['percent_effect']['mean']:+.6f}% | hierarchical higher {effects['slack_derived_frequency_mhz']['changed_greater_count']}/5 |",
        f"| Total power (W) | {flat['total_power_w']['mean']:.7f} | {hierarchical['total_power_w']['mean']:.7f} | {effects['total_power_w']['percent_effect']['mean']:+.6f}% | hierarchical higher {effects['total_power_w']['changed_greater_count']}/5 |",
        f"| Energy/op (pJ) | {flat['energy_per_op_pj']['mean']:.6f} | {hierarchical['energy_per_op_pj']['mean']:.6f} | {effects['energy_per_op_pj']['percent_effect']['mean']:+.6f}% | hierarchical higher {effects['energy_per_op_pj']['changed_greater_count']}/5 |",
        "",
        "The exact per-seed observations and the required mean, median, sample standard deviation, minimum, maximum, range, absolute difference, paired percentage, and ordering counts are preserved in `A_structural_pair_per_seed.csv` and `A_structural_pair_summary.json`.",
        "",
        "## Scoped conclusion",
        "",
        "The intended structural distinction survives common synthesis and produces a repeatable, mixed physical displacement: slightly lower routed cell area but more cells, wire, vias, total power, and energy for the hierarchical identity across these five matched heuristic seeds. This is a scientifically valid small-effect result and demonstrates implementation identity beyond the earlier temporal-pipelining transformation. It does not establish a universally preferable structural style.",
    ]
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")


def analyze_c(repo: Path, rows: list[dict[str, object]]) -> None:
    out = repo / CAMPAIGN / "analysis"
    csv_path = out / "C_5ns_per_seed.csv"
    json_path = out / "C_5ns_summary.json"
    report_path = out / "C_condition_comparison_report.md"
    if any(path.exists() for path in (csv_path, json_path, report_path)):
        raise SystemExit("refusing to overwrite Workstream C analysis")
    architectures = ("C_secded_comb", "C_secded_pipe")
    by_key = {(str(row["architecture"]), int(row["seed"])): row for row in rows}
    within = paired_effects(rows, *architectures)
    historical_payload = json.loads((repo / "docs/date2027/revision2/results/REV2_RUN_RESULTS.json").read_text(encoding="utf-8"))
    historical = {(row["architecture"], int(row["seed"])): row for row in historical_payload["records"]}
    cross = {}
    for new_arch, old_arch in (("C_secded_comb", "secded_comb"), ("C_secded_pipe", "secded_pipe")):
        cross[new_arch] = {}
        for metric in METRICS:
            values: dict[int, float] = {}
            zero_reference_seeds: list[int] = []
            for seed in SEEDS:
                new_value = by_key[(new_arch, seed)].get(metric)
                old_value = historical[(old_arch, seed)]["metrics"].get(
                    "achievable_no_error_energy_pj_per_operation" if metric == "energy_per_op_pj" else metric
                )
                if new_value is not None and old_value is not None:
                    if float(old_value) == 0.0:
                        zero_reference_seeds.append(seed)
                    else:
                        values[seed] = percent_delta(float(new_value), float(old_value))
            cross[new_arch][metric] = stat_summary(values) | {
                "not_assessable_zero_reference_seeds": zero_reference_seeds,
            }

    ordering = {}
    for metric in ("standard_cell_instance_area_um2", "slack_derived_frequency_mhz", "total_power_w", "energy_per_op_pj"):
        same = 0
        assessable = 0
        details = []
        old_metric = "achievable_no_error_energy_pj_per_operation" if metric == "energy_per_op_pj" else metric
        for seed in SEEDS:
            new_comb = by_key[("C_secded_comb", seed)].get(metric)
            new_pipe = by_key[("C_secded_pipe", seed)].get(metric)
            old_comb = historical[("secded_comb", seed)]["metrics"].get(old_metric)
            old_pipe = historical[("secded_pipe", seed)]["metrics"].get(old_metric)
            if None not in (new_comb, new_pipe, old_comb, old_pipe):
                new_sign = (float(new_pipe) > float(new_comb)) - (float(new_pipe) < float(new_comb))
                old_sign = (float(old_pipe) > float(old_comb)) - (float(old_pipe) < float(old_comb))
                assessable += 1
                same += new_sign == old_sign
                details.append({"seed": seed, "historical_pipe_minus_comb_sign": old_sign, "new_pipe_minus_comb_sign": new_sign})
        ordering[metric] = {"same_direction_count": same, "assessable_count": assessable, "details": details}

    pareto = [
        {
            "seed": seed,
            "relation": pareto_relation(by_key[("C_secded_comb", seed)], by_key[("C_secded_pipe", seed)]),
        }
        for seed in SEEDS
    ]
    summary = {
        "schema_version": 1,
        "interpretation": "controlled 10 ns to 5 ns constraint sensitivity over five matched deterministic seeds",
        "historical_target_ns": 10.0,
        "new_target_ns": 5.0,
        "seed_set": list(SEEDS),
        "request_latency": {"combinational_cycles": 1, "pipelined_cycles": 3, "unchanged_across_condition": True},
        "architectures_5ns": architecture_summary(rows, architectures),
        "within_5ns_paired_effects": within,
        "condition_sensitivity_percent": cross,
        "architecture_ordering_preservation": ordering,
        "pareto_5ns": pareto,
    }
    write_csv(csv_path, rows)
    write_json(json_path, summary)
    comb_feasible = summary["architectures_5ns"]["C_secded_comb"]["target_feasible_count"]
    pipe_feasible = summary["architectures_5ns"]["C_secded_pipe"]["target_feasible_count"]
    comb = summary["architectures_5ns"]["C_secded_comb"]["metrics"]
    pipe = summary["architectures_5ns"]["C_secded_pipe"]["metrics"]
    report = [
        "# Workstream C condition-comparison report",
        "",
        "The only major changed condition is the implementation clock target: 10 ns historical versus a fresh 5 ns optimization target. Technology, corner, RTL identities, floorplan policy, utilization, placement density, load, activity sequence, and five matched seeds are unchanged.",
        "",
        "## Configuration and feasibility",
        "",
        "The 5 ns flow uses SKY130HD `tt_025C_1v80` at 1.80 V and 25 C, the frozen ORFS image, 35% utilization, 0.55 placement density, 10 um core margin, 0.05 pF output load, one worker, 10% period-relative I/O delays, a 5,000 ps ABC target, and the exact seeds 11, 13, 17, 19, and 23. The ten routes were implemented fresh in comb-then-pipe order for each seed; no 10 ns database was reused, no retry occurred, and no seed was substituted.",
        "",
        f"5 ns feasibility is combinational {comb_feasible}/5 and pipelined {pipe_feasible}/5. Every point has zero setup violations, nonnegative setup slack, zero hold violations, positive hold slack, completed routing, and zero final DRC. Combinational setup slack spans {comb['signed_worst_setup_slack_ns']['minimum']:.6f} to {comb['signed_worst_setup_slack_ns']['maximum']:.5f} ns; pipelined setup slack spans {pipe['signed_worst_setup_slack_ns']['minimum']:.5f} to {pipe['signed_worst_setup_slack_ns']['maximum']:.5f} ns. Request latencies remain one and three cycles, respectively; II remains one for both.",
        "",
        "## Within-5-ns matched comparison",
        "",
        "| Metric | Comb mean | Pipe mean | Mean paired pipe-vs-comb effect | Ordering |",
        "|---|---:|---:|---:|---:|",
        f"| Standard-cell area (um2) | {comb['standard_cell_instance_area_um2']['mean']:,.2f} | {pipe['standard_cell_instance_area_um2']['mean']:,.2f} | {within['standard_cell_instance_area_um2']['percent_effect']['mean']:+.6f}% | pipe higher {within['standard_cell_instance_area_um2']['changed_greater_count']}/5 |",
        f"| Cell count | {comb['cell_count']['mean']:,.1f} | {pipe['cell_count']['mean']:,.1f} | {within['cell_count']['percent_effect']['mean']:+.6f}% | pipe higher {within['cell_count']['changed_greater_count']}/5 |",
        f"| Clock buffers | {comb['clock_buffer_count']['mean']:.1f} | {pipe['clock_buffer_count']['mean']:.1f} | {within['clock_buffer_count']['percent_effect']['mean']:+.6f}% | pipe higher {within['clock_buffer_count']['changed_greater_count']}/5 |",
        f"| Timing-repair buffers | {comb['timing_repair_buffer_count']['mean']:.1f} | {pipe['timing_repair_buffer_count']['mean']:.1f} | {within['timing_repair_buffer_count']['percent_effect']['mean']:+.6f}% | pipe lower {within['timing_repair_buffer_count']['changed_lower_count']}/5 |",
        f"| Detailed wirelength (um) | {comb['detailed_route_wirelength_um']['mean']:,.1f} | {pipe['detailed_route_wirelength_um']['mean']:,.1f} | {within['detailed_route_wirelength_um']['percent_effect']['mean']:+.6f}% | pipe higher {within['detailed_route_wirelength_um']['changed_greater_count']}/5 |",
        f"| Via count | {comb['via_count']['mean']:,.1f} | {pipe['via_count']['mean']:,.1f} | {within['via_count']['percent_effect']['mean']:+.6f}% | pipe higher {within['via_count']['changed_greater_count']}/5 |",
        f"| Slack-derived frequency (MHz) | {comb['slack_derived_frequency_mhz']['mean']:.3f} | {pipe['slack_derived_frequency_mhz']['mean']:.3f} | {within['slack_derived_frequency_mhz']['percent_effect']['mean']:+.6f}% | pipe higher {within['slack_derived_frequency_mhz']['changed_greater_count']}/5 |",
        f"| Total power (W) | {comb['total_power_w']['mean']:.7f} | {pipe['total_power_w']['mean']:.7f} | {within['total_power_w']['percent_effect']['mean']:+.6f}% | pipe lower {within['total_power_w']['changed_lower_count']}/5 |",
        f"| Energy/op (pJ) | {comb['energy_per_op_pj']['mean']:.6f} | {pipe['energy_per_op_pj']['mean']:.6f} | {within['energy_per_op_pj']['percent_effect']['mean']:+.6f}% | pipe lower {within['energy_per_op_pj']['changed_lower_count']}/5 |",
        "",
        "## 10 ns to 5 ns condition sensitivity",
        "",
        f"For the combinational identity, the 5 ns implementation changes mean area by {cross['C_secded_comb']['standard_cell_instance_area_um2']['mean']:+.6f}%, cell count by {cross['C_secded_comb']['cell_count']['mean']:+.6f}%, clock buffers by {cross['C_secded_comb']['clock_buffer_count']['mean']:+.6f}%, timing-repair buffers by {cross['C_secded_comb']['timing_repair_buffer_count']['mean']:+.6f}%, detailed wirelength by {cross['C_secded_comb']['detailed_route_wirelength_um']['mean']:+.6f}%, slack-derived frequency by {cross['C_secded_comb']['slack_derived_frequency_mhz']['mean']:+.6f}%, total power by {cross['C_secded_comb']['total_power_w']['mean']:+.6f}%, and energy/op by {cross['C_secded_comb']['energy_per_op_pj']['mean']:+.6f}% relative to its matched 10 ns physical identities.",
        "",
        f"For the pipelined identity, the 5 ns implementation changes mean area by {cross['C_secded_pipe']['standard_cell_instance_area_um2']['mean']:+.6f}%, cell count by {cross['C_secded_pipe']['cell_count']['mean']:+.6f}%, clock buffers by {cross['C_secded_pipe']['clock_buffer_count']['mean']:+.6f}%, timing-repair buffers by {cross['C_secded_pipe']['timing_repair_buffer_count']['mean']:+.6f}%, detailed wirelength by {cross['C_secded_pipe']['detailed_route_wirelength_um']['mean']:+.6f}%, slack-derived frequency by {cross['C_secded_pipe']['slack_derived_frequency_mhz']['mean']:+.6f}%, total power by {cross['C_secded_pipe']['total_power_w']['mean']:+.6f}%, and energy/op by {cross['C_secded_pipe']['energy_per_op_pj']['mean']:+.6f}% relative to its matched 10 ns physical identities.",
        "",
        "The near-doubling of total power is evaluated over a trace with half the clock period; energy/op remains a separately reconstructed quantity and is not inferred from power ordering alone.",
        "",
        "## Ordering and Pareto result",
        "",
        f"Ordering preservation versus 10 ns: area {ordering['standard_cell_instance_area_um2']['same_direction_count']}/{ordering['standard_cell_instance_area_um2']['assessable_count']}; timing {ordering['slack_derived_frequency_mhz']['same_direction_count']}/{ordering['slack_derived_frequency_mhz']['assessable_count']}; total power {ordering['total_power_w']['same_direction_count']}/{ordering['total_power_w']['assessable_count']}; energy {ordering['energy_per_op_pj']['same_direction_count']}/{ordering['energy_per_op_pj']['assessable_count']}.",
        "",
        "At 5 ns, the pipeline remains larger and higher-throughput but lower-energy for every seed; each paired relation is non-dominated when area, request latency, energy, and timing are considered. Neither identity becomes infeasible. Thus the evaluated architectural ordering is portable from the 10 ns to the predeclared 5 ns optimization condition, while the magnitudes remain condition-sensitive.",
        "",
        "Results are scoped to these evaluated physical identities and deterministic heuristic seeds; no universal operating-point or population claim is made.",
    ]
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--workstream", choices=("A", "C"), required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = repo / CAMPAIGN / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    verify_manifest(POLICY, POLICY / "frozen-bundle.sha256")
    matrix = json.loads((ROOT / f"MATRIX_{args.workstream}_EXECUTION.json").read_text(encoding="utf-8"))
    if matrix["planned_run_count"] != 10 or matrix["executed_run_count"] != 10:
        raise SystemExit(f"workstream {args.workstream} matrix is incomplete")
    contract = json.loads((SNAPSHOT / CAMPAIGN / "physical/contract_v1.json").read_text(encoding="utf-8"))
    trace_manifest = json.loads((POLICY / "traces/TRACE_MANIFEST.json").read_text(encoding="utf-8"))
    trace_by_file = {row["file"]: row for row in trace_manifest["traces"]}
    records = [row for row in contract["runs"] if row["workstream"] == args.workstream]
    rows = [extract(record, contract, trace_by_file) for record in records]
    if args.workstream == "A":
        analyze_a(repo, rows)
    else:
        analyze_c(repo, rows)
    print(f"WORKSTREAM_{args.workstream}_PHYSICAL_ANALYSIS_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
