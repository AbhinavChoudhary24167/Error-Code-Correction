#!/usr/bin/env python3
"""Generate every Revision-2 manuscript result, table, and figure from evidence."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
EVIDENCE_PATH = REPO / "docs/date2027/revision2/results/REV2_MANUSCRIPT_EVIDENCE.json"
ENVIRONMENT_PATH = REPO / "docs/date2027/revision2/REV2_MULTI_SEED_ENVIRONMENT.json"
CONTRACT_PATH = REPO / "scripts/revision2/contract_v1.json"


def fmt(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def rng(summary: dict, digits: int = 1) -> str:
    return f"{fmt(summary['minimum'], digits)}--{fmt(summary['maximum'], digits)}"


def metric(architectures: dict, architecture: str, name: str) -> dict:
    return architectures[architecture]["metrics"][name]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def methodology_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.1, 1.55))
    ax.set_xlim(0, 10.1)
    ax.set_ylim(0, 1.55)
    ax.axis("off")
    boxes = [
        (0.10, "ECC RTL\nidentity"),
        (1.75, "correctness / exact-\nequivalence qualification"),
        (3.75, "guarantee\nsemantics"),
        (5.25, "common pinned\nphysical policy"),
        (6.95, "matched-seed\nimplementation sweep"),
        (8.65, "post-route PPA / energy\nand trade-off analysis"),
    ]
    widths = [1.25, 1.65, 1.15, 1.35, 1.35, 1.35]
    for (x, label), width in zip(boxes, widths):
        patch = FancyBboxPatch(
            (x, 0.76), width, 0.52, boxstyle="round,pad=0.03",
            facecolor="#e8f0f7", edgecolor="#245274", linewidth=1.0,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, 1.02, label, ha="center", va="center", fontsize=7.2)
    for index in range(len(boxes) - 1):
        x1 = boxes[index][0] + widths[index]
        x2 = boxes[index + 1][0]
        ax.add_patch(FancyArrowPatch((x1 + 0.03, 1.02), (x2 - 0.03, 1.02), arrowstyle="->", mutation_scale=8, color="#245274"))
    side = FancyBboxPatch((2.18, 0.08), 1.65, 0.36, boxstyle="round,pad=0.03", facecolor="#f8ece8", edgecolor="#91452e", linewidth=0.9)
    ax.add_patch(side)
    ax.text(3.00, 0.26, "insufficient evidence\nexplicitly unavailable", ha="center", va="center", fontsize=7.0)
    ax.add_patch(FancyArrowPatch((2.58, 0.76), (2.85, 0.45), arrowstyle="->", mutation_scale=8, color="#91452e"))
    ax.text(6.45, 0.35, "Code identity  ≠  hardware architecture identity  ≠  physical outcome", ha="center", va="center", fontsize=8.4, fontweight="bold", color="#1d3446")
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def seed_area_frequency_figure(path: Path, architectures: dict) -> None:
    colors = {"secded_comb": "#2b6f9c", "secded_pipe": "#d17b28", "hsiao_algorithmic": "#338a66", "bch78": "#9c4f64"}
    labels = {"secded_comb": "SECDED comb.", "secded_pipe": "SECDED pipe.", "hsiao_algorithmic": "Hsiao algorithmic", "bch78": "BCH (78,64,t=2)"}
    fig, ax = plt.subplots(figsize=(4.1, 2.85))
    for architecture in labels:
        area = metric(architectures, architecture, "standard_cell_instance_area_um2")
        freq = metric(architectures, architecture, "slack_derived_frequency_mhz")
        seeds = sorted(int(seed) for seed in area["values_by_seed"])
        xs = [area["values_by_seed"][str(seed)] / 1000.0 for seed in seeds]
        ys = [freq["values_by_seed"][str(seed)] for seed in seeds]
        ax.scatter(xs, ys, s=15, alpha=0.36, color=colors[architecture], linewidths=0)
        xmean, ymean = area["mean"] / 1000.0, freq["mean"]
        xerr = [[xmean - area["minimum"] / 1000.0], [area["maximum"] / 1000.0 - xmean]]
        yerr = [[ymean - freq["minimum"]], [freq["maximum"] - ymean]]
        ax.errorbar(xmean, ymean, xerr=xerr, yerr=yerr, fmt="o", ms=6.5, capsize=2.5, elinewidth=1.1,
                    color=colors[architecture], markeredgecolor="white", markeredgewidth=0.6, label=labels[architecture])
    ax.axhline(100.0, color="#555555", linestyle="--", linewidth=0.8)
    ax.text(0.985, 0.19, "100 MHz target", ha="right", va="bottom", transform=ax.transAxes, fontsize=7.0, color="#555555")
    ax.set_xlabel(r"Final standard-cell area ($10^3\,\mu$m$^2$)", fontsize=8)
    ax.set_ylabel("Slack-derived frequency (MHz)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, color="#d9d9d9", linewidth=0.45, alpha=0.8)
    ax.legend(loc="best", fontsize=6.7, frameon=True, ncol=1)
    fig.tight_layout(pad=0.35)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def paired_effect_figure(path: Path, paired: dict) -> None:
    keys = ["area_percent", "detailed_wirelength_percent", "slack_derived_frequency_percent", "achievable_energy_percent"]
    labels = ["Area\n(cost +)", "Wirelength\n(cost +)", "Frequency\n(benefit +)", "Energy\n(benefit −)"]
    colors = ["#b35b2e", "#b35b2e", "#2f7f63", "#2f7f63"]
    fig, ax = plt.subplots(figsize=(4.1, 2.6))
    for x, (key, color) in enumerate(zip(keys, colors)):
        summary = paired["effects"][key]["summary"]
        values = [summary["values_by_seed"][seed] for seed in sorted(summary["values_by_seed"], key=int)]
        offsets = [-0.10, -0.05, 0, 0.05, 0.10]
        ax.scatter([x + offset for offset in offsets], values, s=16, color=color, alpha=0.45, linewidths=0, zorder=2)
        mean = summary["mean"]
        ax.errorbar(x, mean, yerr=[[mean - summary["minimum"]], [summary["maximum"] - mean]], fmt="D", ms=5.4,
                    color=color, markeredgecolor="white", markeredgewidth=0.5, capsize=3.0, elinewidth=1.2, zorder=3)
    ax.axhline(0.0, color="#4f4f4f", linewidth=0.8)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylabel(r"Paired change, pipe vs. comb. (\%)", fontsize=8)
    ax.tick_params(axis="both", labelsize=7)
    ax.grid(True, axis="y", color="#d9d9d9", linewidth=0.45)
    fig.tight_layout(pad=0.35)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def main() -> int:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    environment = json.loads(ENVIRONMENT_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    architectures = evidence["architectures"]
    paired = evidence["secded_paired"]
    data = HERE / "data"
    tables = HERE / "tables"
    figures = HERE / "figures"
    for directory in (data, tables, figures):
        directory.mkdir(parents=True, exist_ok=True)

    macros: dict[str, str] = {}
    effect_macro = {
        "area_percent": "SecAreaEffect",
        "detailed_wirelength_percent": "SecWireEffect",
        "slack_derived_frequency_percent": "SecFreqEffect",
        "achievable_energy_percent": "SecEnergyEffect",
    }
    for key, macro in effect_macro.items():
        summary = paired["effects"][key]["summary"]
        macros[f"{macro}Mean"] = fmt(summary["mean"], 1)
        macros[f"{macro}Min"] = fmt(summary["minimum"], 1)
        macros[f"{macro}Max"] = fmt(summary["maximum"], 1)
        macros[f"{macro}Median"] = fmt(summary["median"], 1)
        macros[f"{macro}Range"] = fmt(summary["range"], 1)
        macros[f"{macro}Std"] = fmt(summary["sample_standard_deviation"], 2)
    robustness = paired["robustness"]
    for key, macro in (
        ("area_pipe_greater_count", "AreaOrderingCount"),
        ("frequency_pipe_greater_count", "FreqOrderingCount"),
        ("wirelength_pipe_greater_count", "WireOrderingCount"),
        ("energy_pipe_lower_count", "EnergyOrderingCount"),
    ):
        macros[macro] = str(robustness[key])
    macros["BchFeasible"] = evidence["bch_10ns_feasibility"]
    macros["HsiaoFeasible"] = evidence["hsiao_10ns_feasibility"]
    macros["ValidRoutes"] = str(evidence["valid_route_count"])
    macros["SeedCount"] = str(len(environment["experimental_factor"]["values"]))
    macros["SeedList"] = ",".join(str(seed) for seed in environment["experimental_factor"]["values"])
    macros["ClockPeriodNs"] = fmt(environment["flow"]["clock_period_ns"], 0)
    macros["VoltageV"] = fmt(environment["technology"]["voltage_v"], 2)
    macros["TemperatureC"] = fmt(environment["technology"]["temperature_c"], 0)
    macros["IODelayPercent"] = fmt(environment["flow"]["input_delay_fraction"] * 100.0, 0)
    macros["OutputLoadPf"] = fmt(environment["flow"]["output_load_pf"], 2)
    macros["CoreUtilPercent"] = fmt(environment["flow"]["core_utilization_percent"], 0)
    macros["PlaceDensity"] = fmt(environment["flow"]["place_density"], 2)
    macros["WorkerCount"] = str(environment["flow"]["num_cores"])
    macros["PowerOperations"] = str(environment["power"]["payload_operations"])
    macros["MemoryMaxBits"] = str(environment["flow"]["synthesis_memory_max_bits"])
    macros["SecAggregateDominance"] = paired["dominance"]["aggregate_mean"]["relation"].lower().replace("_", "-")
    macros["SecRangeDominance"] = paired["dominance"]["sensitivity_range"]["relation"].lower().replace("_", "-")
    macros["SecNonDominatedSeedCount"] = str(sum(
        row["relation"] == "NON_DOMINATED" for row in paired["dominance"]["per_seed"]
    ))
    architecture_prefix = {
        "secded_comb": "Comb", "secded_pipe": "Pipe", "hsiao_algorithmic": "Hsiao", "bch78": "Bch"
    }
    metric_suffix = {
        "standard_cell_instance_area_um2": ("Area", 0),
        "cell_count": ("Cells", 0),
        "setup_violation_count": ("SetupViolations", 0),
        "signed_worst_setup_slack_ns": ("Slack", 2),
        "slack_derived_frequency_mhz": ("Freq", 1),
        "detailed_route_wirelength_um": ("Wire", 0),
        "total_power_w": ("PowerW", 6),
        "achievable_no_error_energy_pj_per_operation": ("Energy", 2),
    }
    for architecture, prefix in architecture_prefix.items():
        for metric_name, (suffix, digits) in metric_suffix.items():
            summary = metric(architectures, architecture, metric_name)
            if summary["count"]:
                macros[f"{prefix}{suffix}Mean"] = fmt(summary["mean"], digits)
                macros[f"{prefix}{suffix}Min"] = fmt(summary["minimum"], digits)
                macros[f"{prefix}{suffix}Max"] = fmt(summary["maximum"], digits)
            else:
                macros[f"{prefix}{suffix}Mean"] = "--"
                macros[f"{prefix}{suffix}Min"] = "--"
                macros[f"{prefix}{suffix}Max"] = "--"
    for comparison, architecture in (("HsiaoVsComb", "hsiao_algorithmic"), ("BchVsComb", "bch78")):
        for metric_name, suffix in (
            ("standard_cell_instance_area_um2", "Area"),
            ("cell_count", "Cells"),
            ("slack_derived_frequency_mhz", "Freq"),
            ("detailed_route_wirelength_um", "Wire"),
            ("achievable_no_error_energy_pj_per_operation", "Energy"),
        ):
            candidate = metric(architectures, architecture, metric_name)
            reference = metric(architectures, "secded_comb", metric_name)
            if candidate["count"] and reference["count"]:
                macros[comparison + suffix] = fmt((candidate["mean"] - reference["mean"]) / reference["mean"] * 100.0, 1)
            else:
                macros[comparison + suffix] = "--"

    latex = [f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in sorted(macros.items())]
    (data / "generated_claims.tex").write_text("\n".join(latex) + "\n", encoding="utf-8", newline="\n")

    claims = {
        "schema_version": 1,
        "sources": [
            str(EVIDENCE_PATH.relative_to(REPO)).replace("\\", "/"),
            str(ENVIRONMENT_PATH.relative_to(REPO)).replace("\\", "/"),
            str(CONTRACT_PATH.relative_to(REPO)).replace("\\", "/"),
        ],
        "macros": macros,
        "policy": "All visible experimental values in the manuscript are emitted from this registry or the generated tables/figures.",
    }
    (data / "claim_registry.json").write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    labels = {
        "secded_comb": "SECDED comb.",
        "secded_pipe": "SECDED pipe.",
        "hsiao_algorithmic": "Hsiao algorithmic",
        "bch78": "BCH $(78,64,t=2)$",
    }
    guarantees = {
        "secded_comb": "W1 correct; W2 detect",
        "secded_pipe": "W1 correct; W2 detect",
        "hsiao_algorithmic": "W1 correct; W2 detect",
        "bch78": "W1/W2 correct",
    }
    latencies = {"secded_comb": 1, "secded_pipe": 3, "hsiao_algorithmic": 1, "bch78": 1}
    widths = {"secded_comb": 72, "secded_pipe": 72, "hsiao_algorithmic": 72, "bch78": 78}
    identity_rows = []
    for architecture in labels:
        summary = architectures[architecture]
        identity_rows.append({
            "architecture": labels[architecture].replace("$", ""), "codeword_bits": widths[architecture],
            "guarantee": guarantees[architecture], "latency_cycles": latencies[architecture], "ii_cycles": 1,
            "correctness": "exact identity" if architecture == "hsiao_algorithmic" else "qualified",
            "physical": f"routed {summary['valid_route_count']}/5; 10 ns {summary['timing_feasible_count']}/5",
        })
    write_csv(data / "table_i_implementation_identities.csv", identity_rows, list(identity_rows[0]))
    table_i = [
        r"\begin{table*}[t]", r"\caption{Qualified implementation identities}", r"\label{tab:identities}", r"\centering", r"\scriptsize",
        r"\setlength{\tabcolsep}{5.0pt}", r"\begin{tabular}{@{}lccccp{7.2cm}@{}}", r"\toprule",
        "Architecture & Bits & Guarantee & Lat. & II & Evidence " + r"\\", r"\midrule",
    ]
    for row in identity_rows:
        table_i.append(f"{row['architecture']} & {row['codeword_bits']} & {row['guarantee']} & {row['latency_cycles']} & 1 & {row['correctness']}; {row['physical']} " + r"\\")
    table_i += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (tables / "generated_table_i.tex").write_text("\n".join(table_i) + "\n", encoding="utf-8", newline="\n")

    result_rows = []
    for architecture in labels:
        area = metric(architectures, architecture, "standard_cell_instance_area_um2")
        freq = metric(architectures, architecture, "slack_derived_frequency_mhz")
        wire = metric(architectures, architecture, "detailed_route_wirelength_um")
        energy = metric(architectures, architecture, "achievable_no_error_energy_pj_per_operation")
        result_rows.append({
            "architecture": labels[architecture].replace("$", ""), "seeds": 5,
            "area_mean_um2": area["mean"], "area_min_um2": area["minimum"], "area_max_um2": area["maximum"],
            "frequency_mean_mhz": freq["mean"], "frequency_min_mhz": freq["minimum"], "frequency_max_mhz": freq["maximum"],
            "wirelength_mean_um": wire["mean"], "wirelength_min_um": wire["minimum"], "wirelength_max_um": wire["maximum"],
            "energy_mean_pj": energy["mean"], "energy_min_pj": energy["minimum"], "energy_max_pj": energy["maximum"],
            "feasibility": f"{architectures[architecture]['timing_feasible_count']}/5",
        })
    write_csv(data / "table_ii_seed_statistics.csv", result_rows, list(result_rows[0]))
    table_ii = [
        r"\begin{table*}[t]", r"\caption{Fresh five-seed post-route sensitivity statistics (mean [min--max])}", r"\label{tab:results}", r"\centering", r"\scriptsize",
        r"\setlength{\tabcolsep}{3.4pt}", r"\begin{tabular}{@{}lccccc@{}}", r"\toprule",
        "Architecture & Area ($\\mu$m$^2$) & Slack-derived freq. (MHz) & Detailed wire ($\\mu$m) & Energy (pJ/op) & 10 ns " + r"\\", r"\midrule",
    ]
    for architecture, row in zip(labels, result_rows):
        energy = metric(architectures, architecture, "achievable_no_error_energy_pj_per_operation")
        energy_text = "--" if energy["count"] == 0 else f"{fmt(energy['mean'], 2)} [{rng(energy, 2)}]"
        table_ii.append(
            f"{row['architecture']} & {fmt(row['area_mean_um2'], 0)} [{fmt(row['area_min_um2'], 0)}--{fmt(row['area_max_um2'], 0)}] & "
            f"{fmt(row['frequency_mean_mhz'], 1)} [{fmt(row['frequency_min_mhz'], 1)}--{fmt(row['frequency_max_mhz'], 1)}] & "
            f"{fmt(row['wirelength_mean_um'], 0)} [{fmt(row['wirelength_min_um'], 0)}--{fmt(row['wirelength_max_um'], 0)}] & "
            f"{energy_text} & {row['feasibility']} " + r"\\")
    table_ii += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (tables / "generated_table_ii.tex").write_text("\n".join(table_ii) + "\n", encoding="utf-8", newline="\n")

    dominance_by_seed = {str(row["seed"]): row["relation"] for row in paired["dominance"]["per_seed"]}
    table_iii = [
        r"\begin{table*}[t]", r"\caption{Exact matched SECDED effects by seed (pipelined relative to combinational, \%)}",
        r"\label{tab:paired-seeds}", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{6.0pt}",
        r"\begin{tabular}{@{}ccccccc@{}}", r"\toprule",
        r"Seed & Area & Cell count & Detailed wire & $f_{\mathrm{slack}}$ & Energy/op & Pareto relation \\", r"\midrule",
    ]
    paired_columns = (
        "area_percent", "cell_count_percent", "detailed_wirelength_percent",
        "slack_derived_frequency_percent", "achievable_energy_percent",
    )
    for seed in environment["experimental_factor"]["values"]:
        seed_key = str(seed)
        values = [paired["effects"][name]["summary"]["values_by_seed"][seed_key] for name in paired_columns]
        relation = dominance_by_seed[seed_key].replace("NON_DOMINATED", "non-dominated")
        table_iii.append(
            f"{seed} & {fmt(values[0], 1)} & {fmt(values[1], 1)} & {fmt(values[2], 1)} & "
            f"{fmt(values[3], 1)} & {fmt(values[4], 1)} & {relation} " + r"\\"
        )
    table_iii += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (tables / "generated_table_iii.tex").write_text("\n".join(table_iii) + "\n", encoding="utf-8", newline="\n")

    paired_rows = []
    for effect, payload in paired["effects"].items():
        for seed, value in payload["summary"]["values_by_seed"].items():
            paired_rows.append({"effect": effect, "seed": int(seed), "percent": value})
    write_csv(data / "figure03_paired_effects.csv", paired_rows, ["effect", "seed", "percent"])

    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "ps.fonttype": 42})
    methodology_figure(figures / "figure01_methodology.pdf")
    seed_area_frequency_figure(figures / "figure02_seed_area_frequency.pdf", architectures)
    paired_effect_figure(figures / "figure03_paired_effects.pdf", paired)
    print("REV2_MANUSCRIPT_ARTIFACTS_BUILT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
