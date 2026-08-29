#!/usr/bin/env python3
"""Decompose immutable Revision-2 SECDED power without modifying old evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path


REV2 = Path("/var/lib/green-ecc-date2027-revision2")
FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
SEEDS = (11, 13, 17, 19, 23)
POWER_ARITHMETIC_TOLERANCE_W = 1.0e-8


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def verify_manifest(root: Path, manifest: Path) -> None:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = root / relative.strip().removeprefix("./")
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"immutable manifest mismatch: {path}")


def manifest_map(path: Path) -> dict[str, str]:
    return {
        relative.strip(): expected
        for expected, relative in (line.split(maxsplit=1) for line in path.read_text(encoding="utf-8").splitlines())
    }


def verify_join_file(run_root: Path, inventory: dict[str, str], relative: str) -> str:
    path = run_root / relative
    if relative not in inventory:
        raise SystemExit(f"run inventory omits joined evidence: {path}")
    actual = sha256(path)
    if actual != inventory[relative]:
        raise SystemExit(f"run evidence hash mismatch: {path}")
    return actual


def parse_power_groups(path: Path) -> dict[str, dict[str, float]]:
    groups: dict[str, dict[str, float]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        pieces = line.split()
        if pieces and pieces[0] in {"Sequential", "Combinational", "Clock", "Macro", "Pad", "Total"}:
            values = [float(value) for value in FLOAT_RE.findall(line)]
            if len(values) >= 4:
                groups[pieces[0].lower()] = dict(
                    zip(("internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w"), values[:4])
                )
    required = {"sequential", "combinational", "clock", "total"}
    if not required.issubset(groups):
        raise ValueError(f"missing OpenSTA groups {sorted(required - set(groups))}: {path}")
    return groups


def stat_summary(values_by_seed: dict[int, float]) -> dict[str, object]:
    values = [values_by_seed[seed] for seed in sorted(values_by_seed)]
    return {
        "count": len(values),
        "values_by_seed": {str(seed): values_by_seed[seed] for seed in sorted(values_by_seed)},
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "sample_standard_deviation": statistics.stdev(values) if len(values) > 1 else 0.0,
        "minimum": min(values),
        "maximum": max(values),
        "range": max(values) - min(values),
    }


def percent_delta(value: float, reference: float) -> float:
    return (value - reference) / reference * 100.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = repo / "campaigns/date_2027_breadth_remediation/analysis"
    out.mkdir(parents=True, exist_ok=True)
    targets = (
        out / "B_power_components_per_seed.csv",
        out / "B_power_components_summary.json",
        out / "B_power_decomposition_report.md",
    )
    if any(path.exists() for path in targets):
        raise SystemExit("refusing to overwrite Workstream B analysis")

    verify_manifest(REV2 / "policy", REV2 / "policy/frozen-bundle.sha256")
    contract = json.loads((REV2 / "policy/repo_snapshot/scripts/revision2/contract_v1.json").read_text(encoding="utf-8"))
    published = json.loads((repo / "docs/date2027/revision2/results/REV2_RUN_RESULTS.json").read_text(encoding="utf-8"))
    published_by_id = {row["run_id"]: row for row in published["records"]}
    trace_manifest = json.loads((REV2 / "policy/traces/TRACE_MANIFEST.json").read_text(encoding="utf-8"))
    trace = next(
        row for row in trace_manifest["traces"]
        if row["family"] == "conventional_secded" and row["trace_class"] == "no_error"
    )
    trace_path = REV2 / "policy/traces" / trace["file"]
    if sha256(trace_path) != trace["compressed_sha256"]:
        raise SystemExit("Revision-2 conventional SECDED trace hash mismatch")
    trace_time_per_operation_ps = float(trace["total_time_ps"]) / float(trace["useful_operations"])

    rows: list[dict[str, object]] = []
    for architecture in ("secded_comb", "secded_pipe"):
        arch = contract["architectures"][architecture]
        for seed in SEEDS:
            record = next(
                row for row in contract["runs"]
                if row["architecture"] == architecture and int(row["seed"]) == seed
            )
            run_root = REV2 / "runs" / record["run_id"]
            inventory = manifest_map(run_root / "raw-artifacts.sha256")
            metadata_hash = verify_join_file(run_root, inventory, "run-metadata.json")
            environment_hash = verify_join_file(run_root, inventory, "effective-run-environment.json")
            metadata = json.loads((run_root / "run-metadata.json").read_text(encoding="utf-8"))
            environment = json.loads((run_root / "effective-run-environment.json").read_text(encoding="utf-8"))
            if (
                metadata["run_id"] != record["run_id"]
                or metadata["architecture"] != architecture
                or int(metadata["physical_seed"]) != seed
                or metadata["implementation_id"] != arch["implementation_id"]
                or environment["RUN_ID"] != record["run_id"]
                or int(environment["GPL_RANDOM_SEED"]) != seed
                or int(environment["GRT_SEED"]) != seed
                or int(environment["OR_SEED"]) != seed
            ):
                raise SystemExit(f"run identity join mismatch: {record['run_id']}")
            top = arch["design_top"]
            base = f"results/sky130hd/{top}/base"
            odb_hash = verify_join_file(run_root, inventory, f"{base}/6_final.odb")
            netlist_hash = verify_join_file(run_root, inventory, f"{base}/6_final.v")
            sdc_hash = verify_join_file(run_root, inventory, f"{base}/6_final.sdc")
            spef_hash = verify_join_file(run_root, inventory, f"{base}/6_final.spef")
            power_label = "conventional_secded-no_error"
            report_relative = f"power/{power_label}.power.rpt"
            report_hash = verify_join_file(run_root, inventory, report_relative)
            power_command_hash = verify_join_file(run_root, inventory, "power-command.txt")
            command = (run_root / "power-command.txt").read_text(encoding="utf-8")
            if str(trace_path).replace(str(REV2 / "policy"), "/rev2-policy") not in command:
                raise SystemExit(f"power command does not reference joined trace: {record['run_id']}")
            groups = parse_power_groups(run_root / report_relative)
            total = groups["total"]
            component_residual = (
                total["internal_power_w"] + total["switching_power_w"] + total["leakage_power_w"]
                - total["total_power_w"]
            )
            group_residuals = {
                metric: sum(groups[group][metric] for group in ("sequential", "combinational", "clock", "macro", "pad"))
                - total[metric]
                for metric in ("internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w")
            }
            if abs(component_residual) > POWER_ARITHMETIC_TOLERANCE_W or any(
                abs(value) > POWER_ARITHMETIC_TOLERANCE_W for value in group_residuals.values()
            ):
                raise SystemExit(f"power report arithmetic mismatch: {record['run_id']}")
            reconstructed_energy = total["total_power_w"] * trace_time_per_operation_ps
            published_row = published_by_id[record["run_id"]]
            published_total = float(published_row["metrics"]["total_power_w"])
            published_energy = float(published_row["metrics"]["no_error_energy_pj_per_operation_estimate"])
            total_error = reconstructed_energy - published_energy
            power_error = total["total_power_w"] - published_total
            if abs(total_error) > 1e-9 or abs(power_error) > 1e-15:
                raise SystemExit(f"published power/energy reproduction mismatch: {record['run_id']}")
            row: dict[str, object] = {
                "seed": seed,
                "architecture": architecture,
                "implementation_id": arch["implementation_id"],
                "run_id": record["run_id"],
                "internal_power_w": total["internal_power_w"],
                "switching_power_w": total["switching_power_w"],
                "leakage_power_w": total["leakage_power_w"],
                "total_power_w": total["total_power_w"],
                "energy_per_op_pj": reconstructed_energy,
                "sequential_internal_power_w": groups["sequential"]["internal_power_w"],
                "sequential_switching_power_w": groups["sequential"]["switching_power_w"],
                "sequential_leakage_power_w": groups["sequential"]["leakage_power_w"],
                "sequential_total_power_w": groups["sequential"]["total_power_w"],
                "combinational_internal_power_w": groups["combinational"]["internal_power_w"],
                "combinational_switching_power_w": groups["combinational"]["switching_power_w"],
                "combinational_leakage_power_w": groups["combinational"]["leakage_power_w"],
                "combinational_total_power_w": groups["combinational"]["total_power_w"],
                "clock_internal_power_w": groups["clock"]["internal_power_w"],
                "clock_switching_power_w": groups["clock"]["switching_power_w"],
                "clock_leakage_power_w": groups["clock"]["leakage_power_w"],
                "clock_total_power_w": groups["clock"]["total_power_w"],
                "component_sum_residual_w": component_residual,
                "maximum_group_sum_residual_w": max(abs(value) for value in group_residuals.values()),
                "published_total_power_error_w": power_error,
                "published_energy_error_pj": total_error,
                "trace_total_time_ps": trace["total_time_ps"],
                "useful_operations": trace["useful_operations"],
                "rtl_hashes_json": json.dumps({source: contract["source_hashes"][source] for source in arch.get("sources", contract["source_hashes"]) if source in contract["source_hashes"]}, sort_keys=True),
                "run_metadata_sha256": metadata_hash,
                "effective_environment_sha256": environment_hash,
                "final_odb_sha256": odb_hash,
                "final_netlist_sha256": netlist_hash,
                "final_sdc_sha256": sdc_hash,
                "final_spef_sha256": spef_hash,
                "vcd_sha256": trace["compressed_sha256"],
                "power_report_sha256": report_hash,
                "power_command_sha256": power_command_hash,
                "evidence_join_status": "PASS",
            }
            rows.append(row)

    write_csv(targets[0], rows)
    metrics = (
        "internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w", "energy_per_op_pj",
        "sequential_total_power_w", "combinational_total_power_w", "clock_total_power_w",
        "sequential_internal_power_w", "combinational_internal_power_w", "clock_internal_power_w",
        "sequential_switching_power_w", "combinational_switching_power_w", "clock_switching_power_w",
    )
    by_key = {(str(row["architecture"]), int(row["seed"])): row for row in rows}
    architecture_summary = {
        architecture: {
            metric: stat_summary({seed: float(by_key[(architecture, seed)][metric]) for seed in SEEDS})
            for metric in metrics
        }
        for architecture in ("secded_comb", "secded_pipe")
    }
    paired = {}
    for metric in metrics:
        effects = {
            seed: percent_delta(
                float(by_key[("secded_pipe", seed)][metric]),
                float(by_key[("secded_comb", seed)][metric]),
            )
            for seed in SEEDS
        }
        differences = {
            seed: float(by_key[("secded_pipe", seed)][metric]) - float(by_key[("secded_comb", seed)][metric])
            for seed in SEEDS
        }
        paired[metric] = {
            "formula": "(pipelined - combinational) / combinational * 100 percent",
            "percent_effect": stat_summary(effects),
            "absolute_difference": stat_summary(differences),
            "pipelined_lower_count": sum(value < 0 for value in differences.values()),
        }
    top_level_contributions = {
        metric: paired[metric]["absolute_difference"]["mean"]
        for metric in ("internal_power_w", "switching_power_w", "leakage_power_w")
    }
    primary_component = max(top_level_contributions, key=lambda key: abs(top_level_contributions[key]))
    summary = {
        "schema_version": 1,
        "source": "immutable Revision-2 full-precision OpenSTA reports",
        "seed_set": list(SEEDS),
        "evidence_join_count": sum(row["evidence_join_status"] == "PASS" for row in rows),
        "report_arithmetic_status": "PASS",
        "report_arithmetic_tolerance_w": POWER_ARITHMETIC_TOLERANCE_W,
        "maximum_observed_component_sum_residual_w": max(abs(float(row["component_sum_residual_w"])) for row in rows),
        "maximum_observed_group_sum_residual_w": max(float(row["maximum_group_sum_residual_w"]) for row in rows),
        "published_total_power_reproduction_status": "PASS",
        "published_energy_reproduction_status": "PASS",
        "clock_power_availability": "SEPARATELY_AVAILABLE_AS_OPENSTA_CLOCK_GROUP",
        "register_power_availability": "SEQUENTIAL_GROUP_AVAILABLE; REGISTER_SUBTYPES_NOT_SEPARATELY_AVAILABLE",
        "clock_buffer_inverter_availability": "CLOCK_GROUP_AVAILABLE; BUFFER_AND_INVERTER_SUBTYPES_NOT_SEPARATELY_AVAILABLE",
        "architecture_summary": architecture_summary,
        "paired_effects": paired,
        "mean_top_level_component_differences_w": top_level_contributions,
        "primary_component_by_absolute_mean_difference": primary_component,
        "activity_analysis": {
            "status": "NOT_SEPARATELY_ASSESSABLE",
            "reason": "The immutable VCD contains primary inputs only; OpenSTA propagated activity but no per-net toggle table was preserved.",
            "glitch_suppression_claim": "HYPOTHESIS_ONLY",
        },
    }
    write_json(targets[1], summary)

    internal_pct = paired["internal_power_w"]["percent_effect"]
    switching_pct = paired["switching_power_w"]["percent_effect"]
    leakage_pct = paired["leakage_power_w"]["percent_effect"]
    total_pct = paired["total_power_w"]["percent_effect"]
    energy_pct = paired["energy_per_op_pj"]["percent_effect"]
    report = [
        "# Workstream B power decomposition",
        "",
        "## Evidence join and reproduction",
        "",
        "All 10 combinational/pipelined matched-seed records were hash-joined to their immutable run metadata, seed environment, final ODB and netlist, SDC, SPEF, primary-input VCD, power command, and full-precision OpenSTA report. Published total power and energy/op were reproduced exactly to the extraction tolerances. OpenSTA's independently accumulated displayed component/group rows close within the declared 1e-8 W bound; the exact residual is preserved per seed rather than treated as zero.",
        "",
        "## Measured decomposition",
        "",
        f"Across the five paired seeds, pipelining changes internal power by {internal_pct['mean']:.6f}% on average ({paired['internal_power_w']['pipelined_lower_count']}/5 lower), switching power by {switching_pct['mean']:.6f}% ({paired['switching_power_w']['pipelined_lower_count']}/5 lower), leakage by {leakage_pct['mean']:.6f}% ({paired['leakage_power_w']['pipelined_lower_count']}/5 lower), total power by {total_pct['mean']:.6f}% ({paired['total_power_w']['pipelined_lower_count']}/5 lower), and reconstructed energy/op by {energy_pct['mean']:.6f}% ({paired['energy_per_op_pj']['pipelined_lower_count']}/5 lower).",
        "",
        "| Top-level component | Combinational mean (W) | Pipelined mean (W) | Mean paired effect | Pipelined lower |",
        "|---|---:|---:|---:|---:|",
        f"| Internal | {architecture_summary['secded_comb']['internal_power_w']['mean']:.10f} | {architecture_summary['secded_pipe']['internal_power_w']['mean']:.10f} | {internal_pct['mean']:+.6f}% | {paired['internal_power_w']['pipelined_lower_count']}/5 |",
        f"| Switching | {architecture_summary['secded_comb']['switching_power_w']['mean']:.10f} | {architecture_summary['secded_pipe']['switching_power_w']['mean']:.10f} | {switching_pct['mean']:+.6f}% | {paired['switching_power_w']['pipelined_lower_count']}/5 |",
        f"| Leakage | {architecture_summary['secded_comb']['leakage_power_w']['mean']:.10e} | {architecture_summary['secded_pipe']['leakage_power_w']['mean']:.10e} | {leakage_pct['mean']:+.6f}% | {paired['leakage_power_w']['pipelined_lower_count']}/5 |",
        f"| Total | {architecture_summary['secded_comb']['total_power_w']['mean']:.10f} | {architecture_summary['secded_pipe']['total_power_w']['mean']:.10f} | {total_pct['mean']:+.6f}% | {paired['total_power_w']['pipelined_lower_count']}/5 |",
        f"| Energy/op (pJ) | {architecture_summary['secded_comb']['energy_per_op_pj']['mean']:.6f} | {architecture_summary['secded_pipe']['energy_per_op_pj']['mean']:.6f} | {energy_pct['mean']:+.6f}% | {paired['energy_per_op_pj']['pipelined_lower_count']}/5 |",
        "",
        f"The mean absolute switching change is {top_level_contributions['switching_power_w']:.10f} W, while internal changes by {top_level_contributions['internal_power_w']:.10f} W and leakage by {top_level_contributions['leakage_power_w']:.10e} W. `{primary_component}` is therefore the largest absolute mean top-level contribution and numerically accounts for the total-power reduction.",
        "",
        f"OpenSTA cell groups reinforce, but do not causally explain, the decomposition: combinational-group total power changes by {paired['combinational_total_power_w']['percent_effect']['mean']:.6f}% ({paired['combinational_total_power_w']['pipelined_lower_count']}/5 lower), whereas sequential-group total changes by {paired['sequential_total_power_w']['percent_effect']['mean']:.6f}% ({paired['sequential_total_power_w']['pipelined_lower_count']}/5 lower) and clock-group total changes by {paired['clock_total_power_w']['percent_effect']['mean']:.6f}% ({paired['clock_total_power_w']['pipelined_lower_count']}/5 lower). Exact per-seed and descriptive values are in the CSV and JSON outputs.",
        "",
        "## Interpretation discipline",
        "",
        "MEASURED: the component directions and magnitudes above come directly from the routed full-precision power reports.",
        "",
        "SUPPORTED INTERPRETATION: the decomposition identifies which OpenSTA power component and cell group numerically account for the total difference.",
        "",
        "HYPOTHESIS: glitch suppression or logic-depth effects may explain reduced switching, but the immutable primary-input-only VCD/report bundle does not preserve per-net activity evidence. Therefore no causal glitch-suppression claim is made.",
        "",
        "`CLOCK_POWER = SEPARATELY_AVAILABLE_AS_OPENSTA_CLOCK_GROUP`",
        "",
        "Register and clock-buffer/inverter subtypes are not separately reported beyond OpenSTA's Sequential and Clock groups; no unsupported subdivision is estimated.",
        "",
        f"All ten reconstructed totals and energy/op values match the qualified Revision-2 results. The maximum displayed top-level component residual is {summary['maximum_observed_component_sum_residual_w']:.10e} W and the maximum displayed cell-group residual is {summary['maximum_observed_group_sum_residual_w']:.10e} W, both within the declared {POWER_ARITHMETIC_TOLERANCE_W:.0e} W report-precision tolerance.",
    ]
    targets[2].write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print("B_POWER_DECOMPOSITION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
