#!/usr/bin/env python3
"""Build the DATE 2027 Gate 05 reliability x physical-cost evidence join.

This script is deliberately read-only with respect to Gates 02, 03, 03R, and
04.  It copies no stale thesis-era projections and launches no physical flow.
"""

from __future__ import annotations

import csv
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_05"
GATE02 = ROOT / "docs/date2027/rigour_gate_02"
GATE03 = ROOT / "docs/date2027/rigour_gate_03"
GATE03R = ROOT / "docs/date2027/rigour_gate_03r"
GATE04 = ROOT / "docs/date2027/rigour_gate_04_final"

TRACE_CLASSES = ("no_error", "single_error", "double_error")
PPA_METRICS = (
    "standard_cell_instance_area_um2",
    "wns_ns",
    "tns_ns",
    "worst_setup_slack_ns",
    "worst_hold_slack_ns",
    "achieved_fmax_mhz",
    "detailed_route_wirelength_um",
    "global_route_wirelength_um",
    "via_count",
    "final_drc_count",
)

IMPLEMENTATIONS = (
    {
        "implementation_id": "secded-rtl-combinational-72-64-v1",
        "label": "Conventional SECDED (72,64), combinational",
        "reliability_source_implementation_id": "secded-rtl-combinational-72-64-v1",
        "reliability_aggregate": "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/secded-rtl-combinational-72-64-v1.json",
        "mapping_status": "DIRECT_GATE02_IDENTITY_WITH_GATE03R_EXACT_RTL_PROOF",
        "mapping_evidence": (
            "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/secded-rtl-combinational-72-64-v1.json",
            "docs/date2027/rigour_gate_03r/ENCODER_PROOF_MATRIX.csv",
            "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json",
        ),
    },
    {
        "implementation_id": "secded-rtl-pipelined-72-64-v1",
        "label": "Conventional SECDED (72,64), pipelined",
        "reliability_source_implementation_id": "secded-rtl-combinational-72-64-v1",
        "reliability_aggregate": "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/secded-rtl-combinational-72-64-v1.json",
        "mapping_status": "EXACT_CODE_LEVEL_SEMANTICS_TRANSFERRED_BY_UNIVERSAL_GATE03R_EQUIVALENCE",
        "mapping_evidence": (
            "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md",
            "docs/date2027/rigour_gate_03r/ENCODER_PROOF_MATRIX.csv",
            "docs/date2027/rigour_gate_03r/DECODER_PROOF_MATRIX.csv",
            "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json",
        ),
    },
    {
        "implementation_id": "hsiao-generated-combinational-72-64-v1",
        "label": "Hsiao SECDED (72,64), combinational",
        "reliability_source_implementation_id": "hsiao-generated-combinational-72-64-v1",
        "reliability_aggregate": "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/hsiao-generated-combinational-72-64-v1.json",
        "mapping_status": "DIRECT_GATE02_IDENTITY_WITH_TWO_GATE03_COMPILED_FUNCTIONAL_CAMPAIGNS",
        "mapping_evidence": (
            "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/hsiao-generated-combinational-72-64-v1.json",
            "docs/date2027/rigour_gate_03/baseline/run-01/hsiao/functional_verification.log",
            "docs/date2027/rigour_gate_03/baseline/run-02/hsiao/functional_verification.log",
        ),
    },
    {
        "implementation_id": "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
        "label": "Shortened BCH (78,64,t=2), combinational syndrome/Chien",
        "reliability_source_implementation_id": "shortened-bch-78-64-t2-v1-reference-decoder",
        "reliability_aggregate": "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/shortened-bch-78-64-t2-v1-reference-decoder.json",
        "mapping_status": "EXACT_GATE02_REFERENCE_TO_GATE03R_RTL_IDENTITY_TRANSFER",
        "mapping_evidence": (
            "docs/date2027/rigour_gate_03r/BCH_78_64_T2_CONTRACT.md",
            "docs/date2027/rigour_gate_03r/BCH_IDENTITY_RECONSTRUCTION.json",
            "docs/date2027/rigour_gate_03r/ENCODER_PROOF_MATRIX.csv",
            "docs/date2027/rigour_gate_03r/DECODER_PROOF_MATRIX.csv",
            "docs/date2027/rigour_gate_03r/EXACT_PROOF_SUMMARY.json",
            "docs/date2027/rigour_gate_03r/BCH_WEIGHT3_CHARACTERIZATION.json",
        ),
    },
)

