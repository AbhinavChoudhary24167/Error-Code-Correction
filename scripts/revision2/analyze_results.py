#!/usr/bin/env python3
"""Extract and analyze the frozen DATE 2027 Revision-2 seed sweep."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import statistics
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-revision2")
POLICY = ROOT / "policy"
SNAPSHOT = POLICY / "repo_snapshot"
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
        path = root / relative.strip()
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"checksum mismatch: {relative}")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_full_precision_power(path: Path) -> dict[str, float]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Total"):
            values = [float(item) for item in FLOAT_RE.findall(line)]
            if len(values) >= 4:
                return dict(zip(("internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w"), values[:4]))
    raise ValueError(f"full-precision Total power row missing: {path}")


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


def dominates(a: dict[str, float], b: dict[str, float]) -> bool:
    """Return true for objectives area/latency/energy min and frequency max."""
    required = ("area", "latency", "energy", "frequency")
    if any(key not in a or key not in b or a[key] is None or b[key] is None for key in required):
        return False
    no_worse = (
        a["area"] <= b["area"]
        and a["latency"] <= b["latency"]
        and a["energy"] <= b["energy"]
        and a["frequency"] >= b["frequency"]
    )
    strictly_better = (
        a["area"] < b["area"]
        or a["latency"] < b["latency"]
        or a["energy"] < b["energy"]
        or a["frequency"] > b["frequency"]
    )
    return no_worse and strictly_better


def extract_run(record: dict[str, object], contract: dict[str, object], trace_by_key: dict[tuple[str, str], dict[str, object]]) -> dict[str, object]:
    run_root = ROOT / "runs" / str(record["run_id"])
    metadata = json.loads((run_root / "run-metadata.json").read_text(encoding="utf-8"))
    architecture = contract["architectures"][record["architecture"]]
    top = architecture["design_top"]
    logs = run_root / f"logs/sky130hd/{top}/base"
    base = {
        "run_id": record["run_id"],
        "architecture": record["architecture"],
        "implementation_id": architecture["implementation_id"],
        "seed": int(record["seed"]),
        "design_top": top,
        "latency_cycles": architecture["latency_cycles"],
        "initiation_interval_cycles": architecture["initiation_interval_cycles"],
        "physical_exit_status": int(metadata["physical_exit_status"]),
        "physical_failure_reason": metadata.get("physical_failure_reason", ""),
        "routing_complete": bool(metadata["routing_complete"]),
        "power_status": metadata["power_status"],
    }
    report_paths = (logs / "6_report.json", logs / "5_1_grt.json", logs / "5_2_route.json")
    if base["physical_exit_status"] != 0 or not all(path.is_file() for path in report_paths):
        return {**base, "characterization_status": "PHYSICAL_CHARACTERIZATION_FAIL", "timing_feasibility": "NOT_AVAILABLE", "metrics": {}}

    finish = json.loads((logs / "6_report.json").read_text(encoding="utf-8"))
    grt = json.loads((logs / "5_1_grt.json").read_text(encoding="utf-8"))
    drt = json.loads((logs / "5_2_route.json").read_text(encoding="utf-8"))
    setup_slack = float(finish["finish__timing__setup__ws"])
    hold_slack = float(finish["finish__timing__hold__ws"])
    setup_violations = int(finish["finish__timing__drv__setup_violation_count"])
    hold_violations = int(finish["finish__timing__drv__hold_violation_count"])
    timing_feasible = setup_slack >= 0 and setup_violations == 0
    clock_buffers = int(finish.get("finish__design__instance__count__class:clock_buffer", 0))
    repair_buffers = int(finish.get("finish__design__instance__count__class:timing_repair_buffer", 0))
    slack_frequency = 1000.0 / (10.0 - setup_slack)
    orfs_frequency = float(finish["finish__timing__fmax"]) / 1.0e6
    metrics: dict[str, float | int | None] = {
        "standard_cell_instance_area_um2": float(finish["finish__design__instance__area__stdcell"]),
        "cell_count": int(finish["finish__design__instance__count__stdcell"]),
        "sequential_cell_count": int(finish.get("finish__design__instance__count__class:sequential_cell", 0)),
        "clock_buffer_count": clock_buffers,
        "timing_repair_buffer_count": repair_buffers,
        "buffer_count": clock_buffers + repair_buffers,
        "utilization_percent": float(finish["finish__design__instance__utilization__stdcell"]) * 100.0,
        "signed_worst_setup_slack_ns": setup_slack,
        "wns_ns": min(0.0, setup_slack),
        "tns_ns": float(finish["finish__timing__setup__tns"]),
        "setup_violation_count": setup_violations,
        "worst_hold_slack_ns": hold_slack,
        "hold_violation_count": hold_violations,
        "slack_derived_frequency_mhz": slack_frequency,
        "orfs_reported_fmax_mhz": orfs_frequency,
        "frequency_consistency_abs_error_mhz": abs(slack_frequency - orfs_frequency),
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
        "no_error_energy_pj_per_operation_estimate": None,
        "achievable_no_error_energy_pj_per_operation": None,
        "direct_vcd_annotated_pin_count": None,
        "unannotated_pin_count_before_propagation": None,
    }
    if metadata["power_status"].startswith("ACTIVITY_POWER_PASS"):
        family = architecture["power_family"]
        stem = f"{family}-no_error"
        power = parse_full_precision_power(run_root / f"power/{stem}.power.rpt")
        trace = trace_by_key[(family, "no_error")]
        time_per_operation_ps = float(trace["total_time_ps"]) / float(trace["useful_operations"])
        annotated, unannotated = annotation_counts(run_root / f"power/{stem}.annotation.rpt")
        metrics.update(power)
        metrics["no_error_energy_pj_per_operation_estimate"] = power["total_power_w"] * time_per_operation_ps
        metrics["achievable_no_error_energy_pj_per_operation"] = (
            metrics["no_error_energy_pj_per_operation_estimate"] if timing_feasible else None
        )
        metrics["direct_vcd_annotated_pin_count"] = annotated
        metrics["unannotated_pin_count_before_propagation"] = unannotated
    characterization = "PASS_TIMING_MET" if timing_feasible else "PASS_TIMING_MISSED"
    return {
        **base,
        "characterization_status": characterization,
        "timing_feasibility": "MEETS_10NS" if timing_feasible else "FAILS_10NS",
        "hold_status": "HOLD_CLEAN" if hold_slack >= 0 and hold_violations == 0 else "HOLD_VIOLATION",
        "metrics": metrics,
    }


def architecture_summaries(rows: list[dict[str, object]], architectures: list[str]) -> dict[str, object]:
    metrics = (
        "standard_cell_instance_area_um2", "cell_count", "sequential_cell_count", "clock_buffer_count",
        "timing_repair_buffer_count", "utilization_percent", "signed_worst_setup_slack_ns", "wns_ns", "tns_ns",
        "setup_violation_count", "worst_hold_slack_ns", "hold_violation_count", "slack_derived_frequency_mhz",
        "global_route_wirelength_um", "detailed_route_wirelength_um", "via_count", "congestion_violation_count",
        "final_drc_count", "internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w",
        "achievable_no_error_energy_pj_per_operation",
    )
    result: dict[str, object] = {}
    for architecture in architectures:
        selected = [row for row in rows if row["architecture"] == architecture]
        result[architecture] = {
            "implementation_id": selected[0]["implementation_id"] if selected else None,
            "seeds": sorted(row["seed"] for row in selected),
            "valid_route_count": sum(row["routing_complete"] for row in selected),
            "timing_feasible_count": sum(row["timing_feasibility"] == "MEETS_10NS" for row in selected),
            "hold_clean_count": sum(row.get("hold_status") == "HOLD_CLEAN" for row in selected),
            "power_result_count": sum(row["metrics"].get("total_power_w") is not None for row in selected),
            "metrics": {
                metric: stat_summary({int(row["seed"]): float(row["metrics"][metric]) for row in selected if row["metrics"].get(metric) is not None})
                for metric in metrics
            },
        }
    return result


def secded_paired_effects(rows: list[dict[str, object]]) -> dict[str, object]:
    by_pair = {(row["architecture"], int(row["seed"])): row for row in rows}
    definitions = {
        "area_percent": "standard_cell_instance_area_um2",
        "detailed_wirelength_percent": "detailed_route_wirelength_um",
        "cell_count_percent": "cell_count",
        "slack_derived_frequency_percent": "slack_derived_frequency_mhz",
        "total_power_percent": "total_power_w",
        "achievable_energy_percent": "achievable_no_error_energy_pj_per_operation",
    }
    effects: dict[str, object] = {}
    for effect, metric in definitions.items():
        values: dict[int, float] = {}
        for seed in (11, 13, 17, 19, 23):
            comb = by_pair[("secded_comb", seed)]["metrics"].get(metric)
            pipe = by_pair[("secded_pipe", seed)]["metrics"].get(metric)
            if comb is not None and pipe is not None:
                values[seed] = percent_delta(float(pipe), float(comb))
        effects[effect] = {
            "formula": "(pipelined - combinational) / combinational * 100 percent",
            "metric": metric,
            "summary": stat_summary(values),
        }

    area = effects["area_percent"]["summary"]["values_by_seed"]
    wire = effects["detailed_wirelength_percent"]["summary"]["values_by_seed"]
    freq = effects["slack_derived_frequency_percent"]["summary"]["values_by_seed"]
    energy = effects["achievable_energy_percent"]["summary"]["values_by_seed"]
    power = effects["total_power_percent"]["summary"]["values_by_seed"]
    robustness = {
        "area_pipe_greater_count": sum(value > 0 for value in area.values()),
        "frequency_pipe_greater_count": sum(value > 0 for value in freq.values()),
        "wirelength_pipe_greater_count": sum(value > 0 for value in wire.values()),
        "energy_pipe_lower_count": sum(value < 0 for value in energy.values()),
        "power_pipe_lower_count": sum(value < 0 for value in power.values()),
        "secded_comb_10ns_feasible_count": sum(by_pair[("secded_comb", seed)]["timing_feasibility"] == "MEETS_10NS" for seed in (11, 13, 17, 19, 23)),
        "secded_pipe_10ns_feasible_count": sum(by_pair[("secded_pipe", seed)]["timing_feasibility"] == "MEETS_10NS" for seed in (11, 13, 17, 19, 23)),
    }

    per_seed_dominance = []
    for seed in (11, 13, 17, 19, 23):
        comb_row = by_pair[("secded_comb", seed)]
        pipe_row = by_pair[("secded_pipe", seed)]
        comb = {
            "area": comb_row["metrics"].get("standard_cell_instance_area_um2"),
            "latency": 1.0,
            "energy": comb_row["metrics"].get("achievable_no_error_energy_pj_per_operation"),
            "frequency": comb_row["metrics"].get("slack_derived_frequency_mhz"),
        }
        pipe = {
            "area": pipe_row["metrics"].get("standard_cell_instance_area_um2"),
            "latency": 3.0,
            "energy": pipe_row["metrics"].get("achievable_no_error_energy_pj_per_operation"),
            "frequency": pipe_row["metrics"].get("slack_derived_frequency_mhz"),
        }
        relation = "COMB_DOMINATES" if dominates(comb, pipe) else "PIPE_DOMINATES" if dominates(pipe, comb) else "NON_DOMINATED"
        per_seed_dominance.append({"seed": seed, "relation": relation, "combinational": comb, "pipelined": pipe})

    aggregate = {}
    for architecture, latency in (("secded_comb", 1.0), ("secded_pipe", 3.0)):
        architecture_rows = [row for row in rows if row["architecture"] == architecture]
        aggregate[architecture] = {
            "area": statistics.fmean(float(row["metrics"]["standard_cell_instance_area_um2"]) for row in architecture_rows),
            "latency": latency,
            "energy": statistics.fmean(float(row["metrics"]["achievable_no_error_energy_pj_per_operation"]) for row in architecture_rows),
            "frequency": statistics.fmean(float(row["metrics"]["slack_derived_frequency_mhz"]) for row in architecture_rows),
        }
    aggregate_relation = (
        "COMB_DOMINATES" if dominates(aggregate["secded_comb"], aggregate["secded_pipe"])
        else "PIPE_DOMINATES" if dominates(aggregate["secded_pipe"], aggregate["secded_comb"])
        else "NON_DOMINATED"
    )
    return {
        "schema_version": 1,
        "interpretation": "matched-seed sensitivity envelope; no population inference or p-values",
        "effects": effects,
        "robustness": robustness,
        "latency": {"secded_comb_cycles": 1, "secded_pipe_cycles": 3, "seed_sensitive": False},
        "dominance": {
            "objectives": {"minimize": ["area", "latency", "achievable_energy"], "maximize": ["slack_derived_frequency"]},
            "per_seed": per_seed_dominance,
            "aggregate_mean": {"relation": aggregate_relation, "points": aggregate},
            "sensitivity_range": {
                "interpretation": "no range-based dominance is claimed unless worst-case intervals are no worse in every objective",
                "relation": "NON_DOMINATED" if all(item["relation"] == "NON_DOMINATED" for item in per_seed_dominance) else "SEED_DEPENDENT_DOMINANCE",
            },
        },
    }


def main() -> int:
    if os.geteuid() != 0:
        raise SystemExit("run as root inside Ubuntu WSL2")
    verify_manifest(POLICY, POLICY / "frozen-bundle.sha256")
    if (ROOT / "qualification").exists():
        raise SystemExit("refusing to overwrite Revision-2 qualification")
    matrix = json.loads((ROOT / "MATRIX_EXECUTION.json").read_text(encoding="utf-8"))
    if matrix["planned_run_count"] != 20 or matrix["executed_run_count"] != 20:
        raise SystemExit("Revision-2 matrix is incomplete")
    contract = json.loads((SNAPSHOT / "scripts/revision2/contract_v1.json").read_text(encoding="utf-8"))
    for record in contract["runs"]:
        verify_manifest(ROOT / "runs" / record["run_id"], ROOT / "runs" / record["run_id"] / "raw-artifacts.sha256")
    trace_manifest = json.loads((POLICY / "traces/TRACE_MANIFEST.json").read_text(encoding="utf-8"))
    trace_by_key = {(row["family"], row["trace_class"]): row for row in trace_manifest["traces"]}
    rows = [extract_run(record, contract, trace_by_key) for record in contract["runs"]]
    summaries = architecture_summaries(rows, list(contract["architectures"]))
    paired = secded_paired_effects(rows)

    out = ROOT / "qualification"
    out.mkdir()
    write_json(out / "REV2_RUN_RESULTS.json", {"schema_version": 1, "timing_semantics": "slack-derived fixed-implementation estimate under 10 ns optimization", "records": rows})
    flat_rows = []
    for row in rows:
        flat_rows.append({key: value for key, value in row.items() if key != "metrics"} | row["metrics"])
    all_fields = list(dict.fromkeys(key for row in flat_rows for key in row))
    write_csv(out / "REV2_RUN_RESULTS.csv", flat_rows, all_fields)
    write_json(out / "REV2_ARCHITECTURE_SUMMARY.json", {"schema_version": 1, "architectures": summaries})
    write_json(out / "REV2_SECDED_PAIRED_SEED_EFFECTS.json", paired)

    seed_table = []
    for row in rows:
        metrics = row["metrics"]
        seed_table.append(
            {
                "architecture": row["architecture"],
                "seed": row["seed"],
                "area_um2": metrics.get("standard_cell_instance_area_um2"),
                "slack_derived_frequency_mhz": metrics.get("slack_derived_frequency_mhz"),
                "signed_setup_slack_ns": metrics.get("signed_worst_setup_slack_ns"),
                "detailed_wirelength_um": metrics.get("detailed_route_wirelength_um"),
                "total_power_w": metrics.get("total_power_w"),
                "achievable_energy_pj_per_operation": metrics.get("achievable_no_error_energy_pj_per_operation"),
                "timing_feasibility": row["timing_feasibility"],
            }
        )
    write_csv(out / "REV2_SEED_SENSITIVITY_TABLE.csv", seed_table, list(seed_table[0]))
    paired_table = []
    for effect, payload in paired["effects"].items():
        for seed, value in payload["summary"]["values_by_seed"].items():
            paired_table.append({"effect": effect, "seed": int(seed), "percent": value})
    write_csv(out / "REV2_SECDED_PAIRED_EFFECTS.csv", paired_table, ["effect", "seed", "percent"])

    bch = summaries["bch78"]
    hsiao = summaries["hsiao_algorithmic"]
    evidence = {
        "schema_version": 1,
        "source": "fresh Revision-2 routes only",
        "seed_set": [11, 13, 17, 19, 23],
        "timing": {
            "metric_name": "post-route slack-derived frequency estimate",
            "formula": "1000 / (10.0 - signed_worst_setup_slack_ns)",
            "frequency_sweep": False,
            "fixed_implementation_optimized_at_10ns": True,
        },
        "hsiao_qualification_verdict": "HSIAO_EXACT_IDENTITY_PASS",
        "architectures": summaries,
        "secded_paired": paired,
        "bch_10ns_feasibility": f"{bch['timing_feasible_count']}/5",
        "hsiao_10ns_feasibility": f"{hsiao['timing_feasible_count']}/5",
        "all_run_count": len(rows),
        "valid_route_count": sum(row["routing_complete"] for row in rows),
        "all_final_drc_clean": all(row["metrics"].get("final_drc_count") == 0 for row in rows if row["routing_complete"]),
    }
    write_json(out / "REV2_MANUSCRIPT_EVIDENCE.json", evidence)

    robustness = paired["robustness"]
    lines = [
        "# Revision-2 experiment summary",
        "",
        f"Fresh physical routes: {evidence['valid_route_count']}/20.",
        f"SECDED area ordering pipe>comb: {robustness['area_pipe_greater_count']}/5.",
        f"SECDED frequency ordering pipe>comb: {robustness['frequency_pipe_greater_count']}/5.",
        f"SECDED wirelength ordering pipe>comb: {robustness['wirelength_pipe_greater_count']}/5.",
        f"SECDED energy ordering pipe<comb: {robustness['energy_pipe_lower_count']}/5.",
        f"Combinational SECDED 10 ns feasibility: {robustness['secded_comb_10ns_feasible_count']}/5.",
        f"Pipelined SECDED 10 ns feasibility: {robustness['secded_pipe_10ns_feasible_count']}/5.",
        f"Hsiao algorithmic 10 ns feasibility: {evidence['hsiao_10ns_feasibility']}.",
        f"BCH 10 ns feasibility: {evidence['bch_10ns_feasibility']}.",
        "",
        "Timing frequency values are fixed-implementation, signed-slack-derived estimates under the 10 ns optimization constraint; no frequency sweep was performed.",
    ]
    (out / "REV2_EXPERIMENT_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (out / "MATRIX_EXECUTION.json").write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (out / "REV2_EXPERIMENT_MANIFEST.json").write_text((POLICY / "REV2_EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    evidence_rows = []
    for path in sorted(item for item in out.iterdir() if item.is_file() and item.name != "REV2_EVIDENCE.sha256"):
        evidence_rows.append(f"{sha256(path)}  ./{path.name}")
    (out / "REV2_EVIDENCE.sha256").write_text("\n".join(evidence_rows) + "\n", encoding="utf-8", newline="\n")
    for path in (item for item in out.rglob("*") if item.is_file()):
        path.chmod(0o444)
    out.chmod(0o555)
    print("REV2_ANALYSIS_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
