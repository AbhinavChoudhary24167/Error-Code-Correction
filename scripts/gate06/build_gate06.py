#!/usr/bin/env python3
"""Build the DATE 2027 Gate 06 exact-enumeration design-space analysis."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
GATE05 = ROOT / "docs/date2027/rigour_gate_05"
DEFAULT_OUT = ROOT / "docs/date2027/rigour_gate_06"

AUTHORITATIVE_INPUTS = (
    "GATE05_IMPLEMENTATION_IDENTITY.json",
    "GATE05_RELIABILITY_SOURCE_MAP.json",
    "GATE05_INTEGRATED_RESULTS.csv",
    "GATE05_INTEGRATED_RESULTS.json",
    "GATE05_DERIVED_METRICS.json",
    "GATE05_MISSING_EVIDENCE.json",
    "GATE05_CLAIM_CANDIDATES.md",
    "GATE05_ADJUDICATION.md",
)

COMB = "secded-rtl-combinational-72-64-v1"
PIPE = "secded-rtl-pipelined-72-64-v1"
HSIAO = "hsiao-generated-combinational-72-64-v1"
BCH = "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"
ORDER = (COMB, PIPE, HSIAO, BCH)

SHORT_LABELS = {
    COMB: "SECDED\ncombinational",
    PIPE: "SECDED\npipelined",
    HSIAO: "Hsiao\nSECDED",
    BCH: "BCH (78,64,t=2)",
}

COLORS = {
    COMB: "#3569b8",
    PIPE: "#e58b2a",
    HSIAO: "#6d56a3",
    BCH: "#b44343",
    "sdc": "#b44343",
    "due": "#4f83a5",
    "neutral": "#555555",
    "grid": "#d5d5d5",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def pct(value: float, reference: float) -> float:
    return (value - reference) / reference * 100.0


def ratio_percent(value: float, reference: float) -> float:
    return value / reference * 100.0


def no_error(record: dict[str, Any]) -> dict[str, Any] | None:
    return record["power_by_trace"]["no_error"]


def is_routed(record: dict[str, Any]) -> bool:
    return record["physical"]["routing_complete"] is True


def is_timing_feasible(record: dict[str, Any]) -> bool:
    return record["physical"]["timing_feasibility"] == "MEETS_10NS"


def guarantee_tier(implementation_id: str) -> str:
    if implementation_id == BCH:
        return "W1_AND_W2_CORRECTION"
    return "W1_CORRECTION_W2_DETECTION"


def verify_gate05() -> dict[str, str]:
    manifest: dict[str, str] = {}
    for line in (GATE05 / "GATE05_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        manifest[relative.removeprefix("./")] = expected
    assert set(AUTHORITATIVE_INPUTS) == set(manifest)
    for name in AUTHORITATIVE_INPUTS:
        assert sha256(GATE05 / name) == manifest[name]
    return manifest


def dominates(
    left: dict[str, float], right: dict[str, float], objectives: Iterable[dict[str, str]]
) -> bool:
    no_worse = True
    strictly_better = False
    for objective in objectives:
        metric = objective["metric"]
        direction = objective["direction"]
        lv, rv = left[metric], right[metric]
        if direction == "minimize":
            no_worse &= lv <= rv
            strictly_better |= lv < rv
        elif direction == "maximize":
            no_worse &= lv >= rv
            strictly_better |= lv > rv
        else:
            raise ValueError(direction)
    return bool(no_worse and strictly_better)


def enumerate_dominance(
    points: dict[str, dict[str, float]], objectives: list[dict[str, str]]
) -> dict[str, Any]:
    pairs = []
    dominated_by = {identifier: [] for identifier in points}
    for left_id, left in points.items():
        for right_id, right in points.items():
            if left_id != right_id and dominates(left, right, objectives):
                pairs.append({"dominator": left_id, "dominated": right_id})
                dominated_by[right_id].append(left_id)
    return {
        "objectives": objectives,
        "points": points,
        "dominance_pairs": pairs,
        "nondominated": [identifier for identifier in points if not dominated_by[identifier]],
        "dominated_by": dominated_by,
        "method": "exact pairwise enumeration; no optimizer or heuristic",
    }


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.titlesize": 11,
            "axes.linewidth": 0.7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "green-ecc-date2027-gate06",
        }
    )


def save_figure(fig: Any, base: Path) -> None:
    fig.savefig(
        base.with_suffix(".svg"),
        bbox_inches="tight",
        metadata={"Date": None, "Creator": "GREEN-ECC Gate 06 deterministic analysis"},
    )
    fig.savefig(
        base.with_suffix(".pdf"),
        bbox_inches="tight",
        metadata={"CreationDate": None, "ModDate": None, "Creator": "GREEN-ECC Gate 06"},
    )
    fig.savefig(
        base.with_suffix(".png"),
        bbox_inches="tight",
        dpi=300,
        metadata={"Software": "GREEN-ECC Gate 06 deterministic analysis"},
    )
    plt.close(fig)


def figure_methodology(figures: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.15, 2.25))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    nodes = [
        (0.02, "Correctness\nidentity", "Gates 02 / 03R"),
        (0.21, "Reliability\nevidence", "Exact W1/W2/W3\nuniverses"),
        (0.40, "RTL\narchitecture", "Latency and II\npreserved"),
        (0.59, "Frozen physical\nimplementation", "Gate 04\nSKY130HD"),
        (0.78, "Comparison\nspaces A/B/C", "Missing-data\naware"),
    ]
    width, height = 0.16, 0.42
    for x, title, subtitle in nodes:
        patch = FancyBboxPatch(
            (x, 0.40), width, height,
            boxstyle="round,pad=0.012,rounding_size=0.012",
            facecolor="#f5f7fa", edgecolor="#52606d", linewidth=0.9,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, 0.68, title, ha="center", va="center", weight="bold")
        ax.text(x + width / 2, 0.49, subtitle, ha="center", va="center", fontsize=6.8, color="#444444")
    for left, right in zip(nodes[:-1], nodes[1:]):
        arrow = FancyArrowPatch(
            (left[0] + width + 0.005, 0.61), (right[0] - 0.005, 0.61),
            arrowstyle="-|>", mutation_scale=9, linewidth=0.9, color="#52606d",
        )
        ax.add_patch(arrow)
    ax.text(
        0.50, 0.21,
        "Hsiao stops at reliability-only (PPA unavailable)  •  BCH remains routed but target-clock energy is infeasible",
        ha="center", va="center", fontsize=7.6,
    )
    ax.text(
        0.50, 0.08,
        "Outputs: exact effect sizes, stratified dominance, paper tables, and bounded claims",
        ha="center", va="center", fontsize=7.6, color="#444444",
    )
    ax.set_title("Evidence-preserving cross-layer analysis", pad=4)
    save_figure(fig, figures / "F01_CROSS_LAYER_METHOD")


def figure_area_fmax(figures: Path, records: dict[str, dict[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(5.8, 3.65))
    routed = [records[item] for item in (COMB, PIPE, BCH)]
    for record in routed:
        identifier = record["implementation_id"]
        metrics = record["physical"]["metrics"]
        marker = "X" if identifier == BCH else "o"
        ax.scatter(
            metrics["standard_cell_instance_area_um2"] / 1000.0,
            metrics["achieved_fmax_mhz"],
            s=76, marker=marker, color=COLORS[identifier], edgecolor="white", linewidth=0.7, zorder=3,
        )
        label = SHORT_LABELS[identifier].replace("\n", " ")
        suffix = "\nFAILS 10 ns" if identifier == BCH else ""
        if identifier == BCH:
            offset = (-116, 10)
        elif identifier == PIPE:
            offset = (7, -18)
        else:
            offset = (7, 7)
        ax.annotate(
            label + suffix,
            (metrics["standard_cell_instance_area_um2"] / 1000.0, metrics["achieved_fmax_mhz"]),
            xytext=offset, textcoords="offset points", fontsize=7.6,
        )
    ax.axhline(100.0, color="#555555", linestyle="--", linewidth=0.9)
    ax.text(58.0, 104.0, "100 MHz target", ha="right", va="bottom", fontsize=7.5, color="#444444")
    ax.set_xlabel("Final standard-cell instance area (10³ µm²)")
    ax.set_ylabel("Achieved Fmax (MHz)")
    ax.set_xlim(16.5, 61.0)
    ax.set_ylim(50.0, 380.0)
    ax.set_title("Area–performance trade-off under the common physical policy")
    ax.grid(True, color=COLORS["grid"], linewidth=0.55, alpha=0.8)
    ax.set_axisbelow(True)
    ax.text(
        0.01, -0.21, "Hsiao: PPA_UNAVAILABLE (not plotted). BCH remains a routed physical point.",
        transform=ax.transAxes, fontsize=7.4,
    )
    save_figure(fig, figures / "F02_AREA_VS_FMAX")


def figure_normalized_cost(figures: Path, records: dict[str, dict[str, Any]]) -> None:
    reference = records[COMB]
    ref_m = reference["physical"]["metrics"]
    ref_p = no_error(reference)["metrics"]
    metrics = [
        ("Area ↓", "physical", "standard_cell_instance_area_um2"),
        ("Wirelength ↓", "physical", "detailed_route_wirelength_um"),
        ("Fmax ↑", "physical", "achieved_fmax_mhz"),
        ("Power ↓", "power", "total_power_w"),
        ("Energy/op ↓", "power", "achievable_total_energy_pj_per_operation"),
    ]
    x = list(range(len(metrics)))
    width = 0.22
    fig, ax = plt.subplots(figsize=(7.15, 3.75))
    for series_index, identifier in enumerate((COMB, PIPE, BCH)):
        record = records[identifier]
        values: list[float | None] = []
        for _, group, key in metrics:
            if group == "physical":
                values.append(ratio_percent(record["physical"]["metrics"][key], ref_m[key]))
            else:
                row = no_error(record)
                value = row["metrics"][key] if row and is_timing_feasible(record) else None
                reference_value = ref_p[key]
                values.append(ratio_percent(value, reference_value) if value is not None else None)
        positions = [item + (series_index - 1) * width for item in x]
        for position, value in zip(positions, values):
            if value is not None:
                bar = ax.bar(position, value, width, color=COLORS[identifier], label=None, zorder=2)[0]
                ax.text(
                    bar.get_x() + bar.get_width() / 2, value + 7,
                    f"{value:.0f}", ha="center", va="bottom", fontsize=6.8, rotation=90,
                )
            elif identifier == BCH:
                ax.text(
                    position, 8, "TARGET\nCLOCK\nINFEASIBLE", ha="center", va="bottom",
                    fontsize=6.1, rotation=90, color=COLORS[BCH],
                )
        ax.bar([], [], color=COLORS[identifier], label=SHORT_LABELS[identifier].replace("\n", " "))
    ax.axhline(100.0, color="#555555", linestyle="--", linewidth=0.8)
    ax.set_xticks(x, [item[0] for item in metrics])
    ax.set_ylabel("Percent of combinational SECDED reference")
    ax.set_ylim(0, 455)
    ax.set_title("Normalized physical effects (reference = 100%)")
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.55)
    ax.set_axisbelow(True)
    handles = [
        Patch(facecolor=COLORS[identifier], label=SHORT_LABELS[identifier].replace("\n", " "))
        for identifier in (COMB, PIPE, BCH)
    ]
    ax.legend(handles=handles, frameon=False, ncol=1, loc="upper right")
    ax.text(
        0.01, -0.22,
        "BCH power is a target-constraint diagnostic and its achievable energy is unavailable; Hsiao PPA is unavailable.",
        transform=ax.transAxes, fontsize=7.2,
    )
    save_figure(fig, figures / "F03_NORMALIZED_PHYSICAL_COST")


def figure_reliability(figures: Path, records: dict[str, dict[str, Any]]) -> None:
    code_records = [records[COMB], records[HSIAO], records[BCH]]
    labels = [
        "Conventional SECDED\nW1 correct; W2 detect\n(shared by two architectures)",
        "Hsiao SECDED\nW1 correct; W2 detect",
        "BCH (78,64,t=2)\nW1/W2 correct",
    ]
    sdc = []
    due = []
    for record in code_records:
        w3 = record["reliability"]["exact_fault_universes"][3]
        sdc.append(float(Fraction(w3["sdc_fraction"])) * 100.0)
        due.append(float(Fraction(w3["due_fraction"])) * 100.0)
    x = list(range(3))
    fig, ax = plt.subplots(figsize=(6.7, 3.8))
    ax.bar(x, sdc, color=COLORS["sdc"], label="SDC miscorrection observation")
    ax.bar(x, due, bottom=sdc, color=COLORS["due"], label="DUE observation")
    for index, (sdc_value, due_value) in enumerate(zip(sdc, due)):
        ax.text(index, sdc_value / 2, f"SDC\n{sdc_value:.1f}%", ha="center", va="center", color="white", fontsize=7.4)
        ax.text(index, sdc_value + due_value / 2, f"DUE\n{due_value:.1f}%", ha="center", va="center", color="white", fontsize=7.4)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 103)
    ax.set_ylabel("Share of exhaustive weight-3 masks (%)")
    ax.set_title("Reliability-only comparison: weight-3 outcome composition")
    ax.text(
        0.01, -0.25,
        "Canonical-coordinate observations only—not operational probabilities or correction guarantees. Hsiao PPA: unavailable.",
        transform=ax.transAxes, fontsize=7.2,
    )
    save_figure(fig, figures / "F04_RELIABILITY_OUTCOMES")


def physical_values(record: dict[str, Any]) -> dict[str, Any]:
    metrics = record["physical"]["metrics"]
    return {
        "area_um2": metrics["standard_cell_instance_area_um2"],
        "cell_count": metrics["cell_count"],
        "wirelength_um": metrics["detailed_route_wirelength_um"],
        "fmax_mhz": metrics["achieved_fmax_mhz"],
        "timing_deficit_ns": metrics["timing_deficit_ns"],
        "wns_ns": metrics["wns_ns"],
        "latency_cycles": record["architecture"]["nominal_operation_latency_cycles"],
    }


def effect_comparison(
    label: str, candidate: dict[str, Any], reference: dict[str, Any], allow_energy: bool
) -> dict[str, Any]:
    cm, rm = candidate["physical"]["metrics"], reference["physical"]["metrics"]
    metrics = {}
    for key in (
        "standard_cell_instance_area_um2",
        "cell_count",
        "detailed_route_wirelength_um",
        "achieved_fmax_mhz",
    ):
        metrics[key] = {
            "candidate_raw": cm[key],
            "reference_raw": rm[key],
            "absolute_change": cm[key] - rm[key],
            "percent_change": pct(cm[key], rm[key]),
        }
    metrics["timing_deficit_ns"] = {
        "candidate_raw": cm["timing_deficit_ns"],
        "reference_raw": rm["timing_deficit_ns"],
        "absolute_change": cm["timing_deficit_ns"] - rm["timing_deficit_ns"],
        "percent_change": None,
        "percent_missing_reason": "NOT_APPLICABLE_ZERO_REFERENCE",
    }
    metrics["wns_ns"] = {
        "candidate_raw": cm["wns_ns"],
        "reference_raw": rm["wns_ns"],
        "absolute_change": cm["wns_ns"] - rm["wns_ns"],
        "percent_change": None,
        "percent_missing_reason": "NOT_APPLICABLE_SLACK_RATIO",
    }
    candidate_latency = candidate["architecture"]["nominal_operation_latency_cycles"]
    reference_latency = reference["architecture"]["nominal_operation_latency_cycles"]
    metrics["nominal_operation_latency_cycles"] = {
        "candidate_raw": candidate_latency,
        "reference_raw": reference_latency,
        "absolute_change": candidate_latency - reference_latency,
        "percent_change": pct(candidate_latency, reference_latency),
    }
    for key in ("total_power_w", "achievable_total_energy_pj_per_operation"):
        candidate_power = no_error(candidate)
        reference_power = no_error(reference)
        candidate_value = candidate_power["metrics"][key] if candidate_power else None
        reference_value = reference_power["metrics"][key] if reference_power else None
        if allow_energy and candidate_value is not None and reference_value is not None:
            metrics[f"no_error_{key}"] = {
                "candidate_raw": candidate_value,
                "reference_raw": reference_value,
                "absolute_change": candidate_value - reference_value,
                "percent_change": pct(candidate_value, reference_value),
            }
        else:
            metrics[f"no_error_{key}"] = {
                "candidate_raw": candidate_value,
                "reference_raw": reference_value,
                "absolute_change": None,
                "percent_change": None,
                "missing_reason": "TARGET_CLOCK_INFEASIBLE" if candidate_power else "PPA_UNAVAILABLE",
            }
    return {
        "comparison": label,
        "candidate_implementation_id": candidate["implementation_id"],
        "reference_implementation_id": reference["implementation_id"],
        "metrics": metrics,
        "correction_guarantee_context": {
            "candidate": guarantee_tier(candidate["implementation_id"]),
            "reference": guarantee_tier(reference["implementation_id"]),
            "categorical_not_numerically_scored": True,
        },
    }


def build(out: Path) -> None:
    gate05_hashes = verify_gate05()
    integrated = load_json(GATE05 / "GATE05_INTEGRATED_RESULTS.json")
    identity = load_json(GATE05 / "GATE05_IMPLEMENTATION_IDENTITY.json")
    records = {row["implementation_id"]: row for row in integrated["records"]}
    assert tuple(records) == ORDER
    assert identity["operation_normalization"] == integrated["operation_normalization"]
    out.mkdir(parents=True, exist_ok=True)
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    policy = {
        "schema_version": 1,
        "gate": "DATE 2027 Gate 06 design-space trade-off and Pareto analysis",
        "authoritative_input_policy": {
            "gate05_only": True,
            "gate05_artifacts": [
                {
                    "path": f"docs/date2027/rigour_gate_05/{name}",
                    "sha256": gate05_hashes[name],
                }
                for name in AUTHORITATIVE_INPUTS
            ],
            "gate05_evidence_manifest_sha256": sha256(GATE05 / "GATE05_EVIDENCE.sha256"),
            "new_physical_runs": False,
            "stale_thesis_results_imported": False,
        },
        "reliability_semantics": {
            "correction_guarantees_are_categorical": True,
            "weight3_sdc_due": "exhaustive canonical-coordinate observations only",
            "not_operational_probability": True,
            "not_fit_ser": True,
            "not_weight3_correction_guarantee": True,
            "generic_reliability_score_forbidden": True,
        },
        "comparison_spaces": {
            "A_FULL_PHYSICALLY_FEASIBLE": {
                "members": [COMB, PIPE],
                "exclusions": {
                    HSIAO: "PPA_UNAVAILABLE",
                    BCH: "TARGET_CLOCK_INFEASIBLE_FOR_ACHIEVABLE_ENERGY",
                },
            },
            "B_PHYSICAL_IMPLEMENTATION": {
                "members": [COMB, PIPE, BCH],
                "exclusions": {HSIAO: "PPA_UNAVAILABLE"},
            },
            "C_RELIABILITY_ONLY": {
                "members": [COMB, PIPE, HSIAO, BCH],
                "physical_comparability_implied": False,
            },
        },
        "dominance_definition": "x dominates y iff x is no worse in every enumerated objective and strictly better in at least one",
        "nsga_ii_adjudication": {
            "decision": "NOT_USED_NO_SCIENTIFIC_VALUE",
            "reason": "four discrete measured architecture identities, three routed points, two timing-feasible energy points, and no combinatorial configuration space; exact enumeration is complete",
        },
        "power_energy_policy": {
            "headline_trace": "no_error",
            "all_trace_classes_retained_upstream": True,
            "bch_target_constraint_power_role": "DIAGNOSTIC_ONLY",
            "bch_achievable_energy": "TARGET_CLOCK_INFEASIBLE",
            "hsiao": "PPA_UNAVAILABLE",
        },
        "figure_policy": {
            "formats": ["SVG", "PDF", "PNG preview"],
            "source": "programmatic authoritative Gate 05 values",
            "decorative_figures": False,
            "missing_values_plotted_as_zero_or_infinity": False,
        },
    }
    write_json(out / "GATE06_ANALYSIS_POLICY.json", policy)

    effects = {
        "schema_version": 1,
        "formula": "(candidate - reference) / reference * 100%",
        "source": "docs/date2027/rigour_gate_05/GATE05_INTEGRATED_RESULTS.json",
        "comparisons": [
            effect_comparison("pipelined SECDED vs combinational SECDED", records[PIPE], records[COMB], True),
            effect_comparison("BCH vs combinational SECDED", records[BCH], records[COMB], False),
            effect_comparison("BCH vs pipelined SECDED", records[BCH], records[PIPE], False),
        ],
        "rules": {
            "slack_ratios": "NOT_APPLICABLE",
            "zero_reference_ratios": "NOT_APPLICABLE",
            "bch_energy_effect": "TARGET_CLOCK_INFEASIBLE",
            "rounded_prose_is_not_an_input": True,
        },
    }
    write_json(out / "GATE06_EFFECT_SIZES.json", effects)

    space_a_objectives = [
        {"metric": "area_um2", "direction": "minimize"},
        {"metric": "wirelength_um", "direction": "minimize"},
        {"metric": "achievable_energy_pj_per_operation", "direction": "minimize"},
        {"metric": "latency_cycles", "direction": "minimize"},
        {"metric": "fmax_mhz", "direction": "maximize"},
    ]
    space_a_points = {}
    for identifier in (COMB, PIPE):
        record = records[identifier]
        metrics = record["physical"]["metrics"]
        space_a_points[identifier] = {
            "area_um2": metrics["standard_cell_instance_area_um2"],
            "wirelength_um": metrics["detailed_route_wirelength_um"],
            "achievable_energy_pj_per_operation": no_error(record)["metrics"]["achievable_total_energy_pj_per_operation"],
            "latency_cycles": record["architecture"]["nominal_operation_latency_cycles"],
            "fmax_mhz": metrics["achieved_fmax_mhz"],
        }
    space_a = enumerate_dominance(space_a_points, space_a_objectives)
    space_a.update(
        {
            "space": "A_FULL_PHYSICALLY_FEASIBLE",
            "interpretation": "Neither SECDED architecture dominates: combinational is better in area, wirelength, and latency; pipelined is better in Fmax and achievable steady-stream energy.",
        }
    )

    space_b_objectives = [
        {"metric": "area_um2", "direction": "minimize"},
        {"metric": "cell_count", "direction": "minimize"},
        {"metric": "wirelength_um", "direction": "minimize"},
        {"metric": "timing_deficit_ns", "direction": "minimize"},
        {"metric": "latency_cycles", "direction": "minimize"},
        {"metric": "fmax_mhz", "direction": "maximize"},
    ]
    space_b_points = {identifier: physical_values(records[identifier]) for identifier in (COMB, PIPE, BCH)}
    space_b = enumerate_dominance(space_b_points, space_b_objectives)
    space_b.update(
        {
            "space": "B_PHYSICAL_IMPLEMENTATION",
            "reliability_agnostic_physical_dominance_only": True,
            "interpretation": "Combinational SECDED physically dominates BCH on this objective set. This cannot override BCH's stronger categorical correction guarantee.",
        }
    )
    no_latency_objectives = [item for item in space_b_objectives if item["metric"] != "latency_cycles"]
    space_b_sensitivity = enumerate_dominance(space_b_points, no_latency_objectives)
    space_b_sensitivity.update(
        {
            "space": "B_PHYSICAL_IMPLEMENTATION_LATENCY_EXCLUDED_SENSITIVITY",
            "interpretation": "When latency is excluded, both SECDED physical points dominate BCH; this sensitivity is reported, not substituted for the primary set.",
        }
    )

    secded_reliability_points = {}
    for identifier in (COMB, PIPE, HSIAO):
        w3 = records[identifier]["reliability"]["exact_fault_universes"][3]
        secded_reliability_points[identifier] = {
            "weight3_sdc_fraction": float(Fraction(w3["sdc_fraction"])),
            "weight3_due_fraction": float(Fraction(w3["due_fraction"])),
        }
    reliability_objectives = [
        {"metric": "weight3_sdc_fraction", "direction": "minimize"},
        {"metric": "weight3_due_fraction", "direction": "minimize"},
    ]
    secded_reliability = enumerate_dominance(secded_reliability_points, reliability_objectives)
    secded_reliability.update(
        {
            "guarantee_tier": "W1_CORRECTION_W2_DETECTION",
            "interpretation": "No strict dominance: conventional architectures are identical reliability points; Hsiao trades lower observed SDC for higher DUE.",
        }
    )
    bch_w3 = records[BCH]["reliability"]["exact_fault_universes"][3]
    bch_reliability = enumerate_dominance(
        {
            BCH: {
                "weight3_sdc_fraction": float(Fraction(bch_w3["sdc_fraction"])),
                "weight3_due_fraction": float(Fraction(bch_w3["due_fraction"])),
            }
        },
        reliability_objectives,
    )
    bch_reliability.update(
        {
            "guarantee_tier": "W1_AND_W2_CORRECTION",
            "interpretation": "Singleton exact front; no optimization inference.",
        }
    )
    dominance = {
        "schema_version": 1,
        "formal_definition": policy["dominance_definition"],
        "exact_enumeration": True,
        "nsga_ii_used": False,
        "spaces": [space_a, space_b, space_b_sensitivity],
        "reliability_stratified": {
            "cross_tier_dominance_computed": False,
            "reason": "correction guarantees are categorical and are not converted into a numerical reliability score",
            "fronts": [secded_reliability, bch_reliability],
        },
        "hsiao_physical_rule": "PPA_UNAVAILABLE; excluded from every physical-objective front",
        "bch_energy_rule": "TARGET_CLOCK_INFEASIBLE; excluded from achievable-energy fronts",
    }
    write_json(out / "GATE06_DOMINANCE_ANALYSIS.json", dominance)

    design_fields = [
        "implementation_id", "architecture", "guarantee_tier", "space_a_member", "space_b_member",
        "space_c_member", "area_um2", "cell_count", "wirelength_um", "fmax_mhz", "wns_ns",
        "timing_deficit_ns", "feasible_10ns", "no_error_power_w", "achievable_energy_pj_per_operation",
        "latency_cycles", "initiation_interval_cycles", "full_physical_pareto_eligible",
    ]
    with (out / "GATE06_DESIGN_SPACE.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=design_fields, lineterminator="\n")
        writer.writeheader()
        for identifier in ORDER:
            record = records[identifier]
            physical = record["physical"]
            metrics = physical["metrics"]
            routed = is_routed(record)
            power = no_error(record)
            writer.writerow(
                {
                    "implementation_id": identifier,
                    "architecture": record["label"],
                    "guarantee_tier": guarantee_tier(identifier),
                    "space_a_member": str(identifier in (COMB, PIPE)).lower(),
                    "space_b_member": str(identifier in (COMB, PIPE, BCH)).lower(),
                    "space_c_member": "true",
                    "area_um2": metrics["standard_cell_instance_area_um2"] if routed else "PPA_UNAVAILABLE",
                    "cell_count": metrics["cell_count"] if routed else "PPA_UNAVAILABLE",
                    "wirelength_um": metrics["detailed_route_wirelength_um"] if routed else "PPA_UNAVAILABLE",
                    "fmax_mhz": metrics["achieved_fmax_mhz"] if routed else "PPA_UNAVAILABLE",
                    "wns_ns": metrics["wns_ns"] if routed else "PPA_UNAVAILABLE",
                    "timing_deficit_ns": metrics["timing_deficit_ns"] if routed else "PPA_UNAVAILABLE",
                    "feasible_10ns": physical["timing_feasibility"],
                    "no_error_power_w": power["metrics"]["total_power_w"] if power else "PPA_UNAVAILABLE",
                    "achievable_energy_pj_per_operation": (
                        "PPA_UNAVAILABLE" if not power else
                        "TARGET_CLOCK_INFEASIBLE" if power["metrics"]["achievable_total_energy_pj_per_operation"] is None else
                        power["metrics"]["achievable_total_energy_pj_per_operation"]
                    ),
                    "latency_cycles": record["architecture"]["nominal_operation_latency_cycles"],
                    "initiation_interval_cycles": record["architecture"]["initiation_interval_cycles"],
                    "full_physical_pareto_eligible": str(identifier in (COMB, PIPE)).lower(),
                }
            )

    reliability_fields = [
        "implementation_id", "architecture", "code_parameters", "guarantee_tier", "weight1_behavior",
        "weight2_behavior", "weight3_total_observations", "weight3_sdc_count", "weight3_sdc_fraction",
        "weight3_due_count", "weight3_due_fraction", "weight3_caveat", "physical_availability",
    ]
    with (out / "GATE06_RELIABILITY_TABLE.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=reliability_fields, lineterminator="\n")
        writer.writeheader()
        for identifier in ORDER:
            record = records[identifier]
            universes = record["reliability"]["exact_fault_universes"]
            w1, w2, w3 = universes[1], universes[2], universes[3]
            writer.writerow(
                {
                    "implementation_id": identifier,
                    "architecture": record["label"],
                    "code_parameters": f"({record['architecture']['encoded_width_bits']},{record['architecture']['payload_width_bits']})",
                    "guarantee_tier": guarantee_tier(identifier),
                    "weight1_behavior": f"CORRECTED {w1['corrected']}/{w1['total_masks']}",
                    "weight2_behavior": (
                        f"CORRECTED {w2['corrected']}/{w2['total_masks']}" if w2["corrected"] else
                        f"DUE {w2['due']}/{w2['total_masks']}"
                    ),
                    "weight3_total_observations": w3["total_masks"],
                    "weight3_sdc_count": w3["sdc_miscorrection"] + w3["sdc_undetected"],
                    "weight3_sdc_fraction": w3["sdc_fraction"],
                    "weight3_due_count": w3["due"],
                    "weight3_due_fraction": w3["due_fraction"],
                    "weight3_caveat": "EXHAUSTIVE_CANONICAL_COORDINATE_OBSERVATION_NOT_OPERATIONAL_PROBABILITY_OR_GUARANTEE",
                    "physical_availability": "ROUTED" if is_routed(record) else "PPA_UNAVAILABLE",
                }
            )

    physical_fields = [
        "implementation_id", "architecture", "protection_guarantee", "area_um2", "delta_area_percent_vs_comb",
        "fmax_mhz", "feasible_10ns", "wirelength_um", "cell_count", "no_error_power_w",
        "achievable_energy_pj_per_operation", "diagnostic_target_energy_pj_per_operation", "latency_cycles",
        "initiation_interval_cycles", "drc_count",
    ]
    reference_area = records[COMB]["physical"]["metrics"]["standard_cell_instance_area_um2"]
    with (out / "GATE06_PHYSICAL_TABLE.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=physical_fields, lineterminator="\n")
        writer.writeheader()
        for identifier in ORDER:
            record = records[identifier]
            routed = is_routed(record)
            metrics = record["physical"]["metrics"]
            power = no_error(record)
            writer.writerow(
                {
                    "implementation_id": identifier,
                    "architecture": record["label"],
                    "protection_guarantee": guarantee_tier(identifier),
                    "area_um2": metrics["standard_cell_instance_area_um2"] if routed else "PPA_UNAVAILABLE",
                    "delta_area_percent_vs_comb": pct(metrics["standard_cell_instance_area_um2"], reference_area) if routed else "PPA_UNAVAILABLE",
                    "fmax_mhz": metrics["achieved_fmax_mhz"] if routed else "PPA_UNAVAILABLE",
                    "feasible_10ns": record["physical"]["timing_feasibility"],
                    "wirelength_um": metrics["detailed_route_wirelength_um"] if routed else "PPA_UNAVAILABLE",
                    "cell_count": metrics["cell_count"] if routed else "PPA_UNAVAILABLE",
                    "no_error_power_w": power["metrics"]["total_power_w"] if power else "PPA_UNAVAILABLE",
                    "achievable_energy_pj_per_operation": (
                        "PPA_UNAVAILABLE" if not power else
                        "TARGET_CLOCK_INFEASIBLE" if power["metrics"]["achievable_total_energy_pj_per_operation"] is None else
                        power["metrics"]["achievable_total_energy_pj_per_operation"]
                    ),
                    "diagnostic_target_energy_pj_per_operation": (
                        power["metrics"]["total_energy_pj_per_operation_estimate"] if power else "PPA_UNAVAILABLE"
                    ),
                    "latency_cycles": record["architecture"]["nominal_operation_latency_cycles"],
                    "initiation_interval_cycles": record["architecture"]["initiation_interval_cycles"],
                    "drc_count": metrics["final_drc_count"] if routed else "PPA_UNAVAILABLE",
                }
            )

    claims = {
        "schema_version": 1,
        "ranking_policy": "strength reflects this dataset's direct support and claim scope, not rhetorical value",
        "claims": [
            {
                "id": "A",
                "claim": "Hardware microarchitecture materially changes cost even when ECC protection semantics are identical.",
                "rank": "STRONG",
                "basis": "universal SECDED equivalence plus measured area, timing, routing, power, energy, and latency differences",
            },
            {
                "id": "B",
                "claim": "Pipelining the evaluated SECDED implementation increases area but substantially improves achievable frequency and steady-stream energy per operation.",
                "rank": "STRONG",
                "basis": "programmatic raw-data effects: +36.702% area, +45.911% Fmax, -24.016% energy, +2 cycles latency, II unchanged",
            },
            {
                "id": "C",
                "claim": "Stronger error correction may impose nonlinear physical-design cost and can make a design infeasible at a common target clock.",
                "rank": "SUPPORTED",
                "basis": "evaluated BCH point has stronger W2 correction, +207.356% area, +310.975% wirelength, and fails 10 ns; one implementation cannot establish a family-wide law",
            },
            {
                "id": "D",
                "claim": "Algorithm-level correction strength alone is insufficient to select an ECC implementation.",
                "rank": "STRONG",
                "basis": "BCH's stronger guarantee coexists with substantial cost and target infeasibility; identical SECDED semantics also admit materially different costs",
            },
            {
                "id": "E",
                "claim": "A reproducible cross-layer flow exposes implementation trade-offs that code-level ECC comparison alone misses.",
                "rank": "SUPPORTED",
                "basis": "identity-preserving Gate 05 join reveals the SECDED architecture trade and BCH timing failure; novelty relative to external literature remains for Gate 07 audit",
            },
            {
                "id": "F",
                "claim": "Hsiao has a lower exhaustive weight-3 SDC observation fraction than conventional SECDED in its canonical-coordinate universe.",
                "rank": "SUPPORTED",
                "basis": "2847/4970 versus 809/1065; observation-only and not a physical or field-weighted claim",
            },
            {
                "id": "G",
                "claim": "Resolved error-class power differences are practically significant.",
                "rank": "WEAK",
                "basis": "numerically resolved by full-precision OpenSTA, but no practical-significance or field-frequency evidence",
            },
            {
                "id": "H",
                "claim": "The evaluated results establish FIT, SER, operational failure probability, or physical-interleaving superiority.",
                "rank": "UNSUPPORTED",
                "basis": "METRIC_NOT_PROVEN in Gate 05",
            },
            {
                "id": "I",
                "claim": "BCH as a family cannot operate at 100 MHz.",
                "rank": "UNSUPPORTED",
                "basis": "only the evaluated RTL, policy, technology, corner, and constraint were characterized",
            },
            {
                "id": "J",
                "claim": "Hsiao physically or Pareto-dominates a measured implementation.",
                "rank": "UNSUPPORTED",
                "basis": "PPA_UNAVAILABLE",
            },
            {
                "id": "K",
                "claim": "BCH's 10 ns target-constraint energy is achievable 100 MHz operating energy.",
                "rank": "UNSUPPORTED",
                "basis": "TARGET_CLOCK_INFEASIBLE",
            },
            {
                "id": "L",
                "claim": "A unique best ECC or universal Pareto winner has been established.",
                "rank": "UNSUPPORTED",
                "basis": "objectives conflict, correction tiers are categorical, and the measured design space is small",
            },
        ],
    }
    write_json(out / "GATE06_CLAIM_RANKING.json", claims)

    limitations = {
        "schema_version": 1,
        "limitations": [
            {"id": "L01", "scope": "technology", "statement": "SKY130HD only", "impact": "no node/library generalization"},
            {"id": "L02", "scope": "corner", "statement": "TT 1.80 V / 25 C only", "impact": "no PVT robustness claim"},
            {"id": "L03", "scope": "constraint", "statement": "one common primary 10 ns target", "impact": "no timing-normalized energy comparison for BCH"},
            {"id": "L04", "scope": "implementation", "statement": "specific evaluated RTL implementations", "impact": "no universal claim about each ECC family"},
            {"id": "L05", "scope": "missing PPA", "statement": "Hsiao PPA unavailable", "impact": "reliability-only; excluded from physical fronts"},
            {"id": "L06", "scope": "energy", "statement": "BCH target-clock energy is not physically achievable", "impact": "diagnostic only"},
            {"id": "L07", "scope": "reliability projection", "statement": "no proven FIT/SER", "impact": "no device/system failure-rate claims"},
            {"id": "L08", "scope": "fault weighting", "statement": "no operationally weighted SDC/DUE", "impact": "finite-universe fractions only"},
            {"id": "L09", "scope": "weight-3 semantics", "statement": "canonical-coordinate exhaustive observations", "impact": "not operational probabilities or correction guarantees"},
            {"id": "L10", "scope": "memory organization", "statement": "no final physical SRAM-array/interleaving characterization", "impact": "no placement-aware reliability claim"},
            {"id": "L11", "scope": "power", "statement": "post-route OpenSTA estimates, not silicon measurements", "impact": "estimated comparative power only"},
            {"id": "L12", "scope": "sample size", "statement": "four reliability identities, three routed points, two feasible energy points", "impact": "exact enumeration is appropriate; broad optimization claims are not"},
            {"id": "L13", "scope": "physical variability", "statement": "one qualified deterministic seed policy", "impact": "no statistical process/seed distribution claim"},
            {"id": "L14", "scope": "novelty", "statement": "external literature novelty is not re-audited in Gate 06", "impact": "Gate 07 must adversarially verify manuscript claim framing"},
        ],
        "hidden_limitations": False,
        "hsiao_absence_alone_causes_not_ready": False,
    }
    write_json(out / "GATE06_LIMITATIONS.json", limitations)

    strength = {
        "schema_version": 1,
        "scale": "1 (insufficient/severely unbounded) to 5 (strong/fully bounded for the claimed scope); no aggregate score is computed",
        "dimensions": [
            {"dimension": "novelty", "score": 3, "assessment": "promising implementation-aware cross-layer core; external novelty positioning remains for Gate 07"},
            {"dimension": "methodological_rigor", "score": 5, "assessment": "frozen identities, exact universes, immutable PPA evidence, and explicit missing-data rules"},
            {"dimension": "physical_evidence", "score": 3, "assessment": "three routed points with clean DRC and timing evidence, but one technology/corner/target and Hsiao missing"},
            {"dimension": "reliability_evidence", "score": 4, "assessment": "exact finite universes and formal identity transfer; no field weighting or FIT/SER"},
            {"dimension": "cross_layer_contribution", "score": 4, "assessment": "strong SECDED architecture trade plus BCH reliability-cost-feasibility contrast"},
            {"dimension": "reproducibility", "score": 5, "assessment": "content-hashed frozen upstream evidence and deterministic exact analysis"},
            {"dimension": "completeness", "score": 3, "assessment": "principal comparison complete; Hsiao PPA and feasible BCH energy unavailable"},
            {"dimension": "limitations", "score": 3, "assessment": "limitations are explicit and bounded, but constrain generalization and statistical breadth"},
        ],
        "decision": "DATE_REGULAR_PAPER_CORE_READY",
        "decision_scope": "ready for Gate 07 adversarial claim/evidence audit, not a final acceptance or submission-readiness guarantee",
        "reason": "at least two strong independently traceable findings, coherent separated comparison spaces, valid physical/reliability evidence, and bounded missing dimensions support a focused DATE paper core",
    }
    write_json(out / "GATE06_PAPER_STRENGTH.json", strength)

    configure_matplotlib()
    figure_methodology(figures)
    figure_area_fmax(figures, records)
    figure_normalized_cost(figures, records)
    figure_reliability(figures, records)

    figure_data = {
        "schema_version": 1,
        "figures": {
            "F01_CROSS_LAYER_METHOD": {"kind": "methodology diagram", "numeric_data": None},
            "F02_AREA_VS_FMAX": {
                "points": [
                    {
                        "implementation_id": identifier,
                        "area_um2": records[identifier]["physical"]["metrics"]["standard_cell_instance_area_um2"],
                        "fmax_mhz": records[identifier]["physical"]["metrics"]["achieved_fmax_mhz"],
                        "feasible_10ns": is_timing_feasible(records[identifier]),
                    }
                    for identifier in (COMB, PIPE, BCH)
                ],
                "excluded": {HSIAO: "PPA_UNAVAILABLE"},
            },
            "F03_NORMALIZED_PHYSICAL_COST": {
                "reference": COMB,
                "metrics": ["area", "wirelength", "fmax", "no_error_power", "no_error_achievable_energy"],
                "bch_power_energy_annotation": "TARGET_CLOCK_INFEASIBLE",
                "hsiao_annotation": "PPA_UNAVAILABLE",
            },
            "F04_RELIABILITY_OUTCOMES": {
                "weight3_observation_only": True,
                "code_semantics": [COMB, HSIAO, BCH],
                "conventional_secded_shared_by": [COMB, PIPE],
            },
        },
    }
    write_json(out / "GATE06_FIGURE_DATA.json", figure_data)

    specs = """# Gate 06 paper figure specifications

