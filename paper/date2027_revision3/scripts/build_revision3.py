#!/usr/bin/env python3
"""Build Revision-3 claims, tables, and vector figures from qualified evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[3] / "tmp/date2027_revision3_matplotlib"),
)

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


# Okabe-Ito-derived, colorblind-conscious palette. Color is redundant with
# marker shape, hatching, labels, and sign so monochrome readability remains.
TEMPORAL_BLUE = "#0072B2"
STRUCTURAL_VERMILLION = "#D55E00"
POWER_COLORS = ["#E69F00", "#0072B2", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
REV2 = REPO / "docs/date2027/revision2"
BREADTH = REPO / "campaigns/date_2027_breadth_remediation"

SOURCES = {
    "rev2": REV2 / "results/REV2_MANUSCRIPT_EVIDENCE.json",
    "rev2_paired": REV2 / "results/REV2_SECDED_PAIRED_SEED_EFFECTS.json",
    "environment": REV2 / "REV2_MULTI_SEED_ENVIRONMENT.json",
    "structural": BREADTH / "analysis/A_structural_pair_summary.json",
    "power": BREADTH / "analysis/B_power_components_summary.json",
    "condition": BREADTH / "analysis/C_5ns_summary.json",
    "formal": BREADTH / "formal/results/A_formal_qualification.json",
    "synthesis": BREADTH / "synthesis/A_synthesis_structural_comparison.json",
    "contract": BREADTH / "physical/contract_v1.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def tex_percent(value: float, digits: int = 1, plus: bool = True) -> str:
    prefix = "+" if plus and value > 0 else ""
    return f"{prefix}{value:.{digits}f}\\%"


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rev2_effect(rev2: dict, key: str) -> dict:
    return rev2["secded_paired"]["effects"][key]["summary"]


def paired_effect(payload: dict, key: str) -> dict:
    return payload[key]["percent_effect"]


def metric(rev2: dict, architecture: str, key: str) -> dict:
    return rev2["architectures"][architecture]["metrics"][key]


def methodology_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.15, 1.38))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    boxes = [
        (0.01, "CODE\nSEMANTICS", "mapping + guarantee"),
        (0.26, "HARDWARE\nIDENTITY", "RTL + latency + II + structure"),
        (0.52, "PHYSICAL\nIDENTITY", "constraint + tool + seed + route"),
        (0.78, "ADMITTED\nEVIDENCE", "feasible PPA + activity power"),
    ]
    for x, title, subtitle in boxes:
        box = FancyBboxPatch(
            (x, 0.39), 0.20, 0.42,
            boxstyle="round,pad=0.012,rounding_size=0.012",
            edgecolor="black", facecolor="white", linewidth=0.9,
        )
        ax.add_patch(box)
        ax.text(x + 0.10, 0.66, title, ha="center", va="center", fontsize=8.1, weight="bold")
        ax.text(x + 0.10, 0.47, subtitle, ha="center", va="center", fontsize=6.6)
    for x in (0.215, 0.465, 0.725):
        ax.annotate("", xy=(x + 0.035, 0.60), xytext=(x, 0.60), arrowprops=dict(arrowstyle="->", lw=0.9))
    ax.text(0.235, 0.83, "formal qualification", ha="center", fontsize=6.4)
    ax.text(0.495, 0.83, "identity freeze", ha="center", fontsize=6.4)
    ax.text(0.755, 0.83, "eligibility gate", ha="center", fontsize=6.4)
    ax.text(
        0.5, 0.14,
        "Perturbations: temporal SECDED (comb. ↔ pipe)   |   structural Hsiao (flat ↔ hierarchical)   |   constraint (10 ns ↔ 5 ns)   |   guarantee (SECDED/Hsiao ↔ BCH t=2)",
        ha="center", va="center", fontsize=7.0,
    )
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def exact_effects_figure(path: Path, rev2: dict, structural: dict) -> list[dict]:
    labels = ["Area", "Wire", "Timing", "Energy"]
    temporal_keys = [
        "area_percent", "detailed_wirelength_percent",
        "slack_derived_frequency_percent", "achievable_energy_percent",
    ]
    structural_keys = [
        "standard_cell_instance_area_um2", "detailed_route_wirelength_um",
        "slack_derived_frequency_mhz", "energy_per_op_pj",
    ]
    studies = [
        ("Temporal SECDED", [rev2_effect(rev2, key) for key in temporal_keys], "o", TEMPORAL_BLUE),
        ("Structural Hsiao", [paired_effect(structural["paired_effects"], key) for key in structural_keys], "s", STRUCTURAL_VERMILLION),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.35), sharey=True)
    rows: list[dict] = []
    offsets = [-0.12, -0.06, 0.0, 0.06, 0.12]
    for ax, (title, summaries, marker, color) in zip(axes, studies):
        for x, (label, summary) in enumerate(zip(labels, summaries)):
            items = sorted(summary["values_by_seed"].items(), key=lambda item: int(item[0]))
            values = [value for _, value in items]
            ax.scatter([x + off for off in offsets], values, s=14, marker=marker, facecolor="none", edgecolor=color, linewidth=0.75, zorder=2)
            mean = summary["mean"]
            ax.errorbar(
                x, mean,
                yerr=[[mean - summary["minimum"]], [summary["maximum"] - mean]],
                fmt="D", ms=4.8, color=color, markerfacecolor=color,
                capsize=2.5, elinewidth=1.0, zorder=3,
            )
            for seed, value in items:
                rows.append({"study": title, "metric": label, "seed": int(seed), "percent": value})
        ax.axhline(0, color="0.25", lw=0.8)
        ax.set_title(title, fontsize=8.2, weight="bold")
        ax.set_xticks(range(4), ["Area\n(cost +)", "Wire\n(cost +)", "Timing\n(benefit +)", "Energy\n(cost +)"])
        ax.tick_params(labelsize=7)
        ax.grid(axis="y", color="0.88", linewidth=0.45)
        ax.set_ylim(-30, 60)
    axes[0].set_ylabel("Paired implementation effect (%)", fontsize=8)
    axes[1].text(0.98, 0.96, "Shared y-axis", transform=axes[1].transAxes, ha="right", va="top", fontsize=6.5)
    fig.tight_layout(pad=0.55, w_pad=0.8)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return rows


def power_condition_figure(path: Path, rev2: dict, power: dict, condition: dict) -> list[dict]:
    power_keys = [
        "internal_power_w", "switching_power_w", "total_power_w",
        "combinational_total_power_w", "sequential_total_power_w", "clock_total_power_w",
    ]
    power_labels = ["Internal", "Switching", "Total", "Comb.\ngroup", "Seq.\ngroup", "Clock\ngroup"]
    pvalues = [paired_effect(power["paired_effects"], key)["mean"] for key in power_keys]

    temporal = [
        rev2_effect(rev2, "area_percent"),
        rev2_effect(rev2, "slack_derived_frequency_percent"),
        rev2_effect(rev2, "achievable_energy_percent"),
    ]
    five = [
        paired_effect(condition["within_5ns_paired_effects"], "standard_cell_instance_area_um2"),
        paired_effect(condition["within_5ns_paired_effects"], "slack_derived_frequency_mhz"),
        paired_effect(condition["within_5ns_paired_effects"], "energy_per_op_pj"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.35), gridspec_kw={"width_ratios": [1.35, 1.0]})
    ax = axes[0]
    bars = ax.bar(
        range(len(pvalues)), pvalues, color=POWER_COLORS,
        edgecolor="0.20", linewidth=0.45, width=0.68,
    )
    for bar in bars:
        bar.set_hatch("//" if bar.get_height() > 0 else "")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(power_labels)), power_labels)
    ax.set_ylabel("Pipe vs. comb. effect (%)", fontsize=8)
    ax.set_title("(a) 10 ns power decomposition", fontsize=8.2, weight="bold")
    ax.tick_params(labelsize=6.8)
    ax.grid(axis="y", color="0.88", linewidth=0.45)

    ax = axes[1]
    for x, (s10, s5) in enumerate(zip(temporal, five)):
        for summary, marker, color, offset, label in (
            (s10, "o", TEMPORAL_BLUE, -0.07, "10 ns"),
            (s5, "s", STRUCTURAL_VERMILLION, 0.07, "5 ns"),
        ):
            mean = summary["mean"]
            ax.errorbar(
                x + offset, mean,
                yerr=[[mean - summary["minimum"]], [summary["maximum"] - mean]],
                fmt=marker, ms=4.6, color=color, capsize=2.3, elinewidth=0.9,
                label=label if x == 0 else None,
            )
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(3), ["Area\n(cost +)", "Timing\n(benefit +)", "Energy\n(cost +)"])
    ax.set_title("(b) Constraint-conditioned SECDED effect", fontsize=8.2, weight="bold")
    ax.tick_params(labelsize=6.8)
    ax.grid(axis="y", color="0.88", linewidth=0.45)
    ax.legend(fontsize=6.7, frameon=False, loc="upper left")
    fig.tight_layout(pad=0.55, w_pad=0.9)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    rows = [{"panel": "power", "metric": label, "mean_percent": value} for label, value in zip(power_labels, pvalues)]
    rows += [
        {"panel": target, "metric": label, "mean_percent": summary["mean"]}
        for target, summaries in (("10 ns", temporal), ("5 ns", five))
        for label, summary in zip(("Area", "Timing", "Energy"), summaries)
    ]
    return rows


def main() -> int:
    payload = {name: load(path) for name, path in SOURCES.items()}
    rev2 = payload["rev2"]
    structural = payload["structural"]
    power = payload["power"]
    condition = payload["condition"]
    synthesis = payload["synthesis"]
    formal = payload["formal"]
    env = payload["environment"]
    contract = payload["contract"]

    for directory in (HERE / "data", HERE / "tables", HERE / "figures"):
        directory.mkdir(parents=True, exist_ok=True)

    sec_area = rev2_effect(rev2, "area_percent")
    sec_wire = rev2_effect(rev2, "detailed_wirelength_percent")
    sec_freq = rev2_effect(rev2, "slack_derived_frequency_percent")
    sec_energy = rev2_effect(rev2, "achievable_energy_percent")
    hs_area = paired_effect(structural["paired_effects"], "standard_cell_instance_area_um2")
    hs_cells = paired_effect(structural["paired_effects"], "cell_count")
    hs_wire = paired_effect(structural["paired_effects"], "detailed_route_wirelength_um")
    hs_vias = paired_effect(structural["paired_effects"], "via_count")
    hs_freq = paired_effect(structural["paired_effects"], "slack_derived_frequency_mhz")
    hs_energy = paired_effect(structural["paired_effects"], "energy_per_op_pj")
    five_area = paired_effect(condition["within_5ns_paired_effects"], "standard_cell_instance_area_um2")
    five_cells = paired_effect(condition["within_5ns_paired_effects"], "cell_count")
    five_wire = paired_effect(condition["within_5ns_paired_effects"], "detailed_route_wirelength_um")
    five_vias = paired_effect(condition["within_5ns_paired_effects"], "via_count")
    five_freq = paired_effect(condition["within_5ns_paired_effects"], "slack_derived_frequency_mhz")
    five_energy = paired_effect(condition["within_5ns_paired_effects"], "energy_per_op_pj")

    macros = {
        "SeedCount": str(len(env["experimental_factor"]["values"])),
        "SeedList": ",".join(str(value) for value in env["experimental_factor"]["values"]),
        "SecAreaMean": fmt(sec_area["mean"]),
        "SecAreaMin": fmt(sec_area["minimum"]),
        "SecAreaMax": fmt(sec_area["maximum"]),
        "SecAreaStd": fmt(sec_area["sample_standard_deviation"]),
        "SecWireMean": fmt(sec_wire["mean"]),
        "SecWireMin": fmt(sec_wire["minimum"]),
        "SecWireMax": fmt(sec_wire["maximum"]),
        "SecWireStd": fmt(sec_wire["sample_standard_deviation"]),
        "SecFreqMean": fmt(sec_freq["mean"]),
        "SecFreqMin": fmt(sec_freq["minimum"]),
        "SecFreqMax": fmt(sec_freq["maximum"]),
        "SecFreqStd": fmt(sec_freq["sample_standard_deviation"]),
        "SecEnergyMean": fmt(sec_energy["mean"]),
        "SecEnergyMin": fmt(sec_energy["minimum"]),
        "SecEnergyMax": fmt(sec_energy["maximum"]),
        "SecEnergyStd": fmt(sec_energy["sample_standard_deviation"]),
        "HsAreaMean": fmt(hs_area["mean"], 3),
        "HsAreaMin": fmt(hs_area["minimum"], 3),
        "HsAreaMax": fmt(hs_area["maximum"], 3),
        "HsCellsMean": fmt(hs_cells["mean"], 3),
        "HsWireMean": fmt(hs_wire["mean"], 3),
        "HsWireMin": fmt(hs_wire["minimum"], 3),
        "HsWireMax": fmt(hs_wire["maximum"], 3),
        "HsViasMean": fmt(hs_vias["mean"], 3),
        "HsFreqMean": fmt(hs_freq["mean"], 3),
        "HsFreqMin": fmt(hs_freq["minimum"], 3),
        "HsFreqMax": fmt(hs_freq["maximum"], 3),
        "HsEnergyMean": fmt(hs_energy["mean"], 3),
        "HsEnergyMin": fmt(hs_energy["minimum"], 3),
        "HsEnergyMax": fmt(hs_energy["maximum"], 3),
        "FiveAreaMean": fmt(five_area["mean"], 1),
        "FiveAreaMin": fmt(five_area["minimum"], 1),
        "FiveAreaMax": fmt(five_area["maximum"], 1),
        "FiveCellsMean": fmt(five_cells["mean"], 1),
        "FiveWireMean": fmt(five_wire["mean"], 1),
        "FiveViasMean": fmt(five_vias["mean"], 1),
        "FiveFreqMean": fmt(five_freq["mean"], 1),
        "FiveFreqMin": fmt(five_freq["minimum"], 1),
        "FiveFreqMax": fmt(five_freq["maximum"], 1),
        "FiveEnergyMean": fmt(five_energy["mean"], 1),
        "FiveEnergyMin": fmt(five_energy["minimum"], 1),
        "FiveEnergyMax": fmt(five_energy["maximum"], 1),
        "CombAreaAbs": fmt(metric(rev2, "secded_comb", "standard_cell_instance_area_um2")["mean"], 0),
        "PipeAreaAbs": fmt(metric(rev2, "secded_pipe", "standard_cell_instance_area_um2")["mean"], 0),
        "CombWireAbs": fmt(metric(rev2, "secded_comb", "detailed_route_wirelength_um")["mean"], 0),
        "PipeWireAbs": fmt(metric(rev2, "secded_pipe", "detailed_route_wirelength_um")["mean"], 0),
        "CombFreqAbs": fmt(metric(rev2, "secded_comb", "slack_derived_frequency_mhz")["mean"], 1),
        "PipeFreqAbs": fmt(metric(rev2, "secded_pipe", "slack_derived_frequency_mhz")["mean"], 1),
        "CombEnergyAbs": fmt(metric(rev2, "secded_comb", "achievable_no_error_energy_pj_per_operation")["mean"], 2),
        "PipeEnergyAbs": fmt(metric(rev2, "secded_pipe", "achievable_no_error_energy_pj_per_operation")["mean"], 2),
        "CombInternalMw": fmt(power["architecture_summary"]["secded_comb"]["internal_power_w"]["mean"] * 1000, 4),
        "PipeInternalMw": fmt(power["architecture_summary"]["secded_pipe"]["internal_power_w"]["mean"] * 1000, 4),
        "CombSwitchingMw": fmt(power["architecture_summary"]["secded_comb"]["switching_power_w"]["mean"] * 1000, 4),
        "PipeSwitchingMw": fmt(power["architecture_summary"]["secded_pipe"]["switching_power_w"]["mean"] * 1000, 4),
        "CombLeakageNw": fmt(power["architecture_summary"]["secded_comb"]["leakage_power_w"]["mean"] * 1e9, 4),
        "PipeLeakageNw": fmt(power["architecture_summary"]["secded_pipe"]["leakage_power_w"]["mean"] * 1e9, 4),
        "CombTotalMw": fmt(power["architecture_summary"]["secded_comb"]["total_power_w"]["mean"] * 1000, 4),
        "PipeTotalMw": fmt(power["architecture_summary"]["secded_pipe"]["total_power_w"]["mean"] * 1000, 4),
        "PowerInternalEffect": fmt(paired_effect(power["paired_effects"], "internal_power_w")["mean"], 2),
        "PowerSwitchingEffect": fmt(paired_effect(power["paired_effects"], "switching_power_w")["mean"], 2),
        "PowerLeakageEffect": fmt(paired_effect(power["paired_effects"], "leakage_power_w")["mean"], 2),
        "PowerCombGroupEffect": fmt(paired_effect(power["paired_effects"], "combinational_total_power_w")["mean"], 2),
        "PowerSeqGroupEffect": fmt(paired_effect(power["paired_effects"], "sequential_total_power_w")["mean"], 2),
        "PowerClockGroupEffect": fmt(paired_effect(power["paired_effects"], "clock_total_power_w")["mean"], 2),
        "CombConditionEnergy": fmt(condition["condition_sensitivity_percent"]["C_secded_comb"]["energy_per_op_pj"]["mean"], 2),
        "PipeConditionEnergy": fmt(condition["condition_sensitivity_percent"]["C_secded_pipe"]["energy_per_op_pj"]["mean"], 2),
        "CombConditionPower": fmt(condition["condition_sensitivity_percent"]["C_secded_comb"]["total_power_w"]["mean"], 1),
        "PipeConditionPower": fmt(condition["condition_sensitivity_percent"]["C_secded_pipe"]["total_power_w"]["mean"], 1),
        "HsiaoAreaAbs": fmt(metric(rev2, "hsiao_algorithmic", "standard_cell_instance_area_um2")["mean"], 0),
        "HsiaoFreqAbs": fmt(metric(rev2, "hsiao_algorithmic", "slack_derived_frequency_mhz")["mean"], 1),
        "HsiaoWireAbs": fmt(metric(rev2, "hsiao_algorithmic", "detailed_route_wirelength_um")["mean"], 0),
        "HsiaoEnergyAbs": fmt(metric(rev2, "hsiao_algorithmic", "achievable_no_error_energy_pj_per_operation")["mean"], 2),
        "BchArea": fmt(metric(rev2, "bch78", "standard_cell_instance_area_um2")["mean"], 0),
        "BchFreq": fmt(metric(rev2, "bch78", "slack_derived_frequency_mhz")["mean"], 1),
        "BchWire": fmt(metric(rev2, "bch78", "detailed_route_wirelength_um")["mean"], 0),
        "BchSlack": fmt(metric(rev2, "bch78", "signed_worst_setup_slack_ns")["mean"], 2),
        "BchSetupViolations": fmt(metric(rev2, "bch78", "setup_violation_count")["mean"], 0),
        "BchFeasible": rev2["bch_10ns_feasibility"],
        "MappedFlatCells": str(synthesis["baseline"]["mapped_cell_count"]),
        "MappedHierCells": str(synthesis["new_hierarchical"]["mapped_cell_count"]),
        "MappedFlatRegs": str(synthesis["baseline"]["register_count"]),
        "MappedHierRegs": str(synthesis["new_hierarchical"]["register_count"]),
        "MappedFlatXor": str(synthesis["baseline"]["xor_xnor_count"]),
        "MappedHierXor": str(synthesis["new_hierarchical"]["xor_xnor_count"]),
    }
    (HERE / "data/generated_claims.tex").write_text(
        "\n".join(f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in sorted(macros.items())) + "\n",
        encoding="utf-8", newline="\n",
    )

    identity_table = [
        r"\begin{table*}[t]",
        r"\caption{Qualified identity and experiment matrix. W1/W2 denote error weight.}",
        r"\label{tab:matrix}",
        r"\centering\scriptsize\setlength{\tabcolsep}{3.4pt}",
        r"\begin{tabular}{@{}lccccccl@{}}",
        r"\toprule",
        r"Hardware identity & Bits & Guarantee & Lat. & II & Qualification & Campaign & Feasible \\",
        r"\midrule",
        r"SECDED combinational & 72 & W1 corr.; W2 detect & 1 & 1 & exact temporal pair & 10/5 ns, 5 seeds & 5/5; 5/5 \\",
        r"SECDED pipelined & 72 & W1 corr.; W2 detect & 3 & 1 & exact temporal pair & 10/5 ns, 5 seeds & 5/5; 5/5 \\",
        r"Hsiao flat & 72 & W1 corr.; W2 detect & 1 & 1 & arbitrary-word SAT & 10 ns, 5 seeds & 5/5 \\",
        r"Hsiao hierarchical & 72 & W1 corr.; W2 detect & 1 & 1 & SAT + temporal induction & 10 ns, 5 seeds & 5/5 \\",
        rf"BCH $(78,64,t=2)$ & 78 & W1/W2 correct & 1 & 1 & qualified guarantee & 10 ns, 5 seeds & {rev2['bch_10ns_feasibility']} \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (HERE / "tables/identity_matrix.tex").write_text("\n".join(identity_table) + "\n", encoding="utf-8", newline="\n")

    headline_table = [
        r"\begin{table*}[t]",
        r"\caption{Headline post-route results. Paired effects are changed relative to baseline; values are means over five matched deterministic seeds.}",
        r"\label{tab:headline}",
        r"\centering\scriptsize\setlength{\tabcolsep}{3.1pt}",
        r"\begin{tabular}{@{}lccclp{5.0cm}@{}}",
        r"\toprule",
        r"Study & Area & Timing metric & Energy/op & Ordering & Interpretation \\",
        r"\midrule",
        f"Temporal SECDED @ 10 ns & {tex_percent(sec_area['mean'])} & {tex_percent(sec_freq['mean'])} & {tex_percent(sec_energy['mean'])} & area/timing/energy 5/5 & Large non-dominated area--latency--timing--energy displacement." + r" \\",
        f"Structural Hsiao @ 10 ns & {tex_percent(hs_area['mean'], 3)} & {tex_percent(hs_freq['mean'], 3)} & {tex_percent(hs_energy['mean'], 3)} & area/energy 5/5; timing 4/5 & Modest mixed displacement; neither structure is generally superior." + r" \\",
        f"Temporal SECDED @ 5 ns & {tex_percent(five_area['mean'])} & {tex_percent(five_freq['mean'])} & {tex_percent(five_energy['mean'])} & all three 5/5 & Ordering survives; magnitudes remain constraint-conditioned." + r" \\",
        rf"BCH @ 10 ns & {macros['BchArea']} $\mu$m$^2$ & {macros['BchFreq']} MHz & -- & setup feasible 0/5 & Stronger guarantee; this syndrome/Chien RTL misses the common target. \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (HERE / "tables/headline_results.tex").write_text("\n".join(headline_table) + "\n", encoding="utf-8", newline="\n")

    methodology_figure(HERE / "figures/figure01_identity_framework.pdf")
    exact_rows = exact_effects_figure(HERE / "figures/figure02_equivalent_effects.pdf", rev2, structural)
    write_csv(HERE / "data/figure02_equivalent_effects.csv", exact_rows, ["study", "metric", "seed", "percent"])
    power_rows = power_condition_figure(HERE / "figures/figure03_power_condition.pdf", rev2, power, condition)
    write_csv(HERE / "data/figure03_power_condition.csv", power_rows, ["panel", "metric", "mean_percent"])

    registry = {
        "schema_version": 1,
        "starting_commit": contract["baseline_commit"],
        "sources": {
            name: {"path": str(path.relative_to(REPO)).replace("\\", "/"), "sha256": sha256(path)}
            for name, path in SOURCES.items()
        },
        "macros": macros,
        "formal_status": formal["formal_status"],
        "logic_depth_assessment": "NOT ASSESSABLE" if synthesis["baseline"]["logic_depth_no_flip_flops"] is None else "ASSESSABLE",
        "policy": "All experimental values in the manuscript and figures derive from the listed qualified machine-readable sources.",
    }
    (HERE / "data/claim_registry.json").write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("REVISION3_ARTIFACTS_BUILT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
