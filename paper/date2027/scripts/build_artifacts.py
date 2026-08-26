#!/usr/bin/env python3
"""Generate DATE 2027 manuscript data, figures, tables, and claim macros.

All numerical content is derived from the frozen Gate 07 evidence package. The
script performs no simulation, synthesis, or physical experiment.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[3]
PAPER = ROOT / "paper" / "date2027"
G7 = ROOT / "docs" / "date2027" / "rigour_gate_07"
DATA = PAPER / "data"
FIGURES = PAPER / "figures"
TABLES = PAPER / "tables"

COLORS = {
    "comb": "#2463A5",
    "pipe": "#D97706",
    "bch": "#2F855A",
    "excluded": "#6B7280",
    "grid": "#D1D5DB",
}


def read_json(name: str):
    return json.loads((G7 / name).read_text(encoding="utf-8"))


def read_csv(name: str):
    with (G7 / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 8.2,
            "axes.labelsize": 8.2,
            "axes.titlesize": 8.5,
            "xtick.labelsize": 7.4,
            "ytick.labelsize": 7.4,
            "legend.fontsize": 7.1,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def generate_claims(ledger: dict) -> dict:
    by_id = {claim["claim_id"]: claim for claim in ledger["claims"]}
    c02 = by_id["C02"]["raw_numbers"]

    def pct(candidate: float, baseline: float) -> float:
        return (candidate - baseline) / baseline * 100.0

    values = {
        "SEC_AREA_PCT": pct(c02["area_um2"][1], c02["area_um2"][0]),
        "SEC_WIRE_PCT": pct(c02["wirelength_um"][1], c02["wirelength_um"][0]),
        "SEC_FMAX_PCT": pct(c02["fmax_mhz"][1], c02["fmax_mhz"][0]),
        "SEC_ENERGY_PCT": pct(c02["energy_pj_per_operation"][1], c02["energy_pj_per_operation"][0]),
        "SEC_COMB_AREA": c02["area_um2"][0],
        "SEC_PIPE_AREA": c02["area_um2"][1],
        "SEC_COMB_WIRE": c02["wirelength_um"][0],
        "SEC_PIPE_WIRE": c02["wirelength_um"][1],
        "SEC_COMB_FMAX": c02["fmax_mhz"][0],
        "SEC_PIPE_FMAX": c02["fmax_mhz"][1],
        "SEC_COMB_ENERGY": c02["energy_pj_per_operation"][0],
        "SEC_PIPE_ENERGY": c02["energy_pj_per_operation"][1],
        "SEC_COMB_POWER_MW": c02["power_w"][0] * 1000.0,
        "SEC_PIPE_POWER_MW": c02["power_w"][1] * 1000.0,
    }
    c04 = by_id["C04"]["raw_numbers"]
    values.update(
        {
            "BCH_WNS": c04["wns_ns"],
            "BCH_DEFICIT": c04["timing_deficit_ns"],
            "BCH_FMAX": c04["fmax_mhz"],
        }
    )

    figure_data = read_json("GATE07_FIGURE_DATA.json")
    routed = figure_data["F03_NORMALIZED_PHYSICAL_COST"]["routed_metrics"]
    bch_id = "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"
    values.update(
        {
            "BCH_AREA_PCT": routed[bch_id]["standard_cell_instance_area_um2"],
            "BCH_WIRE_PCT": routed[bch_id]["detailed_route_wirelength_um"],
            "BCH_FMAX_PCT": routed[bch_id]["achieved_fmax_mhz"],
        }
    )

    formats = {
        "SEC_AREA_PCT": ".3f",
        "SEC_WIRE_PCT": ".3f",
        "SEC_FMAX_PCT": ".3f",
        "SEC_ENERGY_PCT": ".3f",
        "BCH_AREA_PCT": ".3f",
        "BCH_WIRE_PCT": ".3f",
        "BCH_FMAX_PCT": ".3f",
        "BCH_WNS": ".5f",
        "BCH_DEFICIT": ".5f",
        "BCH_FMAX": ".4f",
        "SEC_COMB_AREA": ".1f",
        "SEC_PIPE_AREA": ".1f",
        "SEC_COMB_WIRE": ".0f",
        "SEC_PIPE_WIRE": ".0f",
        "SEC_COMB_FMAX": ".3f",
        "SEC_PIPE_FMAX": ".3f",
        "SEC_COMB_ENERGY": ".3f",
        "SEC_PIPE_ENERGY": ".3f",
        "SEC_COMB_POWER_MW": ".3f",
        "SEC_PIPE_POWER_MW": ".3f",
    }
    macro_names = {
        "SEC_AREA_PCT": "SecAreaPct",
        "SEC_WIRE_PCT": "SecWirePct",
        "SEC_FMAX_PCT": "SecFmaxPct",
        "SEC_ENERGY_PCT": "SecEnergyPctSigned",
        "BCH_AREA_PCT": "BchAreaPct",
        "BCH_WIRE_PCT": "BchWirePct",
        "BCH_FMAX_PCT": "BchFmaxPctSigned",
        "BCH_WNS": "BchWns",
        "BCH_DEFICIT": "BchDeficit",
        "BCH_FMAX": "BchFmax",
        "SEC_COMB_AREA": "SecCombArea",
        "SEC_PIPE_AREA": "SecPipeArea",
        "SEC_COMB_WIRE": "SecCombWire",
        "SEC_PIPE_WIRE": "SecPipeWire",
        "SEC_COMB_FMAX": "SecCombFmax",
        "SEC_PIPE_FMAX": "SecPipeFmax",
        "SEC_COMB_ENERGY": "SecCombEnergy",
        "SEC_PIPE_ENERGY": "SecPipeEnergy",
        "SEC_COMB_POWER_MW": "SecCombPowerMw",
        "SEC_PIPE_POWER_MW": "SecPipePowerMw",
    }
    lines = ["% Generated from frozen Gate 07 evidence. Do not edit."]
    for key, macro in macro_names.items():
        lines.append(f"\\newcommand{{\\{macro}}}{{{format(values[key], formats[key])}}}")
    lines.extend(
        [
            f"\\newcommand{{\\SecEnergyReductionPct}}{{{format(abs(values['SEC_ENERGY_PCT']), '.3f')}}}",
            f"\\newcommand{{\\BchFmaxReductionPct}}{{{format(abs(values['BCH_FMAX_PCT']), '.3f')}}}",
        ]
    )
    (DATA / "generated_claims.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    registry = {
        "schema_version": 1,
        "authoritative_ledger": "docs/date2027/rigour_gate_07/GATE07_CLAIM_LEDGER.json",
        "claims": [
            {
                "semantic_id": key,
                "value": value,
                "format": formats.get(key, ".3f"),
                "macro": macro_names.get(key),
                "display_macro": (
                    "SecEnergyReductionPct" if key == "SEC_ENERGY_PCT" else
                    "BchFmaxReductionPct" if key == "BCH_FMAX_PCT" else
                    macro_names.get(key)
                ),
                "source_claim_id": "C04" if key.startswith("BCH_WNS") or key.startswith("BCH_DEFICIT") or key == "BCH_FMAX" else ("C03/C05" if key.startswith("BCH_") else "C02"),
            }
            for key, value in values.items()
        ],
        "derived_display_macros": {
            "SecEnergyReductionPct": abs(values["SEC_ENERGY_PCT"]),
            "BchFmaxReductionPct": abs(values["BCH_FMAX_PCT"]),
        },
    }
    write_json(DATA / "claim_registry.json", registry)
    return values


def generate_methodology_figure() -> None:
    style()
    fig, ax = plt.subplots(figsize=(7.1, 1.42))
    ax.set_xlim(0, 13.0)
    ax.set_ylim(-1.0, 2.1)
    ax.axis("off")
    labels = [
        "ECC RTL\ncandidates",
        "Correctness and\nidentity qualification",
        "Reliability\nsemantics",
        "Common physical\nimplementation",
        "Post-route PPA\nand energy",
        "Cross-layer\ntrade-off analysis",
    ]
    xs = [0.2, 2.25, 4.55, 6.55, 8.75, 10.85]
    widths = [1.35, 1.75, 1.45, 1.65, 1.55, 1.7]
    for index, (x, width, label) in enumerate(zip(xs, widths, labels)):
        face = "#E8F1FA" if index < 3 else "#EAF5EE"
        box = FancyBboxPatch(
            (x, 0.55), width, 0.88,
            boxstyle="round,pad=0.025,rounding_size=0.05",
            linewidth=0.8, edgecolor="#374151", facecolor=face,
        )
        ax.add_patch(box)
        ax.text(x + width / 2, 0.99, label, ha="center", va="center", fontsize=7.8)
        if index < len(labels) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + width + 0.04, 0.99), (xs[index + 1] - 0.04, 0.99),
                    arrowstyle="-|>", mutation_scale=8, linewidth=0.8, color="#374151",
                )
            )
    ax.add_patch(
        FancyArrowPatch((3.12, 0.53), (3.12, -0.04), arrowstyle="-|>", mutation_scale=8,
                        linewidth=0.75, color=COLORS["excluded"])
    )
    missing = FancyBboxPatch(
        (2.15, -0.72), 1.95, 0.57,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=0.75, linestyle="--", edgecolor=COLORS["excluded"], facecolor="#F3F4F6",
    )
    ax.add_patch(missing)
    ax.text(3.125, -0.435, "Insufficient evidence:\nexclude or mark unavailable", ha="center", va="center",
            fontsize=7.2, color="#374151")
    fig.savefig(FIGURES / "figure01_methodology.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def generate_area_fmax(figure_data: dict) -> None:
    style()
    labels = {
        "secded-rtl-combinational-72-64-v1": ("SECDED comb.", COLORS["comb"], "o"),
        "secded-rtl-pipelined-72-64-v1": ("SECDED pipe.", COLORS["pipe"], "s"),
        "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1": ("BCH (target missed)", COLORS["bch"], "^"),
    }
    rows = []
    fig, ax = plt.subplots(figsize=(3.48, 2.35))
    for point in figure_data["F02_AREA_VS_FMAX"]["points"]:
        name, color, marker = labels[point["implementation_id"]]
        x = point["area_um2"] / 1000.0
        y = point["fmax_mhz"]
        ax.scatter(x, y, color=color, marker=marker, s=46, edgecolor="white", linewidth=0.6, zorder=3, label=name)
        rows.append(
            {
                "implementation_id": point["implementation_id"],
                "area_um2": point["area_um2"],
                "fmax_mhz": point["fmax_mhz"],
                "meets_10ns": point["meets_10ns"],
            }
        )
    ax.axhline(100.0, color="#9B1C1C", linestyle="--", linewidth=0.9, label="100 MHz target")
    ax.set_xlabel(r"Standard-cell area (10$^3$ $\mu$m$^2$)")
    ax.set_ylabel("Achieved Fmax (MHz)")
    ax.set_xlim(12, 62)
    ax.set_ylim(35, 390)
    ax.grid(True, color=COLORS["grid"], linewidth=0.45, alpha=0.8)
    ax.legend(loc="upper right", frameon=True, framealpha=0.95, borderpad=0.35, handletextpad=0.4)
    fig.tight_layout(pad=0.35)
    fig.savefig(FIGURES / "figure02_area_fmax.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    with (DATA / "figure02_area_fmax.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def generate_normalized(figure_data: dict) -> None:
    style()
    data = figure_data["F03_NORMALIZED_PHYSICAL_COST"]
    impls = [
        "secded-rtl-combinational-72-64-v1",
        "secded-rtl-pipelined-72-64-v1",
        "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
    ]
    names = ["SECDED\ncomb.", "SECDED\npipe.", "BCH"]
    metrics = [
        ("standard_cell_instance_area_um2", "Area"),
        ("detailed_route_wirelength_um", "Wirelength"),
        ("achieved_fmax_mhz", "Fmax"),
    ]
    ratios = {key: [1.0 + data["routed_metrics"][impl][key] / 100.0 for impl in impls] for key, _ in metrics}
    colors = [COLORS["comb"], COLORS["pipe"], COLORS["bch"]]

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(3.48, 4.0),
        gridspec_kw={"height_ratios": [1.35, 1.0]},
    )
    x = list(range(len(metrics)))
    width = 0.23
    for i, (name, color) in enumerate(zip(names, colors)):
        vals = [ratios[key][i] for key, _ in metrics]
        ax1.bar([v + (i - 1) * width for v in x], vals, width=width, label=name.replace("\n", " "), color=color)
    ax1.axhline(1.0, color="#4B5563", linewidth=0.65)
    ax1.set_xticks(x, [label for _, label in metrics])
    ax1.set_ylabel("Normalized ratio")
    ax1.set_title("(a) All routed designs")
    ax1.set_ylim(0, 4.45)
    ax1.grid(axis="y", color=COLORS["grid"], linewidth=0.45)
    ax1.legend(ncol=3, loc="upper center", frameon=False, handlelength=1.0, columnspacing=0.65)

    feasible = [
        "secded-rtl-combinational-72-64-v1",
        "secded-rtl-pipelined-72-64-v1",
    ]
    power_energy = data["timing_feasible_power_energy_metrics"]
    pe_metrics = [("no_error_total_power_percent_change", "Power"), ("no_error_energy_percent_change", "Energy/op")]
    x2 = list(range(len(pe_metrics)))
    width2 = 0.3
    for i, (impl, name, color) in enumerate(zip(feasible, names[:2], colors[:2])):
        vals = [1.0 + power_energy[impl][key] / 100.0 for key, _ in pe_metrics]
        ax2.bar([v + (i - 0.5) * width2 for v in x2], vals, width=width2, label=name.replace("\n", " "), color=color)
    ax2.axhline(1.0, color="#4B5563", linewidth=0.65)
    ax2.set_xticks(x2, [label for _, label in pe_metrics])
    ax2.set_ylabel("Normalized ratio")
    ax2.set_title("(b) Timing-feasible points only")
    ax2.set_ylim(0, 1.18)
    ax2.grid(axis="y", color=COLORS["grid"], linewidth=0.45)
    ax2.legend(loc="upper right", frameon=False)
    fig.tight_layout(pad=0.4, h_pad=0.7)
    fig.savefig(FIGURES / "figure03_normalized_tradeoffs.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    rows = []
    for impl in impls:
        for key, _ in metrics:
            rows.append(
                {
                    "panel": "all_routed",
                    "implementation_id": impl,
                    "metric": key,
                    "percent_change_from_comb_secded": data["routed_metrics"][impl][key],
                    "normalized_ratio": 1.0 + data["routed_metrics"][impl][key] / 100.0,
                }
            )
    for impl in feasible:
        for key, _ in pe_metrics:
            rows.append(
                {
                    "panel": "timing_feasible_energy",
                    "implementation_id": impl,
                    "metric": key,
                    "percent_change_from_comb_secded": power_energy[impl][key],
                    "normalized_ratio": 1.0 + power_energy[impl][key] / 100.0,
                }
            )
    with (DATA / "figure03_normalized_tradeoffs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def protection_short(value: str) -> str:
    if "weight-0/1/2" in value:
        return "W1/W2 correct"
    return "W1 correct; W2 detect"


def generate_tables(table_i: list[dict], table_ii: list[dict]) -> None:
    arch_short = ["SECDED comb.", "SECDED pipe.", "Hsiao SECDED", "BCH"]
    code_short = ["(72,64)", "(72,64)", "(72,64)", "(78,64,t=2)"]
    status_short = ["Routed", "Routed", "PPA unavailable", "Routed; 10 ns missed"]
    lines = [
        "\\begin{table*}[t]",
        "\\caption{Evaluated implementation identities. II is initiation interval.}",
        "\\label{tab:identities}",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{5.2pt}",
        "\\begin{tabular}{lcccccl}",
        "\\toprule",
        "Architecture & Code & Protection guarantee & Latency & II & Payload & Physical status \\\\",
        "\\midrule",
    ]
    for idx, row in enumerate(table_i):
        lines.append(
            f"{arch_short[idx]} & {code_short[idx]} & {protection_short(row['protection_guarantee'])} & "
            f"{row['latency_cycles']} & {row['initiation_interval_cycles']} & {row['payload_bits']} b & {status_short[idx]} \\\\" 
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}"])
    (TABLES / "generated_table_i.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    lines = [
        "\\begin{table*}[t]",
        "\\caption{Post-route results. Power and energy are comparable only for the two timing-feasible SECDED points.}",
        "\\label{tab:results}",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{5.0pt}",
        "\\begin{tabular}{lrrrrrl}",
        "\\toprule",
        "Architecture & Area ($\\mu$m$^2$) & Fmax (MHz) & Wirelength ($\\mu$m) & Power (mW) & Energy (pJ/op) & 10 ns \\\\",
        "\\midrule",
    ]
    for idx, row in enumerate(table_ii):
        if row["area_um2"] == "PPA_UNAVAILABLE":
            vals = ["--", "--", "--", "--", "--", "PPA unavailable"]
        elif idx == 3:
            vals = [f"{float(row['area_um2']):.1f}", f"{float(row['fmax_mhz']):.4f}", f"{float(row['wirelength_um']):.0f}", "diagnostic", "--", "missed"]
        else:
            vals = [
                f"{float(row['area_um2']):.1f}", f"{float(row['fmax_mhz']):.3f}", f"{float(row['wirelength_um']):.0f}",
                f"{float(row['no_error_power_w']) * 1000.0:.3f}", f"{float(row['achievable_energy_pj_per_operation']):.3f}", "met",
            ]
        lines.append(f"{arch_short[idx]} & " + " & ".join(vals) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}"])
    (TABLES / "generated_table_ii.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with (DATA / "table_i_implementation_identities.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=table_i[0].keys())
        writer.writeheader()
        writer.writerows(table_i)
    with (DATA / "table_ii_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=table_ii[0].keys())
        writer.writeheader()
        writer.writerows(table_ii)


def main() -> None:
    for directory in (DATA, FIGURES, TABLES):
        directory.mkdir(parents=True, exist_ok=True)
    ledger = read_json("GATE07_CLAIM_LEDGER.json")
    figure_data = read_json("GATE07_FIGURE_DATA.json")
    table_i = read_csv("GATE07_TABLE_I_IMPLEMENTATIONS.csv")
    table_ii = read_csv("GATE07_TABLE_II_RESULTS.csv")

    generate_claims(ledger)
    generate_methodology_figure()
    generate_area_fmax(figure_data)
    generate_normalized(figure_data)
    generate_tables(table_i, table_ii)

    traceability = {
        "schema_version": 1,
        "policy": "Every numerical display is generated from frozen Gate 07 evidence; manuscript source is not authoritative.",
        "artifacts": {
            "data/generated_claims.tex": {
                "sources": ["GATE07_CLAIM_LEDGER.json:C02.raw_numbers", "GATE07_CLAIM_LEDGER.json:C04.raw_numbers", "GATE07_FIGURE_DATA.json:F03_NORMALIZED_PHYSICAL_COST.routed_metrics"],
                "transformation": "Percent changes recomputed as (candidate-baseline)/baseline*100; display rounding only.",
            },
            "figures/figure01_methodology.pdf": {
                "sources": ["GATE07_MANUSCRIPT_EVIDENCE.json:final_figures.F01_CROSS_LAYER_METHOD", "GATE07_CONTRIBUTION_FREEZE.md"],
                "transformation": "Non-numerical publication diagram; internal gate names removed.",
            },
            "figures/figure02_area_fmax.pdf": {
                "sources": ["GATE07_FIGURE_DATA.json:F02_AREA_VS_FMAX.points"],
                "transformation": "Area divided by 1000 for axis scale; Fmax unchanged; 100 MHz target added; Hsiao excluded, not imputed.",
            },
            "figures/figure03_normalized_tradeoffs.pdf": {
                "sources": ["GATE07_FIGURE_DATA.json:F03_NORMALIZED_PHYSICAL_COST"],
                "transformation": "Percent changes converted to ratios by 1+p/100; BCH excluded from energy panel; Hsiao excluded from both panels.",
            },
            "tables/generated_table_i.tex": {
                "sources": ["GATE07_TABLE_I_IMPLEMENTATIONS.csv:all rows"],
                "transformation": "Labels shortened without changing semantics; missing PPA retained.",
            },
            "tables/generated_table_ii.tex": {
                "sources": ["GATE07_TABLE_II_RESULTS.csv:all rows"],
                "transformation": "Units formatted; W converted to mW; BCH target power labeled diagnostic and energy omitted.",
            },
        },
    }
    write_json(DATA / "traceability.json", traceability)
    print("Generated DATE 2027 manuscript artifacts from frozen Gate 07 evidence.")


if __name__ == "__main__":
    main()
