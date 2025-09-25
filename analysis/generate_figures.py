"""Generate figures for the energy-aware ECC manuscript."""

from __future__ import annotations

import logging
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ecc_selector as selector

logging.getLogger("ecc_selector").setLevel(logging.ERROR)

FIG_DIR = ROOT / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

SCENARIO = dict(
    node=28,
    vdd=0.8,
    temp=65.0,
    capacity_gib=32.0,
    ci=0.35,
    bitcell_um2=0.09,
    lifetime_h=5 * 365 * 24,
)

CODES = ["sec-ded-64", "sec-daec-64", "taec-64"]


def _base_records(scrub_s: float = 10.0) -> list[dict[str, float]]:
    result = selector.select(
        CODES,
        scrub_s=scrub_s,
        mbu="moderate",
        alt_km=0.0,
        latitude_deg=45.0,
        flux_rel=None,
        **SCENARIO,
    )
    return [dict(rec) for rec in result["candidate_records"]]


def pareto_frontier_fig() -> None:
    records = _base_records(scrub_s=20.0)
    if not records:
        raise RuntimeError("No records returned from selector")

    pareto = selector._pareto_front(records)
    pareto_codes = {rec["code"] for rec in pareto}

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for rec in records:
        label = rec["code"].replace("-64", "").upper()
        ax.scatter(
            rec["carbon_kg"],
            rec["FIT"],
            s=120,
            marker="o" if rec["code"] in pareto_codes else "x",
            c="#1f77b4" if rec["code"] in pareto_codes else "#bbbbbb",
            edgecolor="black" if rec["code"] in pareto_codes else "none",
            linewidths=1.0,
            alpha=0.9 if rec["code"] in pareto_codes else 0.7,
            label=label,
        )
        ax.annotate(
            label,
            (rec["carbon_kg"], rec["FIT"]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Total carbon (kg CO$_2$e)")
    ax.set_ylabel("Post-ECC FIT (failures / 10$^9$ h)")
    ax.set_title("Pareto frontier across ECC candidates")
    ax.grid(True, which="both", ls=":", alpha=0.6)
    ax.legend(frameon=False, loc="upper right")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_pareto_frontier.png", dpi=300)
    plt.close(fig)


def carbon_heatmap_fig() -> None:
    code = "sec-daec-64"
    scrub_vals = np.logspace(0, 3, 40)
    ci_vals = np.linspace(0.05, 0.7, 36)

    Z = np.zeros((ci_vals.size, scrub_vals.size))
    for i, ci in enumerate(ci_vals):
        for j, scrub in enumerate(scrub_vals):
            rec = selector._compute_metrics(
                code,
                node=SCENARIO["node"],
                vdd=SCENARIO["vdd"],
                temp=SCENARIO["temp"],
                ci=float(ci),
                capacity_gib=SCENARIO["capacity_gib"],
                bitcell_um2=SCENARIO["bitcell_um2"],
                alt_km=0.0,
                latitude_deg=45.0,
                flux_rel=None,
                mbu="moderate",
                scrub_s=float(scrub),
                lifetime_h=SCENARIO["lifetime_h"],
            )
            Z[i, j] = rec["carbon_kg"]

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    im = ax.imshow(
        Z,
        origin="lower",
        aspect="auto",
        extent=[
            math.log10(scrub_vals.min()),
            math.log10(scrub_vals.max()),
            ci_vals.min(),
            ci_vals.max(),
        ],
        cmap="viridis",
    )
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label("Total carbon (kg CO$_2$e)")

    x_ticks = np.array([1, 3, 10, 30, 100, 300, 1000])
    ax.set_xticks(np.log10(x_ticks))
    ax.set_xticklabels([f"{int(x)}" for x in x_ticks])
    ax.set_xlabel("Scrub interval (s)")
    ax.set_ylabel("Grid carbon intensity (kg CO$_2$/kWh)")
    ax.set_title("Carbon sensitivity for SEC-DAEC")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_carbon_heatmap.png", dpi=300)
    plt.close(fig)


def metric_correlation_fig() -> None:
    rows: list[dict[str, float]] = []
    scrub_candidates = [1, 5, 10, 30, 60, 120, 300, 600]
    for code in CODES:
        for scrub in scrub_candidates:
            rec = selector._compute_metrics(
                code,
                node=SCENARIO["node"],
                vdd=SCENARIO["vdd"],
                temp=SCENARIO["temp"],
                ci=SCENARIO["ci"],
                capacity_gib=SCENARIO["capacity_gib"],
                bitcell_um2=SCENARIO["bitcell_um2"],
                alt_km=0.0,
                latitude_deg=45.0,
                flux_rel=None,
                mbu="moderate",
                scrub_s=float(scrub),
                lifetime_h=SCENARIO["lifetime_h"],
            )
            rec = dict(rec)
            rec["code"] = code
            rec["scrub_s"] = scrub
            rows.append(rec)

    df = pd.DataFrame(rows)
    metrics = ["FIT", "carbon_kg", "latency_ns", "ESII"]
    corr = df[metrics].corr()

    fig, ax = plt.subplots(figsize=(5.2, 4.5))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Pearson correlation")

    ax.set_xticks(range(len(metrics)))
    ax.set_yticks(range(len(metrics)))
    ax.set_xticklabels(metrics, rotation=45, ha="right")
    ax.set_yticklabels(metrics)
    ax.set_title("Metric correlation across codes & scrubs")

    for i in range(len(metrics)):
        for j in range(len(metrics)):
            ax.text(
                j,
                i,
                f"{corr.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                color="black",
                fontsize=9,
            )

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_metric_correlation.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    pareto_frontier_fig()
    carbon_heatmap_fig()
    metric_correlation_fig()
