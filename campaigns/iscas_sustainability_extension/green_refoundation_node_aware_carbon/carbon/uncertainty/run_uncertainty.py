"""Reproduce the campaign's normalized manufacturing uncertainty artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from uncertainty import (
    IntervalParameter,
    evaluate_ensemble,
    normalized_good_die_carbon_index,
    scenario_quantile_summary,
    spearman_sensitivity,
)


HERE = Path(__file__).resolve().parent


def run() -> None:
    config = json.loads((HERE / "UNCERTAINTY_MODEL.json").read_text("utf-8"))
    parameters = [
        IntervalParameter(
            item["name"], float(item["low"]), float(item["high"]), item["scale"]
        )
        for item in config["parameters"]
    ]
    samples, outputs = evaluate_ensemble(
        parameters,
        int(config["sample_count"]),
        int(config["seed"]),
        normalized_good_die_carbon_index,
    )
    summary = scenario_quantile_summary(outputs)
    result_fields = [
        "analysis_id",
        "sample_count",
        "seed",
        "output_metric",
        "unit",
        "mean",
        "median",
        "p05",
        "p95",
        "minimum",
        "maximum",
        "evidence_label",
        "quantile_semantics",
        "source_ids",
    ]
    with (HERE / "UNCERTAINTY_RESULTS.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=result_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "analysis_id": config["analysis_id"],
                "sample_count": config["sample_count"],
                "seed": config["seed"],
                "output_metric": config["output"]["name"],
                "unit": config["output"]["unit"],
                **{name: f"{value:.12g}" for name, value in summary.items()},
                "evidence_label": config["output"]["evidence_label"],
                "quantile_semantics": "SCENARIO_ENSEMBLE_NOT_CONFIDENCE",
                "source_ids": ";".join(config["source_ids"]),
            }
        )
    sensitivity = spearman_sensitivity(samples, outputs)
    with (HERE / "UNCERTAINTY_SENSITIVITY.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "rank",
                "parameter",
                "spearman_rho",
                "normalized_absolute_influence",
                "evidence_label",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for rank, row in enumerate(sensitivity, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "parameter": row["parameter"],
                    "spearman_rho": f"{float(row['spearman_rho']):.12g}",
                    "normalized_absolute_influence": f"{float(row['normalized_absolute_influence']):.12g}",
                    "evidence_label": "PARAMETRIC_UNCERTAIN",
                }
            )


if __name__ == "__main__":
    run()