All figures are generated deterministically from the hash-verified Gate 05 dataset. SVG and PDF are manuscript masters; PNG files are review previews. Hsiao is never placed at zero or infinity, and BCH is never plotted as an achievable-energy point.

## Figure 1 — Cross-layer methodology

- **Files:** `figures/F01_CROSS_LAYER_METHOD.svg`, `.pdf`, `.png`
- **Claim served:** exact identity and missing-data boundaries are preserved from correctness through design-space conclusions.
- **Content:** correctness identity → exact reliability universes → RTL architecture → frozen physical implementation → comparison spaces A/B/C.
- **Mandatory annotation:** Hsiao stops at reliability-only; BCH retains routed physical evidence but no achievable target-clock energy.

## Figure 2 — Area versus achieved Fmax

- **Files:** `figures/F02_AREA_VS_FMAX.svg`, `.pdf`, `.png`
- **Claim served:** common physical policy exposes an architectural SECDED trade-off and BCH target infeasibility.
- **Points:** combinational SECDED, pipelined SECDED, BCH.
- **Reference:** horizontal 100 MHz target line.
- **Exclusion:** Hsiao is annotated `PPA_UNAVAILABLE`, not plotted.

## Figure 3 — Normalized physical effects

- **Files:** `figures/F03_NORMALIZED_PHYSICAL_COST.svg`, `.pdf`, `.png`
- **Claim served:** effect sizes relative to combinational SECDED are multi-dimensional and directionally conflicting.
- **Axes:** each metric is normalized to the conventional combinational SECDED value (100%); arrows identify minimize/maximize direction.
- **Metrics:** area, detailed wirelength, Fmax, no-error power, and no-error achievable steady-stream energy.
- **Missing semantics:** BCH achievable-energy bar is absent and annotated `TARGET_CLOCK_INFEASIBLE`; its diagnostic power is not used as an achievable-power comparison. Hsiao is annotated `PPA_UNAVAILABLE`.