SOURCE_ROLES = {
    "docs/date2027/rigour_gate_02/GATE_02_REPORT.md": "Gate 02 scope boundary, including absence of physical, FIT, SER, and physical-placement evidence",
    "docs/date2027/rigour_gate_02/baseline/translation_invariance.json": "Gate 02 basis for payload-translation invariance of finite mask results",
    "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/secded-rtl-combinational-72-64-v1.json": "Exact SECDED reliability outcomes by finite fault universe",
    "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/hsiao-generated-combinational-72-64-v1.json": "Exact Hsiao reliability outcomes by finite fault universe",
    "docs/date2027/rigour_gate_02/baseline/implementation_aggregates/shortened-bch-78-64-t2-v1-reference-decoder.json": "Exact BCH reliability outcomes by finite fault universe",
    "docs/date2027/rigour_gate_03/baseline/run-01/hsiao/functional_verification.log": "First compiled Hsiao RTL campaign",
    "docs/date2027/rigour_gate_03/baseline/run-02/hsiao/functional_verification.log": "Second compiled Hsiao RTL campaign",
    "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md": "SECDED code identity, latency, initiation interval, and universal equivalence contract",
    "docs/date2027/rigour_gate_03r/ENCODER_PROOF_MATRIX.csv": "Exact encoder identity results",
    "docs/date2027/rigour_gate_03r/DECODER_PROOF_MATRIX.csv": "Exact decoder identity results",
    "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json": "Universal SECDED equivalence summary",
    "docs/date2027/rigour_gate_03r/BCH_78_64_T2_CONTRACT.md": "Frozen BCH construction and proof boundary",
    "docs/date2027/rigour_gate_03r/BCH_IDENTITY_RECONSTRUCTION.json": "Independent BCH identity reconstruction",
    "docs/date2027/rigour_gate_03r/EXACT_PROOF_SUMMARY.json": "BCH 3,082-job symbolic proof summary",
    "docs/date2027/rigour_gate_03r/BCH_WEIGHT3_CHARACTERIZATION.json": "BCH exhaustive zero-payload weight-3 characterization summary",
    "docs/date2027/rigour_gate_04_final/GATE04_FINAL_ECC_SET.json": "Frozen Gate 04 implementation identities and comparison boundary",
    "docs/date2027/rigour_gate_04_final/GATE04_EXPERIMENT_MANIFEST.json": "Frozen physical environment and useful-operation definition",
    "docs/date2027/rigour_gate_04_final/GATE04_RAW_RESULTS.json": "Authoritative physical and full-precision power values",
    "docs/date2027/rigour_gate_04_final/GATE04_POWER_ACTIVITY_AUDIT.json": "Read-only VCD activity counts and trace hashes",
    "scripts/gate04/generate_traces.py": "Frozen trace construction, reset, valid workload, and pipeline drain behavior",
    "scripts/gate04/rtl/gate04_boundaries.sv": "Common registered boundaries and architecture-specific valid alignment",
    "scripts/gate05/build_gate05.py": "Gate 05 deterministic evidence-join and derived-metric implementation",
}


