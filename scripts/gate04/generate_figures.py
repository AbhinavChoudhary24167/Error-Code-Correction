#!/usr/bin/env python3
"""Generate only the ten preregistered Gate 04 figures from validated CSV data."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SHORT = {
    "secded-rtl-combinational-72-64-v1": "SECDED comb",
    "secded-rtl-pipelined-72-64-v1": "SECDED pipe",
    "hsiao-generated-combinational-72-64-v1": "Hsiao",
    "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1": "BCH(78,64,t=2)",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    root = args.results.resolve()
    figure_dir = root / "figures"
    figure_dir.mkdir(exist_ok=True)
    verdict = (root / "GATE_04_VERDICT.txt").read_text(encoding="utf-8").strip()
    specs = [
        ("F01", "paired_seed_area.png", "paired-seed post-route area comparison", "um^2", "PPA_RESULTS.csv", "Individual paired seeds at both clocks; medians shown by distribution"),
        ("F02", "timing_fmax.png", "timing and maximum-feasible-frequency comparison", "MHz", "PPA_RESULTS.csv", "Five physical seeds per candidate and clock"),
        ("F03", "activity_power_energy.png", "activity-based power and energy-per-operation comparison", "mW and pJ/op", "POWER_RESULTS.csv", "No-error trace; five physical seeds"),
        ("F04", "same_code_tradeoff.png", "same-code combinational versus pipelined tradeoff", "um^2 and MHz", "PPA_RESULTS.csv", "Paired seed lines"),
        ("F05", "physical_ppa_pareto.png", "physical PPA Pareto frontier", "um^2 versus pJ/op", "PPA_RESULTS.csv; POWER_RESULTS.csv", "Seed variation shown as points"),
        ("F06", "reliability_physical_pareto.png", "reliability-versus-physical-cost Pareto frontier", "conditional SDC probability versus um^2", "RELIABILITY_RESULTS.csv; PPA_RESULTS.csv", "Exact triple-random enumeration plus median physical area"),
        ("F07", "selector_decision_map.png", "selector decision map across scenarios", "selection count", "DSE_RESULTS.csv", "All preregistered scenarios and physical seeds"),
        ("F08", "analytical_vs_implementation_regret.png", "mathematical-only versus implementation-aware regret", "normalized regret", "DSE_RESULTS.csv", "Distribution across frozen scenarios and seeds"),
        ("F09", "mapping_interleaving_scrub_sensitivity.png", "mapping/interleaving/scrubbing sensitivity", "selection count", "DSE_RESULTS.csv", "Stratified exhaustive selections"),
        ("F10", "evidence_provenance_summary.png", "evidence/provenance summary", "machine-readable row count", "PPA_RESULTS.csv; POWER_RESULTS.csv; RELIABILITY_RESULTS.csv; DSE_RESULTS.csv; CLAIMS_LEDGER.csv", "Evidence-class counts; not a scientific effect size"),
    ]
    manifest: list[dict[str, object]] = []
    if verdict == "ASIC_EXPERIMENT_BLOCKED":
        for figure_id, filename, description, unit, sources, uncertainty in specs:
            manifest.append({"figure_id": figure_id, "file": filename, "status": "NOT_GENERATED_BLOCKED_RAW_EVIDENCE", "sha256": "UNAVAILABLE", "raw_data_references": sources, "units": unit, "uncertainty_or_seed_variation": uncertainty, "caption_ready_description": description})
        with (root / "FIGURE_DATA_MANIFEST.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(manifest[0]), lineterminator="\n")
            writer.writeheader(); writer.writerows(manifest)
        print("GATE04_FIGURES_NOT_GENERATED blocked")
        return 0

    ppa = rows(root / "PPA_RESULTS.csv")
    power = rows(root / "POWER_RESULTS.csv")
    reliability = rows(root / "RELIABILITY_RESULTS.csv")
    dse = rows(root / "DSE_RESULTS.csv")
    candidates = list(SHORT)
    colors = dict(zip(candidates, ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728")))

    def ppa_values(metric: str, clock: float) -> dict[str, list[tuple[int, float]]]:
        values: dict[str, list[tuple[int, float]]] = defaultdict(list)
        for row in ppa:
            if row["implementation_id"] in SHORT and row["metric"] == metric and float(row["clock_period_ns"]) == clock:
                values[row["implementation_id"]].append((int(row["physical_seed"]), float(row["value"])))
        return values

    # F01
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for axis, clock in zip(axes, (10.0, 5.0)):
        values = ppa_values("stdcell_area_um2", clock)
        for index, impl in enumerate(candidates):
            points = sorted(values[impl])
            axis.scatter([index] * len(points), [value for _, value in points], color=colors[impl], alpha=.8)
        axis.set_xticks(range(4), [SHORT[item] for item in candidates], rotation=25, ha="right")
        axis.set_title(f"{clock:g} ns")
        axis.grid(axis="y", alpha=.25)
    axes[0].set_ylabel("Post-route standard-cell area (um^2)")
    save(fig, figure_dir / specs[0][1])

    # F02
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for axis, clock in zip(axes, (10.0, 5.0)):
        values = ppa_values("fmax_hz", clock)
        axis.boxplot([[value / 1e6 for _, value in values[impl]] for impl in candidates], tick_labels=[SHORT[item] for item in candidates])
        axis.tick_params(axis="x", rotation=25)
        axis.set_title(f"{clock:g} ns context")
        axis.grid(axis="y", alpha=.25)
    axes[0].set_ylabel("Fmax (MHz)")
    save(fig, figure_dir / specs[1][1])

    # F03 raw candidate no-error at 10 ns.
    selected_power = [row for row in power if row["implementation_id"] in SHORT and row["workload_fault_trace"] == "no_error" and row["clock_period_ns"] == "10.0" and row["evidence_class"] == "SYNTHESIZED"]
    grouped_power: dict[str, list[float]] = defaultdict(list)
    grouped_energy: dict[str, list[float]] = defaultdict(list)
    for row in selected_power:
        grouped_power[row["implementation_id"]].append(float(row["total_power_w"]) * 1e3)
        if row["energy_per_useful_operation_j"] != "UNRESOLVED_TIMING_UNMET":
            grouped_energy[row["implementation_id"]].append(float(row["energy_per_useful_operation_j"]) * 1e12)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].boxplot([grouped_power[item] for item in candidates], tick_labels=[SHORT[item] for item in candidates]); axes[0].set_ylabel("Power (mW)")
    axes[1].boxplot([grouped_energy[item] for item in candidates], tick_labels=[SHORT[item] for item in candidates]); axes[1].set_ylabel("Energy (pJ/useful op)")
    for axis in axes: axis.tick_params(axis="x", rotation=25); axis.grid(axis="y", alpha=.25)
    save(fig, figure_dir / specs[2][1])

    # F04
    comb_area = dict(ppa_values("stdcell_area_um2", 10.0)[candidates[0]])
    pipe_area = dict(ppa_values("stdcell_area_um2", 10.0)[candidates[1]])
    comb_fmax = dict(ppa_values("fmax_hz", 10.0)[candidates[0]])
    pipe_fmax = dict(ppa_values("fmax_hz", 10.0)[candidates[1]])
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for seed in sorted(comb_area):
        axes[0].plot([0, 1], [comb_area[seed], pipe_area[seed]], marker="o", alpha=.65)
        axes[1].plot([0, 1], [comb_fmax[seed] / 1e6, pipe_fmax[seed] / 1e6], marker="o", alpha=.65)
    axes[0].set_ylabel("Area (um^2)"); axes[1].set_ylabel("Fmax (MHz)")
    for axis in axes: axis.set_xticks([0, 1], ["comb", "pipe"]); axis.grid(alpha=.25)
    save(fig, figure_dir / specs[3][1])

    # F05
    area10 = ppa_values("stdcell_area_um2", 10.0)
    energy10 = defaultdict(dict)
    for row in selected_power:
        if row["energy_per_useful_operation_j"] != "UNRESOLVED_TIMING_UNMET":
            energy10[row["implementation_id"]][int(row["physical_seed"])] = float(row["energy_per_useful_operation_j"]) * 1e12
    fig, axis = plt.subplots(figsize=(6, 5))
    for impl in candidates:
        for seed, area in area10[impl]:
            if seed in energy10[impl]: axis.scatter(area, energy10[impl][seed], color=colors[impl], label=SHORT[impl] if seed == 11 else None)
    axis.set_xlabel("Standard-cell area (um^2)"); axis.set_ylabel("Energy (pJ/useful op)"); axis.legend(); axis.grid(alpha=.25)
    save(fig, figure_dir / specs[4][1])

    # F06
    rel_lookup = {}
    for row in reliability:
        if row["fault_model"] == "triple_random" and row["logical_physical_mapping"] == "identity" and row["interleaving_factor"] == "1":
            rel_lookup[row["implementation_id"]] = float(row["residual_sdc_probability"])
    fig, axis = plt.subplots(figsize=(6, 5))
    for impl in candidates:
        area = sum(value for _, value in area10[impl]) / len(area10[impl])
        axis.scatter(area, rel_lookup[impl], color=colors[impl], s=55, label=SHORT[impl])
    axis.set_xlabel("Mean standard-cell area (um^2)"); axis.set_ylabel("Triple-random conditional SDC probability"); axis.legend(); axis.grid(alpha=.25)
    save(fig, figure_dir / specs[5][1])

    # F07
    decision_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in dse:
        decision_counts[row["selector"]][row["selected_implementation_id"]] += 1
    selector_names = list(decision_counts)
    fig, axis = plt.subplots(figsize=(9, 5))
    bottom = [0] * len(selector_names)
    for impl in candidates:
        values = [decision_counts[name][impl] for name in selector_names]
        axis.bar(range(len(selector_names)), values, bottom=bottom, color=colors[impl], label=SHORT[impl])
        bottom = [left + right for left, right in zip(bottom, values)]
    axis.set_xticks(range(len(selector_names)), [name.replace("_", " ") for name in selector_names], rotation=20, ha="right"); axis.set_ylabel("Selected scenario-seed rows"); axis.legend(fontsize=8)
    save(fig, figure_dir / specs[6][1])

    # F08
    regret: dict[str, list[float]] = defaultdict(list)
    for row in dse:
        value = row["normalized_regret_vs_exhaustive"]
        if value != "UNAVAILABLE": regret[row["selector"]].append(float(value))
    names = [name for name in selector_names if name != "implementation_aware_exhaustive"]
    fig, axis = plt.subplots(figsize=(8, 4))
    axis.boxplot([regret[name] for name in names], tick_labels=[name.replace("_", " ") for name in names], showfliers=False)
    axis.tick_params(axis="x", rotation=20); axis.set_ylabel("Normalized regret"); axis.grid(axis="y", alpha=.25)
    save(fig, figure_dir / specs[7][1])

    # F09
    sensitivity: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in dse:
        if row["selector"] == "implementation_aware_exhaustive":
            sensitivity[(row["fault_model"], row["interleaving_factor"])][row["selected_implementation_id"]] += 1
    labels = sorted(sensitivity)
    fig, axis = plt.subplots(figsize=(10, 5))
    bottom = [0] * len(labels)
    for impl in candidates:
        values = [sensitivity[label][impl] for label in labels]
        axis.bar(range(len(labels)), values, bottom=bottom, color=colors[impl], label=SHORT[impl])
        bottom = [a + b for a, b in zip(bottom, values)]
    axis.set_xticks(range(len(labels)), [f"{fault}\nI={interleave}" for fault, interleave in labels], rotation=30, ha="right"); axis.set_ylabel("Exhaustive selection count"); axis.legend(fontsize=8)
    save(fig, figure_dir / specs[8][1])

    # F10
    provenance = Counter()
    for filename in ("PPA_RESULTS.csv", "POWER_RESULTS.csv", "RELIABILITY_RESULTS.csv", "DSE_RESULTS.csv", "CLAIMS_LEDGER.csv"):
        for row in rows(root / filename): provenance[row["evidence_class"]] += 1
    fig, axis = plt.subplots(figsize=(7, 4))
    axis.bar(list(provenance), list(provenance.values()), color="#4c78a8"); axis.set_ylabel("Machine-readable rows"); axis.tick_params(axis="x", rotation=25); axis.set_yscale("log")
    save(fig, figure_dir / specs[9][1])

    for figure_id, filename, description, unit, sources, uncertainty in specs:
        path = figure_dir / filename
        manifest.append({"figure_id": figure_id, "file": f"figures/{filename}", "status": "GENERATED_FROM_VALIDATED_MACHINE_READABLE_DATA", "sha256": sha256(path), "raw_data_references": sources, "units": unit, "uncertainty_or_seed_variation": uncertainty, "caption_ready_description": description})
    with (root / "FIGURE_DATA_MANIFEST.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(manifest)
    print(f"GATE04_FIGURES_PASS count={len(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