## Figure 4 — Reliability-only outcome composition

- **Files:** `figures/F04_RELIABILITY_OUTCOMES.svg`, `.pdf`, `.png`
- **Claim served:** correction guarantees and beyond-guarantee outcomes are distinct; Hsiao and BCH remain scientifically informative without fabricating physical comparability.
- **Bars:** exhaustive weight-3 SDC miscorrection and DUE fractions for conventional SECDED semantics, Hsiao, and BCH.
- **Guarantee labels:** SECDED-class W1 correction/W2 detection; BCH W1/W2 correction.
- **Caveat:** the bars are canonical-coordinate observations, not operational probabilities or weight-3 correction guarantees.
"""
    (out / "GATE06_FIGURE_SPECIFICATIONS.md").write_text(specs, encoding="utf-8", newline="\n")

    pipe_effect = effects["comparisons"][0]["metrics"]
    bch_comb_effect = effects["comparisons"][1]["metrics"]
    bch_pipe_effect = effects["comparisons"][2]["metrics"]
    paper_tables = f"""# Gate 06 DATE-ready paper tables

## Primary hardware table

| Architecture | Protection guarantee | Area µm² | ΔArea vs comb | Fmax MHz | 10 ns | Wirelength µm | Power W | Achievable energy/op pJ | Latency cycles |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| Conventional SECDED, combinational | W1 correct; W2 detect | 18644.1 | +0.000% | 243.881 | MEETS_10NS | 44609 | 0.0145747941 | 145.762516 | 1 |
| Conventional SECDED, pipelined | W1 correct; W2 detect | 25486.9 | {pipe_effect['standard_cell_instance_area_um2']['percent_change']:+.3f}% | 355.849 | MEETS_10NS | 49992 | 0.0110745076 | 110.756151 | 3 |
| Hsiao SECDED | W1 correct; W2 detect | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | 1 |
| BCH (78,64,t=2) | W1/W2 correct | 57303.7 | {bch_comb_effect['standard_cell_instance_area_um2']['percent_change']:+.3f}% | 67.6566 | FAILS_10NS | 183332 | 0.848764658 (diagnostic) | TARGET_CLOCK_INFEASIBLE | 1 |

