#!/usr/bin/env python3
"""Regenerate DATE 2027 figures, tables, macros, and claim provenance.

The qualified numerical transforms are shared with Revision 3 so the revision
cannot silently fork the established arithmetic. This script redirects those
outputs into this additive manuscript directory, replaces Figure 1 with the
revised identity diagram, and emits a per-seed result-provenance ledger.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(REPO / "tmp/date2027_revision_matplotlib"))

import matplotlib

matplotlib.use("pdf")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


UPSTREAM_SCRIPT = REPO / "paper/date2027_revision3/scripts/build_revision3.py"
SPEC = importlib.util.spec_from_file_location("date2027_revision3_builder", UPSTREAM_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot import {UPSTREAM_SCRIPT}")
UPSTREAM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPSTREAM)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def methodology_figure(path: Path) -> None:
    """Draw a one-column vector figure that exposes both non-transfer rules."""
    blue = "#0072B2"
    orange = "#D55E00"
    green = "#009E73"
    fig, ax = plt.subplots(figsize=(3.45, 4.30))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    stages = [
        (0.810, blue, "CODE IDENTITY", "payload/codeword mapping\ncorrection/detection semantics"),
        (0.580, orange, "HARDWARE IDENTITY", "RTL + interface + architecture\nlatency + initiation interval"),
        (0.350, green, "PHYSICAL IDENTITY", "library/corner + target + seed\nroute + SDC/SPEF + activity"),
        (0.120, "#4D4D4D", "ADMITTED EVIDENCE", "area + timing + routing\npower + energy"),
    ]
    for y, color, title, detail in stages:
        box = FancyBboxPatch(
            (0.10, y), 0.80, 0.170,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            facecolor="white", edgecolor=color, linewidth=1.2,
        )
        ax.add_patch(box)
        ax.text(0.50, y + 0.128, title, ha="center", va="center",
                fontsize=11.2, weight="bold", color=color)
        ax.text(0.50, y + 0.057, detail, ha="center", va="center", fontsize=10.0)

    for y in (0.780, 0.550, 0.320):
        ax.annotate("", xy=(0.50, y - 0.025), xytext=(0.50, y + 0.030),
                    arrowprops=dict(arrowstyle="-|>", lw=0.9, color="0.25"))

    fig.savefig(path, bbox_inches="tight", pad_inches=0.015)
    plt.close(fig)


def exact_effects_figure(path: Path, rev2: dict, structural: dict) -> list[dict[str, Any]]:
    """Draw the two exact-equivalence contrasts on one honest visual scale."""
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
        ("Temporal SECDED", [UPSTREAM.rev2_effect(rev2, key) for key in temporal_keys], "o", "#0072B2"),
        ("Structural Hsiao", [UPSTREAM.paired_effect(structural["paired_effects"], key) for key in structural_keys], "s", "#D55E00"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.62), sharey=True)
    rows: list[dict[str, Any]] = []
    offsets = [-0.12, -0.06, 0.0, 0.06, 0.12]
    for ax, (title, summaries, marker, color) in zip(axes, studies):
        for x, (label, summary) in enumerate(zip(labels, summaries)):
            items = sorted(summary["values_by_seed"].items(), key=lambda item: int(item[0]))
            values = [value for _, value in items]
            ax.scatter([x + off for off in offsets], values, s=22, marker=marker,
                       facecolor="none", edgecolor=color, linewidth=1.0, zorder=2)
            mean = summary["mean"]
            ax.errorbar(
                x, mean,
                yerr=[[mean - summary["minimum"]], [summary["maximum"] - mean]],
                fmt="D", ms=5.5, color=color, markerfacecolor=color,
                capsize=3.0, elinewidth=1.1, zorder=3,
            )
            for seed, value in items:
                rows.append({"study": title, "metric": label, "seed": int(seed), "percent": value})
        ax.axhline(0, color="0.25", lw=0.9)
        ax.set_title(title, fontsize=11.2, weight="bold")
        ax.set_xticks(range(4), ["Area\n(cost +)", "Wire\n(cost +)",
                                 "Timing\n(benefit +)", "Energy\n(cost +)"])
        ax.tick_params(labelsize=10.8)
        ax.grid(axis="y", color="0.88", linewidth=0.55)
        ax.set_ylim(-30, 60)
    axes[0].set_ylabel("Paired implementation effect (%)", fontsize=11.0)
    axes[1].text(0.98, 0.96, "Shared y-axis", transform=axes[1].transAxes,
                 ha="right", va="top", fontsize=10.2)
    fig.tight_layout(pad=0.75, w_pad=1.0)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return rows


def power_condition_figure(path: Path, rev2: dict, power: dict, condition: dict) -> list[dict[str, Any]]:
    """Use absolute power deltas for valid additive component accounting."""
    power_keys = [
        "internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w",
        "combinational_total_power_w", "sequential_total_power_w", "clock_total_power_w",
    ]
    power_labels = ["Int.", "Sw.", "Leak.", "Total", "Comb.", "Seq.", "Clk."]
    difference_mw = [
        power["paired_effects"][key]["absolute_difference"]["mean"] * 1000
        for key in power_keys
    ]
    percent_effects = [
        power["paired_effects"][key]["percent_effect"]["mean"]
        for key in power_keys
    ]
    temporal = [
        UPSTREAM.rev2_effect(rev2, "area_percent"),
        UPSTREAM.rev2_effect(rev2, "slack_derived_frequency_percent"),
        UPSTREAM.rev2_effect(rev2, "achievable_energy_percent"),
    ]
    five = [
        UPSTREAM.paired_effect(condition["within_5ns_paired_effects"], "standard_cell_instance_area_um2"),
        UPSTREAM.paired_effect(condition["within_5ns_paired_effects"], "slack_derived_frequency_mhz"),
        UPSTREAM.paired_effect(condition["within_5ns_paired_effects"], "energy_per_op_pj"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.72), gridspec_kw={"width_ratios": [1.38, 1.0]})
    ax = axes[0]
    colors = ["#E69F00", "#0072B2", "#999999", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]
    bars = ax.bar(range(len(difference_mw)), difference_mw, color=colors,
                  edgecolor="0.20", linewidth=0.55, width=0.68)
    for bar in bars:
        bar.set_hatch("//" if bar.get_height() > 0 else "")
    ax.axhline(0, color="black", lw=0.9)
    ax.axvline(3.5, color="0.45", lw=0.7, ls=":")
    ax.set_xticks(range(len(power_labels)), power_labels)
    ax.set_ylabel(r"Mean $\Delta$ power, pipe $-$ comb. (mW)", fontsize=10.8)
    ax.set_title("(a) 10 ns power accounting", fontsize=11.2, weight="bold")
    ax.tick_params(labelsize=10.2)
    ax.grid(axis="y", color="0.88", linewidth=0.55)
    ax.text(1.5, 0.98, "components", transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=10.0)
    ax.text(5.0, 0.98, "cell groups", transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=10.0)

    ax = axes[1]
    for x, (s10, s5) in enumerate(zip(temporal, five)):
        for summary, marker, color, offset, label in (
            (s10, "o", "#0072B2", -0.07, "10 ns"),
            (s5, "s", "#D55E00", 0.07, "5 ns"),
        ):
            mean = summary["mean"]
            ax.errorbar(
                x + offset, mean,
                yerr=[[mean - summary["minimum"]], [summary["maximum"] - mean]],
                fmt=marker, ms=5.4, color=color, capsize=2.8, elinewidth=1.0,
                label=label if x == 0 else None,
            )
    ax.axhline(0, color="black", lw=0.9)
    ax.set_xticks(range(3), ["Area\n(cost +)", "Timing\n(benefit +)", "Energy\n(cost +)"])
    ax.set_title("(b) Target-conditioned effect", fontsize=11.2, weight="bold")
    ax.tick_params(labelsize=10.2)
    ax.grid(axis="y", color="0.88", linewidth=0.55)
    ax.legend(fontsize=10.0, frameon=False, loc="upper left")
    fig.tight_layout(pad=0.75, w_pad=1.0)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    rows = [
        {"panel": "power", "metric": label, "mean_percent": percent}
        for label, percent in zip(power_labels, percent_effects)
    ]
    rows += [
        {"panel": target, "metric": label, "mean_percent": summary["mean"]}
        for target, summaries in (("10 ns", temporal), ("5 ns", five))
        for label, summary in zip(("Area", "Timing", "Energy"), summaries)
    ]
    return rows


def add_summary_rows(
    rows: list[dict[str, Any]], *, claim_id: str, paper_section: str,
    experiment: str, baseline: str, changed: str, condition: str,
    metric: str, summary: dict[str, Any], digits: int, unit: str,
    source: Path, qualification: str, sign: bool = False,
) -> None:
    for seed, value in sorted(summary.get("values_by_seed", {}).items(), key=lambda item: int(item[0])):
        rows.append({
            "claim_id": claim_id,
            "paper_section": paper_section,
            "experiment": experiment,
            "baseline_identity": baseline,
            "changed_identity": changed,
            "condition": condition,
            "seed": seed,
            "metric": metric,
            "raw_value": repr(value),
            "display_value": f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}",
            "unit": unit,
            "source_artifact": source.relative_to(REPO).as_posix(),
            "source_hash": sha256(source),
            "qualification_status": qualification,
        })
    value = summary.get("mean")
    rows.append({
        "claim_id": claim_id,
        "paper_section": paper_section,
        "experiment": experiment,
        "baseline_identity": baseline,
        "changed_identity": changed,
        "condition": condition,
        "seed": "aggregate_mean",
        "metric": metric,
        "raw_value": repr(value),
        "display_value": f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}",
        "unit": unit,
        "source_artifact": source.relative_to(REPO).as_posix(),
        "source_hash": sha256(source),
        "qualification_status": qualification,
    })


def scalar_row(
    rows: list[dict[str, Any]], *, claim_id: str, paper_section: str,
    experiment: str, baseline: str, changed: str, condition: str, seed: str,
    metric: str, raw: Any, display: str, unit: str, source: Path,
    qualification: str,
) -> None:
    rows.append({
        "claim_id": claim_id,
        "paper_section": paper_section,
        "experiment": experiment,
        "baseline_identity": baseline,
        "changed_identity": changed,
        "condition": condition,
        "seed": seed,
        "metric": metric,
        "raw_value": repr(raw),
        "display_value": display,
        "unit": unit,
        "source_artifact": source.relative_to(REPO).as_posix(),
        "source_hash": sha256(source),
        "qualification_status": qualification,
    })


def build_provenance() -> None:
    rev2_path = UPSTREAM.SOURCES["rev2"]
    env_path = UPSTREAM.SOURCES["environment"]
    structural_path = UPSTREAM.SOURCES["structural"]
    power_path = UPSTREAM.SOURCES["power"]
    condition_path = UPSTREAM.SOURCES["condition"]
    formal_path = UPSTREAM.SOURCES["formal"]
    synthesis_path = UPSTREAM.SOURCES["synthesis"]
    secded_contract_path = REPO / "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md"
    secded_proof_path = REPO / "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json"
    secded_encoder_path = REPO / "docs/date2027/rigour_gate_03r/ENCODER_PROOF_MATRIX.csv"
    secded_decoder_path = REPO / "docs/date2027/rigour_gate_03r/DECODER_PROOF_MATRIX.csv"
    energy_normalization_path = REPO / "docs/date2027/rigour_gate_05/GATE05_INTEGRATED_RESULTS.json"
    rev2 = load(rev2_path)
    env = load(env_path)
    structural = load(structural_path)
    power = load(power_path)
    condition = load(condition_path)
    formal = load(formal_path)
    synthesis = load(synthesis_path)
    secded_proof = load(secded_proof_path)
    energy_normalization = load(energy_normalization_path)["operation_normalization"]
    rows: list[dict[str, Any]] = []

    q = "QUALIFIED_MATCHED_PHYSICAL"
    sec_effects = {
        "area_percent": ("SEC10_AREA", "standard-cell area effect", 1),
        "detailed_wirelength_percent": ("SEC10_WIRE", "detailed-wire effect", 1),
        "slack_derived_frequency_percent": ("SEC10_TIMING", "signed-slack-derived frequency effect", 1),
        "achievable_energy_percent": ("SEC10_ENERGY", "energy/op effect", 1),
    }
    for key, (cid, label, digits) in sec_effects.items():
        add_summary_rows(
            rows, claim_id=cid, paper_section="Abstract; Results; Conclusion",
            experiment="Temporal SECDED", baseline="secded_comb",
            changed="secded_pipe", condition="10 ns", metric=label,
            summary=rev2["secded_paired"]["effects"][key]["summary"],
            digits=digits, unit="percent", source=rev2_path,
            qualification=q, sign=True,
        )

    absolute_specs = [
        ("standard_cell_instance_area_um2", "AREA_ABS", 0, "um2"),
        ("detailed_route_wirelength_um", "WIRE_ABS", 0, "um"),
        ("slack_derived_frequency_mhz", "TIMING_ABS", 1, "MHz"),
        ("achievable_no_error_energy_pj_per_operation", "ENERGY_ABS", 2, "pJ/op"),
    ]
    for architecture in ("secded_comb", "secded_pipe", "hsiao_algorithmic"):
        for key, suffix, digits, unit in absolute_specs:
            add_summary_rows(
                rows, claim_id=f"{architecture.upper()}_{suffix}",
                paper_section="Results", experiment="10 ns absolute scale",
                baseline=architecture, changed=architecture, condition="10 ns",
                metric=key, summary=rev2["architectures"][architecture]["metrics"][key],
                digits=digits, unit=unit, source=rev2_path, qualification=q,
            )

    hs_specs = [
        ("standard_cell_instance_area_um2", "HS_AREA", "area effect", 3),
        ("cell_count", "HS_CELLS", "cell-count effect", 3),
        ("detailed_route_wirelength_um", "HS_WIRE", "detailed-wire effect", 3),
        ("via_count", "HS_VIAS", "via-count effect", 3),
        ("slack_derived_frequency_mhz", "HS_TIMING", "signed-slack-derived frequency effect", 3),
        ("energy_per_op_pj", "HS_ENERGY", "energy/op effect", 3),
    ]
    for key, cid, label, digits in hs_specs:
        add_summary_rows(
            rows, claim_id=cid, paper_section="Abstract; Results; Conclusion",
            experiment="Structural Hsiao", baseline="hsiao_flat",
            changed="hsiao_hierarchical", condition="10 ns", metric=label,
            summary=structural["paired_effects"][key]["percent_effect"],
            digits=digits, unit="percent", source=structural_path,
            qualification=q, sign=True,
        )

    for arch in ("secded_comb", "secded_pipe"):
        for key, digits, unit in (
            ("internal_power_w", 4, "mW"),
            ("switching_power_w", 4, "mW"),
            ("leakage_power_w", 4, "nW"),
            ("total_power_w", 4, "mW"),
        ):
            source_summary = power["architecture_summary"][arch][key]
            factor = 1e9 if key == "leakage_power_w" else 1000
            converted = dict(source_summary)
            converted["mean"] = source_summary["mean"] * factor
            converted["values_by_seed"] = {
                seed: value * factor for seed, value in source_summary["values_by_seed"].items()
            }
            add_summary_rows(
                rows, claim_id=f"POWER_{arch.upper()}_{key.upper()}",
                paper_section="Results", experiment="SECDED power accounting",
                baseline=arch, changed=arch, condition="10 ns", metric=key,
                summary=converted, digits=digits, unit=unit, source=power_path,
                qualification="QUALIFIED_HASH_JOINED_POWER",
            )

    for key, cid in (
        ("internal_power_w", "POWER_EFFECT_INTERNAL"),
        ("switching_power_w", "POWER_EFFECT_SWITCHING"),
        ("leakage_power_w", "POWER_EFFECT_LEAKAGE"),
        ("total_power_w", "POWER_EFFECT_TOTAL"),
        ("combinational_total_power_w", "POWER_EFFECT_COMB_GROUP"),
        ("sequential_total_power_w", "POWER_EFFECT_SEQ_GROUP"),
        ("clock_total_power_w", "POWER_EFFECT_CLOCK_GROUP"),
    ):
        add_summary_rows(
            rows, claim_id=cid, paper_section="Abstract; Results",
            experiment="SECDED power accounting", baseline="secded_comb",
            changed="secded_pipe", condition="10 ns", metric=key,
            summary=power["paired_effects"][key]["percent_effect"], digits=2,
            unit="percent", source=power_path,
            qualification="QUALIFIED_HASH_JOINED_POWER", sign=True,
        )

    five_specs = [
        ("standard_cell_instance_area_um2", "SEC5_AREA", 1),
        ("cell_count", "SEC5_CELLS", 1),
        ("detailed_route_wirelength_um", "SEC5_WIRE", 1),
        ("via_count", "SEC5_VIAS", 1),
        ("slack_derived_frequency_mhz", "SEC5_TIMING", 1),
        ("energy_per_op_pj", "SEC5_ENERGY", 1),
    ]
    for key, cid, digits in five_specs:
        add_summary_rows(
            rows, claim_id=cid, paper_section="Abstract; Results; Conclusion",
            experiment="Temporal SECDED condition replication",
            baseline="secded_comb", changed="secded_pipe", condition="5 ns",
            metric=key + " effect", summary=condition["within_5ns_paired_effects"][key]["percent_effect"],
            digits=digits, unit="percent", source=condition_path,
            qualification=q, sign=True,
        )

    bch_metrics = [
        ("standard_cell_instance_area_um2", "BCH_AREA", 0, "um2"),
        ("slack_derived_frequency_mhz", "BCH_TIMING", 1, "MHz"),
        ("detailed_route_wirelength_um", "BCH_WIRE", 0, "um"),
        ("signed_worst_setup_slack_ns", "BCH_SLACK", 2, "ns"),
        ("setup_violation_count", "BCH_VIOLATIONS", 0, "violations"),
    ]
    for key, cid, digits, unit in bch_metrics:
        add_summary_rows(
            rows, claim_id=cid, paper_section="Results",
            experiment="BCH feasibility boundary", baseline="bch78",
            changed="bch78", condition="10 ns", metric=key,
            summary=rev2["architectures"]["bch78"]["metrics"][key],
            digits=digits, unit=unit, source=rev2_path,
            qualification="QUALIFIED_PHYSICAL_TARGET_INFEASIBLE",
        )
    scalar_row(
        rows, claim_id="BCH_FEASIBILITY", paper_section="Results; Conclusion",
        experiment="BCH feasibility boundary", baseline="bch78", changed="bch78",
        condition="10 ns", seed="aggregate", metric="target feasibility",
        raw=0, display=rev2["bch_10ns_feasibility"], unit="feasible runs",
        source=rev2_path, qualification="QUALIFIED_PHYSICAL_TARGET_INFEASIBLE",
    )

    scalar_row(
        rows, claim_id="SEED_SET", paper_section="Method",
        experiment="All matched physical studies", baseline="all", changed="all",
        condition="10 ns and 5 ns", seed="campaign", metric="physical seeds",
        raw=env["experimental_factor"]["values"],
        display=",".join(str(v) for v in env["experimental_factor"]["values"]),
        unit="seed IDs", source=env_path, qualification="PROSPECTIVELY_FROZEN",
    )
    scalar_row(
        rows, claim_id="TRACE_OPERATIONS", paper_section="Method",
        experiment="Activity-based energy", baseline="all", changed="all",
        condition="qualified no-error traces", seed="trace", metric="useful operations",
        raw=env["power"]["payload_operations"], display="100,000", unit="operations",
        source=env_path, qualification="QUALIFIED_TRACE",
    )
    scalar_row(
        rows, claim_id="SECDED_LATENCY", paper_section="Abstract; Method; Results",
        experiment="Temporal SECDED", baseline="secded_comb", changed="secded_pipe",
        condition="transaction contract", seed="hardware identity", metric="request latency",
        raw=[1, 3], display="1 vs 3", unit="cycles", source=env_path,
        qualification="PROVEN_TRANSACTION_RELATION",
    )
    scalar_row(
        rows, claim_id="HSIAO_FORMAL", paper_section="Method",
        experiment="Structural Hsiao", baseline="hsiao_flat", changed="hsiao_hierarchical",
        condition="arbitrary-word and temporal proof", seed="hardware identity",
        metric="formal status", raw=formal["formal_status"], display=formal["formal_status"],
        unit="status", source=formal_path, qualification="PROVEN",
    )
    for key, label in (("mapped_cell_count", "mapped cells"), ("register_count", "registers"), ("xor_xnor_count", "XOR/XNOR cells")):
        scalar_row(
            rows, claim_id=f"HSIAO_STRUCTURE_{key.upper()}", paper_section="Method; Results",
            experiment="Structural Hsiao", baseline="hsiao_flat", changed="hsiao_hierarchical",
            condition="common synthesis policy", seed="mapped netlists", metric=label,
            raw=[synthesis["baseline"][key], synthesis["new_hierarchical"][key]],
            display=f"{synthesis['baseline'][key]} vs {synthesis['new_hierarchical'][key]}",
            unit="cells", source=synthesis_path, qualification="QUALIFIED_STRUCTURAL_DISTINCTNESS",
        )

    scalar_row(
        rows, claim_id="SECDED_FORMAL", paper_section="Abstract; Method; Results; Conclusion",
        experiment="Temporal SECDED exact equivalence", baseline="secded_comb",
        changed="secded_pipe", condition="universal encoder/decoder proof",
        seed="hardware identity", metric="formal qualification",
        raw=secded_proof["status"], display=secded_proof["status"], unit="status",
        source=secded_proof_path, qualification="PROVEN",
    )
    scalar_row(
        rows, claim_id="SECDED_ENCODER_PROOF", paper_section="Method",
        experiment="Temporal SECDED exact equivalence", baseline="secded_comb",
        changed="secded_pipe", condition="all 64 payload bits plus affine proof",
        seed="hardware identity", metric="encoder proof matrix", raw="PASS",
        display="PASS", unit="status", source=secded_encoder_path,
        qualification="PROVEN",
    )
    scalar_row(
        rows, claim_id="SECDED_DECODER_PROOF", paper_section="Method",
        experiment="Temporal SECDED exact equivalence", baseline="secded_comb",
        changed="secded_pipe", condition="arbitrary 72-bit received word",
        seed="hardware identity", metric="decoder proof matrix", raw="PASS",
        display="PASS", unit="status", source=secded_decoder_path,
        qualification="PROVEN",
    )
    scalar_row(
        rows, claim_id="SECDED_ALIGNMENT", paper_section="Abstract; Method; Results",
        experiment="Temporal SECDED exact equivalence", baseline="secded_comb",
        changed="secded_pipe", condition="transaction boundary",
        seed="hardware identity", metric="response alignment", raw=2,
        display="2", unit="cycles", source=secded_contract_path,
        qualification="PROVEN_TRANSACTION_RELATION",
    )

    for key, cid, unit in (
        ("reset_cycles", "TRACE_RESET_CYCLES", "cycles"),
        ("drain_cycles", "TRACE_DRAIN_CYCLES", "cycles"),
        ("total_trace_cycles", "TRACE_TOTAL_CYCLES", "cycles"),
    ):
        scalar_row(
            rows, claim_id=cid, paper_section="Method",
            experiment="Activity normalization", baseline="all", changed="all",
            condition="common no-error trace", seed="trace", metric=key,
            raw=energy_normalization[key], display=f"{energy_normalization[key]:,}",
            unit=unit, source=energy_normalization_path, qualification="QUALIFIED_TRACE",
        )

    for key, cid, unit, scale, digits in (
        ("internal_power_w", "POWER_DELTA_INTERNAL", "mW", 1000, 4),
        ("switching_power_w", "POWER_DELTA_SWITCHING", "mW", 1000, 4),
        ("leakage_power_w", "POWER_DELTA_LEAKAGE", "nW", 1e9, 4),
        ("total_power_w", "POWER_DELTA_TOTAL", "mW", 1000, 4),
    ):
        summary = power["paired_effects"][key]["absolute_difference"]
        value = summary["mean"] * scale
        scalar_row(
            rows, claim_id=cid, paper_section="Results",
            experiment="SECDED absolute power accounting", baseline="secded_comb",
            changed="secded_pipe", condition="10 ns common no-error trace",
            seed="aggregate_mean", metric=f"{key} absolute difference",
            raw=value, display=f"{value:+.{digits}f}", unit=unit, source=power_path,
            qualification="QUALIFIED_HASH_JOINED_POWER",
        )

    fields = [
        "claim_id", "paper_section", "experiment", "baseline_identity",
        "changed_identity", "condition", "seed", "metric", "raw_value",
        "display_value", "unit", "source_artifact", "source_hash",
        "qualification_status",
    ]
    with (HERE / "RESULT_PROVENANCE.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def augment_generated_artifacts() -> None:
    """Add revision-only proof sources, macros, readable tables, and figure data."""
    proof_sources = {
        "secded_contract": REPO / "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md",
        "secded_proof": REPO / "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json",
        "secded_encoder_matrix": REPO / "docs/date2027/rigour_gate_03r/ENCODER_PROOF_MATRIX.csv",
        "secded_decoder_matrix": REPO / "docs/date2027/rigour_gate_03r/DECODER_PROOF_MATRIX.csv",
        "energy_normalization": REPO / "docs/date2027/rigour_gate_05/GATE05_INTEGRATED_RESULTS.json",
    }
    registry_path = HERE / "data/claim_registry.json"
    registry = load(registry_path)
    registry["sources"].update({
        name: {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path)}
        for name, path in proof_sources.items()
    })

    power = load(UPSTREAM.SOURCES["power"])
    environment = load(UPSTREAM.SOURCES["environment"])
    normalization = load(proof_sources["energy_normalization"])["operation_normalization"]
    extra_macros = {
        "PowerInternalDeltaMw": f"{power['paired_effects']['internal_power_w']['absolute_difference']['mean'] * 1000:.4f}",
        "PowerSwitchingDeltaMw": f"{power['paired_effects']['switching_power_w']['absolute_difference']['mean'] * 1000:.4f}",
        "PowerLeakageDeltaNw": f"{power['paired_effects']['leakage_power_w']['absolute_difference']['mean'] * 1e9:.4f}",
        "PowerTotalDeltaMw": f"{power['paired_effects']['total_power_w']['absolute_difference']['mean'] * 1000:.4f}",
        "PayloadSeed": str(environment["power"]["payload_seed"]),
        "ResetCycles": str(normalization["reset_cycles"]),
        "DrainCycles": str(normalization["drain_cycles"]),
        "TraceCycles": str(normalization["total_trace_cycles"]),
    }
    registry["macros"].update(extra_macros)
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (HERE / "data/generated_claims.tex").open("a", encoding="utf-8", newline="\n") as handle:
        for name, value in sorted(extra_macros.items()):
            handle.write(f"\\newcommand{{\\{name}}}{{{value}}}\n")

    matrix = [
        r"\begin{table*}[t]",
        r"\caption{Qualified identities. W1C/W2D: weight-1 correction/weight-2 detection; W1/2C: correction of both. Lat./II are cycles.}",
        r"\label{tab:matrix}",
        r"\centering\setlength{\tabcolsep}{4.0pt}",
        r"\begin{tabular}{@{}lcccccc@{}}",
        r"\toprule",
        r"Hardware identity & Guarantee & Lat. & II & Qualification & Target $\times$ seeds & Feasible \\",
        r"\midrule",
        r"SECDED comb. (72,64) & W1C/W2D & 1 & 1 & exact aligned pair & 10/5 ns $\times$ 5 & 5/5; 5/5 \\",
        r"SECDED pipe (72,64) & W1C/W2D & 3 & 1 & exact aligned pair & 10/5 ns $\times$ 5 & 5/5; 5/5 \\",
        r"Hsiao flat/hier. (72,64) & W1C/W2D & 1 & 1 & pairwise SAT + induction & 10 ns $\times$ 5 & 5/5 each \\",
        r"BCH (78,64,$t=2$) & W1/2C & 1 & 1 & guarantee qualified & 10 ns $\times$ 5 & 0/5 \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (HERE / "tables/identity_matrix.tex").write_text("\n".join(matrix) + "\n", encoding="utf-8", newline="\n")

    macros = registry["macros"]
    headline = [
        r"\begin{table*}[t]",
        r"\caption{Headline post-route results. Exact-equivalence rows are paired mean effects; BCH entries are absolute means because it changes guarantee and is target-infeasible.}",
        r"\label{tab:headline}",
        r"\centering\setlength{\tabcolsep}{5.0pt}",
        r"\begin{tabular}{@{}lcccp{2.25in}@{}}",
        r"\toprule",
        r"Study & Area & $f_{\mathrm{slack}}$ & Energy/op & Qualification and ordering \\",
        r"\midrule",
        f"Temporal SECDED, 10 ns & +{macros['SecAreaMean']}\\% & +{macros['SecFreqMean']}\\% & {macros['SecEnergyMean']}\\% & 5/5 directions; latency 1$\\rightarrow$3, II=1. \\\\",
        f"Structural Hsiao, 10 ns & {macros['HsAreaMean']}\\% & +{macros['HsFreqMean']}\\% & +{macros['HsEnergyMean']}\\% & Area/energy 5/5; timing 4/5 with one reversal. \\\\",
        f"Temporal SECDED, 5 ns & +{macros['FiveAreaMean']}\\% & +{macros['FiveFreqMean']}\\% & {macros['FiveEnergyMean']}\\% & Directions persist 5/5; magnitudes are target-conditioned. \\\\",
        f"BCH, 10 ns & {macros['BchArea']} $\\mu$m$^2$ & {macros['BchFreq']} MHz & -- & Stronger guarantee; setup feasible 0/5. \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (HERE / "tables/headline_results.tex").write_text("\n".join(headline) + "\n", encoding="utf-8", newline="\n")

    condition = load(UPSTREAM.SOURCES["condition"])
    rev2 = load(UPSTREAM.SOURCES["rev2"])
    power_labels = ["Internal", "Switching", "Leakage", "Total", "Combinational group", "Sequential group", "Clock group"]
    power_keys = ["internal_power_w", "switching_power_w", "leakage_power_w", "total_power_w",
                  "combinational_total_power_w", "sequential_total_power_w", "clock_total_power_w"]
    rows: list[dict[str, Any]] = []
    for label, key in zip(power_labels, power_keys):
        rows.append({
            "panel": "power", "metric": label,
            "mean_percent": power["paired_effects"][key]["percent_effect"]["mean"],
            "mean_mw": power["paired_effects"][key]["absolute_difference"]["mean"] * 1000,
        })
    for target, summaries in (
        ("10 ns", [UPSTREAM.rev2_effect(rev2, "area_percent"),
                   UPSTREAM.rev2_effect(rev2, "slack_derived_frequency_percent"),
                   UPSTREAM.rev2_effect(rev2, "achievable_energy_percent")]),
        ("5 ns", [UPSTREAM.paired_effect(condition["within_5ns_paired_effects"], "standard_cell_instance_area_um2"),
                  UPSTREAM.paired_effect(condition["within_5ns_paired_effects"], "slack_derived_frequency_mhz"),
                  UPSTREAM.paired_effect(condition["within_5ns_paired_effects"], "energy_per_op_pj")]),
    ):
        for label, summary in zip(("Area", "Timing", "Energy"), summaries):
            rows.append({"panel": target, "metric": label, "mean_percent": summary["mean"], "mean_mw": ""})
    with (HERE / "data/figure03_power_condition.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["panel", "metric", "mean_percent", "mean_mw"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    UPSTREAM.HERE = HERE
    UPSTREAM.methodology_figure = methodology_figure
    UPSTREAM.exact_effects_figure = exact_effects_figure
    UPSTREAM.power_condition_figure = power_condition_figure
    result = UPSTREAM.main()
    augment_generated_artifacts()
    build_provenance()
    print("DATE2027_REVISION_ARTIFACTS_BUILT")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
