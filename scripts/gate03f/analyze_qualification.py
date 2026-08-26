#!/usr/bin/env python3
"""Extract Gate 03F metrics, quantify noise, and issue the single gate verdict."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path("/var/lib/green-ecc-date2027-final")
POLICY = ROOT / "policy"
SNAPSHOT = POLICY / "repo_snapshot"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_policy() -> None:
    for line in (POLICY / "frozen-bundle.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = POLICY / relative.strip()
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"frozen policy hash mismatch: {relative}")


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def metric_statistics(values: list[float]) -> dict[str, object]:
    if len(values) < 2:
        raise ValueError("reproducibility statistics require at least two values")
    mean = statistics.fmean(values)
    stddev = statistics.stdev(values)
    minimum = min(values)
    maximum = max(values)
    observed_range = maximum - minimum
    denominator = max(abs(maximum), abs(minimum))
    max_relative = 0.0 if denominator == 0.0 else observed_range / denominator
    coefficient = None if mean == 0.0 else stddev / abs(mean)
    return {
        "n": len(values),
        "mean": mean,
        "sample_standard_deviation": stddev,
        "coefficient_of_variation": coefficient,
        "coefficient_of_variation_status": "UNDEFINED_ZERO_MEAN" if coefficient is None else "DEFINED",
        "minimum": minimum,
        "maximum": maximum,
        "range": observed_range,
        "maximum_relative_run_to_run_difference": max_relative,
        "zero_observed_variation": observed_range == 0.0,
        "five_x_noise_absolute_threshold": observed_range * 5.0,
        "five_x_noise_relative_threshold": max_relative * 5.0,
    }


def extract_physical(record: dict[str, object]) -> dict[str, object]:
    run_root = ROOT / "runs" / str(record["run_id"])
    top = str(record["design_top"])
    metadata = json.loads((run_root / "run-metadata.json").read_text(encoding="utf-8"))
    logs = run_root / f"logs/sky130hd/{top}/base"
    finish = json.loads((logs / "6_report.json").read_text(encoding="utf-8"))
    global_route = json.loads((logs / "5_1_grt.json").read_text(encoding="utf-8"))
    detailed_route = json.loads((logs / "5_2_route.json").read_text(encoding="utf-8"))
    worst_slack = float(finish["finish__timing__setup__ws"])
    clock_buffers = float(finish.get("finish__design__instance__count__class:clock_buffer", 0))
    repair_buffers = float(finish.get("finish__design__instance__count__class:timing_repair_buffer", 0))
    metrics = {
        "stdcell_area_um2": float(finish["finish__design__instance__area__stdcell"]),
        "setup_worst_slack_ns": worst_slack,
        "wns_ns": min(0.0, worst_slack),
        "tns_ns": float(finish["finish__timing__setup__tns"]),
        "fmax_hz": float(finish["finish__timing__fmax"]),
        "cell_count": float(finish["finish__design__instance__count__stdcell"]),
        "utilization_fraction": float(finish["finish__design__instance__utilization__stdcell"]),
        "detailed_route_wirelength_um": float(detailed_route["detailedroute__route__wirelength"]),
        "drc_count": float(detailed_route["detailedroute__route__drc_errors"]),
        "buffer_count": clock_buffers + repair_buffers,
        "clock_buffer_count": clock_buffers,
        "timing_repair_buffer_count": repair_buffers,
        "sequential_cell_count": float(finish.get("finish__design__instance__count__class:sequential_cell", 0)),
        "global_route_wirelength_um": float(global_route["globalroute__global_route__wirelength"]),
        "global_route_congestion_violations": float(global_route["globalroute__design__violations"]),
        "detailed_route_via_count": float(detailed_route["detailedroute__route__vias"]),
        "routed_signal_net_count": float(detailed_route["detailedroute__route__net"]),
        "finish_flow_error_count": float(finish["finish__flow__errors__count"]),
    }
    return {
        "run_id": record["run_id"],
        "design_family": record["design_family"],
        "design_top": top,
        "clock_period_ns": metadata["clock_period_ns"],
        "physical_seed": metadata["physical_seed"],
        "routing_complete": bool(metadata["routing_complete"]),
        "physical_exit_status": metadata["physical_exit_status"],
        "power_status": metadata["power_status"],
        "metrics": metrics,
    }


def annotation_counts(path: Path) -> tuple[int, int]:
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        pieces = line.split()
        if len(pieces) == 2 and pieces[1].isdigit():
            counts[pieces[0]] = int(pieces[1])
    return counts.get("vcd", 0), counts.get("unannotated", 0)


def extract_power(
    record: dict[str, object], trace_by_key: dict[tuple[str, str], dict[str, object]]
) -> list[dict[str, object]]:
    family = record["power_family"]
    if not family:
        return []
    run_root = ROOT / "runs" / str(record["run_id"])
    rows = []
    for trace_class in ("no_error", "single_error", "double_error"):
        stem = f"{family}-{trace_class}"
        payload = json.loads((run_root / f"power/{stem}.power.json").read_text(encoding="utf-8"))
        total = payload["Total"]
        trace = trace_by_key[(str(family), trace_class)]
        time_per_operation_ps = float(trace["total_time_ps"]) / float(trace["useful_operations"])
        annotated, unannotated = annotation_counts(run_root / f"power/{stem}.annotation.rpt")
        metrics = {
            "internal_power_w": float(total["internal"]),
            "switching_power_w": float(total["switching"]),
            "leakage_power_w": float(total["leakage"]),
            "total_power_w": float(total["total"]),
            "internal_energy_pj_per_operation": float(total["internal"]) * time_per_operation_ps,
            "switching_energy_pj_per_operation": float(total["switching"]) * time_per_operation_ps,
            "leakage_energy_pj_per_operation": float(total["leakage"]) * time_per_operation_ps,
            "total_energy_pj_per_operation": float(total["total"]) * time_per_operation_ps,
            "direct_vcd_annotated_pin_count": float(annotated),
            "unannotated_pin_count_before_propagation": float(unannotated),
        }
        rows.append(
            {
                "run_id": record["run_id"],
                "design_family": record["design_family"],
                "power_family": family,
                "trace_class": trace_class,
                "useful_operations": trace["useful_operations"],
                "total_time_ps": trace["total_time_ps"],
                "metrics": metrics,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logical-validation", choices=("PASS", "FAIL"), required=True)
    args = parser.parse_args()
    verify_policy()

    out = ROOT / "qualification"
    if out.exists():
        raise SystemExit(f"refusing to overwrite qualification analysis: {out}")
    out.mkdir()
    contract = json.loads((SNAPSHOT / "scripts/gate03f/contract_v1.json").read_text(encoding="utf-8"))
    environment = json.loads((POLICY / "DATE_FINAL_PHYSICAL_ENVIRONMENT.json").read_text(encoding="utf-8"))
    records = contract["qualification_runs"]
    missing = [record["run_id"] for record in records if not (ROOT / "runs" / record["run_id"] / "run-metadata.json").is_file()]
    if missing:
        raise SystemExit(f"concrete qualification measurements missing: {missing}")

    physical_rows = [extract_physical(record) for record in records]
    trace_manifest = json.loads((POLICY / "traces/TRACE_MANIFEST.json").read_text(encoding="utf-8"))
    trace_by_key = {
        (str(item["family"]), str(item["trace_class"])): item
        for item in trace_manifest["traces"]
        if float(item["clock_period_ns"]) == 10.0
    }
    power_rows = [row for record in records for row in extract_power(record, trace_by_key)]

    physical_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in physical_rows:
        physical_groups[str(row["design_family"])].append(row)
    physical_stats: dict[str, dict[str, object]] = {}
    for family, rows in sorted(physical_groups.items()):
        names = sorted(rows[0]["metrics"])
        physical_stats[family] = {
            name: metric_statistics([float(row["metrics"][name]) for row in rows]) for name in names
        }

    power_groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in power_rows:
        power_groups[(str(row["design_family"]), str(row["trace_class"]))].append(row)
    power_stats: dict[str, dict[str, object]] = {}
    for (family, trace_class), rows in sorted(power_groups.items()):
        key = f"{family}:{trace_class}"
        names = sorted(rows[0]["metrics"])
        power_stats[key] = {
            name: metric_statistics([float(row["metrics"][name]) for row in rows]) for name in names
        }

    geometric_metrics = (
        "stdcell_area_um2", "cell_count", "utilization_fraction", "detailed_route_wirelength_um"
    )
    timing_metrics = ("setup_worst_slack_ns", "fmax_hz")
    geometric_stable = all(
        stats[name]["maximum_relative_run_to_run_difference"]
        <= contract["statistics"]["area_cell_utilization_wirelength_max_noise_fraction"]
        for stats in physical_stats.values() for name in geometric_metrics
    )
    timing_stable = all(
        stats[name]["maximum_relative_run_to_run_difference"]
        <= contract["statistics"]["timing_fmax_max_noise_fraction"]
        for stats in physical_stats.values() for name in timing_metrics
    )
    routes_valid = all(
        row["routing_complete"]
        and row["physical_exit_status"] == 0
        and row["metrics"]["drc_count"] == 0
        and row["metrics"]["finish_flow_error_count"] == 0
        for row in physical_rows
    )
    power_complete = len(power_rows) == 12 and all(
        row["power_status"] == "ACTIVITY_POWER_PASS"
        for row in physical_rows if row["design_family"] != "gcd"
    )
    power_stable = power_complete and all(
        stats["total_power_w"]["maximum_relative_run_to_run_difference"]
        <= contract["statistics"]["power_max_noise_fraction"]
        for stats in power_stats.values()
    )
    power_verdict = "ACTIVITY_BASED_POWER_QUALIFIED" if power_stable else "POWER_DEFERRED"

    conditions = {
        "provenance_pinned": environment["state"] == "DATE_FINAL_PHYSICAL_ENVIRONMENT_FROZEN",
        "exactly_seven_unique_runs_present": len(physical_rows) == 7 and len({row["run_id"] for row in physical_rows}) == 7,
        "all_runs_complete_normally": all(row["physical_exit_status"] == 0 for row in physical_rows),
        "logical_behavior_valid": args.logical_validation == "PASS",
        "routing_and_drc_consistent": routes_valid,
        "area_cell_utilization_wirelength_stable": geometric_stable,
        "timing_and_fmax_stable": timing_stable,
        "noise_small_enough_for_meaningful_ecc_comparison": geometric_stable and timing_stable,
    }
    verdict = "GATE_03F_PASS" if all(conditions.values()) else "GATE_03F_FAIL"
    gate04_state = "GATE_04_READY" if verdict == "GATE_03F_PASS" else "GATE_04_NOT_READY"

    write_json(out / "QUALIFICATION_RUN_METRICS.json", {"schema_version": 1, "runs": physical_rows})
    write_json(out / "POWER_RESULTS.json", {"schema_version": 1, "status": power_verdict, "rows": power_rows})
    write_json(
        out / "REPRODUCIBILITY_STATISTICS.json",
        {
            "schema_version": 1,
            "physical": physical_stats,
            "power": power_stats,
            "interpretation_policy": contract["statistics"]["interpretation_policy"],
            "noise_magnitude": contract["statistics"]["noise_magnitude"],
            "zero_noise_policy": contract["statistics"]["zero_noise_policy"],
        },
    )
    verdict_payload = {
        "schema_version": 1,
        "verdict": verdict,
        "gate04_state": gate04_state,
        "power_status": power_verdict,
        "conditions": conditions,
        "interpretation_policy": contract["statistics"]["interpretation_policy"],
        "environment_manifest_sha256": sha256(POLICY / "DATE_FINAL_PHYSICAL_ENVIRONMENT.json"),
        "physical_run_count": len(physical_rows),
        "power_result_count": len(power_rows),
    }
    write_json(out / "GATE_03F_VERDICT.json", verdict_payload)

    metric_names = sorted(physical_rows[0]["metrics"])
    with (out / "QUALIFICATION_RUN_METRICS.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = [
            "run_id", "design_family", "design_top", "clock_period_ns", "physical_seed",
            "routing_complete", "physical_exit_status", "power_status", *metric_names,
        ]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in physical_rows:
            writer.writerow({**{key: row[key] for key in fields if key in row}, **row["metrics"]})

    report = f"""# DATE 2027 Gate 03F qualification verdict

`{verdict}`

`{gate04_state}`

Seven immutable physical runs were evaluated: three GCD, two representative conventional SECDED (72,64), and two BCH (78,64,t=2). All used the frozen image, SKY130HD corner, 10.0 ns clock, constraints policy, placement settings, seed 11, and one OpenROAD worker.

## Adjudication

""" + "\n".join(f"- {name}: `{'PASS' if value else 'FAIL'}`" for name, value in conditions.items()) + f"""

## Power

`{power_verdict}`

Power is nonblocking for Gate 03F. When qualified, values are post-route OpenSTA estimates from deterministic 100,000-operation VCDs for no-error, single-error, and double-error activity. No arbitrary toggle rate or field-rate weighting is used. Energy per useful operation is total trace energy divided by exactly 100,000 useful transactions.

## Frozen interpretation policy

> {contract['statistics']['interpretation_policy']}

Noise is the observed repeated-run range in each metric's own units. Every report also retains the sample standard deviation, coefficient of variation, extrema, range, and maximum relative run-to-run difference. Zero observed variation is reported as zero; no positive tolerance is invented.
"""
    (out / "GATE_03F_REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(f"{verdict} {gate04_state} {power_verdict}")
    return 0 if verdict == "GATE_03F_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