Power is the no-error post-route OpenSTA estimate. BCH power is retained only as a target-constraint diagnostic. SECDED energy values are steady-stream energy per accepted comparison transaction under the verified Gate 05 normalization.

## Reliability table

| Architecture / ECC | Parameters | W1 behavior | W2 behavior | Weight-3 observations | Weight-3 SDC | Weight-3 DUE | Caveat |
|---|---|---|---|---:|---:|---:|---|
| Conventional SECDED, combinational | (72,64) | 72/72 corrected | 2556/2556 DUE | 59640 | 45304 (809/1065) | 14336 (256/1065) | shared code semantics |
| Conventional SECDED, pipelined | (72,64) | 72/72 corrected | 2556/2556 DUE | 59640 | 45304 (809/1065) | 14336 (256/1065) | exact-equivalent architecture |
| Hsiao SECDED | (72,64) | 72/72 corrected | 2556/2556 DUE | 59640 | 34164 (2847/4970) | 25476 (2123/4970) | PPA_UNAVAILABLE |
| BCH | (78,64,t=2) | 78/78 corrected | 3003/3003 corrected | 76076 | 13780 (265/1463) | 62296 (1198/1463) | weight-3 observation only |

Weight-3 columns are exhaustive canonical-coordinate observations, never operational probabilities, FIT/SER values, or correction guarantees.

