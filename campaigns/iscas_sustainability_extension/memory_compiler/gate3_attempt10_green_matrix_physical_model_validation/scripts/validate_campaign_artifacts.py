#!/usr/bin/env python3
"""Validate Attempt10 cross-artifact counts, schemas, and evidence gates."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator


HERE = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((HERE / path).read_text(encoding="utf-8"))


def csv_count(path: str) -> int:
    with (HERE / path).open(newline="", encoding="utf-8-sig") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def finite_json(value) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite_json(item) for item in value.values())
    if isinstance(value, list):
        return all(finite_json(item) for item in value)
    return True


def main() -> int:
    required = [
        "README.md", "PHASE_SUMMARY.md", "CAMPAIGN_STATUS.json", "ENVIRONMENT_MANIFEST.json", "ARTIFACT_MANIFEST.json",
        "liberty/LIBERTY_TRANSITION_MODEL_AUDIT.json", "liberty/LIBERTY_TRANSITION_MODEL_AUDIT.md",
        "liberty/LIBERTY_SENSITIVITY_RESULTS.json", "liberty/LIBERTY_SENSITIVITY_RESULTS.csv", "liberty/LIBERTY_SENSITIVITY_ANALYSIS.md",
        "rstb/RSTB_INTERFACE_CHARACTERIZATION.json", "rstb/RSTB_INTERFACE_CHARACTERIZATION.csv", "rstb/RSTB_INTERFACE_CHARACTERIZATION.md",
        "green_matrix/GREEN_MATRIX_SCHEMA.json", "green_matrix/GREEN_MATRIX_PHYSICAL.csv", "green_matrix/GREEN_MATRIX_PHYSICAL.json",
        "green_matrix/GREEN_MATRIX_RELIABILITY.csv", "green_matrix/GREEN_MATRIX_RELIABILITY.json",
        "green_matrix/GREEN_MATRIX_RAW.csv", "green_matrix/GREEN_MATRIX_NORMALIZED.csv", "green_matrix/GREEN_MATRIX_METADATA.json",
        "energy/ACTIVITY_MODEL.md", "energy/WORKLOAD_MANIFEST.json", "energy/ENERGY_RESULTS.csv", "energy/ENERGY_RESULTS.json",
        "interleaving/BIT_INTERLEAVING_MAP.json", "interleaving/BIT_INTERLEAVING_PHYSICAL_COST.csv", "interleaving/MBU_TO_CODEWORD_MAPPING.json",
        "carbon/CARBON_MODEL.md", "carbon/CARBON_ASSUMPTIONS.json", "carbon/CARBON_RESULTS.csv", "carbon/CARBON_RESULTS.json", "carbon/CARBON_SENSITIVITY.csv",
        "pareto/PARETO_RESULTS.json", "pareto/PARETO_RESULTS.csv", "pareto/PARETO_ANALYSIS.md",
        "integrity/baseline_repository.json", "integrity/baseline_external.json", "integrity/final_repository.json", "integrity/final_external.json",
        "integrity/external_raw_manifest.json", "integrity/REGRESSION_STATUS.json",
    ]
    json_documents = [json.loads(path.read_text(encoding="utf-8")) for path in HERE.rglob("*.json")]
    sensitivity = load("liberty/LIBERTY_SENSITIVITY_RESULTS.json")
    physical = load("green_matrix/GREEN_MATRIX_PHYSICAL.json")
    reliability = load("green_matrix/GREEN_MATRIX_RELIABILITY.json")
    energy = load("energy/ENERGY_RESULTS.json")
    postroute = load("energy/POSTROUTE_ACTIVITY_DIAGNOSTIC.json")
    carbon = load("carbon/CARBON_RESULTS.json")
    pareto = load("pareto/PARETO_RESULTS.json")
    status = load("CAMPAIGN_STATUS.json")
    schema_errors = list(Draft202012Validator(load("green_matrix/GREEN_MATRIX_SCHEMA.json")).iter_errors(physical))
    phase_fields = {
        "exact_classification", "proven", "unproven", "original_vs_corrected_model", "u0_e0_matched_results",
        "five_seed_robustness", "effect_on_ppa", "effect_on_energy", "effect_on_reliability", "effect_on_carbon",
        "effect_on_green_ranking", "impact_on_iscas_claims", "new_unsupported_claims", "repository_integrity_status",
        "recommended_next_action",
    }
    checks = {
        "all_required_deliverables_exist": all((HERE / path).is_file() for path in required),
        "all_json_documents_parse_and_are_finite": all(finite_json(item) for item in json_documents),
        "green_physical_json_schema_valid": not schema_errors,
        "sensitivity_rows_30": len(sensitivity["rows"]) == csv_count("liberty/LIBERTY_SENSITIVITY_RESULTS.csv") == 30,
        "sensitivity_20_complete_10_explicit_aborts": sum(row["run_status"] == "COMPLETE" for row in sensitivity["rows"]) == 20 and sum(row["run_status"] == "ABORTED_RSZ_0090" for row in sensitivity["rows"]) == 10,
        "original_attempt09_reproduction_10_of_10": sensitivity["original_attempt09_reproduction"]["metrics_and_deterministic_artifacts_exact_pair_count"] == 10,
        "physical_rows_20_and_cross_format_equal": len(physical["rows"]) == csv_count("green_matrix/GREEN_MATRIX_PHYSICAL.csv") == 20,
        "physical_model_balance_10_and_10": sum(row["liberty_model"] == "UPSTREAM_ORIGINAL" for row in physical["rows"]) == 10 and sum(row["liberty_model"] == "RESEARCH_CORRECTED_DIAGNOSTIC" for row in physical["rows"]) == 10,
        "gate3_never_promoted": all(str(row["gate3_status"]).startswith("FAIL") for row in physical["rows"]),
        "energy_rows_16_cross_format_and_unqualified": len(energy["rows"]) == csv_count("energy/ENERGY_RESULTS.csv") == 16 and all(row["energy_access_j"] == "NOT_QUALIFIED" for row in energy["rows"]),
        "postroute_is_partial_seed11_diagnostic": len(postroute["rows"]) == 2 and all(row["seed"] == 11 and row["energy_evidence_level"] == "NOT_QUALIFIED" for row in postroute["rows"]),
        "reliability_rows_72_cross_format": len(reliability["rows"]) == csv_count("green_matrix/GREEN_MATRIX_RELIABILITY.csv") == 72,
        "physical_reliability_results_empty": reliability["physical_event_results"] == [],
        "carbon_rows_160_cross_format_and_unqualified": len(carbon["rows"]) == csv_count("carbon/CARBON_RESULTS.csv") == 160 and all(row["total_lifecycle_carbon_kgCO2e"] == "NOT_QUALIFIED" for row in carbon["rows"]),
        "carbon_sensitivity_rows_1280": csv_count("carbon/CARBON_SENSITIVITY.csv") == 1280,
        "raw_green_rows_5760": csv_count("green_matrix/GREEN_MATRIX_RAW.csv") == 5760,
        "normalized_green_has_no_promoted_rows": csv_count("green_matrix/GREEN_MATRIX_NORMALIZED.csv") == 0,
        "pareto_rows_5760_cross_format_and_zero_eligible": csv_count("pareto/PARETO_RESULTS.csv") == len(pareto["excluded_rows"]) == 5760 and pareto["eligible_row_count"] == 0,
        "phase_summaries_A_through_J": [item["phase"] for item in status["phase_summaries"]] == list("ABCDEFGHIJ"),
        "each_phase_has_all_15_required_summary_fields": all(phase_fields <= set(item) for item in status["phase_summaries"]),
        "baseline_and_final_integrity_pass": all(load(path)["status"] == "PASS" for path in ["integrity/baseline_repository.json", "integrity/baseline_external.json", "integrity/final_repository.json", "integrity/final_external.json"]),
        "regression_has_only_expected_frozen_failures": load("integrity/REGRESSION_STATUS.json")["no_new_regression"] is True,
        "external_raw_manifest_2950_files": load("integrity/external_raw_manifest.json")["file_count"] == 2950,
    }
    document = {
        "schema_version": 1,
        "classification": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "check_count": len(checks),
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "json_document_count": len(json_documents),
        "green_schema_error_count": len(schema_errors),
    }
    output = HERE / "integrity" / "consistency_validation.json"
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(document))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