def read_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def write_json(name: str, value: Any) -> None:
    (OUT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def weight_of(row: dict[str, Any]) -> int:
    return int(json.loads(row["universe_definition"])["weight"])


def exact_universe(row: dict[str, Any]) -> dict[str, Any]:
    definition = json.loads(row["universe_definition"])
    return {
        "source_universe_id": row["universe_id"],
        "weight": definition["weight"],
        "coordinate_space": definition["coordinate_space"],
        "kind": definition["kind"],
        "declared_capability": row["declared_capability"],
        "proven_capability": row["proven_capability"],
        "exhaustive": row["exhaustive"],
        "total_masks": row["total_masks"],
        "clean": row["clean"],
        "corrected": row["corrected"],
        "due": row["due"],
        "sdc_miscorrection": row["sdc_miscorrection"],
        "sdc_undetected": row["sdc_undetected"],
        "invalid_state": row["invalid_state"],
        "correction_fraction": row["correction_fraction"],
        "due_fraction": row["due_fraction"],
        "sdc_fraction": row["sdc_fraction"],
        "safe_handling_fraction": row["safe_handling_fraction"],
        "detection_fraction": row["detection_fraction"],
        "ordered_transcript_sha256": row["ordered_transcript_sha256"],
        "source": {
            "path": f"docs/date2027/rigour_gate_02/{row['evidence_path']}",
            "selector": f"aggregates[universe_id={row['universe_id']}]",
        },
    }


def percent_delta(value: float, reference: float) -> float:
    return (value - reference) / reference * 100.0


def reliability_record(spec: dict[str, Any]) -> dict[str, Any]:
    aggregate = read_json(spec["reliability_aggregate"])
    assert aggregate["implementation_id"] == spec["reliability_source_implementation_id"]
    universes = [exact_universe(row) for row in sorted(aggregate["aggregates"], key=weight_of)]
    assert [row["weight"] for row in universes] == [0, 1, 2, 3]
    support = [row for row in universes if row["weight"] in (1, 2)]
    support_total = sum(row["total_masks"] for row in support)
    support_safe = sum(row["corrected"] + row["due"] for row in support)
    assert support_total == support_safe
    weight3 = universes[3]
    return {
        "code_id": aggregate["code_id"],
        "source_implementation_id": aggregate["implementation_id"],
        "application_to_architecture": spec["mapping_status"],
        "gate_status": aggregate["gate_status"],
        "exact_fault_universes": universes,
        "declared_proven_error_universe": "all canonical-storage-coordinate masks of weight 1 and 2; weight 3 is observation only",
        "modeled_support_fault_coverage": {
            "definition": "(CORRECTED + DUE) over the combined exhaustive weight-1 and weight-2 universes",
            "safe_masks": support_safe,
            "total_masks": support_total,
            "fraction": str(Fraction(support_safe, support_total)),
            "sdc_masks": sum(row["sdc_miscorrection"] + row["sdc_undetected"] for row in support),
        },
        "weight3_miscorrection_behavior": {
            "claim_scope": "EXHAUSTIVE_OBSERVATION_ONLY_NOT_A_CORRECTION_GUARANTEE",
            "sdc_miscorrection": weight3["sdc_miscorrection"],
            "sdc_undetected": weight3["sdc_undetected"],
            "sdc_fraction": weight3["sdc_fraction"],
            "due": weight3["due"],
            "due_fraction": weight3["due_fraction"],
            "total_masks": weight3["total_masks"],
        },
        "placement_interleaving": {
            "value": None,
            "missing_reason": "METRIC_NOT_PROVEN",
            "reason": "Gate 02 explicitly states that logical adjacency has no physical bit/interleave mapping; arbitrary-weight universes are canonical storage coordinates.",
        },
        "fit_ser_projection": {
            "value": None,
            "missing_reason": "METRIC_NOT_PROVEN",
            "reason": "No FIT/SER projection was validated by Gates 02/03/03R/04.",
        },
        "field_or_distribution_weighted_sdc_due": {
            "value": None,
            "missing_reason": "METRIC_NOT_PROVEN",
            "reason": "Exact finite-universe fractions are available, but no frozen operational fault-probability distribution exists for Gate 05 weighting.",
        },
        "identity_evidence": list(spec["mapping_evidence"]),
    }


def operation_normalization(manifest: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    power_rows = raw["power_results"]
    counts = {row["useful_operations"] for row in power_rows}
    durations = {row["total_time_ps"] for row in power_rows}
    assert counts == {100000}
    assert durations == {1000100000}
    boundary = manifest["comparison_boundary"]
    assert boundary["initiation_interval_cycles"] == 1
    assert boundary["latency_cycles"]["secded-rtl-combinational-72-64-v1"] == 1
    assert boundary["latency_cycles"]["secded-rtl-pipelined-72-64-v1"] == 3
    return {
        "status": "VALID_FOR_EQUIVALENT_STEADY_STREAM_USEFUL_OPERATION_COMPARISON",
        "useful_operation_definition": "one accepted 64-bit comparison transaction per asserted-valid cycle, exercising one independent encoder payload and one independent decoder codeword channel in parallel",
        "useful_operations_per_trace": 100000,
        "valid_workload_cycles": 100000,
        "reset_cycles": 6,
        "drain_cycles": 4,
        "total_trace_cycles": 100010,
        "total_time_ps": 1000100000,
        "effective_trace_time_ps_per_useful_operation": 10001.0,
        "common_clock_period_ns": 10.0,
        "common_initiation_interval_cycles": 1,
        "latency_cycles": boundary["latency_cycles"],
        "pipeline_drain_adjudication": "four invalid drain cycles exceed the three-cycle pipelined SECDED comparison-boundary latency; all 100,000 accepted inputs drain",
        "comparison_scope": "steady-stream energy per accepted comparison transaction, not single-request response energy or latency",
        "equivalent_work_basis": "Gate 03R proves identical conventional SECDED encoder/decoder behavior after temporal alignment; both traces use the same conventional_secded input VCD and physical comparison boundary",
        "overhead_treatment": "the common six reset plus four drain cycles are included in every reported trace duration and divided by the same 100,000 useful operations",
        "sources": [
            "docs/date2027/rigour_gate_04_final/GATE04_EXPERIMENT_MANIFEST.json",
            "docs/date2027/rigour_gate_04_final/GATE04_RAW_RESULTS.json",
            "docs/date2027/rigour_gate_04_final/GATE04_POWER_ACTIVITY_AUDIT.json",
            "scripts/gate04/generate_traces.py",
            "scripts/gate04/rtl/gate04_boundaries.sv",
            "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md",
        ],
    }


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    final_set = read_json("docs/date2027/rigour_gate_04_final/GATE04_FINAL_ECC_SET.json")
    manifest = read_json("docs/date2027/rigour_gate_04_final/GATE04_EXPERIMENT_MANIFEST.json")
    raw = read_json("docs/date2027/rigour_gate_04_final/GATE04_RAW_RESULTS.json")
    final_by_id = {
        row["implementation_id"]: row
        for row in final_set["records"]
        if row["classification"] == "INCLUDED"
    }
    physical_by_id = {row["implementation_id"]: row for row in raw["physical_results"]}
    power_by_id: dict[str, dict[str, dict[str, Any]]] = {}
    for row in raw["power_results"]:
        power_by_id.setdefault(row["implementation_id"], {})[row["trace_class"]] = row
    expected_ids = [spec["implementation_id"] for spec in IMPLEMENTATIONS]
    assert list(final_set["included_implementation_ids"]) == expected_ids
    assert set(physical_by_id) == set(expected_ids)

    normalization = operation_normalization(manifest, raw)
    reliability_by_id = {spec["implementation_id"]: reliability_record(spec) for spec in IMPLEMENTATIONS}

    identity_records = []
    integrated_records = []
    missing_records = []
    for spec in IMPLEMENTATIONS:
        impl = spec["implementation_id"]
        identity = final_by_id[impl]
        reliability = reliability_by_id[impl]
        physical = physical_by_id[impl]
        powers = power_by_id.get(impl, {})
        architecture = {
            "organization": identity["organization"],
            "pipeline_depth_cycles": identity["pipeline_depth_cycles"],
            "nominal_operation_latency_cycles": identity["nominal_operation_latency_cycles"],
            "initiation_interval_cycles": identity["initiation_interval_cycles"],
            "throughput_capability": identity["throughput_capability"],
            "payload_width_bits": identity["payload_width_bits"],
            "encoded_width_bits": identity["encoded_width_bits"],
            "rtl_top": identity["rtl_top"],
            "implementation_variant": identity["implementation_variant"],
        }
        full_point = physical["characterization_status"] != "PHYSICAL_CHARACTERIZATION_PARTIAL"
        identity_records.append(
            {
                "implementation_id": impl,
                "label": spec["label"],
                "code_id": reliability["code_id"],
                "reliability_source_implementation_id": spec["reliability_source_implementation_id"],
                "mapping_status": spec["mapping_status"],
                "mapping_evidence": list(spec["mapping_evidence"]),
                "correction_capability": identity["correction_capability"],
                "formal_exhaustive_correctness_status": identity["formal_exhaustive_correctness_status"],
                "architecture": architecture,
                "architecture_specific_physical_identity_preserved": True,
                "full_ppa_point_available": full_point,
                "pareto_input_status": "ELIGIBLE_FOR_FUTURE_FULL_DIMENSION_ANALYSIS" if full_point else "EXCLUDE_FROM_FULL_PPA_PARETO_PPA_UNAVAILABLE",
                "sources": {
                    "identity": "docs/date2027/rigour_gate_04_final/GATE04_FINAL_ECC_SET.json",
                    "physical": "docs/date2027/rigour_gate_04_final/GATE04_RAW_RESULTS.json",
                    "reliability": spec["reliability_aggregate"],
                },
            }
        )

        missing_reasons: dict[str, str] = {}
        if not full_point:
            for metric in PPA_METRICS:
                missing_reasons[f"physical.metrics.{metric}"] = "PPA_UNAVAILABLE"
            for trace_class in TRACE_CLASSES:
                missing_reasons[f"power_by_trace.{trace_class}"] = "PPA_UNAVAILABLE"
            missing_reasons["future_full_dimension_pareto_point"] = "PPA_UNAVAILABLE"
        if physical["timing_feasibility"] == "FAILS_10NS":
            for trace_class in TRACE_CLASSES:
                missing_reasons[
                    f"power_by_trace.{trace_class}.metrics.achievable_total_energy_pj_per_operation"
                ] = "TARGET_CLOCK_INFEASIBLE"
        missing_reasons["reliability.fit_ser_projection"] = "METRIC_NOT_PROVEN"
        missing_reasons["reliability.placement_interleaving"] = "METRIC_NOT_PROVEN"
        missing_reasons["reliability.field_or_distribution_weighted_sdc_due"] = "METRIC_NOT_PROVEN"
        for field, reason in missing_reasons.items():
            missing_records.append(
                {
                    "implementation_id": impl,
                    "field": field,
                    "missing_reason": reason,
                    "explanation": (
                        "Gate 04 Hsiao synthesis stopped under the frozen memory policy; no PPA is fabricated."
                        if reason == "PPA_UNAVAILABLE"
                        else "BCH failed the common 10 ns target; target-constraint energy is diagnostic, not achievable."
                        if reason == "TARGET_CLOCK_INFEASIBLE"
                        else reliability[
                            "fit_ser_projection" if "fit_ser" in field else
                            "placement_interleaving" if "placement" in field else
                            "field_or_distribution_weighted_sdc_due"
                        ]["reason"]
                    ),
                }
            )

        integrated_records.append(
            {
                "implementation_id": impl,
                "label": spec["label"],
                "code_id": reliability["code_id"],
                "correction_capability": identity["correction_capability"],
                "architecture": architecture,
                "reliability": reliability,
                "physical": physical,
                "power_by_trace": {trace: powers.get(trace) for trace in TRACE_CLASSES},
                "missing_reasons": missing_reasons,
                "provenance": {
                    "identity": {
                        "path": "docs/date2027/rigour_gate_04_final/GATE04_FINAL_ECC_SET.json",
                        "selector": f"records[implementation_id={impl}]",
                    },
                    "physical": {
                        "path": "docs/date2027/rigour_gate_04_final/GATE04_RAW_RESULTS.json",
                        "selector": f"physical_results[implementation_id={impl}]",
                    },
                    "power": {
                        "path": "docs/date2027/rigour_gate_04_final/GATE04_RAW_RESULTS.json",
                        "selector": f"power_results[implementation_id={impl}]",
                    },
                    "reliability": {
                        "path": spec["reliability_aggregate"],
                        "selector": "aggregates[*]",
                        "identity_transfer_evidence": list(spec["mapping_evidence"]),
                    },
                },
            }
        )

    identity_output = {
        "schema_version": 1,
        "gate": "DATE 2027 Gate 05 reliability x physical-cost integration",
        "implementation_count": len(identity_records),
        "architecture_identity_required": True,
        "operation_normalization": normalization,
        "implementations": identity_records,
    }
    write_json("GATE05_IMPLEMENTATION_IDENTITY.json", identity_output)

    source_map = {
        "schema_version": 1,
        "policy": {
            "only_gate_validated_evidence": True,
            "stale_thesis_values_allowed": False,
            "missing_values_converted_to_zero": False,
            "physical_runs_launched": False,
        },
        "source_artifacts": [
            {"path": path, "sha256": sha256(path), "role": role}
            for path, role in sorted(SOURCE_ROLES.items())
        ],
        "implementation_sources": [
            {
                "implementation_id": spec["implementation_id"],
                "reliability_source_implementation_id": spec["reliability_source_implementation_id"],
                "reliability_aggregate": spec["reliability_aggregate"],
                "identity_transfer": list(spec["mapping_evidence"]),
                "physical_source": "docs/date2027/rigour_gate_04_final/GATE04_RAW_RESULTS.json",
            }
            for spec in IMPLEMENTATIONS
        ],
        "quantity_rules": {
            "sdc_due": "exact counts and rational fractions remain universe-specific; no cross-universe averaging",
            "power": "all three Gate 04 trace classes retained separately; no averaging",
            "energy": "achievable energy populated only when MEETS_10NS; target-constraint diagnostic estimate retained separately",
            "fit_ser": "METRIC_NOT_PROVEN because no frozen validated projection exists",
            "placement_interleaving": "METRIC_NOT_PROVEN because Gate 02 adjacency is logical, not a physical mapping",
        },
    }
    write_json("GATE05_RELIABILITY_SOURCE_MAP.json", source_map)

    integrated_output = {
        "schema_version": 1,
        "gate04_environment_identity": manifest["authoritative_environment_identity"],
        "row_granularity": "one exact hardware architecture; code-level reliability may transfer only through listed equivalence evidence",
        "headline_power_basis": "no_error trace; single_error and double_error remain separate in every record",
        "sdc_due_basis": "exhaustive canonical-coordinate finite universes, never field-rate weighted",
        "operation_normalization": normalization,
        "records": integrated_records,
    }
    write_json("GATE05_INTEGRATED_RESULTS.json", integrated_output)

    csv_fields = [
        "implementation_id", "ecc_architecture", "code_id", "reliability_source_implementation_id",
        "reliability_transfer_status", "correction_capability", "declared_proven_error_universe",
        "modeled_support_fault_coverage_fraction", "weight3_universe_id", "weight3_sdc_count",
        "weight3_sdc_fraction", "weight3_due_count", "weight3_due_fraction",
        "weight3_miscorrection_claim_scope", "placement_interleaving", "fit_ser_projection",
        "payload_width_bits", "encoded_width_bits", "redundancy_bits", "organization",
        "pipeline_depth_cycles", "nominal_operation_latency_cycles", "initiation_interval_cycles",
        "physical_characterization_status", "area_um2", "wns_ns", "tns_ns", "fmax_mhz",
        "feasible_10ns", "no_error_power_w", "no_error_energy_estimate_pj_per_operation",
        "no_error_achievable_energy_pj_per_operation", "single_error_power_w",
        "single_error_achievable_energy_pj_per_operation", "double_error_power_w",
        "double_error_achievable_energy_pj_per_operation", "detailed_wirelength_um", "drc_count",
        "power_interpretation", "full_ppa_pareto_point_eligible",
    ]
    with (OUT / "GATE05_INTEGRATED_RESULTS.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields, lineterminator="\n")
        writer.writeheader()
        for spec, record in zip(IMPLEMENTATIONS, integrated_records):
            reliability = record["reliability"]
            w3 = reliability["exact_fault_universes"][3]
            physical = record["physical"]
            metrics = physical["metrics"]
            powers = record["power_by_trace"]
            ppa_missing = physical["characterization_status"] == "PHYSICAL_CHARACTERIZATION_PARTIAL"

            def physical_value(key: str) -> Any:
                return "PPA_UNAVAILABLE" if ppa_missing else metrics[key]

            def power_value(trace: str, key: str) -> Any:
                row = powers[trace]
                if row is None:
                    return "PPA_UNAVAILABLE"
                value = row["metrics"][key]
                if value is None and key == "achievable_total_energy_pj_per_operation":
                    return "TARGET_CLOCK_INFEASIBLE"
                return value

            writer.writerow(
                {
                    "implementation_id": record["implementation_id"],
                    "ecc_architecture": record["label"],
                    "code_id": record["code_id"],
                    "reliability_source_implementation_id": spec["reliability_source_implementation_id"],
                    "reliability_transfer_status": spec["mapping_status"],
                    "correction_capability": record["correction_capability"],
                    "declared_proven_error_universe": reliability["declared_proven_error_universe"],
                    "modeled_support_fault_coverage_fraction": reliability["modeled_support_fault_coverage"]["fraction"],
                    "weight3_universe_id": w3["source_universe_id"],
                    "weight3_sdc_count": w3["sdc_miscorrection"] + w3["sdc_undetected"],
                    "weight3_sdc_fraction": w3["sdc_fraction"],
                    "weight3_due_count": w3["due"],
                    "weight3_due_fraction": w3["due_fraction"],
                    "weight3_miscorrection_claim_scope": "OBSERVATION_ONLY_NOT_CORRECTION_GUARANTEE",
                    "placement_interleaving": "METRIC_NOT_PROVEN",
                    "fit_ser_projection": "METRIC_NOT_PROVEN",
                    "payload_width_bits": record["architecture"]["payload_width_bits"],
                    "encoded_width_bits": record["architecture"]["encoded_width_bits"],
                    "redundancy_bits": record["architecture"]["encoded_width_bits"] - record["architecture"]["payload_width_bits"],
                    "organization": record["architecture"]["organization"],
                    "pipeline_depth_cycles": record["architecture"]["pipeline_depth_cycles"],
                    "nominal_operation_latency_cycles": record["architecture"]["nominal_operation_latency_cycles"],
                    "initiation_interval_cycles": record["architecture"]["initiation_interval_cycles"],
                    "physical_characterization_status": physical["characterization_status"],
                    "area_um2": physical_value("standard_cell_instance_area_um2"),
                    "wns_ns": physical_value("wns_ns"),
                    "tns_ns": physical_value("tns_ns"),
                    "fmax_mhz": physical_value("achieved_fmax_mhz"),
                    "feasible_10ns": physical["timing_feasibility"],
                    "no_error_power_w": power_value("no_error", "total_power_w"),
                    "no_error_energy_estimate_pj_per_operation": power_value("no_error", "total_energy_pj_per_operation_estimate"),
                    "no_error_achievable_energy_pj_per_operation": power_value("no_error", "achievable_total_energy_pj_per_operation"),
                    "single_error_power_w": power_value("single_error", "total_power_w"),
                    "single_error_achievable_energy_pj_per_operation": power_value("single_error", "achievable_total_energy_pj_per_operation"),
                    "double_error_power_w": power_value("double_error", "total_power_w"),
                    "double_error_achievable_energy_pj_per_operation": power_value("double_error", "achievable_total_energy_pj_per_operation"),
                    "detailed_wirelength_um": physical_value("detailed_route_wirelength_um"),
                    "drc_count": physical_value("final_drc_count"),
                    "power_interpretation": (
                        "PPA_UNAVAILABLE" if ppa_missing else
                        "TARGET_CONSTRAINT_DIAGNOSTIC_TIMING_INFEASIBLE" if physical["timing_feasibility"] == "FAILS_10NS" else
                        "TIMING_FEASIBLE_ACTIVITY_ESTIMATE"
                    ),
                    "full_ppa_pareto_point_eligible": str(not ppa_missing).lower(),
                }
            )

    derived_rows = []
    for record in integrated_records:
        arch = record["architecture"]
        physical = record["physical"]
        metrics = physical["metrics"]
        area = metrics["standard_cell_instance_area_um2"]
        no_error = record["power_by_trace"]["no_error"]
        derived_rows.append(
            {
                "implementation_id": record["implementation_id"],
                "redundancy_bits": arch["encoded_width_bits"] - arch["payload_width_bits"],
                "redundancy_bits_per_payload_bit": (arch["encoded_width_bits"] - arch["payload_width_bits"]) / arch["payload_width_bits"],
                "area_um2_per_protected_payload_bit": area / arch["payload_width_bits"] if area is not None else None,
                "area_metric_missing_reason": None if area is not None else "PPA_UNAVAILABLE",
                "achieved_fmax_mhz_per_kum2": metrics["achieved_fmax_mhz"] / (area / 1000.0) if area is not None else None,
                "performance_per_area_missing_reason": None if area is not None else "PPA_UNAVAILABLE",
                "no_error_achievable_energy_pj_per_useful_operation": (
                    no_error["metrics"]["achievable_total_energy_pj_per_operation"] if no_error else None
                ),
                "no_error_achievable_energy_missing_reason": (
                    "PPA_UNAVAILABLE" if no_error is None else
                    "TARGET_CLOCK_INFEASIBLE" if no_error["metrics"]["achievable_total_energy_pj_per_operation"] is None else None
                ),
                "no_error_target_constraint_energy_estimate_pj_per_useful_operation": (
                    no_error["metrics"]["total_energy_pj_per_operation_estimate"] if no_error else None
                ),
                "sources": {
                    "architecture": "GATE05_IMPLEMENTATION_IDENTITY.json",
                    "physical_and_energy": "GATE05_INTEGRATED_RESULTS.json",
                },
            }
        )

    integrated_by_id = {row["implementation_id"]: row for row in integrated_records}
    comb = integrated_by_id["secded-rtl-combinational-72-64-v1"]
    pipe = integrated_by_id["secded-rtl-pipelined-72-64-v1"]
    bch = integrated_by_id["shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"]
    hsiao = integrated_by_id["hsiao-generated-combinational-72-64-v1"]
    cm, pm = comb["physical"]["metrics"], pipe["physical"]["metrics"]
    cp = comb["power_by_trace"]["no_error"]["metrics"]
    pp = pipe["power_by_trace"]["no_error"]["metrics"]
    architecture_trade = {
        "comparison": "pipelined conventional SECDED relative to combinational conventional SECDED",
        "same_reliability_semantics": True,
        "operation_normalization_status": normalization["status"],
        "area_percent_change": percent_delta(pm["standard_cell_instance_area_um2"], cm["standard_cell_instance_area_um2"]),
        "fmax_percent_change": percent_delta(pm["achieved_fmax_mhz"], cm["achieved_fmax_mhz"]),
        "detailed_wirelength_percent_change": percent_delta(pm["detailed_route_wirelength_um"], cm["detailed_route_wirelength_um"]),
        "no_error_power_percent_change": percent_delta(pp["total_power_w"], cp["total_power_w"]),
        "no_error_achievable_energy_percent_change": percent_delta(
            pp["achievable_total_energy_pj_per_operation"], cp["achievable_total_energy_pj_per_operation"]
        ),
        "pipeline_depth_change_cycles": pipe["architecture"]["pipeline_depth_cycles"] - comb["architecture"]["pipeline_depth_cycles"],
        "nominal_latency_change_cycles": pipe["architecture"]["nominal_operation_latency_cycles"] - comb["architecture"]["nominal_operation_latency_cycles"],
        "initiation_interval_change_cycles": pipe["architecture"]["initiation_interval_cycles"] - comb["architecture"]["initiation_interval_cycles"],
        "interpretation": "steady-stream energy is comparable at 10 ns and II=1; the pipelined architecture retains a two-cycle nominal-latency penalty",
    }

    def w3_fraction(record: dict[str, Any]) -> Fraction:
        return Fraction(record["reliability"]["exact_fault_universes"][3]["sdc_fraction"])

    secded_w3, hsiao_w3, bch_w3 = w3_fraction(comb), w3_fraction(hsiao), w3_fraction(bch)
    cross_layer = {
        "weight3_comparison_scope": "exhaustive uniform mask fractions within each implementation's canonical codeword coordinates; not a field-rate model and not a correction guarantee",
        "conventional_secded_weight3_sdc_fraction": str(secded_w3),
        "hsiao_weight3_sdc_fraction": str(hsiao_w3),
        "bch_weight3_sdc_fraction": str(bch_w3),
        "hsiao_vs_conventional_weight3_sdc_absolute_percentage_point_change": float(hsiao_w3 - secded_w3) * 100.0,
        "bch_vs_conventional_weight3_sdc_absolute_percentage_point_change": float(bch_w3 - secded_w3) * 100.0,
        "bch_vs_conventional_physical": {
            "area_percent_change": percent_delta(bch["physical"]["metrics"]["standard_cell_instance_area_um2"], cm["standard_cell_instance_area_um2"]),
            "detailed_wirelength_percent_change": percent_delta(bch["physical"]["metrics"]["detailed_route_wirelength_um"], cm["detailed_route_wirelength_um"]),
            "fmax_percent_change": percent_delta(bch["physical"]["metrics"]["achieved_fmax_mhz"], cm["achieved_fmax_mhz"]),
            "timing_feasibility": bch["physical"]["timing_feasibility"],
            "achievable_energy_at_10ns": None,
            "achievable_energy_missing_reason": "TARGET_CLOCK_INFEASIBLE",
        },
        "reliability_improvement_per_area_overhead": {
            "value": None,
            "missing_reason": "METRIC_NOT_PROVEN",
            "reason": "A physically weighted common fault distribution is absent and BCH/SECDED weight-3 mask universes have different codeword widths; a scalar ratio would overstate comparability.",
        },
        "reliability_improvement_per_energy_overhead": {
            "value": None,
            "missing_reason": "TARGET_CLOCK_INFEASIBLE",
            "reason": "BCH has no achievable 10 ns energy, so a realizable reliability-per-energy ratio cannot be formed.",
        },
    }
    derived = {
        "schema_version": 1,
        "operation_normalization": normalization,
        "per_implementation": derived_rows,
        "conventional_secded_architecture_trade": architecture_trade,
        "cross_layer_observations": cross_layer,
        "excluded_derived_quantities": [
            {"quantity": "arbitrary composite score", "reason": "FORBIDDEN_NOT_PHYSICALLY_INTERPRETABLE"},
            {"quantity": "GREEN Score", "reason": "OUT_OF_SCOPE_GATE05"},
            {"quantity": "formal Pareto frontier", "reason": "DEFERRED_TO_GATE06"},
            {"quantity": "field-weighted SDC/DUE/FIT/SER", "reason": "METRIC_NOT_PROVEN"},
        ],
    }
    write_json("GATE05_DERIVED_METRICS.json", derived)

    missing_output = {
        "schema_version": 1,
        "missing_value_tokens": ["PPA_UNAVAILABLE", "RELIABILITY_NOT_APPLICABLE", "TARGET_CLOCK_INFEASIBLE", "METRIC_NOT_PROVEN"],
        "zero_substitution_forbidden": True,
        "records": missing_records,
        "hsiao_pareto_rule": "Hsiao may appear in reliability/correctness tables but must not be a full point in any analysis requiring unavailable PPA dimensions.",
        "bch_energy_rule": "BCH target-constraint energy remains diagnostic; achievable 100 MHz energy is TARGET_CLOCK_INFEASIBLE.",
    }
    write_json("GATE05_MISSING_EVIDENCE.json", missing_output)

    claims = """# Gate 05 claim candidates

No Pareto frontier, GREEN Score, NSGA-II result, or final ECC selection is produced here.

## STRONG

1. **Microarchitectural realization materially changes physical cost for identical coding semantics.** Gate 03R proves the combinational and pipelined SECDED implementations universally equivalent after temporal alignment. At the frozen 10 ns point, pipelining changes area by +36.702%, Fmax by +45.911%, detailed wirelength by +12.067%, and no-error power/steady-stream energy per useful operation by -24.016%, while nominal latency rises from one to three cycles and initiation interval remains one.
2. **The common target exposes implementation feasibility differences hidden by algorithm-level capability.** The evaluated BCH RTL completes routing with zero DRC but has WNS -4.78052 ns and achieved Fmax 67.6566 MHz, so it cannot meet the common 100 MHz target under this implementation, technology, corner, and physical policy.

## SUPPORTED

1. **Reliability capability alone is insufficient for selection.** The evaluated BCH implementation corrects every weight-1 and weight-2 mask in its proven universe, but incurs +207.356% area and +310.975% detailed wirelength relative to combinational SECDED and misses 10 ns. This is an implementation-scoped conclusion, not a universal BCH claim.
2. **Beyond-guarantee behavior differs among validated codes.** Under exhaustive canonical-coordinate weight-3 observation, SDC fractions are 809/1065 for conventional SECDED, 2847/4970 for Hsiao, and 265/1463 for BCH. These are finite-universe observations, not field-weighted SDC rates or weight-3 correction guarantees.
3. **Hsiao remains reliability-qualified but not cross-layer complete.** Its weight-3 reliability observation is usable, while `PPA_UNAVAILABLE` prevents it from becoming a full point in a future PPA-dimensional analysis.

## WEAK

1. **Error-class power differs numerically.** Full-precision OpenSTA estimates resolve small class differences, but Gate 05 has no evidence that those differences are practically significant or representative of field error frequencies.

## UNSUPPORTED

1. Any FIT, SER, operational fault-rate, or physical interleaving superiority claim.
2. Any claim that BCH as a family cannot operate at 100 MHz.
3. Any Hsiao area, timing, power, energy, or Pareto-dominance claim.
4. Any claim that the 10 ns BCH energy estimate is achievable 100 MHz operating energy.
5. Any final best-ECC selection, Pareto-frontier membership, GREEN Score, or NSGA-II result.
"""
    (OUT / "GATE05_CLAIM_CANDIDATES.md").write_text(claims, encoding="utf-8", newline="\n")

    def headline(record: dict[str, Any]) -> list[str]:
        w3 = record["reliability"]["exact_fault_universes"][3]
        p = record["physical"]
        m = p["metrics"]
        no_error = record["power_by_trace"]["no_error"]
        if p["characterization_status"] == "PHYSICAL_CHARACTERIZATION_PARTIAL":
            return [
                record["label"], f"w1/w2 safe=1/1; w3 SDC={w3['sdc_fraction']}", w3["due_fraction"],
                "PPA_UNAVAILABLE", "PPA_UNAVAILABLE", "PPA_UNAVAILABLE", p["timing_feasibility"],
                "PPA_UNAVAILABLE", "PPA_UNAVAILABLE", "PPA_UNAVAILABLE", "PPA_UNAVAILABLE",
            ]
        energy = no_error["metrics"]["achievable_total_energy_pj_per_operation"]
        return [
            record["label"], f"w1/w2 safe=1/1; w3 SDC={w3['sdc_fraction']}", w3["due_fraction"],
            f"{m['standard_cell_instance_area_um2']:.3f}", f"{m['wns_ns']:.6f}", f"{m['achieved_fmax_mhz']:.6f}",
            p["timing_feasibility"], f"{no_error['metrics']['total_power_w']:.12g}",
            f"{energy:.9f}" if energy is not None else "TARGET_CLOCK_INFEASIBLE",
            f"{m['detailed_route_wirelength_um']:.0f}", str(m["final_drc_count"]),
        ]

    table_rows = [headline(row) for row in integrated_records]
    table = "\n".join(
        "| " + " | ".join(row) + " |" for row in table_rows
    )
    report = f"""# DATE 2027 Gate 05 reliability x physical-cost integration

`GATE_05_CONDITIONAL_PASS`

| ECC / architecture | Reliability evidence / SDC | Weight-3 DUE | Area um2 | WNS ns | Fmax MHz | 10 ns | No-error power W | Achievable energy/op pJ | Wirelength um | DRC |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
{table}

The SDC and DUE entries are exhaustive **weight-3 observation-only** fractions. In every declared/proven weight-1/weight-2 support universe, modeled safe handling is 1/1 and SDC is zero. The table never treats weight-3 behavior as a correction guarantee or field-weighted rate.

## Identity adjudication

- Conventional combinational SECDED maps directly to the Gate 02 aggregate and Gate 03R exact RTL proof.
- Pipelined SECDED has the same proven code behavior as combinational SECDED through universal encoder/decoder equivalence, but retains an independent architecture and physical row.
- Hsiao maps directly to its Gate 02 aggregate plus two Gate 03 compiled functional campaigns; its Gate 04 PPA is unavailable.
- BCH maps from the Gate 02 reference to the exact Gate 03R RTL identity through the independent matrix reconstruction and all 3,082 symbolic weight-0/1/2 proof jobs.

## Operation normalization

`{normalization['status']}`

Every power trace contains 100,000 asserted-valid comparison transactions at initiation interval one, preceded by six reset clocks and followed by four drain clocks. The four-cycle drain exceeds the pipelined SECDED boundary latency of three cycles. Both SECDED architectures therefore perform the same accepted steady-stream work over the same 1,000,100,000 ps trace. The energy comparison is valid for steady-stream throughput; it does not erase the pipelined architecture's nominal latency increase from one to three cycles.

## Supported cross-layer trade-offs

- Pipelined versus combinational SECDED: area {architecture_trade['area_percent_change']:+.3f}%, Fmax {architecture_trade['fmax_percent_change']:+.3f}%, detailed wirelength {architecture_trade['detailed_wirelength_percent_change']:+.3f}%, no-error power {architecture_trade['no_error_power_percent_change']:+.3f}%, and achievable steady-stream energy/op {architecture_trade['no_error_achievable_energy_percent_change']:+.3f}%. Pipeline depth and nominal latency increase by two cycles; initiation interval stays at one.
- Evaluated BCH versus combinational SECDED: area {cross_layer['bch_vs_conventional_physical']['area_percent_change']:+.3f}%, detailed wirelength {cross_layer['bch_vs_conventional_physical']['detailed_wirelength_percent_change']:+.3f}%, and Fmax {cross_layer['bch_vs_conventional_physical']['fmax_percent_change']:+.3f}%. BCH corrects the larger proven fault universe but fails the common 10 ns target.
- Hsiao's exhaustive weight-3 SDC fraction is lower than conventional SECDED's in the respective canonical-coordinate universes, but the missing PPA prevents a complete reliability-cost point.

## Missing and excluded evidence

- Hsiao physical dimensions are `PPA_UNAVAILABLE`; no values are fabricated and it is excluded from future full-dimensional PPA analysis.
- BCH diagnostic target-constraint power and energy estimates are preserved, but achievable 100 MHz energy is `TARGET_CLOCK_INFEASIBLE`.
- FIT, SER, operationally weighted SDC/DUE, and physical placement/interleaving effects are `METRIC_NOT_PROVEN`.
- Reliability-per-cost scalar ratios are not computed without a common physically weighted fault distribution. Formal Pareto analysis is deferred to Gate 06.

## Gate 05 verdict

`GATE_05_CONDITIONAL_PASS`

The exact identity join is defensible for all four implementations. Three architectures have complete physical rows, including BCH's scientifically meaningful timing failure, and Hsiao contributes only validated reliability evidence. The bounded Hsiao PPA absence prevents an unconditional pass but does not invalidate the principal cross-layer comparison.

## Gate 06 readiness

Gate 06 may use only the three complete PPA points for full-dimensional analysis and must retain Hsiao as reliability-only unless a separately authorized physical result exists. No Gate 06 analysis has been started.

`GATE_06_READY`
"""
    (OUT / "GATE05_ADJUDICATION.md").write_text(report, encoding="utf-8", newline="\n")

    required = (
        "GATE05_IMPLEMENTATION_IDENTITY.json",
        "GATE05_RELIABILITY_SOURCE_MAP.json",
        "GATE05_INTEGRATED_RESULTS.csv",
        "GATE05_INTEGRATED_RESULTS.json",
        "GATE05_DERIVED_METRICS.json",
        "GATE05_MISSING_EVIDENCE.json",
        "GATE05_CLAIM_CANDIDATES.md",
        "GATE05_ADJUDICATION.md",
    )
    hashes = [f"{hashlib.sha256((OUT / name).read_bytes()).hexdigest()}  ./{name}" for name in required]
    (OUT / "GATE05_EVIDENCE.sha256").write_text("\n".join(hashes) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()
    print("GATE05_ARTIFACTS_BUILT")