## Effect-size table

| Comparison | ΔArea | ΔCells | ΔWirelength | ΔFmax | Timing deficit | ΔPower | ΔEnergy/op |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pipelined vs combinational SECDED | {pipe_effect['standard_cell_instance_area_um2']['percent_change']:+.3f}% | {pipe_effect['cell_count']['percent_change']:+.3f}% | {pipe_effect['detailed_route_wirelength_um']['percent_change']:+.3f}% | {pipe_effect['achieved_fmax_mhz']['percent_change']:+.3f}% | 0 ns | {pipe_effect['no_error_total_power_w']['percent_change']:+.3f}% | {pipe_effect['no_error_achievable_total_energy_pj_per_operation']['percent_change']:+.3f}% |
| BCH vs combinational SECDED | {bch_comb_effect['standard_cell_instance_area_um2']['percent_change']:+.3f}% | {bch_comb_effect['cell_count']['percent_change']:+.3f}% | {bch_comb_effect['detailed_route_wirelength_um']['percent_change']:+.3f}% | {bch_comb_effect['achieved_fmax_mhz']['percent_change']:+.3f}% | +4.78052 ns | NOT_APPLICABLE | TARGET_CLOCK_INFEASIBLE |
| BCH vs pipelined SECDED | {bch_pipe_effect['standard_cell_instance_area_um2']['percent_change']:+.3f}% | {bch_pipe_effect['cell_count']['percent_change']:+.3f}% | {bch_pipe_effect['detailed_route_wirelength_um']['percent_change']:+.3f}% | {bch_pipe_effect['achieved_fmax_mhz']['percent_change']:+.3f}% | +4.78052 ns | NOT_APPLICABLE | TARGET_CLOCK_INFEASIBLE |
"""
    (out / "GATE06_PAPER_TABLES.md").write_text(paper_tables, encoding="utf-8", newline="\n")

    scores = "\n".join(
        f"| {row['dimension']} | {row['score']}/5 | {row['assessment']} |" for row in strength["dimensions"]
    )
    adjudication = f"""# DATE 2027 Gate 06 design-space adjudication

