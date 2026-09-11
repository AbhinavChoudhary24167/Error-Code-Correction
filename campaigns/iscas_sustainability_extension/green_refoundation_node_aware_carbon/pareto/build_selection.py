"""Build exact-Pareto and robust-selection artifacts from GREEN matrix v2."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from campaigns.iscas_sustainability_extension.green_refoundation_node_aware_carbon.pareto.selection import (  # noqa: E402
    Objective,
    exact_pareto_front,
    qualified_rows,
)


BASE = Path(__file__).resolve().parents[1]
OBJECTIVES = (
    Objective("GCI", "min"),
    Objective("SDC", "min"),
    Objective("DUE", "min"),
    Objective("latency_ns", "min"),
)


def build(base: Path = BASE) -> tuple[Path, Path, Path, Path]:
    matrix_path = base / "green_matrix_v2" / "GREEN_MATRIX_V2_RAW.csv"
    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    eligible = list(qualified_rows(rows, [objective.name for objective in OBJECTIVES]))
    frontier_indices = exact_pareto_front(eligible, OBJECTIVES) if eligible else []
    frontier = [eligible[index] for index in frontier_indices]

    output_dir = base / "pareto"
    output_dir.mkdir(parents=True, exist_ok=True)
    exact_csv = output_dir / "EXACT_PARETO_RESULTS.csv"
    exact_json = output_dir / "EXACT_PARETO_RESULTS.json"
    robust_csv = output_dir / "ROBUST_SELECTION.csv"
    robust_json = output_dir / "ROBUST_SELECTION.json"

    with exact_csv.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["row_id", "architecture_id", "GCI", "SDC", "DUE", "latency_ns"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in frontier:
            writer.writerow({field: row[field] for field in fieldnames})

    exact_result = {
        "schema_version": 1,
        "method": "EXACT_DETERMINISTIC_ENUMERATION",
        "candidate_row_count": len(rows),
        "eligible_row_count": len(eligible),
        "frontier_row_count": len(frontier),
        "objectives": [objective.__dict__ for objective in OBJECTIVES],
        "frontier_row_ids": [row["row_id"] for row in frontier],
        "classification": "NO_QUALIFIED_FULL_OBJECTIVE_ROWS",
        "winner": None,
        "reason": (
            "GCI, physical SDC/DUE probabilities, and service latency are not "
            "jointly qualified for any row. Logical mask fractions are not substituted."
        ),
        "NSGA_II_used": False,
    }
    exact_json.write_text(
        json.dumps(exact_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )

    with robust_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "architecture_id",
                "mean_GSE",
                "median_GSE",
                "p05_GSE",
                "worst_case_lower_GSE",
                "selection_status",
            ]
        )

    robust_result = {
        "schema_version": 1,
        "policies_compared": ["mean", "median", "P05", "worst_case_interval_lower"],
        "qualified_GSE_distributions": 0,
        "selected_policy": None,
        "selected_architecture": None,
        "classification": "NOT_EVALUATED_NO_QUALIFIED_GSE_DISTRIBUTIONS",
        "policy_statement": (
            "P05 is not adopted automatically. A risk policy requires stakeholder "
            "semantics plus jointly qualified service and lifecycle-carbon samples."
        ),
    }
    robust_json.write_text(
        json.dumps(robust_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    return exact_csv, exact_json, robust_csv, robust_json


if __name__ == "__main__":
    build()
