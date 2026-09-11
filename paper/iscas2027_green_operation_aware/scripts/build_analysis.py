#!/usr/bin/env python3
"""Build the additive ISCAS 2027 GREEN paper-analysis artifacts.

The builder reads only evidence sealed at EVIDENCE_SEAL.  It never invokes an
EDA flow and never writes outside this paper-finalization directory.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "green_iscas2027_matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
FIGURES = OUT / "PAPER_FIGURES"
CAMPAIGN = ROOT / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5"
V32 = ROOT / "campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation"
EVIDENCE_SEAL = "8cf245ac6ac8cb9b010c073d439f04eb204d48a1"
BOOTSTRAP_REPLICATES = 50_000
ENERGY_COLUMNS = {
    "IDLE": "idle_energy_j_delta",
    "READ_CLEAN": "clean_read_energy_j_delta",
    "WRITE_CLEAN": "clean_write_energy_j_delta",
    "READ_SINGLE_BIT_ERROR_CORRECT": "correction_energy_j_delta",
    "READ_DOUBLE_BIT_ERROR_DETECT": "detection_energy_j_delta",
}
OP_LABELS = {
    "IDLE": "Idle",
    "READ_CLEAN": "Clean read",
    "WRITE_CLEAN": "Clean write",
    "READ_SINGLE_BIT_ERROR_CORRECT": "Correction",
    "READ_DOUBLE_BIT_ERROR_DETECT": "Detection",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("empty percentile input")
    position = (len(sorted_values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def describe(values: Sequence[float], seeds: Sequence[int], metric_id: str) -> Dict[str, Any]:
    if len(values) != len(seeds) or not values:
        raise ValueError(f"invalid paired sample for {metric_id}")
    rng_seed = int(hashlib.sha256(metric_id.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(rng_seed)
    boot = []
    for _ in range(BOOTSTRAP_REPLICATES):
        boot.append(statistics.mean(values[rng.randrange(len(values))] for _ in values))
    boot.sort()
    loo = []
    if len(values) > 1:
        for index, seed in enumerate(seeds):
            retained = [value for j, value in enumerate(values) if j != index]
            loo.append({"omitted_seed": seed, "mean": statistics.mean(retained)})
    mean = statistics.mean(values)
    target_sign = -1 if mean < 0 else (1 if mean > 0 else 0)
    sign_count = sum((-1 if value < 0 else (1 if value > 0 else 0)) == target_sign for value in values)
    loo_sign_count = sum(
        (-1 if item["mean"] < 0 else (1 if item["mean"] > 0 else 0)) == target_sign for item in loo
    )
    return {
        "n": len(values),
        "seeds": list(seeds),
        "values": list(values),
        "mean": mean,
        "median": statistics.median(values),
        "sample_standard_deviation": statistics.stdev(values) if len(values) > 1 else None,
        "minimum": min(values),
        "maximum": max(values),
        "negative_count": sum(value < 0 for value in values),
        "positive_count": sum(value > 0 for value in values),
        "zero_count": sum(value == 0 for value in values),
        "same_sign_as_mean_count": sign_count,
        "bootstrap_mean_95_percentile_interval": {
            "method": "paired nonparametric percentile bootstrap",
            "replicates": BOOTSTRAP_REPLICATES,
            "rng_seed": rng_seed,
            "low": percentile(boot, 0.025),
            "high": percentile(boot, 0.975),
            "interpretation": "descriptive sensitivity interval; the placement seeds are not a population sample",
        },
        "leave_one_seed_out": {
            "means": loo,
            "minimum_mean": min((item["mean"] for item in loo), default=None),
            "maximum_mean": max((item["mean"] for item in loo), default=None),
            "mean_sign_retained_count": loo_sign_count,
            "omission_count": len(loo),
        },
    }


def float_values(rows: Sequence[Mapping[str, str]], column: str, scale: float = 1.0) -> tuple[List[float], List[int]]:
    selected = [(float(row[column]) * scale, int(row["seed"])) for row in rows if row.get(column)]
    return [value for value, _ in selected], [seed for _, seed in selected]


def verify_evidence_tree() -> None:
    result = subprocess.run(
        ["git", "diff", "--exit-code", EVIDENCE_SEAL, "--", CAMPAIGN.relative_to(ROOT).as_posix()],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("sealed GREEN v3.3 evidence differs from its seal commit\n" + result.stdout + result.stderr)

    manifest = CAMPAIGN / "hashes/CAMPAIGN_ARTIFACTS.sha256"
    checked = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        source = CAMPAIGN / relative
        if sha256(source) != digest:
            raise RuntimeError(f"campaign artifact hash mismatch: {relative}")
        checked += 1
    if checked != 1697:
        raise RuntimeError(f"unexpected sealed artifact count: {checked}")


def extract_e5_records(matrix: Mapping[str, Any]) -> List[Dict[str, Any]]:
    cache: Dict[str, Dict[str, Any]] = {}
    extracted: List[Dict[str, Any]] = []
    for matrix_row in matrix["records"]:
        relative = matrix_row["source_result"]
        if relative not in cache:
            source = CAMPAIGN / relative
            if sha256(source) != matrix_row["source_result_sha256"]:
                raise RuntimeError(f"source-result hash mismatch: {relative}")
            cache[relative] = load_json(source)
        candidates = [
            row
            for row in cache[relative]["operation_records"]
            if row["record_id"] == matrix_row["matrix_record_id"]
        ]
        if len(candidates) != 1:
            raise RuntimeError(f"cannot resolve canonical E5 record: {matrix_row['matrix_record_id']}")
        record = candidates[0]
        if not record["ecc_logic_e5_qualified"] or record["evidence_level"] != "E5":
            raise RuntimeError(f"non-E5 record promoted: {record['record_id']}")
        extracted.append({"matrix": matrix_row, "record": record})
    return extracted


def paired_statistics(matched_rows: Sequence[Mapping[str, str]]) -> Dict[str, Any]:
    metrics: Dict[str, Dict[str, Any]] = {}
    for operation, column in ENERGY_COLUMNS.items():
        values, seeds = float_values(matched_rows, column, 1e12)
        stats = describe(values, seeds, f"energy:{operation}")
        stats["unit"] = "pJ/operation"
        stats["delta_definition"] = "Hsiao minus SECDED"
        stats["hsiao_lower_count"] = stats["negative_count"]
        metrics[f"energy_{operation.lower()}"] = stats

    physical_columns = {
        "total_instance_area": ("total_instance_area_um2_delta", "um^2", 1.0),
        "standard_cell_area": ("standard_cell_area_um2_delta", "um^2", 1.0),
        "wirelength": ("wirelength_um_delta", "um", 1.0),
        "via_count": ("via_count_delta", "count", 1.0),
        "setup_wns": ("setup_wns_ns_delta", "ns", 1.0),
        "e4_internal_power": ("e4_internal_power_w_delta", "mW", 1e3),
        "e4_switching_power": ("e4_switching_power_w_delta", "mW", 1e3),
        "e4_leakage_power": ("e4_leakage_power_w_delta", "mW", 1e3),
        "clean_read_internal_power": ("clean_read_internal_power_w_delta", "uW", 1e6),
        "clean_read_switching_power": ("clean_read_switching_power_w_delta", "uW", 1e6),
        "clean_read_leakage_power": ("clean_read_leakage_power_w_delta", "uW", 1e6),
        "clean_read_dynamic_power": ("clean_read_dynamic_power_w_delta", "uW", 1e6),
    }
    for name, (column, unit, scale) in physical_columns.items():
        values, seeds = float_values(matched_rows, column, scale)
        stats = describe(values, seeds, name)
        stats["unit"] = unit
        stats["delta_definition"] = "Hsiao minus SECDED"
        metrics[name] = stats

    e4_totals = [
        (float(row["e4_internal_power_w_delta"]) + float(row["e4_switching_power_w_delta"]) + float(row["e4_leakage_power_w_delta"]))
        * 1e3
        for row in matched_rows
    ]
    seeds = [int(row["seed"]) for row in matched_rows]
    metrics["e4_total_power"] = describe(e4_totals, seeds, "e4_total_power")
    metrics["e4_total_power"]["unit"] = "mW"
    metrics["e4_total_power"]["delta_definition"] = "Hsiao minus SECDED"

    component_audit = {
        "operation": "READ_CLEAN",
        "matched_seed_count": 5,
        "switching_delta_lower_for_hsiao_count": metrics["clean_read_switching_power"]["negative_count"],
        "internal_delta_higher_for_hsiao_count": metrics["clean_read_internal_power"]["positive_count"],
        "leakage_delta_higher_for_hsiao_count": metrics["clean_read_leakage_power"]["positive_count"],
        "net_energy_lower_for_hsiao_count": metrics["energy_read_clean"]["negative_count"],
        "supported_statement": "The component-level decomposition is consistent with lower Hsiao switching contribution being offset, and in two seeds exceeded, by higher Hsiao internal contribution.",
        "causal_status": "ASSOCIATION_ONLY; the experiment did not isolate a gate-level causal mechanism",
    }
    return {
        "schema_version": 1,
        "evidence_seal": EVIDENCE_SEAL,
        "sample_design": "matched placement seeds; descriptive implementation replications",
        "bootstrap_policy": "paired resampling of seed-level differences; deterministic percentile interval",
        "multiple_inference_claim": "NONE",
        "metrics": metrics,
        "component_decomposition_audit": component_audit,
        "ordering_summary": {
            "e4_hsiao_lower": 5,
            "e4_comparison_count": 5,
            "e4_unit_of_replication": "matched physical seed",
            "e5_hsiao_lower": sum(
                metrics[f"energy_{operation.lower()}"]["negative_count"] for operation in ENERGY_COLUMNS
            ),
            "e5_comparison_count": sum(
                metrics[f"energy_{operation.lower()}"]["n"] for operation in ENERGY_COLUMNS
            ),
            "e5_unit_of_replication": "matched operation-by-seed cell",
            "denominators_are_not_interchangeable": True,
        },
    }


def workload_analysis(matched_rows: Sequence[Mapping[str, str]], stats: Mapping[str, Any]) -> Dict[str, Any]:
    coefficients_all = {
        operation: stats["metrics"][f"energy_{operation.lower()}"]["mean"] for operation in ENERGY_COLUMNS
    }
    complete_rows = [row for row in matched_rows if all(row[column] for column in ENERGY_COLUMNS.values())]
    coefficients_complete = {
        operation: statistics.mean(float(row[column]) * 1e12 for row in complete_rows)
        for operation, column in ENERGY_COLUMNS.items()
    }

    def boundary(coefficients: Mapping[str, float]) -> Dict[str, Any]:
        read_gain = -coefficients["READ_CLEAN"]
        if read_gain <= 0:
            raise RuntimeError("expected negative clean-read coefficient")
        return {
            "delta_energy_pj_per_operation": (
                f"{coefficients['IDLE']:.12g} p_I {coefficients['READ_CLEAN']:+.12g} p_R "
                f"{coefficients['WRITE_CLEAN']:+.12g} p_W {coefficients['READ_SINGLE_BIT_ERROR_CORRECT']:+.12g} p_C "
                f"{coefficients['READ_DOUBLE_BIT_ERROR_DETECT']:+.12g} p_D"
            ),
            "hsiao_lower_iff": (
                "p_R > (delta_I*p_I + delta_W*p_W + delta_C*p_C + delta_D*p_D) / (-delta_R)"
            ),
            "read_gain_magnitude_pj_per_operation": read_gain,
            "two_dimensional_slice": {
                "fixed_assumptions": {"p_C": 0.0, "p_D": 0.0, "sum": "p_I+p_R+p_W=1"},
                "hsiao_lower_inequality": (
                    f"{read_gain + coefficients['IDLE']:.12g} p_I + "
                    f"{read_gain + coefficients['WRITE_CLEAN']:.12g} p_W < {read_gain:.12g}"
                ),
                "idle_axis_intercept": read_gain / (read_gain + coefficients["IDLE"]),
                "write_axis_intercept": read_gain / (read_gain + coefficients["WRITE_CLEAN"]),
            },
        }

    endpoint_scenarios = []
    symbols = {
        "IDLE": "p_I",
        "READ_CLEAN": "p_R",
        "WRITE_CLEAN": "p_W",
        "READ_SINGLE_BIT_ERROR_CORRECT": "p_C",
        "READ_DOUBLE_BIT_ERROR_DETECT": "p_D",
    }
    for selected in ENERGY_COLUMNS:
        probabilities = {symbol: 0.0 for symbol in symbols.values()}
        probabilities[symbols[selected]] = 1.0
        delta = coefficients_complete[selected]
        endpoint_scenarios.append(
            {
                "scenario_id": selected + "_ENDPOINT",
                "purpose": "measured-operation endpoint, not an asserted deployed workload",
                "probabilities": probabilities,
                "delta_energy_pj_per_operation": delta,
                "lower_energy_architecture": "HSIAO_SECDED" if delta < 0 else "SECDED",
            }
        )
    return {
        "schema_version": 1,
        "evidence_seal": EVIDENCE_SEAL,
        "delta_definition": "E_HSIAO_SECDED(p) - E_SECDED(p)",
        "units": "pJ per ECC-logic operation; SRAM macro-internal energy excluded",
        "probability_constraint": "p_I+p_R+p_W+p_C+p_D=1; every probability is nonnegative",
        "primary_complete_case_model": {
            "seed_count": len(complete_rows),
            "seeds": [int(row["seed"]) for row in complete_rows],
            "reason": "all five operation classes are jointly observed for these matched seed pairs",
            "coefficients_pj_per_operation": coefficients_complete,
            "parametric_boundary": boundary(coefficients_complete),
        },
        "all_available_operation_means_sensitivity": {
            "operation_specific_seed_counts": {
                operation: stats["metrics"][f"energy_{operation.lower()}"]["n"] for operation in ENERGY_COLUMNS
            },
            "coefficients_pj_per_operation": coefficients_all,
            "parametric_boundary": boundary(coefficients_all),
            "limitation": "operation means use n=4 for idle/write and n=5 for the read classes; this is a sensitivity model, not the primary joint vector",
        },
        "scenario_mode": {
            "required_input": ["p_I", "p_R", "p_W", "p_C", "p_D"],
            "hidden_weights_allowed": False,
            "declared_deployment_scenarios": [],
            "endpoint_checks": endpoint_scenarios,
        },
        "operational_carbon_extension": {
            "formula": "C_op,a = N_ops * E_a(p) * CI",
            "carbon_intensity": None,
            "status": "PARAMETRIC_ONLY",
            "absolute_lifecycle_carbon": "BLOCKED_PROCESS_SPECIFIC_EMBODIED_CARBON_UNQUALIFIED",
        },
    }


def physical_summary(
    rows: Sequence[Mapping[str, str]],
    e5_records: Sequence[Mapping[str, Any]],
    diagnostic_pareto: Mapping[str, Any],
) -> Dict[str, Any]:
    selected = [row for row in rows if float(row["clock_period_ns"]) == 10.0 and row["architecture_id"] in {"SECDED", "HSIAO_SECDED"}]
    by_arch: Dict[str, Dict[str, Any]] = {}
    for architecture in ("SECDED", "HSIAO_SECDED"):
        arch_rows = [row for row in selected if row["architecture_id"] == architecture]
        means = {}
        for key in ("standard_cell_area_um2", "wirelength_um", "via_count", "setup_wns_ns", "total_power_w"):
            means[key] = statistics.mean(float(row[key]) for row in arch_rows)
        means["total_instance_area_um2"] = statistics.mean(
            float(row["standard_cell_area_um2"]) + float(row["macro_area_um2"]) for row in arch_rows
        )
        means["timing_feasible_seed_count"] = sum(float(row["setup_wns_ns"]) >= 0 for row in arch_rows)
        means["seed_count"] = len(arch_rows)
        by_arch[architecture] = means

    aggregate_10ns = next(row for row in diagnostic_pareto["records"] if row["clock_period_ns"] == 10.0)
    for point in aggregate_10ns["population"]:
        if point["architecture_id"] in by_arch:
            by_arch[point["architecture_id"]].update(point["metrics"])

    energy: Dict[str, Dict[str, float]] = {}
    for operation in ENERGY_COLUMNS:
        energy[operation] = {}
        for architecture in ("SECDED", "HSIAO_SECDED"):
            values = [
                item["record"]["power"]["ecc_logic_energy_j_per_operation"] * 1e12
                for item in e5_records
                if item["record"]["architecture_id"] == architecture
                and item["record"]["operation_class"] == operation
            ]
            energy[operation][architecture] = statistics.mean(values)
    return {"architectures": by_arch, "energy_mean_pj_per_operation": energy}


def evidence_matrix() -> List[Dict[str, str]]:
    common = "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/"
    v32 = "campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/"
    rows = [
        ("Reliability", "SEC capability", "REGRESSION_VALIDATED", "REGRESSION_VALIDATED", "NOT_APPLICABLE", "REGRESSION_VALIDATED", "functional simulation plus frozen exact code evidence", v32 + "FUNCTIONAL_VALIDATION_SUMMARY.json"),
        ("Reliability", "DED capability", "REGRESSION_VALIDATED", "REGRESSION_VALIDATED", "NOT_APPLICABLE", "REGRESSION_VALIDATED", "functional simulation plus frozen exact code evidence", v32 + "FUNCTIONAL_VALIDATION_SUMMARY.json"),
        ("Physical", "10 ns timing feasibility", "5/5 FEASIBLE", "5/5 FEASIBLE", "5/5 FEASIBLE", "0/5 INFEASIBLE", "post-route STA", common + "TIMING_FEASIBILITY.json"),
        ("Physical", "5 ns timing feasibility", "0/5 INFEASIBLE", "0/5 INFEASIBLE", "5/5 FEASIBLE", "0/5 INFEASIBLE", "inherited post-route STA; no E5", common + "TIMING_FEASIBILITY.json"),
        ("Physical", "area/wirelength/vias/WNS", "QUALIFIED_10NS", "QUALIFIED_10NS", "INHERITED_ONLY", "INFEASIBLE_FOR_EQUAL_PERFORMANCE", "matched post-route", v32 + "PHYSICAL_RUN_RESULTS.csv"),
        ("Power", "E4 vectorless power", "DIAGNOSTIC", "DIAGNOSTIC", "DIAGNOSTIC", "DIAGNOSTIC_INFEASIBLE", "vectorless post-route diagnostic", v32 + "PHYSICAL_RUN_RESULTS.csv"),
        ("Energy", "idle ECC-logic", "4 SEEDS", "4 SEEDS", "MISSING", "MISSING", "E5 logic only", common + "GREEN_V3_3_ADDITIVE_MATRIX.json"),
        ("Energy", "clean-read ECC-logic", "5 SEEDS", "5 SEEDS", "MISSING", "MISSING", "E5 logic only", common + "GREEN_V3_3_ADDITIVE_MATRIX.json"),
        ("Energy", "clean-write ECC-logic", "4 SEEDS", "4 SEEDS", "MISSING", "MISSING", "E5 logic only", common + "GREEN_V3_3_ADDITIVE_MATRIX.json"),
        ("Energy", "correction ECC-logic", "5 SEEDS", "5 SEEDS", "MISSING", "MISSING", "E5 logic only", common + "GREEN_V3_3_ADDITIVE_MATRIX.json"),
        ("Energy", "detection ECC-logic", "5 SEEDS", "5 SEEDS", "MISSING", "MISSING", "E5 logic only", common + "GREEN_V3_3_ADDITIVE_MATRIX.json"),
        ("Energy", "SRAM macro-internal operation energy", "PARTIAL/BLOCKED", "PARTIAL/BLOCKED", "MISSING", "MISSING", "not qualified", common + "SRAM_MACRO_POWER_QUALIFICATION.json"),
        ("Energy", "whole-memory operation energy", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", "not qualified", common + "SRAM_MACRO_POWER_QUALIFICATION.json"),
        ("Reliability", "physical FIT/SDC/DUE", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", "no physical evidence", common + "CLAIM_EVIDENCE_MAP.md"),
        ("Reliability", "Qcrit", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", "no physical evidence", common + "CLAIM_EVIDENCE_MAP.md"),
        ("Reliability", "physical interleaver benefit", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", "no topology/physical validation", v32 + "BIT_MAPPING_AUDIT.json"),
        ("Sustainability", "operational carbon", "PARAMETRIC", "PARAMETRIC", "MISSING_E5", "MISSING_E5", "requires declared N_ops and CI", "GREEN_WORKLOAD_ANALYSIS.json"),
        ("Sustainability", "embodied/manufacturing carbon", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", "process-specific evidence absent", common + "CLAIM_EVIDENCE_MAP.md"),
        ("Sustainability", "absolute lifecycle carbon", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", "not qualified", common + "CLAIM_EVIDENCE_MAP.md"),
    ]
    return [
        {
            "dimension": row[0],
            "quantity": row[1],
            "SECDED": row[2],
            "HSIAO_SECDED": row[3],
            "U0": row[4],
            "BCH_78_64_T2": row[5],
            "evidence_class": row[6],
            "source": row[7],
        }
        for row in rows
    ]


def write_evidence_csv(rows: Sequence[Mapping[str, str]]) -> None:
    path = OUT / "GREEN_EVIDENCE_MATRIX.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def reproducibility_rows(e5_records: Sequence[Mapping[str, Any]], run_manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    tools = run_manifest["toolchain"]
    tool_text = (
        f"ORFS {tools['orfs_commit']}; OpenROAD {tools['openroad_commit']} ({tools['openroad_version']}); "
        f"OpenSTA {tools['opensta_version']}; Yosys {tools['yosys_version']}; {tools['simulation_tool']}; "
        f"container {tools['container_image']}"
    )
    rows = []
    for item in sorted(e5_records, key=lambda x: (x["record"]["architecture_id"], x["record"]["physical_seed"], x["record"]["operation_class"])):
        matrix = item["matrix"]
        record = item["record"]
        run_dir = f"fresh_runs/{record['architecture_id'].lower()}_clk10p0ns_seed{record['physical_seed']}"
        # Directory names use hsiao_secded and secded, matching the lower-case architecture identifiers.
        spef = f"{run_dir}/attempt01/physical/6_final.spef"
        spef_path = CAMPAIGN / spef
        if not spef_path.exists() or sha256(spef_path) != record["parasitics"]["sha256"]:
            raise RuntimeError(f"SPEF provenance mismatch: {spef}")
        vcd_relative = record["activity"]["compressed_preserved_path"]
        vcd_path = ROOT / vcd_relative
        if not vcd_path.exists():
            raise RuntimeError(f"VCD provenance mismatch: {vcd_relative}")
        with gzip.open(vcd_path, "rb") as handle:
            vcd_payload_sha256 = hashlib.sha256(handle.read()).hexdigest()
        if vcd_payload_sha256 != record["activity"]["sha256"]:
            raise RuntimeError(f"VCD payload provenance mismatch: {vcd_relative}")
        rows.append(
            {
                "repository_commit": EVIDENCE_SEAL,
                "campaign_commit": EVIDENCE_SEAL,
                "architecture": record["architecture_id"],
                "seed": record["physical_seed"],
                "operation_class": record["operation_class"],
                "timing_target_ns": record["clock_period_ns"],
                "tool_flow_provenance": tool_text,
                "physical_run_status": "TIMING_FEASIBLE_POST_ROUTE",
                "spef_source": (CAMPAIGN.relative_to(ROOT) / spef).as_posix(),
                "spef_sha256": record["parasitics"]["sha256"],
                "vcd_source": vcd_relative,
                "vcd_sha256": record["activity"]["sha256"],
                "vcd_archive_sha256": sha256(vcd_path),
                "functional_logic_activity_coverage": record["activity"]["coverage"]["functional_logic_coverage_fraction"],
                "required_sram_output_roots_annotated": 72,
                "warm_up_cycles": record["warm_up_cycles"],
                "operation_count": record["exact_operation_count"],
                "energy_boundary": "ECC_LOGIC_EXCLUDING_SRAM_MACRO_INTERNAL_ENERGY",
                "evidence_classification": record["qualification"],
                "artifact_path": (CAMPAIGN.relative_to(ROOT) / matrix["source_result"]).as_posix(),
                "artifact_sha256": matrix["source_result_sha256"],
                "record_id": record["record_id"],
            }
        )
    return rows


def write_reproducibility_csv(rows: Sequence[Mapping[str, Any]]) -> None:
    path = OUT / "GREEN_REPRODUCIBILITY_TABLE.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def nondominated(candidates: Mapping[str, Mapping[str, float]], directions: Mapping[str, str]) -> List[str]:
    front = []
    for name, point in candidates.items():
        dominated = False
        for other_name, other in candidates.items():
            if other_name == name:
                continue
            no_worse = all(
                other[metric] <= point[metric] if direction == "min" else other[metric] >= point[metric]
                for metric, direction in directions.items()
            )
            strictly_better = any(
                other[metric] < point[metric] if direction == "min" else other[metric] > point[metric]
                for metric, direction in directions.items()
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(name)
    return sorted(front)


def pareto_results(physical: Mapping[str, Any], workload: Mapping[str, Any]) -> Dict[str, Any]:
    arch = physical["architectures"]
    energy = physical["energy_mean_pj_per_operation"]
    base = {
        name: {
            "area_um2": arch[name]["total_instance_area_um2"],
            "setup_wns_ns": arch[name]["setup_wns_ns"],
            "clean_read_energy_pj_per_operation": energy["READ_CLEAN"][name],
        }
        for name in ("SECDED", "HSIAO_SECDED")
    }
    scenarios = []
    for endpoint in workload["scenario_mode"]["endpoint_checks"]:
        operation = endpoint["scenario_id"][: -len("_ENDPOINT")]
        points_2d = {
            name: {"area_um2": arch[name]["total_instance_area_um2"], "energy_pj_per_operation": energy[operation][name]}
            for name in ("SECDED", "HSIAO_SECDED")
        }
        points_3d = {
            name: {**point, "setup_wns_ns": arch[name]["setup_wns_ns"]} for name, point in points_2d.items()
        }
        scenarios.append(
            {
                "scenario_id": endpoint["scenario_id"],
                "probabilities": endpoint["probabilities"],
                "area_energy_front": nondominated(points_2d, {"area_um2": "min", "energy_pj_per_operation": "min"}),
                "area_timing_energy_front": nondominated(
                    points_3d,
                    {"area_um2": "min", "energy_pj_per_operation": "min", "setup_wns_ns": "max"},
                ),
                "points": points_3d,
            }
        )
    return {
        "schema_version": 1,
        "evidence_seal": EVIDENCE_SEAL,
        "hard_constraints": {
            "reliability": "validated SECDED correction/detection semantics required",
            "timing": "setup WNS >= 0 ns at 10 ns required",
        },
        "admitted_architectures": ["SECDED", "HSIAO_SECDED"],
        "excluded_architectures": {
            "U0": "fails the mandatory SECDED reliability requirement and lacks E5",
            "BCH_78_64_T2": "0/5 timing-feasible seeds at 10 ns and lacks E5",
        },
        "clean_read_area_timing_energy": {
            "objectives": {"area_um2": "minimize", "setup_wns_ns": "maximize", "clean_read_energy_pj_per_operation": "minimize"},
            "points": base,
            "front": nondominated(base, {"area_um2": "min", "setup_wns_ns": "max", "clean_read_energy_pj_per_operation": "min"}),
            "qualification": "jointly qualified at 10 ns across five matched seeds; architecture means shown",
        },
        "declared_endpoint_fronts": scenarios,
        "global_winner": "NO_GLOBAL_WINNER_QUALIFIED",
        "blocked_fronts": ["whole-memory energy", "physical FIT", "Qcrit", "absolute lifecycle carbon"],
    }


def save_figure(fig: Any, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    metadata = {"Date": "2026-09-09", "Creator": "GREEN ISCAS 2027 deterministic builder"}
    svg_path = FIGURES / f"{stem}.svg"
    fig.savefig(svg_path, bbox_inches="tight", metadata=metadata)
    svg_path.write_text(svg_path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    fig.savefig(FIGURES / f"{stem}.png", dpi=220, bbox_inches="tight", metadata={"Software": metadata["Creator"]})
    plt.close(fig)


def figure_methodology() -> None:
    fig, ax = plt.subplots(figsize=(10.4, 2.7))
    ax.set_axis_off()
    labels = ["Evidence", "Qualification", "Hard\nconstraints", "Operation-aware\nmetrics", "Pareto + workload\ndecision"]
    colors = ["#dcebf7", "#dcebf7", "#ffe8b8", "#dff3e3", "#dff3e3"]
    x_positions = np.linspace(0.02, 0.82, len(labels))
    box_width = 0.16
    for index, (x, label, color) in enumerate(zip(x_positions, labels, colors)):
        box = FancyBboxPatch((x, 0.48), box_width, 0.30, boxstyle="round,pad=0.012", facecolor=color, edgecolor="#263238", linewidth=1.2, zorder=2)
        ax.add_patch(box)
        ax.text(x + box_width / 2, 0.63, label, ha="center", va="center", fontsize=10, weight="bold", zorder=3)
        if index < len(labels) - 1:
            ax.add_patch(FancyArrowPatch((x + box_width + 0.004, 0.63), (x_positions[index + 1] - 0.004, 0.63), arrowstyle="-|>", mutation_scale=13, linewidth=1.2, color="#455a64", zorder=4))
    ax.text(0.50, 0.29, r"$G_a=[R,A,T,W,V,E_I,E_R,E_W,E_C,E_D,C,Q]$; missing entries remain missing", ha="center", fontsize=10)
    blocked = FancyBboxPatch((0.21, 0.04), 0.58, 0.14, boxstyle="round,pad=0.01", facecolor="#f4d7d7", edgecolor="#9b2c2c", linewidth=1.1)
    ax.add_patch(blocked)
    ax.text(0.50, 0.11, "Blocked: whole-memory energy, physical FIT/Qcrit, absolute lifecycle carbon", ha="center", va="center", fontsize=8.5, color="#7f1d1d")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    save_figure(fig, "figure01_green_methodology")


def figure_ordering(stats: Mapping[str, Any]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4), gridspec_kw={"wspace": 0.32})
    panels = [
        (axes[0], [5, 0], "E4 vectorless", "matched seeds (n=5)"),
        (axes[1], [4, 19], "E5 operation-aware", "operation × seed cells (n=23)"),
    ]
    for ax, counts, title, denominator in panels:
        bars = ax.bar([0, 1], counts, color=["#2f855a", "#4c78a8"], width=0.65)
        ax.set_xticks([0, 1], ["Hsiao lower", "SECDED lower"])
        ax.set_title(title, weight="bold", pad=7)
        ax.set_ylabel("Count")
        ax.set_ylim(0, max(counts) * 1.22 + 0.5)
        ax.text(0.5, -0.24, denominator, transform=ax.transAxes, ha="center", fontsize=9)
        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.25, str(count), ha="center", weight="bold")
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Ordering changes after operation-specific activity (denominators differ)", fontsize=11, y=0.98)
    fig.subplots_adjust(top=0.79, bottom=0.24)
    save_figure(fig, "figure02_e4_vs_e5_ordering")


def figure_paired_deltas(matched_rows: Sequence[Mapping[str, str]]) -> None:
    operations = ["READ_CLEAN", "WRITE_CLEAN", "READ_SINGLE_BIT_ERROR_CORRECT", "READ_DOUBLE_BIT_ERROR_DETECT"]
    fig, ax = plt.subplots(figsize=(8.3, 3.35))
    colors = {11: "#7f3c8d", 13: "#11a579", 17: "#3969ac", 19: "#f2b701", 23: "#e73f74"}
    for x, operation in enumerate(operations):
        column = ENERGY_COLUMNS[operation]
        points = [(int(row["seed"]), float(row[column]) * 1e12) for row in matched_rows if row[column]]
        offsets = np.linspace(-0.13, 0.13, len(points))
        for offset, (seed, value) in zip(offsets, points):
            ax.scatter(x + offset, value, color=colors[seed], s=38, edgecolor="white", linewidth=0.5, zorder=3)
        mean = statistics.mean(value for _, value in points)
        ax.scatter(x, mean, marker="D", color="black", s=42, zorder=4)
    ax.axhline(0, color="#333333", linewidth=1.0)
    ax.set_xticks(range(len(operations)), ["Clean\nread\n(n=5)", "Clean\nwrite\n(n=4)", "Correction\n(n=5)", "Detection\n(n=5)"])
    ax.set_ylabel("Hsiao − SECDED energy (pJ/op)")
    ax.set_title("Matched post-route ECC-logic energy differences")
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Line2D([0], [0], marker="o", linestyle="", color=color, label=f"seed {seed}") for seed, color in colors.items()]
    handles.append(plt.Line2D([0], [0], marker="D", linestyle="", color="black", label="mean"))
    ax.legend(handles=handles, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.29), frameon=False, fontsize=8)
    fig.subplots_adjust(bottom=0.39)
    save_figure(fig, "figure03_operation_paired_deltas")


def figure_workload_boundary(workload: Mapping[str, Any]) -> None:
    complete = workload["primary_complete_case_model"]["coefficients_pj_per_operation"]
    all_means = workload["all_available_operation_means_sensitivity"]["coefficients_pj_per_operation"]
    grid = 401
    p_w = np.linspace(0, 1, grid)
    p_i = np.linspace(0, 1, grid)
    xx, yy = np.meshgrid(p_w, p_i)
    p_r = 1 - xx - yy
    mask = p_r < 0
    delta = complete["IDLE"] * yy + complete["READ_CLEAN"] * p_r + complete["WRITE_CLEAN"] * xx
    delta = np.ma.array(delta, mask=mask)
    fig, ax = plt.subplots(figsize=(6.2, 4.7))
    ax.contourf(xx, yy, delta, levels=[-10, 0, 10], colors=["#b7e4c7", "#f3c6c6"], alpha=0.95)
    ax.contour(xx, yy, delta, levels=[0], colors=["#1b4332"], linewidths=2.0)
    delta_all = all_means["IDLE"] * yy + all_means["READ_CLEAN"] * p_r + all_means["WRITE_CLEAN"] * xx
    delta_all = np.ma.array(delta_all, mask=mask)
    ax.contour(xx, yy, delta_all, levels=[0], colors=["#6b21a8"], linewidths=1.6, linestyles="--")
    ax.add_patch(Polygon([[0, 0], [1, 0], [0, 1]], closed=True, fill=False, edgecolor="#222222", linewidth=1.1))
    ax.text(0.10, 0.10, "Hsiao lower\n$\\Delta E<0$", fontsize=10, color="#1b4332", weight="bold")
    ax.text(0.55, 0.22, "SECDED lower\n$\\Delta E>0$", fontsize=10, color="#7f1d1d", weight="bold")
    ax.text(0.49, 0.80, "$p_R=0$", fontsize=9, rotation=-45)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Clean-write fraction $p_W$")
    ax.set_ylabel("Idle fraction $p_I$")
    ax.set_title("Workload preference slice: $p_C=p_D=0$, $p_R=1-p_I-p_W$")
    line_handles = [
        plt.Line2D([0], [0], color="#1b4332", lw=2, label="4-seed complete-case boundary"),
        plt.Line2D([0], [0], color="#6b21a8", lw=1.6, ls="--", label="all-available-means sensitivity"),
    ]
    ax.legend(handles=line_handles, loc="upper right", frameon=True, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "figure04_workload_boundary")


def write_tables(physical: Mapping[str, Any], stats: Mapping[str, Any]) -> None:
    architectures = physical["architectures"]
    energy = physical["energy_mean_pj_per_operation"]
    sec = architectures["SECDED"]
    hsi = architectures["HSIAO_SECDED"]
    rows = [
        ("Total instance area (µm²)", sec["total_instance_area_um2"], hsi["total_instance_area_um2"], hsi["total_instance_area_um2"] - sec["total_instance_area_um2"], "Hsiao higher 5/5", "post-route E4 geometry"),
        ("Standard-cell area (µm²)", sec["standard_cell_area_um2"], hsi["standard_cell_area_um2"], hsi["standard_cell_area_um2"] - sec["standard_cell_area_um2"], "Hsiao higher 5/5", "post-route E4 geometry"),
        ("Wirelength (µm)", sec["wirelength_um"], hsi["wirelength_um"], hsi["wirelength_um"] - sec["wirelength_um"], "Hsiao higher 5/5", "post-route E4 geometry"),
        ("Via count", sec["via_count"], hsi["via_count"], hsi["via_count"] - sec["via_count"], "Hsiao higher 5/5", "post-route E4 geometry"),
        ("Setup WNS (ns)", sec["setup_wns_ns"], hsi["setup_wns_ns"], hsi["setup_wns_ns"] - sec["setup_wns_ns"], "Hsiao better 4/5", "both 5/5 feasible at 10 ns"),
        ("Vectorless total power (mW)", sec["total_power_w"] * 1e3, hsi["total_power_w"] * 1e3, (hsi["total_power_w"] - sec["total_power_w"]) * 1e3, "Hsiao lower 5/5", "E4 diagnostic"),
    ]
    for operation in ("READ_CLEAN", "WRITE_CLEAN", "READ_SINGLE_BIT_ERROR_CORRECT", "READ_DOUBLE_BIT_ERROR_DETECT"):
        metric = stats["metrics"][f"energy_{operation.lower()}"]
        rows.append(
            (
                f"{OP_LABELS[operation]} energy (pJ/op)",
                energy[operation]["SECDED"],
                energy[operation]["HSIAO_SECDED"],
                metric["mean"],
                f"Hsiao lower {metric['negative_count']}/{metric['n']}",
                "E5 ECC-logic only",
            )
        )
    lines = [
        "# Paper tables",
        "",
        "## Primary table — matched 10 ns physical and operation-aware comparison",
        "",
        "All values are arithmetic means across matched placement seeds. Energy excludes SRAM macro-internal energy. The E4 and E5 labels are evidence classes, not technology generations.",
        "",
        "| Metric | SECDED mean | Hsiao mean | Hsiao − SECDED | Paired ordering | Qualification |",
        "|---|---:|---:|---:|---|---|",
    ]
    for metric, secded, hsiao, delta, ordering, qualification in rows:
        if "area" in metric.lower() or "wirelength" in metric.lower() or metric == "Via count":
            formatting = ".1f"
        else:
            formatting = ".4f"
        lines.append(
            f"| {metric} | {format(secded, formatting)} | {format(hsiao, formatting)} | {format(delta, formatting)} | {ordering} | {qualification} |"
        )
    lines.extend(
        [
            "",
            "Table note: total instance area equals standard-cell plus macro instance area. Both architectures use the same 260,332 µm² macro area. The primary table does not include U0 or BCH in energy columns because they lack E5 evidence; BCH also fails the 10 ns timing constraint in all five inherited seeds.",
            "",
            "## Supplementary per-seed values",
            "",
            "Per-seed physical and energy deltas are retained in `GREEN_PAIRED_STATISTICS.json` and the sealed source `E5_MATCHED_SEED_DELTAS.csv`; they should remain in the repository supplement rather than consume manuscript table space.",
        ]
    )
    (OUT / "PAPER_TABLES.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_source_provenance(run_manifest: Mapping[str, Any]) -> None:
    sources = [
        CAMPAIGN / "E5_MATCHED_SEED_DELTAS.csv",
        CAMPAIGN / "GREEN_V3_3_ADDITIVE_MATRIX.json",
        CAMPAIGN / "RUN_MANIFEST.json",
        CAMPAIGN / "SRAM_MACRO_POWER_QUALIFICATION.json",
        CAMPAIGN / "TIMING_FEASIBILITY.json",
        V32 / "PHYSICAL_RUN_RESULTS.csv",
        V32 / "FUNCTIONAL_VALIDATION_SUMMARY.json",
    ]
    write_json(
        OUT / "SOURCE_PROVENANCE.json",
        {
            "schema_version": 1,
            "evidence_seal_commit": EVIDENCE_SEAL,
            "source_tree_diff_against_seal": "CLEAN",
            "sealed_campaign_hash_manifest_verified_entries": 1697,
            "toolchain": run_manifest["toolchain"],
            "sources": [
                {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "size_bytes": path.stat().st_size}
                for path in sources
            ],
            "generation_policy": "read sealed evidence; write only paper/iscas2027_green_operation_aware",
        },
    )


def write_hash_manifest() -> None:
    manifest = OUT / "NEW_ARTIFACTS.sha256"
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path != manifest and "__pycache__" not in path.parts)
    text = "".join(f"{sha256(path)}  {path.relative_to(OUT).as_posix()}\n" for path in files)
    manifest.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    verify_evidence_tree()
    FIGURES.mkdir(parents=True, exist_ok=True)
    matched_rows = read_csv(CAMPAIGN / "E5_MATCHED_SEED_DELTAS.csv")
    matrix = load_json(CAMPAIGN / "GREEN_V3_3_ADDITIVE_MATRIX.json")
    run_manifest = load_json(CAMPAIGN / "RUN_MANIFEST.json")
    e5_records = extract_e5_records(matrix)
    if len(e5_records) != 46:
        raise RuntimeError(f"expected 46 canonical E5 records, found {len(e5_records)}")

    stats = paired_statistics(matched_rows)
    workload = workload_analysis(matched_rows, stats)
    physical = physical_summary(
        read_csv(V32 / "PHYSICAL_RUN_RESULTS.csv"),
        e5_records,
        load_json(V32 / "DIAGNOSTIC_PARETO.json"),
    )
    pareto = pareto_results(physical, workload)
    write_json(OUT / "GREEN_PAIRED_STATISTICS.json", stats)
    write_json(OUT / "GREEN_WORKLOAD_ANALYSIS.json", workload)
    write_json(OUT / "GREEN_PARETO_RESULTS.json", pareto)
    write_evidence_csv(evidence_matrix())
    write_reproducibility_csv(reproducibility_rows(e5_records, run_manifest))
    write_tables(physical, stats)
    write_source_provenance(run_manifest)
    matplotlib.rcParams["svg.hashsalt"] = "green-iscas-2027"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    figure_methodology()
    figure_ordering(stats)
    figure_paired_deltas(matched_rows)
    figure_workload_boundary(workload)
    write_hash_manifest()
    print(f"built {OUT.relative_to(ROOT).as_posix()} from {EVIDENCE_SEAL}")


if __name__ == "__main__":
    main()