`GATE_06_PASS`

`DATE_REGULAR_PAPER_CORE_READY`

## Three comparison spaces

### Space A — Full physically feasible comparison

Members: conventional combinational SECDED and pipelined SECDED. Neither dominates the other. Combinational SECDED improves area, wirelength, and latency; pipelined SECDED improves achieved Fmax, no-error power, and equivalent steady-stream energy/op. The result is a genuine architecture trade-off.

### Space B — Physical implementation comparison

Members: both SECDED architectures and BCH. BCH remains a valid routed point with zero DRC, WNS -4.78052 ns, timing deficit 4.78052 ns, and achieved Fmax 67.6566 MHz. On the primary physical-only objective set including latency, combinational SECDED dominates BCH. This physical dominance does not override BCH's categorically stronger W2 correction guarantee.

### Space C — Reliability-only comparison

Members: all four architecture identities. The two conventional SECDED architectures share exact reliability semantics. Within the W1-correction/W2-detection tier, Hsiao has lower observed weight-3 SDC and higher DUE, so no SDC/DUE dominance exists. BCH is separately reported in the W1/W2-correction tier. No reliability score or cross-tier numerical dominance is constructed.

## Smallest supported paper core

1. **STRONG:** exact-equivalent SECDED microarchitectures expose a non-dominated area/latency versus Fmax/energy trade-off.
2. **STRONG:** algorithm-level correction semantics alone cannot determine implementation choice.
3. **SUPPORTED:** the evaluated stronger-correction BCH RTL incurs large physical penalties and fails the common target, without implying a universal BCH limitation.
4. **SUPPORTED:** identity-preserving cross-layer analysis exposes feasibility and architecture effects absent from code-level comparison.

