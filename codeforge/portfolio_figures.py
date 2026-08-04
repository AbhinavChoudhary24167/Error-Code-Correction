"""Publication-oriented vector figures for portfolio co-synthesis evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from visualization_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

import matplotlib.pyplot as plt
import numpy as np


COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "gray": "#666666",
}


def _save(fig: Any, base: Path) -> None:
    fig.tight_layout()
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=180, bbox_inches="tight")
    plt.close(fig)


def generate_portfolio_figures(portfolio: Mapping[str, Any], outdir: Path) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    regime_weights = list(portfolio["regime_probabilities"].values())
    independent = portfolio["baselines"]["independent_hardware_aware"]["codes"]
    independent_residual = sum(
        weight
        * (
            code["synthesis_probability_mass"]["residual"]
            if "residual" in code["synthesis_probability_mass"]
            else code["synthesis_probability_mass"]["due"]
            + code["synthesis_probability_mass"]["sdc"]
        )
        for weight, code in zip(regime_weights, independent)
    )
    general_residual = portfolio["baselines"]["one_general_generated_code"]["weighted_residual_probability"]
    joint_residual = portfolio["objective_metrics"]["weighted_residual_probability"]
    fallback_reports = portfolio["safety_policy"]["fallback_reports"]
    synthesis_ids = [code["synthesis_distribution_id"] for code in portfolio["modes"]]
    secded_residual = sum(
        weight * fallback_reports[distribution_id]["probability_mass"]["residual"]
        for weight, distribution_id in zip(regime_weights, synthesis_ids)
    )
    labels = ["SEC-DED", "One generated\ncode", "Independent\nportfolio", "Joint\nportfolio"]
    values = [secded_residual, general_residual, independent_residual, joint_residual]
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    bars = ax.bar(labels, values, color=[COLORS["gray"], COLORS["orange"], COLORS["sky"], COLORS["blue"]])
    ax.set_ylabel("Modeled residual probability")
    ax.set_title("Equal-redundancy reliability comparison")
    ax.set_ylim(0, max(values) * 1.18)
    ax.bar_label(bars, fmt="%.3f", padding=3)
    ax.text(0.01, 0.98, "Synthetic finite PMFs; lower is better", transform=ax.transAxes, va="top", fontsize=9)
    _save(fig, outdir / "equal_redundancy_reliability")

    graph = portfolio["shared_graph"]
    baseline = portfolio["baselines"]
    hardware_labels = ["Naive\nequations", "Separate\nengines", "Independent +\nshared CSE", "Joint\nco-search", "Programmable\nfabric"]
    hardware_values = [
        graph["naive_total_xor_gates"],
        baseline["separate_engines_plus_muxes"]["engine_xor_gates"],
        baseline["independent_hardware_aware"]["shared_graph_after_generation"]["total_xor_gates"],
        graph["total_xor_gates"],
        baseline["naive_programmable_xor_fabric"]["xor_gates"],
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    bars = ax.bar(
        hardware_labels,
        hardware_values,
        color=[COLORS["gray"], COLORS["orange"], COLORS["green"], COLORS["blue"], COLORS["purple"]],
    )
    ax.set_ylabel("Structural two-input-XOR proxy")
    ax.set_title("Shared-hardware structural baselines")
    ax.bar_label(bars, padding=3)
    ax.text(
        0.01,
        0.98,
        f"Ordinary synthesis baseline: {baseline['ordinary_combined_synthesis']['status']}",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
    )
    _save(fig, outdir / "shared_hardware_structural_baselines")

    mode_names = list(portfolio["distribution_shift"])
    distribution_ids = list(next(iter(portfolio["distribution_shift"].values())))
    residual = np.array(
        [
            [
                portfolio["distribution_shift"][mode][distribution]["probability_mass"]["residual"]
                for distribution in distribution_ids
            ]
            for mode in mode_names
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(10.2, 3.5 + 0.5 * len(mode_names)))
    image = ax.imshow(residual, aspect="auto", cmap="viridis_r", vmin=0, vmax=max(1e-12, float(residual.max())))
    ax.set_yticks(range(len(mode_names)), mode_names)
    short_ids = [identifier.split("-72bit")[0].replace("_", " ") for identifier in distribution_ids]
    ax.set_xticks(range(len(distribution_ids)), short_ids, rotation=28, ha="right")
    ax.set_title("Distribution-shift residual probability")
    for row in range(residual.shape[0]):
        for col in range(residual.shape[1]):
            safe = portfolio["distribution_shift"][mode_names[row]][distribution_ids[col]]["safe"]
            ax.text(col, row, f"{residual[row, col]:.2f}\n{'safe' if safe else 'reject'}", ha="center", va="center", color="white" if residual[row, col] > residual.max() / 2 else "black", fontsize=8)
    fig.colorbar(image, ax=ax, label="Residual probability")
    _save(fig, outdir / "distribution_shift_safety")

    trajectory = portfolio["search"]["trajectory"]
    xs = [item["shared_xor_gates"] for item in trajectory]
    ys = [item["weighted_residual_probability"] for item in trajectory]
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(xs, ys, color=COLORS["blue"], marker="o")
    for item, x, y in zip(trajectory, xs, ys):
        ax.annotate(str(item["iteration"]), (x, y), xytext=(5, 5), textcoords="offset points")
    ax.set_xlabel("Shared XOR proxy gates")
    ax.set_ylabel("Weighted modeled residual probability")
    ax.set_title("Alternating co-synthesis trajectory")
    ax.grid(alpha=0.25)
    _save(fig, outdir / "cosynthesis_pareto_trajectory")

    return {
        "equal_redundancy_reliability.svg": "The generated portfolio improves modeled residual probability over one general code at equal redundancy for the configured synthetic regimes.",
        "shared_hardware_structural_baselines.svg": "Joint matrix search did not beat independent generation followed by shared CSE in structural XOR count, and ordinary synthesis remains unavailable.",
        "distribution_shift_safety.svg": "Most shifted mixtures leave the zero-SDC validation envelope, causing fallback or deployment rejection.",
        "cosynthesis_pareto_trajectory.svg": "Reliability improvements required more shared XOR proxy gates, exposing a Pareto trade-off rather than a joint hardware win.",
    }
