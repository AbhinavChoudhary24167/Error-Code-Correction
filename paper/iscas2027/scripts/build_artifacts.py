#!/usr/bin/env python3
"""Regenerate every quantitative ISCAS 2027 paper artifact from frozen evidence.

The script intentionally derives the primary cohort rather than naming seeds in
the analysis: a seed is admitted only when both SECDED implementations are setup-
and hold-clean at 10 ns and all five E5 operation classes are present.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon


SCRIPT = Path(__file__).resolve()
PAPER = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]
PHYSICAL = ROOT / "campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/PHYSICAL_RUN_RESULTS.csv"
ARCH_AUDIT = ROOT / "campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/ARCHITECTURE_AUDIT.json"
E5_MATRIX = ROOT / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/GREEN_V3_3_ADDITIVE_MATRIX.json"
E5_STATUS = ROOT / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/CAMPAIGN_STATUS.json"
RUN_MANIFEST = ROOT / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/RUN_MANIFEST.json"
WORKLOAD_MANIFEST = ROOT / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/WORKLOAD_MANIFEST.json"

FIGURES = PAPER / "figures"
TABLES = PAPER / "tables"
PROVENANCE = PAPER / "RESULT_PROVENANCE.csv"

ARCHS = ("U0", "SECDED", "HSIAO_SECDED", "BCH_78_64_T2")
PAIR = ("SECDED", "HSIAO_SECDED")
OPS = (
    "IDLE",
    "READ_CLEAN",
    "WRITE_CLEAN",
    "READ_SINGLE_BIT_ERROR_CORRECT",
    "READ_DOUBLE_BIT_ERROR_DETECT",
)
OP_SHORT = {
    "IDLE": "Idle",
    "READ_CLEAN": "Clean read",
    "WRITE_CLEAN": "Clean write",
    "READ_SINGLE_BIT_ERROR_CORRECT": "W1 correct",
    "READ_DOUBLE_BIT_ERROR_DETECT": "W2 detect",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def tex_signed(value: float, digits: int) -> str:
    return f"{value:+.{digits}f}"


def provenance_row(
    claim_id: str,
    claim: str,
    metric: str,
    value,
    unit: str,
    level: str,
    boundary: str,
    sources: list[Path],
    derivation: str,
) -> dict[str, str]:
    return {
        "claim_id": claim_id,
        "manuscript_claim": claim,
        "metric": metric,
        "value": str(value),
        "unit": unit,
        "evidence_level": level,
        "qualification_boundary": boundary,
        "source_path": "|".join(str(p.relative_to(ROOT)).replace("\\", "/") for p in sources),
        "source_sha256": "|".join(sha256(p) for p in sources),
        "derivation": derivation,
        "generator": str(SCRIPT.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    physical = load_csv(PHYSICAL)
    arch_audit = load_json(ARCH_AUDIT)
    e5_matrix = load_json(E5_MATRIX)
    status = load_json(E5_STATUS)
    manifest = load_json(RUN_MANIFEST)
    workload_manifest = load_json(WORKLOAD_MANIFEST)

    rows10 = [r for r in physical if math.isclose(float(r["clock_period_ns"]), 10.0)]
    by_arch_seed = {(r["architecture_id"], int(r["seed"])): r for r in rows10}
    all_seeds = sorted({int(r["seed"]) for r in rows10})

    e5 = {}
    for rec in e5_matrix["records"]:
        if rec["architecture_id"] in PAIR and math.isclose(float(rec["clock_period_ns"]), 10.0):
            e5[(rec["architecture_id"], int(rec["physical_seed"]), rec["operation_class"])] = float(rec["energy_j_per_operation"])

    primary_seeds = []
    for seed in all_seeds:
        timing_clean = all(
            float(by_arch_seed[(arch, seed)]["setup_wns_ns"]) >= 0.0
            and float(by_arch_seed[(arch, seed)]["hold_wns_ns"]) >= 0.0
            for arch in PAIR
        )
        e5_complete = all((arch, seed, op) in e5 for arch in PAIR for op in OPS)
        if timing_clean and e5_complete:
            primary_seeds.append(seed)

    if not primary_seeds:
        raise RuntimeError("No fully timing-clean, complete-operation matched cohort")

    primary_workloads = [
        r for r in workload_manifest["records"]
        if r["architecture_id"] in PAIR
        and int(r["physical_seed"]) in primary_seeds
        and math.isclose(float(r["clock_period_ns"]), 10.0)
        and r["operation_class"] in OPS
    ]
    warmup_values = {int(r["warm_up_cycles"]) for r in primary_workloads}
    operation_counts = {int(r["exact_operation_count"]) for r in primary_workloads}
    if len(warmup_values) != 1 or len(operation_counts) != 1:
        raise RuntimeError("Primary workload timing/count invariants are not unique")
    warmup_cycles = warmup_values.pop()
    measured_operations = operation_counts.pop()

    deltas_pj: dict[str, list[float]] = {op: [] for op in OPS}
    for op in OPS:
        for seed in primary_seeds:
            delta = e5[("HSIAO_SECDED", seed, op)] - e5[("SECDED", seed, op)]
            deltas_pj[op].append(delta * 1e12)

    mean_delta = {op: mean(values) for op, values in deltas_pj.items()}
    lower_count = sum(value < 0 for values in deltas_pj.values() for value in values)
    comparisons = len(primary_seeds) * len(OPS)

    physical_delta = {}
    for field in ("standard_cell_area_um2", "wirelength_um", "via_count", "setup_wns_ns"):
        values = [
            float(by_arch_seed[("HSIAO_SECDED", seed)][field])
            - float(by_arch_seed[("SECDED", seed)][field])
            for seed in primary_seeds
        ]
        physical_delta[field] = {"mean": mean(values), "min": min(values), "max": max(values), "values": values}

    setup_summary = {}
    for arch in ARCHS:
        vals = [float(r["setup_wns_ns"]) for r in rows10 if r["architecture_id"] == arch]
        setup_summary[arch] = {"mean": mean(vals), "min": min(vals), "max": max(vals), "clean": sum(v >= 0 for v in vals)}

    bch_setup_mean = setup_summary["BCH_78_64_T2"]["mean"]
    h_hold_min = min(float(r["hold_wns_ns"]) for r in rows10 if r["architecture_id"] == "HSIAO_SECDED")

    # Generated macros keep manuscript numerics coupled to the evidence files.
    macros = {
        "PrimarySeedCount": f"{len(primary_seeds)}",
        "PrimarySeedList": ", ".join(str(v) for v in primary_seeds),
        "PrimaryEfiveRecordCount": f"{len(primary_seeds) * len(PAIR) * len(OPS)}",
        "PrimaryComparisonCount": f"{comparisons}",
        "CampaignEfiveRecordCount": f"{len(e5_matrix['records'])}",
        "HsiaoLowerCount": f"{lower_count}",
        "ConventionalLowerCount": f"{comparisons - lower_count}",
        "AreaDeltaPrimary": tex_signed(physical_delta["standard_cell_area_um2"]["mean"], 1),
        "WireDeltaPrimary": tex_signed(physical_delta["wirelength_um"]["mean"], 1),
        "ViaDeltaPrimary": tex_signed(physical_delta["via_count"]["mean"], 1),
        "SlackDeltaPrimary": tex_signed(physical_delta["setup_wns_ns"]["mean"], 3),
        "IdleDelta": tex_signed(mean_delta["IDLE"], 4),
        "ReadDelta": tex_signed(mean_delta["READ_CLEAN"], 4),
        "WriteDelta": tex_signed(mean_delta["WRITE_CLEAN"], 4),
        "CorrectionDelta": tex_signed(mean_delta["READ_SINGLE_BIT_ERROR_CORRECT"], 4),
        "DetectionDelta": tex_signed(mean_delta["READ_DOUBLE_BIT_ERROR_DETECT"], 4),
        "BchSetupMean": tex_signed(bch_setup_mean, 3),
        "BchCleanCount": f"{setup_summary['BCH_78_64_T2']['clean']}",
        "PhysicalSeedCount": f"{len(all_seeds)}",
        "HsiaoHoldMinimum": f"{h_hold_min:.4f}",
        "CoverageRootCount": f"{status['activity_annotation_coverage']['macro_output_roots_required_and_annotated']}",
        "MeasuredOperations": f"{measured_operations}",
    }
    with (TABLES / "generated_claims.tex").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("% Generated by scripts/build_artifacts.py; do not hand edit.\n")
        for key, value in macros.items():
            stream.write(f"\\newcommand{{\\{key}}}{{{value}}}\n")

    # Table I: qualification population (textual cells are controlled mappings of the audit).
    audits = {r["architecture_id"]: r for r in arch_audit["records"] if r["architecture_id"] in ARCHS}
    service = {"U0": "none", "SECDED": "W1 C / W2 D", "HSIAO_SECDED": "W1 C / W2 D", "BCH_78_64_T2": "W1--W2 C"}
    storage = {"U0": "64", "SECDED": "64+8", "HSIAO_SECDED": "64+8", "BCH_78_64_T2": "64+16$^{a}$"}
    names = {"U0": "U0", "SECDED": "Ext.-Hamming", "HSIAO_SECDED": "Hsiao", "BCH_78_64_T2": "BCH(78,64,$t$=2)"}
    with (TABLES / "architecture_population.tex").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("% Generated by scripts/build_artifacts.py; do not hand edit.\n")
        for arch in ARCHS:
            latency = audits[arch]["latency_cycles"]
            clean = setup_summary[arch]["clean"]
            e5_cell = "primary" if arch in PAIR else "not run"
            stream.write(f"{names[arch]} & {service[arch]} & {storage[arch]} & {latency}/1 & {clean}/5 & {e5_cell} \\\\\n")
        stream.write("\\bottomrule\n")

    with (TABLES / "headline_results.tex").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("% Generated by scripts/build_artifacts.py; do not hand edit.\n")
        for op in OPS:
            values = deltas_pj[op]
            stream.write(
                f"{OP_SHORT[op]} & {mean(values):+.4f} & [{min(values):+.4f}, {max(values):+.4f}] & "
                f"{sum(v < 0 for v in values)}/{len(values)} \\\\\n"
            )
        stream.write("\\bottomrule\n")

    # Machine-readable derived values.
    derived = {
        "derivation_version": "1.0.0",
        "delta_definition": "HSIAO_SECDED_MINUS_SECDED",
        "primary_admission": "both architectures setup_wns>=0 and hold_wns>=0 at 10 ns; all five E5 operations present",
        "primary_seeds": primary_seeds,
        "primary_record_count": len(primary_seeds) * len(PAIR) * len(OPS),
        "matched_operation_comparison_count": comparisons,
        "hsiao_lower_count": lower_count,
        "operation_mean_delta_pj": mean_delta,
        "operation_seed_delta_pj": deltas_pj,
        "physical_mean_delta": {k: v["mean"] for k, v in physical_delta.items()},
        "setup_summary_10ns": setup_summary,
        "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in (PHYSICAL, ARCH_AUDIT, E5_MATRIX, E5_STATUS, RUN_MANIFEST, WORKLOAD_MANIFEST)},
    }
    with (TABLES / "derived_metrics.json").open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(derived, stream, indent=2, sort_keys=True)
        stream.write("\n")

    # Figure 1: evidence-gated decision flow.
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.0,
        "axes.labelsize": 8.0,
        "axes.titlesize": 9.0,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(7.15, 1.38))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2)
    ax.axis("off")
    labels = [
        ("Service", "named RTL\nW1/W2 contract"),
        ("Identity", "hashes + macro\norganization"),
        ("Feasibility", "route + setup\n+ hold"),
        ("Operation", "VCD + SPEF\nenergy class"),
        ("Lifecycle", "matched boundary\nor symbolic term"),
    ]
    xs = [0.25, 2.25, 4.25, 6.25, 8.25]
    colors = ["#d8ecf8", "#d8ecf8", "#d8ecf8", "#d8ecf8", "#f6e6bd"]
    for i, ((title, body), x, color) in enumerate(zip(labels, xs, colors)):
        box = FancyBboxPatch((x, 0.45), 1.48, 1.08, boxstyle="round,pad=0.04", facecolor=color, edgecolor="#24445c", linewidth=1.0)
        ax.add_patch(box)
        ax.text(x + 0.74, 1.21, title, ha="center", va="center", fontweight="bold")
        ax.text(x + 0.74, 0.79, body, ha="center", va="center", fontsize=7.2)
        if i < 4:
            ax.annotate("", xy=(xs[i + 1] - 0.08, 0.99), xytext=(x + 1.56, 0.99), arrowprops=dict(arrowstyle="->", lw=1.0, color="#24445c"))
    ax.text(5.0, 0.15, "Fail closed: infeasible and missing quantities remain visible; they do not enter the Pareto set.", ha="center", fontsize=7.4, color="#7a2d2d")
    fig.tight_layout(pad=0.05)
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES / f"figure1_evidence_pipeline.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Figure 2: setup feasibility and primary operation deltas.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.15, 2.35), gridspec_kw={"width_ratios": [0.92, 1.38]})
    colors_arch = {"U0": "#4c78a8", "SECDED": "#f58518", "HSIAO_SECDED": "#54a24b", "BCH_78_64_T2": "#b279a2"}
    labels_arch = {"U0": "U0", "SECDED": "Ext.-Ham.", "HSIAO_SECDED": "Hsiao", "BCH_78_64_T2": "BCH t=2"}
    for idx, arch in enumerate(ARCHS):
        vals = [float(by_arch_seed[(arch, seed)]["setup_wns_ns"]) for seed in all_seeds]
        offsets = [-0.08, -0.04, 0, 0.04, 0.08]
        ax1.scatter([idx + d for d in offsets], vals, s=18, color=colors_arch[arch], edgecolor="white", linewidth=0.35, zorder=3)
        ax1.plot([idx - 0.17, idx + 0.17], [mean(vals), mean(vals)], color="black", lw=1.0, zorder=4)
    ax1.axhline(0, color="#7a2d2d", lw=0.9, ls="--")
    ax1.set_xticks(range(len(ARCHS)), [labels_arch[a] for a in ARCHS], rotation=22, ha="right")
    ax1.set_ylabel("Setup WNS at 10 ns (ns)")
    ax1.set_title("(a) Five routed seeds")
    ax1.grid(axis="y", color="#dddddd", lw=0.5)

    op_x = list(range(len(OPS)))
    for seed, marker in zip(primary_seeds, ("o", "s", "^", "D", "v", "P")):
        vals = [deltas_pj[op][primary_seeds.index(seed)] for op in OPS]
        ax2.plot(op_x, vals, marker=marker, ms=4, lw=0.8, alpha=0.72, label=f"seed {seed}")
    ax2.plot(op_x, [mean_delta[op] for op in OPS], color="black", marker="o", ms=4.6, lw=1.5, label="mean")
    ax2.axhline(0, color="#7a2d2d", lw=0.9, ls="--")
    ax2.set_xticks(op_x, ["Idle", "Read", "Write", "Correct", "Detect"], rotation=22, ha="right")
    ax2.set_ylabel("Hsiao $-$ ext.-Hamming (pJ/op)")
    ax2.set_title("(b) Fully timing-clean matched cohort")
    ax2.grid(axis="y", color="#dddddd", lw=0.5)
    ax2.legend(ncol=3, fontsize=6.5, frameon=False, loc="upper left")
    fig.tight_layout(pad=0.35, w_pad=0.9)
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES / f"figure2_feasibility_energy.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Figure 3: clean-operation simplex, pC=pD=0. Coefficients are derived above.
    n = 241
    idle_x, write_y, delta_z = [], [], []
    for i in range(n):
        p_idle = i / (n - 1)
        for j in range(n - i):
            p_write = j / (n - 1)
            p_read = 1.0 - p_idle - p_write
            delta = mean_delta["IDLE"] * p_idle + mean_delta["READ_CLEAN"] * p_read + mean_delta["WRITE_CLEAN"] * p_write
            idle_x.append(p_idle)
            write_y.append(p_write)
            delta_z.append(delta)
    fig, ax = plt.subplots(figsize=(3.55, 2.45))
    tri = Polygon([[0, 0], [1, 0], [0, 1]], closed=True, fill=False, edgecolor="black", lw=1.0)
    ax.add_patch(tri)
    contour = ax.tricontourf(idle_x, write_y, delta_z, levels=[min(delta_z), 0, max(delta_z)], colors=["#8cc7e8", "#efb07a"], alpha=0.92)
    ax.tricontour(idle_x, write_y, delta_z, levels=[0], colors="black", linewidths=1.3)
    ax.text(0.08, 0.08, "Hsiao lower", fontsize=8, color="#163f5c")
    ax.text(0.44, 0.33, "Ext.-Hamming lower", fontsize=8, color="#71340d", rotation=-37)
    ax.text(0.015, 0.015, "$p_R=1$", ha="left", va="bottom", fontsize=7.5)
    ax.text(0.985, 0.015, "$p_I=1$", ha="right", va="bottom", fontsize=7.5)
    ax.text(0.015, 0.985, "$p_W=1$", ha="left", va="top", fontsize=7.5)
    ax.set_xlabel("Idle fraction $p_I$")
    ax.set_ylabel("Write fraction $p_W$")
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_aspect("equal", adjustable="box")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(pad=0.35)
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES / f"figure3_workload_boundary.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Claim-level provenance. One row per manuscript-facing derived quantity.
    prov = []
    prov.append(provenance_row("C01", "Four fully timing-clean matched seed pairs form the primary cohort.", "primary_seed_pair_count", len(primary_seeds), "pairs", "E4+E5", "10 ns; both setup and hold clean; five E5 operations present", [PHYSICAL, E5_MATRIX], "filter and inner join by architecture, clock, seed, operation"))
    prov.append(provenance_row("C02", "The primary cohort contains 40 E5 records and 20 matched operation comparisons.", "primary_e5_record_count", len(primary_seeds) * len(PAIR) * len(OPS), "records", "E5", "ECC logic only; SRAM macro internal energy excluded", [E5_MATRIX], "4 seeds x 2 architectures x 5 operations"))
    prov.append(provenance_row("C03", "Hsiao is lower energy in 4 of 20 primary comparisons.", "hsiao_lower_comparison_count", lower_count, "comparisons", "E5", "paired final-routed activity; ECC logic only", [E5_MATRIX], "count(energy_Hsiao - energy_SECDED < 0)"))
    for cid, op in zip(("C04a", "C04b", "C04c", "C04d", "C04e"), OPS):
        prov.append(provenance_row(cid, f"Mean Hsiao-minus-conventional energy delta for {OP_SHORT[op].lower()}.", f"mean_delta_{op.lower()}", f"{mean_delta[op]:+.9f}", "pJ/op", "E5", "four full-timing-clean seeds; ECC logic only", [E5_MATRIX, PHYSICAL], "arithmetic mean of paired per-seed energy differences"))
        prov.append(provenance_row(cid + "r", f"Seed range and Hsiao-lower count for {OP_SHORT[op].lower()}.", f"range_and_lower_count_{op.lower()}", f"[{min(deltas_pj[op]):+.9f},{max(deltas_pj[op]):+.9f}];{sum(v < 0 for v in deltas_pj[op])}/{len(deltas_pj[op])}", "pJ/op;count", "E5", "four full-timing-clean seeds; ECC logic only", [E5_MATRIX, PHYSICAL], "min/max paired delta; count(delta<0)"))
    prov.append(provenance_row("C05", "Mean Hsiao standard-cell-area delta in the primary cohort.", "standard_cell_area_delta", f"{physical_delta['standard_cell_area_um2']['mean']:+.6f}", "um^2", "E4", "routed wrapper/logic plus macro interfaces; macro area excluded", [PHYSICAL], "mean paired Hsiao-minus-conventional delta"))
    prov.append(provenance_row("C05b", "Mean Hsiao routed-wire delta in the primary cohort.", "routed_wirelength_delta", f"{physical_delta['wirelength_um']['mean']:+.6f}", "um", "E4", "routed wrapper/logic plus macro interfaces", [PHYSICAL], "mean paired Hsiao-minus-conventional delta"))
    prov.append(provenance_row("C05c", "Mean Hsiao via-count delta in the primary cohort.", "via_count_delta", f"{physical_delta['via_count']['mean']:+.6f}", "vias", "E4", "routed wrapper/logic plus macro interfaces", [PHYSICAL], "mean paired Hsiao-minus-conventional delta"))
    prov.append(provenance_row("C06", "Mean Hsiao setup-slack delta in the primary cohort.", "setup_wns_delta", f"{physical_delta['setup_wns_ns']['mean']:+.9f}", "ns", "E4", "10 ns target; four full-timing-clean seeds", [PHYSICAL], "mean paired Hsiao-minus-conventional delta"))
    prov.append(provenance_row("C07", "The routed BCH identity is setup-clean in 0/5 seeds at 10 ns.", "bch_setup_clean_count", setup_summary["BCH_78_64_T2"]["clean"], "of 5 seeds", "E4", "one named unpipelined BCH wrapper identity", [PHYSICAL, ARCH_AUDIT], "count(setup_wns_ns >= 0)"))
    prov.append(provenance_row("C08", "Mean BCH setup WNS is -11.112 ns at the 10 ns target.", "bch_mean_setup_wns", f"{bch_setup_mean:+.9f}", "ns", "E4", "five routed seeds; one named unpipelined BCH identity", [PHYSICAL], "arithmetic mean over five seeds"))
    prov.append(provenance_row("C09", "Hsiao seed 11 is hold-incomplete with negative WNS.", "hsiao_min_hold_wns", f"{h_hold_min:+.9f}", "ns", "E4", "10 ns target; five routed seeds", [PHYSICAL], "minimum hold WNS"))
    prov.append(provenance_row("C10", "The additive campaign contains 46 E5 records.", "campaign_e5_record_count", len(e5_matrix["records"]), "records", "E5", "ECC logic; includes partial-operation seed 11", [E5_MATRIX], "length(records)"))
    prov.append(provenance_row("C11", "All 72 required SRAM-output activity roots are annotated.", "annotated_required_root_count", status["activity_annotation_coverage"]["macro_output_roots_required_and_annotated"], "roots", "E5", "post-route zero-delay routed-netlist VCD boundary", [E5_STATUS, RUN_MANIFEST], "campaign status field"))
    prov.append(provenance_row("C12", "Each qualified record uses 256 measured operations.", "measured_operation_count", measured_operations, "operations/record", "E5", "after the recorded warm-up interval", [RUN_MANIFEST, WORKLOAD_MANIFEST], "unique exact_operation_count across the primary workload cohort"))
    prov.append(provenance_row("C13", "Every retained physical record reports zero route-DRC errors.", "route_drc_error_sum", sum(int(r["route_drc_errors"]) for r in physical), f"errors across {len(physical)} records", "E4", "final route reports; not independent foundry signoff", [PHYSICAL], "sum(route_drc_errors); count(rows)"))
    prov.append(provenance_row("C14", "The physical population spans four architectures, two targets, and five seeds.", "physical_population_shape", f"{len(ARCHS)}x{len({float(r['clock_period_ns']) for r in physical})}x{len(all_seeds)}={len(physical)}", "architectures x targets x seeds = records", "E4", "matched routed population", [PHYSICAL, ARCH_AUDIT], "count unique architecture, clock, seed and rows"))
    prov.append(provenance_row("C15", "Setup-clean seed counts at 10 ns for the four architecture identities.", "setup_clean_counts_10ns", ";".join(f"{a}:{setup_summary[a]['clean']}/5" for a in ARCHS), "seeds", "E4", "one named identity per architecture at 10 ns", [PHYSICAL], "count(setup_wns_ns>=0) by architecture"))
    prov.append(provenance_row("C16", "Named RTL dimensions and recorded correctness proof/regression boundaries.", "correctness_population", "SECDED:72/64 W1C W2D;HSIAO:72/64 W1C W2D;BCH:78/64 t2 W1-2C,3082 proofs", "bits;proof obligations", "E3", "named RTL only; no field-rate inference", [ARCH_AUDIT], "architecture-audit record fields and formal-evidence text"))
    prov.append(provenance_row("C17", "Activity records use 16 warm-up cycles.", "warmup_cycles", warmup_cycles, "cycles/record", "E5", "before the measured interval", [WORKLOAD_MANIFEST], "unique warm_up_cycles across the primary workload cohort"))
    prov.append(provenance_row("C18", "Physical analysis corner and targets.", "physical_conditions", "TT;25;1.80;5,10", "corner;degC;V;ns", "E4", "pinned SKY130HD flow", [RUN_MANIFEST, PHYSICAL], "manifest and unique target values"))
    prov.append(provenance_row("C19", "Inherited SRAM22 macro organization.", "macro_dimensions", "256x64;256x8", "words x bits", "E4_BOUNDARY", "inherited LEF/GDS/Liberty; incomplete macro energy and independent signoff", [ARCH_AUDIT], "architecture-audit sram_interface fields"))

    fields = list(prov[0].keys())
    with PROVENANCE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(prov)

    print(f"primary_seeds={primary_seeds}")
    print(f"primary_records={macros['PrimaryEfiveRecordCount']}")
    print(f"hsiao_lower={lower_count}/{comparisons}")
    for op in OPS:
        print(f"{op}={mean_delta[op]:+.6f} pJ/op")


if __name__ == "__main__":
    main()