## NSGA-II adjudication

`NOT_USED_NO_SCIENTIFIC_VALUE`

Exact enumeration covers all four discrete measured identities. There is no valid combinatorial configuration space on which evolutionary optimization could add information.

## Adversarial paper-strength assessment

Scale: 1 (insufficient or severely unbounded) to 5 (strong and bounded for the claimed scope). Scores are independent; no composite score is formed.

| Dimension | Score | Evidence-driven assessment |
|---|---:|---|
{scores}

`DATE_REGULAR_PAPER_CORE_READY` means the focused core is ready for Gate 07's adversarial manuscript-claim audit. It does not assert acceptance, completed literature novelty verification, or final submission readiness.

## Verdict

The evidence supports a coherent, quantitatively traceable design-space story and four claim-serving figures. Hsiao's missing PPA and BCH's infeasible target energy are bounded transparently by the three-space analysis and do not invalidate the paper core.

No Gate 07 work, new physical run, RTL modification, reliability-model change, GREEN Score, carbon analysis, ML, NSGA-II, commit, or push was performed.

`GATE_07_READY`
"""
    (out / "GATE06_ADJUDICATION.md").write_text(adjudication, encoding="utf-8", newline="\n")

    evidence_files = [
        path for path in sorted(out.rglob("*"))
        if path.is_file() and path.name != "GATE06_EVIDENCE.sha256"
    ]
    manifest_lines = [f"{sha256(path)}  ./{path.relative_to(out).as_posix()}" for path in evidence_files]
    (out / "GATE06_EVIDENCE.sha256").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    build(args.out.resolve())
    print("GATE06_ARTIFACTS_BUILT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
