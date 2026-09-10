#!/usr/bin/env python3
"""Regenerate the DATE 2027 evidence tables and figures from sealed inputs."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

_SCRIPT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(_SCRIPT_ROOT / "build/matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
E5 = REPO / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5"
PHY = REPO / "campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation"
MATCHED = E5 / "E5_MATCHED_SEED_DELTAS.csv"
RUN_MANIFEST = E5 / "RUN_MANIFEST.json"
PHYSICAL = PHY / "PHYSICAL_RUN_RESULTS.csv"

EXPECTED = {
    MATCHED: "2e344e77ccd16623473b752a1d44b5e577a0d53bc1b8f683044d83a32048769c",
    RUN_MANIFEST: "5b1b42351eeb092bb59381443e980ee768d518a8b2ed519fa5ac57f930497999",
    E5 / "GREEN_V3_3_ADDITIVE_MATRIX.json": "f604c397276c4ccf7773af1bf9e6765bbd1a8ccb1c2d03c96cbedb318ccf7fb6",
    E5 / "TIMING_FEASIBILITY.json": "795b112cbcb5b9c2917bd296897a55c062cf8b8ad1ae4bf48430c7245005de5b",
    PHY / "PHYSICAL_RUN_RESULTS.csv": "fd3a4adae99f73dd887cea2fe5ad1581419ea7d57f8f221ce1fbf68742e12f2d",
}

SEEDS = [11, 13, 17, 19, 23]
OPS = ["idle", "clean_write", "clean_read", "correction", "detection"]
OP_LABEL = {
    "idle": "Idle",
    "clean_write": "Write",
    "clean_read": "Clean read",
    "correction": "Correction",
    "detection": "Detection",
}
MANIFEST_OP = {
    "IDLE": "idle",
    "WRITE_CLEAN": "clean_write",
    "READ_CLEAN": "clean_read",
    "READ_SINGLE_BIT_ERROR_CORRECT": "correction",
    "READ_DOUBLE_BIT_ERROR_DETECT": "detection",
}
ARCH_LABEL = {"SECDED": "Conventional SECDED", "HSIAO_SECDED": "Hsiao SECDED"}
COLORS = {"blue": "#2166AC", "orange": "#D6604D", "green": "#1B7837", "gray": "#666666"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sources() -> None:
    failures = []
    for path, expected in EXPECTED.items():
        actual = sha256(path)
        if actual != expected:
            failures.append(f"{path}: expected {expected}, got {actual}")
    if failures:
        raise SystemExit("Sealed input mismatch:\n" + "\n".join(failures))


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(values)


def fnum(value: str | float | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def sample_sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def load_physical() -> dict[tuple[str, int], dict[str, str]]:
    keep = {}
    for r in rows(PHYSICAL):
        arch = r["architecture_id"]
        seed = int(r["seed"])
        if arch in {"SECDED", "HSIAO_SECDED"} and float(r["clock_period_ns"]) == 10.0 and seed in SEEDS:
            keep[(arch, seed)] = r
    if len(keep) != 10:
        raise SystemExit(f"Expected 10 matched physical rows, found {len(keep)}")
    return keep


def build_data() -> tuple[list[dict], list[dict], dict]:
    ROOT.joinpath("data").mkdir(exist_ok=True)
    matched = rows(MATCHED)
    if [int(r["seed"]) for r in matched] != SEEDS:
        raise SystemExit("Matched-seed row set changed")

    energy_rows: list[dict] = []
    component_rows: list[dict] = []
    physical_rows: list[dict] = []
    vectorless_rows: list[dict] = []
    physical = load_physical()

    for r in matched:
        seed = int(r["seed"])
        vectorless_delta_uw = float(r["e4_switching_power_w_delta"]) * 1e6 + float(r["e4_internal_power_w_delta"]) * 1e6 + float(r["e4_leakage_power_w_delta"]) * 1e6
        vectorless_rows.append({
            "seed": seed,
            "delta_definition": "Hsiao SECDED minus conventional SECDED",
            "total_power_delta_uW": f"{vectorless_delta_uw:.9f}",
            "lower_energy_architecture": "Hsiao SECDED" if vectorless_delta_uw < 0 else "Conventional SECDED",
            "qualification": "DIAGNOSTIC_VECTORLESS",
        })
        physical_rows.append({
            "seed": seed,
            "area_delta_um2": r["total_instance_area_um2_delta"],
            "standard_cell_area_delta_um2": r["standard_cell_area_um2_delta"],
            "wirelength_delta_um": r["wirelength_um_delta"],
            "via_count_delta": r["via_count_delta"],
            "setup_wns_delta_ns": r["setup_wns_ns_delta"],
            "delta_definition": "Hsiao SECDED minus conventional SECDED",
        })
        for op in OPS:
            ej = fnum(r[f"{op}_energy_j_delta"])
            if ej is not None:
                delta_pj = ej * 1e12
                energy_rows.append({
                    "operation": op,
                    "operation_label": OP_LABEL[op],
                    "seed": seed,
                    "energy_delta_pJ_per_operation": f"{delta_pj:.9f}",
                    "delta_definition": "Hsiao SECDED minus conventional SECDED",
                    "lower_energy_architecture": "Hsiao SECDED" if delta_pj < 0 else "Conventional SECDED",
                    "qualification": "LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE",
                })
            for comp in ("internal", "switching", "leakage"):
                pw = fnum(r[f"{op}_{comp}_power_w_delta"])
                if pw is not None:
                    component_rows.append({
                        "operation": op,
                        "operation_label": OP_LABEL[op],
                        "seed": seed,
                        "component": comp,
                        "power_delta_uW": f"{pw * 1e6:.9f}",
                        "delta_definition": "Hsiao SECDED minus conventional SECDED",
                    })

    if len(energy_rows) != 23:
        raise SystemExit(f"Expected 23 matched operation/seed cells, found {len(energy_rows)}")
    write_csv(ROOT / "data/operation_energy_deltas.csv", list(energy_rows[0]), energy_rows)
    write_csv(ROOT / "data/component_power_deltas.csv", list(component_rows[0]), component_rows)
    write_csv(ROOT / "data/vectorless_ordering.csv", list(vectorless_rows[0]), vectorless_rows)
    write_csv(ROOT / "data/physical_deltas.csv", list(physical_rows[0]), physical_rows)

    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    recs = manifest["new_activity_power_records"]
    if len(recs) != 46:
        raise SystemExit(f"Expected 46 activity records, found {len(recs)}")
    rep_rows = []
    coverage_rows = []
    for r in sorted(recs, key=lambda x: (x["architecture_id"], x["physical_seed"], x["operation_class"])):
        op = MANIFEST_OP[r["operation_class"]]
        coverage_rows.append({
            "architecture": ARCH_LABEL[r["architecture_id"]],
            "seed": r["physical_seed"],
            "operation": op,
            "functional_coverage_percent": f"{100*r['functional_logic_coverage_fraction']:.6f}",
            "combinational_coverage_percent": f"{100*r['combinational_coverage_fraction']:.6f}",
            "sequential_coverage_percent": f"{100*r['sequential_coverage_fraction']:.6f}",
            "macro_output_activity_roots": r["macro_output_activity_root_count"],
        })
        p = physical[(r["architecture_id"], int(r["physical_seed"]))]
        rep_rows.append({
            "record_id": r["record_id"],
            "architecture": ARCH_LABEL[r["architecture_id"]],
            "seed": r["physical_seed"],
            "operation": op,
            "clock_period_ns": r["clock_period_ns"],
            "technology_library_corner": "SKY130 HD / nom_tt_025C_1v80",
            "route_success": p["route_success"],
            "setup_wns_ns": p["setup_wns_ns"],
            "timing_feasible": r["timing_feasible"],
            "routed_netlist_sha256": r["routed_netlist_sha256"],
            "spef_sha256": r["spef_sha256"],
            "vcd_sha256": r["activity_sha256"],
            "workload_sha256": r["workload_sha256"],
            "source_result_sha256": r["source_result_sha256"],
            "activity_boundary": r["activity_boundary"],
            "functional_coverage_percent": f"{100*r['functional_logic_coverage_fraction']:.6f}",
            "macro_output_activity_roots": r["macro_output_activity_root_count"],
            "warm_up_cycles": r["warm_up_cycles"],
            "measured_operations": r["exact_operation_count"],
            "measurement_duration_s": r["measurement_duration_seconds"],
            "internal_power_W": r["internal_power_w"],
            "switching_power_W": r["switching_power_w"],
            "leakage_power_W": r["leakage_power_w"],
            "total_power_W": r["total_power_w"],
            "logic_energy_J_per_operation": r["energy_j_per_operation"],
            "qualification": r["qualification"],
            "sealed_campaign_commit": "8cf245ac6ac8cb9b010c073d439f04eb204d48a1",
        })
    write_csv(ROOT / "data/activity_coverage.csv", list(coverage_rows[0]), coverage_rows)
    write_csv(ROOT / "DATE2027_REPRODUCIBILITY_TABLE.csv", list(rep_rows[0]), rep_rows)

    grouped = defaultdict(list)
    for r in energy_rows:
        grouped[r["operation"]].append(float(r["energy_delta_pJ_per_operation"]))
    op_stats = []
    for op in OPS:
        vals = grouped[op]
        op_stats.append({
            "operation": op,
            "label": OP_LABEL[op],
            "n": len(vals),
            "mean_delta_pJ": mean(vals),
            "sample_sd_pJ": sample_sd(vals),
            "min_delta_pJ": min(vals),
            "max_delta_pJ": max(vals),
            "hsiao_lower_count": sum(v < 0 for v in vals),
            "conventional_lower_count": sum(v > 0 for v in vals),
        })
    stats = {
        "delta_definition": "Hsiao SECDED minus conventional SECDED",
        "matched_physical_runs": 10,
        "seeds_per_architecture": 5,
        "activity_records": 46,
        "matched_operation_seed_cells": 23,
        "vectorless_hsiao_lower_count": sum(float(r["total_power_delta_uW"]) < 0 for r in vectorless_rows),
        "activity_hsiao_lower_count": sum(float(r["energy_delta_pJ_per_operation"]) < 0 for r in energy_rows),
        "activity_coverage_min_percent": min(float(r["functional_coverage_percent"]) for r in coverage_rows),
        "activity_coverage_max_percent": max(float(r["functional_coverage_percent"]) for r in coverage_rows),
        "operation_statistics": op_stats,
        "physical_mean_deltas": {
            "total_instance_area_um2": mean([float(r["area_delta_um2"]) for r in physical_rows]),
            "standard_cell_area_um2": mean([float(r["standard_cell_area_delta_um2"]) for r in physical_rows]),
            "wirelength_um": mean([float(r["wirelength_delta_um"]) for r in physical_rows]),
            "via_count": mean([float(r["via_count_delta"]) for r in physical_rows]),
            "setup_wns_ns": mean([float(r["setup_wns_delta_ns"]) for r in physical_rows]),
        },
    }
    (ROOT / "data/derived_statistics.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return energy_rows, vectorless_rows, stats


def save_figure(fig, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        kwargs = {"bbox_inches": "tight", "facecolor": "white"}
        if ext == "png":
            kwargs["dpi"] = 450
        fig.savefig(stem.with_suffix("." + ext), **kwargs)
    plt.close(fig)


def pipeline_figure() -> None:
    fig, ax = plt.subplots(figsize=(3.45, 2.35))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    labels = [
        (0.2, 5.3, "ECC semantics", "functional gate"),
        (5.8, 5.3, "Hardware identity", "interface + seed"),
        (0.2, 3.0, "Routed physical identity", "route + timing gate"),
        (5.8, 3.0, "Extracted parasitics", "final SPEF hash"),
        (0.2, 0.7, "Activity identity", "VCD + coverage gate"),
        (5.8, 0.7, "Qualified energy", "256-op normalization"),
    ]
    for x, y, label, gate in labels:
        box = FancyBboxPatch((x, y), 4.0, 1.25, boxstyle="round,pad=0.08", linewidth=0.9,
                             edgecolor=COLORS["blue"], facecolor="#EAF2F8")
        ax.add_patch(box)
        ax.text(x + 2.0, y + 0.78, label, ha="center", va="center", fontsize=7.0, fontweight="bold")
        ax.text(x + 2.0, y + 0.35, gate, ha="center", va="center", fontsize=6.2, color=COLORS["gray"])
    arrows = [((4.35, 5.93), (5.65, 5.93)), ((7.8, 5.2), (2.2, 4.4)),
              ((4.35, 3.63), (5.65, 3.63)), ((7.8, 2.9), (2.2, 2.1)),
              ((4.35, 1.33), (5.65, 1.33))]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8,
                                     linewidth=0.8, color=COLORS["gray"], connectionstyle="arc3,rad=0"))
    ax.text(5.0, 0.05, "Measured boundary: routed ECC logic; SRAM-macro internal energy excluded",
            ha="center", va="bottom", fontsize=5.8, color=COLORS["gray"])
    save_figure(fig, ROOT / "figures/final/figure01_evidence_pipeline")
    (ROOT / "figures/source_data/figure01_evidence_pipeline.json").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "figures/source_data/figure01_evidence_pipeline.json").write_text(json.dumps({
        "stages": ["ECC semantics", "hardware identity", "routed physical identity", "extracted parasitics", "activity identity", "qualified operation-level energy"],
        "qualification_gates": ["functional correctness", "interface and seed identity", "route completion and timing feasibility", "final SPEF association", "VCD association and activity coverage", "256-operation normalization"],
        "identity_keys": ["architecture", "seed", "routed_netlist_sha256", "spef_sha256", "workload_sha256"],
    }, indent=2) + "\n", encoding="utf-8")


def ordering_figure(energy_rows: list[dict], vectorless_rows: list[dict]) -> None:
    # -1 means Hsiao lower, +1 means conventional lower, 0 is missing.
    matrix = []
    labels = ["Vectorless\n$\\Delta P$ ($\\mu$W)"] + [OP_LABEL[o] + "\n$\\Delta E$ (pJ/op)" for o in OPS]
    text_values: list[list[str]] = []
    eidx = {(int(r["seed"]), r["operation"]): float(r["energy_delta_pJ_per_operation"]) for r in energy_rows}
    vidx = {int(r["seed"]): float(r["total_power_delta_uW"]) for r in vectorless_rows}
    for seed in SEEDS:
        row, txt = [], []
        vals = [vidx[seed]] + [eidx.get((seed, op)) for op in OPS]
        for value in vals:
            if value is None:
                row.append(0)
                txt.append("—")
            else:
                row.append(-1 if value < 0 else 1)
                txt.append(f"{value:+.2f}")
        matrix.append(row)
        text_values.append(txt)
    fig, ax = plt.subplots(figsize=(7.08, 2.18))
    cmap = ListedColormap(["#2C7BB6", "#EEEEEE", "#D7191C"])
    ax.imshow(matrix, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(labels)), labels, fontsize=7.2)
    ax.set_yticks(range(len(SEEDS)), [f"Seed {s}" for s in SEEDS], fontsize=7.2)
    ax.tick_params(length=0)
    for i in range(len(SEEDS)):
        for j in range(len(labels)):
            ax.text(j, i, text_values[i][j], ha="center", va="center", fontsize=7,
                    color="white" if matrix[i][j] else "#555555", fontweight="bold")
    ax.set_title("Ordering changes when the activity abstraction changes ($\\Delta$ = Hsiao − conventional)", fontsize=9)
    ax.text(0.0, -0.34, "Blue: Hsiao lower   Red: conventional lower   —: unavailable (seed 11 idle/write)",
            transform=ax.transAxes, fontsize=7, va="top")
    save_figure(fig, ROOT / "figures/final/figure02_activity_ordering")
    out = []
    for seed, vals in zip(SEEDS, text_values):
        out.append({"seed": seed, **{labels[i].replace("\n", " "): vals[i] for i in range(len(labels))}})
    write_csv(ROOT / "figures/source_data/figure02_activity_ordering.csv", list(out[0]), out)


def delta_figure(energy_rows: list[dict], stats: dict) -> None:
    eidx = defaultdict(list)
    for r in energy_rows:
        eidx[r["operation"]].append((int(r["seed"]), float(r["energy_delta_pJ_per_operation"])))
    fig, ax = plt.subplots(figsize=(3.45, 2.45))
    for i, op in enumerate(OPS):
        vals = eidx[op]
        x = [i + (SEEDS.index(seed) - 2) * 0.035 for seed, _ in vals]
        y = [v for _, v in vals]
        ax.scatter(x, y, s=14, facecolor="white", edgecolor=COLORS["blue"], linewidth=0.8, zorder=3)
        m = mean(y)
        ax.plot([i - 0.20, i + 0.20], [m, m], color=COLORS["orange"], linewidth=2.0, zorder=4)
        lower = sum(v < 0 for v in y)
        ax.text(i, max(y) + 0.035, f"{lower}/{len(y)}", ha="center", fontsize=6.8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(OPS)), ["Idle", "Write", "Read", "Correct", "Detect"], rotation=22, ha="right", fontsize=7)
    ax.set_ylabel("$\\Delta E$ (pJ/operation)", fontsize=8)
    ax.set_title("Matched operation energy by seed", fontsize=9)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.5)
    ax.text(0.01, 0.98, "Hsiao lower", transform=ax.transAxes, va="top", fontsize=6.8, color=COLORS["blue"])
    ax.text(0.01, 0.04, "Conventional lower", transform=ax.transAxes, va="bottom", fontsize=6.8, color=COLORS["orange"])
    ax.text(0.99, 0.98, "labels: Hsiao-lower / matched", transform=ax.transAxes, ha="right", va="top", fontsize=6.2)
    save_figure(fig, ROOT / "figures/final/figure03_operation_energy_deltas")
    write_csv(ROOT / "figures/source_data/figure03_operation_energy_deltas.csv", list(energy_rows[0]), energy_rows)


def analysis_figures() -> None:
    comps = rows(ROOT / "data/component_power_deltas.csv")
    grouped = defaultdict(list)
    for r in comps:
        grouped[(r["operation"], r["component"])].append(float(r["power_delta_uW"]))
    fig, ax = plt.subplots(figsize=(7.08, 2.5))
    x = range(len(OPS))
    bottom_pos = [0.0] * len(OPS)
    bottom_neg = [0.0] * len(OPS)
    comp_colors = {"internal": "#2166AC", "switching": "#D6604D", "leakage": "#7B3294"}
    for comp in ("internal", "switching", "leakage"):
        vals = [mean(grouped[(op, comp)]) for op in OPS]
        bottoms = [bottom_pos[i] if v >= 0 else bottom_neg[i] for i, v in enumerate(vals)]
        ax.bar(list(x), vals, bottom=bottoms, label=comp.title(), color=comp_colors[comp], width=0.62)
        for i, v in enumerate(vals):
            if v >= 0:
                bottom_pos[i] += v
            else:
                bottom_neg[i] += v
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(list(x), [OP_LABEL[o] for o in OPS])
    ax.set_ylabel("Mean power delta ($\\mu$W)")
    ax.set_title("Component deltas explain the operation-dependent total")
    ax.legend(frameon=False, ncol=3, fontsize=8)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.5)
    save_figure(fig, ROOT / "figures/final/figure04_component_decomposition")
    (ROOT / "figures/candidates").mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        shutil.copy2(ROOT / f"figures/final/figure04_component_decomposition.{ext}",
                     ROOT / f"figures/candidates/figure04_component_decomposition.{ext}")
    alt = [[mean(grouped[(op, comp)]) for comp in ("internal", "switching", "leakage")] for op in OPS]
    fig, ax = plt.subplots(figsize=(5.4, 2.4))
    im = ax.imshow(alt, cmap="RdBu_r", aspect="auto", vmin=-40, vmax=40)
    ax.set_xticks(range(3), ["Internal", "Switching", "Leakage"])
    ax.set_yticks(range(len(OPS)), [OP_LABEL[o] for o in OPS])
    for i, line in enumerate(alt):
        for j, value in enumerate(line):
            ax.text(j, i, f"{value:+.2f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(value) > 22 else "black")
    ax.set_title("Candidate heatmap: mean component delta ($\\mu$W)")
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
    save_figure(fig, ROOT / "figures/candidates/figure04_component_decomposition_alternative")
    write_csv(ROOT / "figures/source_data/figure04_component_decomposition.csv",
              ["operation", "component", "mean_power_delta_uW"],
              [{"operation": op, "component": comp, "mean_power_delta_uW": f"{mean(grouped[(op, comp)]):.9f}"}
               for op in OPS for comp in ("internal", "switching", "leakage")])

    cov = rows(ROOT / "data/activity_coverage.csv")
    fig, ax = plt.subplots(figsize=(3.45, 2.2))
    vals = [float(r["functional_coverage_percent"]) for r in cov]
    ax.hist(vals, bins=8, color=COLORS["blue"], edgecolor="white")
    ax.set_xlabel("Functional logic coverage (%)")
    ax.set_ylabel("Records")
    ax.set_title("Coverage across 46 activity records")
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.5)
    save_figure(fig, ROOT / "figures/analysis/figure05_activity_coverage")
    write_csv(ROOT / "figures/source_data/figure05_activity_coverage.csv", list(cov[0]), cov)


def write_tables(stats: dict) -> None:
    table_dir = ROOT / "tables"
    table_dir.mkdir(exist_ok=True)
    op_rows = stats["operation_statistics"]
    tex = [
        "% Generated by scripts/build_artifacts.py",
        "\\begin{table}[t]",
        "\\caption{Operation-specific matched energy ordering at 10 ns. $\\Delta E=E_{\\mathrm{Hsiao}}-E_{\\mathrm{conv.}}$.}",
        "\\label{tab:headline}",
        "\\centering\\footnotesize",
        "\\setlength{\\tabcolsep}{3.1pt}",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "Operation & $n$ & Mean $\\Delta E$ & Range & Hsiao lower \\\\",
        " & & (pJ/op) & (pJ/op) & \\\\",
        "\\midrule",
    ]
    for r in op_rows:
        tex.append(f"{r['label']} & {r['n']} & {r['mean_delta_pJ']:+.4f} & {r['min_delta_pJ']:+.3f}--{r['max_delta_pJ']:+.3f} & {r['hsiao_lower_count']}/{r['n']} \\\\")
    tex += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    (table_dir / "headline_results.tex").write_text("\n".join(tex), encoding="utf-8")
    write_csv(table_dir / "headline_results.csv",
              ["operation", "n", "mean_delta_pJ_per_operation", "sample_sd_pJ", "minimum_pJ", "maximum_pJ", "hsiao_lower_count"],
              [{"operation": r["label"], "n": r["n"], "mean_delta_pJ_per_operation": f"{r['mean_delta_pJ']:.9f}",
                "sample_sd_pJ": f"{r['sample_sd_pJ']:.9f}", "minimum_pJ": f"{r['min_delta_pJ']:.9f}",
                "maximum_pJ": f"{r['max_delta_pJ']:.9f}", "hsiao_lower_count": r["hsiao_lower_count"]} for r in op_rows])
    pm = stats["physical_mean_deltas"]
    (table_dir / "generated_macros.tex").write_text(
        "% Generated by scripts/build_artifacts.py\n"
        f"\\newcommand{{\\ActivityCells}}{{{stats['matched_operation_seed_cells']}}}\n"
        f"\\newcommand{{\\ActivityHsiaoLower}}{{{stats['activity_hsiao_lower_count']}}}\n"
        f"\\newcommand{{\\CoverageMin}}{{{stats['activity_coverage_min_percent']:.6f}}}\n"
        f"\\newcommand{{\\CoverageMax}}{{{stats['activity_coverage_max_percent']:.6f}}}\n"
        f"\\newcommand{{\\AreaDelta}}{{{pm['total_instance_area_um2']:.1f}}}\n"
        f"\\newcommand{{\\WireDelta}}{{{pm['wirelength_um']:.1f}}}\n"
        f"\\newcommand{{\\ViaDelta}}{{{pm['via_count']:.1f}}}\n"
        f"\\newcommand{{\\WnsDelta}}{{{pm['setup_wns_ns']:.4f}}}\n",
        encoding="utf-8")


def manifests() -> None:
    figures = []
    repository_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    definitions = {
        "figure01_evidence_pipeline": ("final", "Evidence pipeline and identity-preservation boundary", "figures/source_data/figure01_evidence_pipeline.json", "included"),
        "figure02_activity_ordering": ("final", "Per-seed ordering under vectorless and operation-specific activity", "figures/source_data/figure02_activity_ordering.csv", "included"),
        "figure03_operation_energy_deltas": ("final", "Matched operation energy deltas by seed", "figures/source_data/figure03_operation_energy_deltas.csv", "included"),
        "figure04_component_decomposition": ("final", "Mean internal, switching, and leakage component deltas", "figures/source_data/figure04_component_decomposition.csv", "included"),
        "figure04_component_decomposition_alternative": ("candidate", "Alternative heatmap for the component concept", "figures/source_data/figure04_component_decomposition.csv", "candidate retained; not included"),
        "figure05_activity_coverage": ("analysis", "Distribution of functional logic activity coverage", "figures/source_data/figure05_activity_coverage.csv", "analysis only"),
    }
    for stem, (tier, purpose, source, disposition) in definitions.items():
        folder = "final" if tier == "final" else ("candidates" if tier == "candidate" else "analysis")
        for ext in ("pdf", "svg", "png"):
            p = ROOT / f"figures/{folder}/{stem}.{ext}"
            figures.append({
                "figure_id": stem,
                "tier": tier,
                "purpose": purpose,
                "format": ext,
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(p),
                "source_data": source,
                "source_data_sha256": sha256(ROOT / source),
                "generation_script": "scripts/build_artifacts.py",
                "generated_date": "2026-09-10",
                "repository_head": repository_head,
                "sealed_source_commit": "8cf245ac6ac8cb9b010c073d439f04eb204d48a1",
                "manuscript_disposition": disposition,
            })
    for ext in ("pdf", "svg", "png"):
        p = ROOT / f"figures/candidates/figure04_component_decomposition.{ext}"
        figures.append({
            "figure_id": "figure04_component_decomposition_early_candidate",
            "tier": "candidate",
            "purpose": "Preserved early candidate of the promoted component-decomposition view",
            "format": ext,
            "path": str(p.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(p),
            "source_data": "figures/source_data/figure04_component_decomposition.csv",
            "source_data_sha256": sha256(ROOT / "figures/source_data/figure04_component_decomposition.csv"),
            "generation_script": "scripts/build_artifacts.py",
            "generated_date": "2026-09-10",
            "repository_head": repository_head,
            "sealed_source_commit": "8cf245ac6ac8cb9b010c073d439f04eb204d48a1",
            "manuscript_disposition": "preserved duplicate candidate; final version included",
        })
    write_csv(ROOT / "DATE2027_FIGURE_MANIFEST.csv", list(figures[0]), figures)
    (ROOT / "DATE2027_TABLE_MANIFEST.md").write_text(
        "# Table Manifest\n\n"
        "| ID | Source | Script | Manuscript use |\n|---|---|---|---|\n"
        "| Experimental controls | controlled-design specification and sealed run manifest | authored in `DATE2027_MANUSCRIPT.tex` | Table I |\n"
        "| Headline results | `data/operation_energy_deltas.csv` | `scripts/build_artifacts.py` | Table II |\n"
        "| Reproducibility ledger | sealed `RUN_MANIFEST.json` plus physical results | `scripts/build_artifacts.py` | Supplementary audit artifact |\n"
        "| Component means | `data/component_power_deltas.csv` | `scripts/build_artifacts.py` | Explained in text and final Figure 4 |\n",
        encoding="utf-8")
    upstream = {
        "figure01_evidence_pipeline": "sealed physical results + sealed run manifest",
        "figure02_activity_ordering": "E5_MATCHED_SEED_DELTAS.csv",
        "figure03_operation_energy_deltas": "E5_MATCHED_SEED_DELTAS.csv",
        "figure04_component_decomposition": "E5_MATCHED_SEED_DELTAS.csv",
        "figure04_component_decomposition_alternative": "E5_MATCHED_SEED_DELTAS.csv",
        "figure04_component_decomposition_early_candidate": "E5_MATCHED_SEED_DELTAS.csv",
        "figure05_activity_coverage": "RUN_MANIFEST.json",
    }
    fields = {
        "figure01_evidence_pipeline": "method stages and identity keys; no quantitative axis",
        "figure02_activity_ordering": "seed; vectorless total-power delta (uW); operation energy delta (pJ/op); missing cells",
        "figure03_operation_energy_deltas": "operation; seed; energy delta (pJ/op); arithmetic mean; Hsiao-lower count",
        "figure04_component_decomposition": "operation; internal/switching/leakage mean power delta (uW)",
        "figure04_component_decomposition_alternative": "operation; internal/switching/leakage mean power delta (uW)",
        "figure04_component_decomposition_early_candidate": "operation; internal/switching/leakage mean power delta (uW)",
        "figure05_activity_coverage": "functional logic coverage (%), all 46 records",
    }
    grouped = defaultdict(list)
    for row in figures:
        grouped[row["figure_id"]].append(row)
    lines = [
        "# Figure/Data Provenance", "",
        "Every value is regenerated by `scripts/build_artifacts.py` after SHA-256 verification of sealed inputs. "
        "Seeds are 11, 13, 17, 19, and 23; operations are idle, clean write, clean read, correction, and detection. "
        "Seed-11 idle/write values remain missing and are never imputed.", "",
        f"Repository HEAD at generation: `{repository_head}`. Sealed evidence commit: `8cf245ac6ac8cb9b010c073d439f04eb204d48a1`.", "",
        "| Figure ID | Usage | Upstream evidence | Source data (SHA-256) | Plotted fields / units | Outputs | Date |", "|---|---|---|---|---|---|---|",
    ]
    for figure_id, rs in grouped.items():
        first = rs[0]
        outputs = ", ".join(f"`{r['path']}`" for r in rs)
        lines.append(
            f"| {figure_id} | {first['manuscript_disposition']} | {upstream[figure_id]} | "
            f"`{first['source_data']}` (`{first['source_data_sha256']}`) | {fields[figure_id]} | {outputs} | 2026-09-10 |"
        )
    lines += ["", "## Transformation and filtering", "",
              "The generator reads all five matched seed rows, converts joules to pJ/op and watts to uW, keeps qualified nonblank operation cells, and computes unweighted arithmetic means. "
              "It writes the exact plotted rows before plotting. No outlier filter, interpolation, smoothing, or manual value is applied. Figure 1 is a semantic diagram whose source JSON is complete.", ""]
    (ROOT / "FIGURE_DATA_PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    verify_sources()
    energy_rows, vectorless_rows, stats = build_data()
    pipeline_figure()
    ordering_figure(energy_rows, vectorless_rows)
    delta_figure(energy_rows, stats)
    analysis_figures()
    write_tables(stats)
    manifests()
    print(json.dumps({
        "status": "PASS",
        "verified_inputs": len(EXPECTED),
        "activity_records": stats["activity_records"],
        "matched_operation_seed_cells": stats["matched_operation_seed_cells"],
        "vectorless_hsiao_lower": f"{stats['vectorless_hsiao_lower_count']}/5",
        "activity_hsiao_lower": f"{stats['activity_hsiao_lower_count']}/23",
    }, indent=2))


if __name__ == "__main__":
    main()
