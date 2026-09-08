"""Build deterministic GREEN Matrix 3.1 physical-population artifacts.

The builder is an adapter over immutable GREEN Matrix 3.0, Attempt09, and
Attempt10 evidence.  It executes no physical tool and promotes no source tier.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Mapping

from .core import (
    OUTCOMES,
    ServiceMetrics,
    classify_literature_transfer,
    classify_pareto_front,
    derive_energy_from_power,
    exact_pareto_indices,
)


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
FOUNDATION = BASE.parent / "green_matrix_v3_imec_aligned"
MEMORY = BASE.parent / "memory_compiler"
ATTEMPT09 = MEMORY / "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
ATTEMPT10 = MEMORY / "gate3_attempt10_green_matrix_physical_model_validation"

SCHEMA_VERSION = "3.1.0"
FOUNDATION_COMMIT = "affc8145b184803189dac36391cb486f00e7b4f8"
REQUESTED_BASELINE_COMMIT = "59f3821"
CLASSIFICATION = "GREEN_MATRIX_V3_1_PHYSICAL_POPULATION_PARTIAL_E4_E3_PHYSICAL_SDC_DUE_BLOCKED"
BOUNDARY = "SB_V3_1_MATCHED_U0_E0_IMPLEMENTATION_AND_SERVICE"
SEEDS = (11, 13, 17, 19, 23)
ARCHITECTURES = ("U0", "E0")


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(name: str, value: Any) -> None:
    (BASE / name).write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    if isinstance(value, bool):
        return str(value).lower()
    return value


def _write_csv(name: str, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = [dict(row) for row in rows]
    fields: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fields:
                fields.append(key)
    with (BASE / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in materialized:
            writer.writerow({key: _csv_value(row.get(key, "")) for key in fields})


def _source_result_path(architecture: str, seed: int, name: str) -> Path:
    return (
        ATTEMPT09
        / "raw"
        / "openroad"
        / "work"
        / "results"
        / "sky130hd"
        / f"attempt09_{architecture.lower()}"
        / f"seed{seed}"
        / name
    )


def _service_metrics() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for architecture in ARCHITECTURES:
        metrics = ServiceMetrics(1, 1, 10e-9)
        rows[architecture] = {
            "architecture_id": architecture,
            "encoder_latency_cycles": 0 if architecture == "E0" else "NOT_APPLICABLE",
            "sram_access_latency_cycles": 1,
            "decoder_latency_cycles": 0 if architecture == "E0" else "NOT_APPLICABLE",
            "registered_service_latency_cycles": metrics.latency_cycles,
            "registered_service_latency_s": metrics.latency_s,
            "correction_service_latency_cycles": 1 if architecture == "E0" else "NOT_APPLICABLE",
            "retry_latency_cycles": "UNAVAILABLE",
            "scrub_interference_cycles": "UNAVAILABLE",
            "pipeline_depth_cycles": 1,
            "initiation_interval_cycles": metrics.initiation_interval_cycles,
            "nominal_initiation_capacity_services_per_s": metrics.nominal_initiation_capacity_services_per_s,
            "maximum_sustainable_throughput_services_per_s": "UNAVAILABLE",
            "clock_period_s": metrics.clock_period_s,
            "clock_hz": 100_000_000.0,
            "evidence_tier": "E3",
            "evidence_kind": "ANALYTICAL",
            "qualification_status": "RTL_SERVICE_SEMANTICS_QUALIFIED_PHYSICAL_MAX_THROUGHPUT_BLOCKED",
            "boundary": "one request accepted before a rising edge; synchronous SRAM result and combinational ECC response after that edge",
            "source_rtl": str(
                (
                    ATTEMPT09
                    / "rtl"
                    / ("ecc_sram_256x72_sram22.sv" if architecture == "E0" else "unprotected_sram_256x64_sram22.sv")
                ).relative_to(REPO)
            ).replace("\\", "/"),
            "not_established": [
                "analog SRAM access time",
                "post-route request-to-correct-payload latency distribution",
                "maximum sustainable throughput under backpressure",
                "retry latency",
                "scrub interference",
            ],
        }
    return rows


def _physical_source_rows() -> list[dict[str, Any]]:
    source = _load(ATTEMPT10 / "green_matrix" / "GREEN_MATRIX_PHYSICAL.json")["rows"]
    rows = [row for row in source if row["liberty_model"] == "UPSTREAM_ORIGINAL"]
    rows.sort(key=lambda row: (int(row["seed"]), ARCHITECTURES.index(row["architecture_id"])))
    if [(row["seed"], row["architecture_id"]) for row in rows] != [
        (seed, architecture) for seed in SEEDS for architecture in ARCHITECTURES
    ]:
        raise RuntimeError("Attempt10 does not contain the expected matched U0/E0 five-seed population")
    return rows


def _activity_sources() -> tuple[dict[str, dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    diagnostic = _load(ATTEMPT10 / "energy" / "POSTROUTE_ACTIVITY_DIAGNOSTIC.json")
    by_architecture = {row["architecture_id"]: row for row in diagnostic["rows"]}
    manifest = _load(ATTEMPT10 / "energy" / "WORKLOAD_MANIFEST.json")
    workloads = manifest["workloads"]
    return by_architecture, manifest, workloads


def _new_physical_rows() -> list[dict[str, Any]]:
    service = _service_metrics()
    activity, _, workloads = _activity_sources()
    read_workload = next(row for row in workloads if row["workload_id"] == "read_dominant")
    source_rows = _physical_source_rows()
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        architecture = source["architecture_id"]
        seed = int(source["seed"])
        result_dir = _source_result_path(architecture, seed, "6_final.odb").parent
        trace = read_workload["activity"][architecture]
        postroute = activity[architecture] if seed == 11 else None
        rows.append(
            {
                "record_id": f"MP31|{architecture}|UPSTREAM_ORIGINAL|seed{seed}|I0",
                "design_id": f"{architecture}|SKY130|I0|read_dominant|P0_NO_SCRUB_NO_RETRY",
                "architecture_id": architecture,
                "ecc_family": "HSIAO_SECDED" if architecture == "E0" else "UNPROTECTED",
                "payload_bits": 64,
                "codeword_bits": 72 if architecture == "E0" else 64,
                "parity_bits": 8 if architecture == "E0" else 0,
                "correction_capability_bits": 1 if architecture == "E0" else 0,
                "detection_capability_bits": 2 if architecture == "E0" else 0,
                "decoder_architecture": "HSIAO_COMBINATIONAL" if architecture == "E0" else "NONE",
                "pipeline_stages": 1,
                "initiation_interval_cycles": 1,
                "technology_id": "SKY130HD_WITH_SRAM22_RESEARCH_MACROS",
                "process_route_id": "ORFS_ATTEMPT09_UPSTREAM_ORIGINAL",
                "compiler_id": "SRAM22_RESEARCH_MACROS",
                "implementation_id": f"A09_{architecture}_UPSTREAM_ORIGINAL_seed{seed}",
                "interleaving_id": "I0",
                "physical_interleaver_implemented": False,
                "workload_id": "read_dominant",
                "service_policy_id": "P0_NO_SCRUB_NO_RETRY",
                "fault_environment_id": "PHYSICAL_EVENT_DISTRIBUTION_UNAVAILABLE",
                "clock_hz": 100_000_000.0,
                "voltage_v": 1.8,
                "temperature_c": 25.0,
                "observed_macro_area_um2": source["area_macro_um2"],
                "activity_coverage_fraction": postroute["annotated_pin_fraction"] if postroute else "",
                "diagnostic_tool_power_w": postroute["power_total_w"] if postroute else "",
                "latency_s": service[architecture]["registered_service_latency_s"],
                "throughput_services_per_s": "",
                "logical_pattern_count": "",
                "logical_success_normal_count": "",
                "logical_success_corrected_count": "",
                "logical_success_after_retry_count": "",
                "logical_detected_failure_count": "",
                "logical_sdc_count": "",
                "logical_timeout_count": "",
                "logical_control_success_fraction": "",
                "logical_control_due_fraction": "",
                "logical_control_sdc_fraction": "",
                "logical_control_corrected_fraction": "",
                "logical_control_retry_fraction": "",
                "rate_semantics": "PHYSICAL_EVENT_PROBABILITY_UNAVAILABLE",
                "source_record_id": source["row_id"],
                "record_origin": "V3_1_PHYSICAL_POPULATION",
                "seed": seed,
                "pvt": "TT/25C/1.8V",
                "physical_flow": "OpenROAD-flow-scripts SKY130HD, frozen image sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e",
                "routed_total_area_um2": source["area_total_um2"],
                "wirelength_um": source["wirelength_um"],
                "via_count": source["via_count"],
                "setup_wns_ns": source["setup_wns_ns"],
                "hold_wns_ns": source["hold_wns_ns"],
                "power_internal_w": source["power_internal_w"],
                "power_switching_w": source["power_switching_w"],
                "power_leakage_w": source["power_leakage_w"],
                "power_total_vectorless_w": source["power_total_w"],
                "nominal_initiation_capacity_services_per_s": service[architecture][
                    "nominal_initiation_capacity_services_per_s"
                ],
                "implementation_hash": _sha(result_dir / "6_final.odb"),
                "netlist_hash": _sha(result_dir / "6_final.v"),
                "physical_configuration_hash": _sha(ATTEMPT09 / "openroad" / architecture.lower() / "config.mk"),
                "timing_constraint_hash": _sha(result_dir / "6_final.sdc"),
                "activity_file_hash": trace["sha256"] if seed == 11 else "",
                "workload_hash": read_workload["trace_sha256"] if seed == 11 else "",
                "source_artifact_hash": source["source_artifact_sha256"],
                "source_result_directory": str(result_dir.relative_to(REPO)).replace("\\", "/"),
                "qualification_status": source["qualification_status"],
                "blocking_reason": "residual SRAM input transition violations; power is vectorless except the separately labelled seed-11 partial-annotation diagnostic",
            }
        )
    return rows


def _evidence_record(
    *,
    quantity_id: str,
    entity: Mapping[str, Any],
    quantity_name: str,
    value: Any,
    unit: str,
    source_type: str,
    tier: str,
    kind: str,
    status: str,
    blocking_reason: str = "",
    experiment_hash: str = "",
    activity_hash: str = "",
) -> dict[str, Any]:
    return {
        "quantity_id": quantity_id,
        "entity_id": entity["record_id"],
        "quantity_name": quantity_name,
        "value": value,
        "unit": unit,
        "source_id": entity["source_record_id"],
        "source_type": source_type,
        "implementation_hash": entity["implementation_hash"],
        "experiment_hash": experiment_hash or entity["source_artifact_hash"],
        "technology_id": entity["technology_id"],
        "pvt": entity["pvt"],
        "workload_id": entity["workload_id"],
        "measurement_model_boundary": BOUNDARY,
        "evidence_tier": tier,
        "evidence_kind": kind,
        "uncertainty_representation": "FIVE_IMPLEMENTATION_SEEDS" if tier == "E4" else "STRUCTURAL_MISSINGNESS" if tier == "E0" else "DETERMINISTIC_RTL_CONTRACT",
        "citation": "repository provenance; no external numeric substitution",
        "date_version": "2026-09-08/v3.1.0",
        "qualification_status": status,
        "blocking_reason": blocking_reason,
        "netlist_hash": entity["netlist_hash"],
        "physical_configuration": entity["physical_flow"],
        "physical_configuration_hash": entity["physical_configuration_hash"],
        "timing_constraint_hash": entity["timing_constraint_hash"],
        "workload_hash": entity["workload_hash"],
        "activity_file_hash": activity_hash or entity["activity_file_hash"],
        "record_origin": "V3_1_PHYSICAL_POPULATION",
    }


def _new_evidence_rows(physical_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    activity, _, workloads = _activity_sources()
    read_workload = next(row for row in workloads if row["workload_id"] == "read_dominant")
    rows: list[dict[str, Any]] = []
    available = (
        ("routed_total_area_um2", "routed_total_area_um2", "um2"),
        ("wirelength_um", "wirelength_um", "um"),
        ("via_count", "via_count", "count"),
        ("power_internal_w", "power_internal_w", "W"),
        ("power_switching_w", "power_switching_w", "W"),
        ("power_leakage_w", "power_leakage_w", "W"),
        ("power_total_vectorless_w", "power_total_vectorless_w", "W"),
        ("setup_wns_ns", "setup_wns_ns", "ns"),
        ("hold_wns_ns", "hold_wns_ns", "ns"),
    )
    unavailable = (
        ("bitcell_physical_geometry", "mapping", "complete address/column-select-to-GDS-bitcell map is unavailable"),
        ("qcrit_c", "C", "no qualified transient-injection experiment and model-card provenance were established"),
        ("physical_fault_probability", "probability", "no technology/PVT/geometry-matched physical event PMF or rate"),
        ("physical_sdc_probability", "probability", "physical topology probabilities and exact cell mapping are unavailable"),
        ("physical_due_probability", "probability", "physical topology probabilities and exact cell mapping are unavailable"),
        ("fit", "FIT", "no qualified event rate; logical enumeration is not FIT"),
        ("implemented_nontrivial_interleaver_overhead", "um2", "I1/I2 are proposals, not routed implementations"),
        ("manufacturing_carbon_kgco2e", "kgCO2e", "matched SKY130 manufacturing inventory is unavailable"),
        ("csci_kgco2e_per_correct_service", "kgCO2e_per_correct_service", "lifecycle carbon and physical correct-service probability are unavailable"),
        ("mrcc_kgco2e_per_additional_correct_service", "kgCO2e_per_additional_correct_service", "matched lifecycle carbon and physical correct-service counts are unavailable"),
        ("maximum_sustainable_throughput_services_per_s", "services_per_s", "no saturated architecture-level traffic experiment with backpressure"),
    )
    for entity in physical_rows:
        suffix = entity["record_id"].replace("|", "_")
        for key, quantity, unit in available:
            rows.append(
                _evidence_record(
                    quantity_id=f"ME31|{suffix}|{quantity}",
                    entity=entity,
                    quantity_name=quantity,
                    value=entity[key],
                    unit=unit,
                    source_type="MATCHED_POST_ROUTE_TOOL",
                    tier="E4",
                    kind="POST_ROUTE_ESTIMATE",
                    status="DIAGNOSTIC_ONLY",
                    blocking_reason="residual SRAM input-transition violations prevent signoff qualification",
                )
            )
        service_values = (
            ("registered_service_latency_s", entity["latency_s"], "s"),
            ("initiation_interval_cycles", entity["initiation_interval_cycles"], "cycle"),
            (
                "nominal_initiation_capacity_services_per_s",
                entity["nominal_initiation_capacity_services_per_s"],
                "services_per_s",
            ),
            ("conditional_ecc_outcome_model", "DECODER_REQUIRED_AFTER_PHYSICAL_MAPPING", "mapping"),
        )
        for quantity, value, unit in service_values:
            rows.append(
                _evidence_record(
                    quantity_id=f"ME31|{suffix}|{quantity}",
                    entity=entity,
                    quantity_name=quantity,
                    value=value,
                    unit=unit,
                    source_type="RTL_CONTRACT_AND_EXACT_LOGICAL_MODEL",
                    tier="E3",
                    kind="ANALYTICAL",
                    status="QUALIFIED_WITHIN_DECLARED_RTL_BOUNDARY",
                )
            )
        rows.append(
            _evidence_record(
                quantity_id=f"ME31|{suffix}|macro_placement_geometry",
                entity=entity,
                quantity_name="macro_placement_geometry",
                value="DEF_MACRO_ORIGIN_ORIENTATION_AND_LEF_EXTENT",
                unit="mapping",
                source_type="POST_ROUTE_DEF_LEF_AND_SPICE_CONNECTIVITY",
                tier="E4",
                kind="POST_ROUTE_ESTIMATE",
                status="MACRO_LEVEL_ONLY",
                blocking_reason="does not establish bitcell xy or address-to-cell mapping",
            )
        )
        for quantity, unit, reason in unavailable:
            rows.append(
                _evidence_record(
                    quantity_id=f"ME31|{suffix}|{quantity}",
                    entity=entity,
                    quantity_name=quantity,
                    value="",
                    unit=unit,
                    source_type="NOT_AVAILABLE",
                    tier="E0",
                    kind="UNAVAILABLE",
                    status="BLOCKED",
                    blocking_reason=reason,
                )
            )
        if entity["seed"] == 11:
            architecture = entity["architecture_id"]
            diagnostic = activity[architecture]
            trace = read_workload["activity"][architecture]
            rows.append(
                _evidence_record(
                    quantity_id=f"ME31|{suffix}|activity_trace_sha256",
                    entity=entity,
                    quantity_name="activity_trace_sha256",
                    value=trace["sha256"],
                    unit="sha256",
                    source_type="DETERMINISTIC_RTL_SIMULATION",
                    tier="E3",
                    kind="ANALYTICAL",
                    status="QUALIFIED_RTL_ACTIVITY_TRACE",
                    experiment_hash=trace["testbench_sha256"],
                    activity_hash=trace["sha256"],
                )
            )
            rows.append(
                _evidence_record(
                    quantity_id=f"ME31|{suffix}|activity_coverage_fraction",
                    entity=entity,
                    quantity_name="activity_coverage_fraction",
                    value=diagnostic["annotated_pin_fraction"],
                    unit="fraction",
                    source_type="PARTIAL_RTL_ACTIVITY_ANNOTATED_POST_ROUTE_TOOL",
                    tier="E4",
                    kind="POST_ROUTE_ESTIMATE",
                    status="DIAGNOSTIC_ONLY",
                    blocking_reason=diagnostic["blockers"],
                    activity_hash=trace["sha256"],
                )
            )
            powers = {
                "internal": diagnostic["power_internal_w"],
                "switching": diagnostic["power_switching_w"],
                "leakage": diagnostic["power_leakage_w"],
                "total": diagnostic["power_total_w"],
            }
            for component, power in powers.items():
                energy = derive_energy_from_power(
                    power,
                    read_workload["duration_s"],
                    read_workload["cycles"],
                    source_kind="POST_ROUTE_ESTIMATE",
                    functional_unit="one requested read-or-write memory service in the matched read_dominant trace",
                )
                quantity = f"diagnostic_{component}_energy_per_requested_service_j"
                rows.append(
                    _evidence_record(
                        quantity_id=f"ME31|{suffix}|{quantity}",
                        entity=entity,
                        quantity_name=quantity,
                        value=energy.energy_per_service_j,
                        unit="J_per_requested_service",
                        source_type="DERIVED_FROM_PARTIALLY_ANNOTATED_POST_ROUTE_POWER",
                        tier="E4",
                        kind=energy.derived_kind,
                        status="DIAGNOSTIC_ONLY_NOT_E5",
                        blocking_reason=diagnostic["blockers"],
                        activity_hash=trace["sha256"],
                    )
                )
    return rows


def _literature_records() -> list[dict[str, Any]]:
    records = [
        {
            "dataset_id": "LIT_PIEPER_2023_5NM_SRAM",
            "title": "Study of Multicell Upsets in SRAM at a 5-nm Bulk FinFET Node",
            "technology_process": "5-nm bulk FinFET",
            "bulk_soi_fdsoi": "BULK",
            "sram_organization": "custom single-port 8Kx32 and two-port 1Kx72 arrays",
            "cell_geometry": "UNAVAILABLE_IN_REUSABLE_MACHINE_READABLE_FORM",
            "supply_voltage_v": "voltage sweep; alpha MCU lower-bound statement applies below 0.55 V",
            "temperature_c": 25,
            "particle_species": ["241Am alpha", "LANSCE terrestrial-spectrum neutron", "14-MeV neutron", "thermal neutron", "heavy ion"],
            "particle_energy": "heavy ions: 10 MeV/nucleon cocktail; neutrons source-specific",
            "let_mev_cm2_mg": "2-86 for heavy-ion campaign",
            "incident_angle": "normal incidence for heavy-ion campaign",
            "beam_environment": "LBNL 88-inch Cyclotron, LANSCE, Sandia 14-MeV source, alpha and thermal-neutron facilities",
            "fluence": "approximately 1e11 n/cm2 at LANSCE; approximately 1e13 n/cm2 for each 14-MeV test",
            "cross_section": "SOURCE_TABLES_NOT_EXTRACTED_IN_THIS_ADAPTER",
            "sbu_fraction": "UNAVAILABLE_AS_ONE_UNIVERSAL_VALUE",
            "mcu_mbu_fraction": "P(MCU)>0.15 under alpha exposure below 0.55 V for both designs; condition-specific lower statement",
            "multiplicity": "event clusters reported; no raw event list ingested",
            "physical_spacing_span": "cluster membership within three cells; range measured in word-line/bit-line cell distances",
            "orientation": "word-line and bit-line range retained separately",
            "measurement_uncertainty": "no reusable numeric sampling interval for the extracted lower statement",
            "citation": "N. J. Pieper et al., IEEE TNS (2023), doi:10.1109/TNS.2023.3240318",
            "url": "https://www.osti.gov/servlets/purl/2004056",
            "experimental_model_boundary": "SILICON_PARTICLE_EXPERIMENT_WITH_PUBLISHED_AGGREGATES",
        },
        {
            "dataset_id": "LIT_PEREZ_CELIS_2020_FPGA",
            "title": "Statistical Method to Extract Radiation-Induced Multiple-Cell Upsets in SRAM-Based FPGAs",
            "technology_process": "Xilinx 7-Series, UltraScale, and UltraScale+ SRAM FPGA configuration memories; not a SKY130 SRAM macro",
            "bulk_soi_fdsoi": "UNAVAILABLE",
            "sram_organization": "FPGA CRAM and 7-Series BRAM with vendor interleaving",
            "cell_geometry": "PROPRIETARY_OR_UNAVAILABLE",
            "supply_voltage_v": "UNAVAILABLE_IN_INGESTED_AGGREGATE",
            "temperature_c": "UNAVAILABLE_IN_INGESTED_AGGREGATE",
            "particle_species": ["LANSCE neutron"],
            "particle_energy": "LANSCE terrestrial-spectrum beam",
            "let_mev_cm2_mg": "NOT_APPLICABLE_TO_REPORTED_NEUTRON_AGGREGATE",
            "incident_angle": "UNAVAILABLE",
            "beam_environment": "LANSCE neutron irradiation",
            "fluence": "UNAVAILABLE_IN_INGESTED_AGGREGATE",
            "cross_section": "NOT_TRANSFERRED",
            "sbu_fraction": "device-specific complement not treated as a universal SBU fraction",
            "mcu_mbu_fraction": {"XC7A200T": 0.277, "XCKU040": 0.1459, "XCZU9EG": 0.0559},
            "multiplicity": "statistically classified MCU aggregates",
            "physical_spacing_span": "reconstructed frame/bit shapes; no reusable physical xy map",
            "orientation": "UNAVAILABLE",
            "measurement_uncertainty": "cross-device range is not a confidence interval",
            "citation": "A. Perez-Celis and M. J. Wirthlin, IEEE TNS 67(1), doi:10.1109/TNS.2019.2955006",
            "url": "https://par.nsf.gov/servlets/purl/10184000",
            "experimental_model_boundary": "SILICON_NEUTRON_EXPERIMENT_PLUS_STATISTICAL_CLASSIFICATION",
        },
        {
            "dataset_id": "LIT_IBE_2009_CORIMS_SCALING",
            "title": "Scaling Effects on Neutron-Induced Soft Error in SRAMs Down to 22nm Process",
            "technology_process": "modeled 130-to-22-nm SRAM roadmap, CORIMS calibrated against 250-to-130-nm experiments",
            "bulk_soi_fdsoi": "BULK_MODEL",
            "sram_organization": "rectangular modeled SRAM cell matrix",
            "cell_geometry": "roadmap-scaled model; not SKY130 geometry",
            "supply_voltage_v": "held constant in roadmap model",
            "temperature_c": "UNAVAILABLE",
            "particle_species": ["terrestrial neutron and simulated secondary ions"],
            "particle_energy": "field and accelerator neutron spectra; energy-dependent results",
            "let_mev_cm2_mg": "NOT_APPLICABLE_TO_NEUTRON_ROADMAP_SUMMARY",
            "incident_angle": "model-dependent",
            "beam_environment": "CORIMS; validation cited field, LANSCE, TSL, and CYRIC experiments",
            "fluence": "UNAVAILABLE_IN_SUMMARY",
            "cross_section": "MODEL_OUTPUT_NOT_TRANSFERRED",
            "sbu_fraction": "UNAVAILABLE",
            "mcu_mbu_fraction": "130-nm modeled checkerboard MCU ratio 7%; model-form evidence only",
            "multiplicity": "130-nm modeled maximum multiplicity 10 bits in the declared checkerboard scenario",
            "physical_spacing_span": "failed-bit maps classified along bit-line, word-line, and clustered orientations",
            "orientation": ["bit-line", "word-line", "cluster"],
            "measurement_uncertainty": "authors report model agreement within 20% of cited 250-to-130-nm experiments; not a SKY130 interval",
            "citation": "E. Ibe et al., WDSN 2009, Scaling Effects on Neutron-Induced Soft Error in SRAMs Down to 22nm Process",
            "url": "https://webhost.laas.fr/TSF/WDSN09/WDSN09_files/Texts/WDSN09-2-1-Ibe.pdf",
            "experimental_model_boundary": "PHYSICALLY_CALIBRATED_MONTE_CARLO_MODEL_AND_ROADMAP_PROJECTION",
        },
        {
            "dataset_id": "LIT_YAHAGI_2007_130_180NM",
            "title": "A Novel Feature of Neutron-Induced Multi-Cell Upsets in 130 and 180 nm SRAMs",
            "technology_process": "commercial/proprietary 130-nm and 180-nm CMOS SRAMs; process identity not equivalent to SKY130",
            "bulk_soi_fdsoi": "UNAVAILABLE",
            "sram_organization": "UNAVAILABLE_IN_PUBLIC_METADATA",
            "cell_geometry": "UNAVAILABLE_IN_PUBLIC_METADATA",
            "supply_voltage_v": "UNAVAILABLE_IN_PUBLIC_METADATA",
            "temperature_c": "UNAVAILABLE_IN_PUBLIC_METADATA",
            "particle_species": ["mono-energetic, quasi-mono-energetic, and spallation neutrons"],
            "particle_energy": "multiple accelerator neutron spectra",
            "let_mev_cm2_mg": "NOT_APPLICABLE",
            "incident_angle": "UNAVAILABLE_IN_PUBLIC_METADATA",
            "beam_environment": "multiple accelerator facilities",
            "fluence": "UNAVAILABLE_IN_PUBLIC_METADATA",
            "cross_section": "energy-dependent MCU/total-upset behavior reported; no value transferred",
            "sbu_fraction": "UNAVAILABLE_IN_INGESTED_METADATA",
            "mcu_mbu_fraction": "Weibull-type energy dependence reported; no numeric curve digitized",
            "multiplicity": "130-nm multiplicity distribution modeled as exponential plus Lorentzian components",
            "physical_spacing_span": "UNAVAILABLE_IN_INGESTED_METADATA",
            "orientation": "UNAVAILABLE_IN_INGESTED_METADATA",
            "measurement_uncertainty": "UNAVAILABLE_IN_INGESTED_METADATA",
            "citation": "Y. Yahagi et al., IEEE TNS 54(4), 1030-1036 (2007), doi:10.1109/TNS.2007.897066",
            "url": "https://doi.org/10.1109/TNS.2007.897066",
            "experimental_model_boundary": "SILICON_NEUTRON_EXPERIMENT_WITH_PUBLIC_METADATA_ONLY_IN_THIS_ADAPTER",
        },
        {
            "dataset_id": "LIT_NASA_KINTEX_ULTRASCALE_2020",
            "title": "Xilinx Kintex-UltraScale Field Programmable Gate Array Single Event Effects Heavy-Ion Test Report",
            "technology_process": "Kintex UltraScale FPGA BRAM; vendor process, not SKY130 SRAM22",
            "bulk_soi_fdsoi": "UNAVAILABLE",
            "sram_organization": "256 RAMB36 blocks configured at 8-bit data width",
            "cell_geometry": "UNAVAILABLE",
            "supply_voltage_v": "SOURCE_RUN_SPECIFIC_NOT_EXTRACTED",
            "temperature_c": "SOURCE_RUN_SPECIFIC_NOT_EXTRACTED",
            "particle_species": ["heavy ion"],
            "particle_energy": "SOURCE_RUN_SPECIFIC_NOT_EXTRACTED",
            "let_mev_cm2_mg": "SOURCE_RUN_SPECIFIC_NOT_EXTRACTED",
            "incident_angle": "SOURCE_RUN_SPECIFIC_NOT_EXTRACTED",
            "beam_environment": "accelerated heavy-ion SEE campaign",
            "fluence": "SOURCE_RUN_SPECIFIC_NOT_EXTRACTED",
            "cross_section": "NOT_TRANSFERRED",
            "sbu_fraction": "UNAVAILABLE_FROM_INGESTED_TEXT",
            "mcu_mbu_fraction": "UNAVAILABLE_FROM_INGESTED_TEXT",
            "multiplicity": "method classifies 1-, 2-, 3-, and higher-bit errors",
            "physical_spacing_span": "UNAVAILABLE",
            "orientation": "UNAVAILABLE",
            "measurement_uncertainty": "report states event-association confidence; numeric histogram not ingested",
            "citation": "NASA NTRS 20205007765 (2020)",
            "url": "https://ntrs.nasa.gov/api/citations/20205007765/downloads/20205007765.pdf",
            "experimental_model_boundary": "INSTITUTIONAL_SILICON_HEAVY_ION_TEST_REPORT",
        },
    ]
    for record in records:
        transfer = classify_literature_transfer(record["technology_process"], "SKY130")
        record.update(
            {
                "evidence_tier": "E2",
                "evidence_kind": "TECHNOLOGY_MISMATCH",
                "qualification_status": transfer,
                "technology_matched_to_sky130": False,
                "numeric_value_transferred_to_sky130": False,
                "allowed_uses": [
                    "MODEL_FORM_VALIDATION",
                    "TOPOLOGY_FAMILY_VALIDATION",
                    "SENSITIVITY_STUDY",
                    "BOUNDED_SCENARIO_CONSTRUCTION",
                    "ADVERSARIAL_TESTING",
                    "RESEARCH_PRIOR_WITH_EXPLICIT_BOUNDARY",
                ],
                "prohibited_use": "ABSOLUTE_SKY130_SDC_DUE_SER_OR_FIT_CALIBRATION",
            }
        )
    return records


def _qualification(new_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in new_evidence:
        counts[row["evidence_tier"]] = counts.get(row["evidence_tier"], 0) + 1
    metrics = [
        ("matched_route_area_wirelength_vias", "E4", "DIAGNOSTIC_ONLY", "five matched U0/E0 seeds"),
        ("power_internal_switching_leakage", "E4", "DIAGNOSTIC_ONLY", "post-route tool estimates; vectorless for five seeds"),
        ("matched_trace_energy_per_requested_service", "E4", "DIAGNOSTIC_ONLY_NOT_E5", "seed-11 partial pin annotation; not read/write partitioned"),
        ("rtl_service_latency", "E3", "QUALIFIED_WITHIN_RTL_BOUNDARY", "one synchronous cycle at the declared 10 ns clock"),
        ("rtl_initiation_interval", "E3", "QUALIFIED_WITHIN_RTL_BOUNDARY", "one request per cycle; separate from latency"),
        ("maximum_sustainable_throughput", "E0", "BLOCKED", "no saturation/backpressure experiment"),
        ("macro_placement_geometry", "E4", "MACRO_LEVEL_ONLY", "DEF origin/orientation plus LEF extent and SPICE organization"),
        ("bitcell_xy_and_logical_map", "E0", "BLOCKED", "address/column-select-to-GDS-cell join unavailable"),
        ("qcrit", "E0", "BLOCKED", "no defensible transient-injection run with complete model/waveform provenance"),
        ("physical_event_probability", "E0", "BLOCKED", "no technology/PVT/geometry-matched radiation or field data"),
        ("physical_sdc_due_fit", "E0", "PHYSICAL_SDC_DUE_BLOCKED", "total-probability first stage unavailable"),
        ("implemented_nontrivial_interleaver", "E0", "BLOCKED", "I1/I2 remain proposals"),
        ("manufacturing_and_lifecycle_carbon", "E0", "BLOCKED", "matched SKY130 inventory/lifetime unavailable"),
        ("csci_mrcc", "E0", "BLOCKED", "reliability and lifecycle chain incomplete"),
        ("pareto", "E4", "DIAGNOSTIC_FRONT", "exact area/diagnostic-energy view only"),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "validated_equation_does_not_validate_parameter": True,
        "new_evidence_count": len(new_evidence),
        "new_evidence_tier_counts": dict(sorted(counts.items())),
        "e5_measurement_count": counts.get("E5", 0),
        "metrics": [
            {"metric": metric, "highest_tier": tier, "status": status, "reason": reason}
            for metric, tier, status, reason in metrics
        ],
        "global_architecture_winner": "NO_GLOBAL_WINNER_QUALIFIED",
    }


def _final_report(qualification: Mapping[str, Any], literature: list[dict[str, Any]]) -> str:
    tier_counts = qualification["new_evidence_tier_counts"]
    return f"""# GREEN Matrix 3.1 physical-population final report

## Outcome

This additive campaign preserves GREEN Matrix 3.0 at `{FOUNDATION_COMMIT}` and
adapts existing reproducible U0/E0 evidence into v3.1-compatible records.  It
adds **{qualification['new_evidence_count']}** evidence records: {tier_counts}.  No E5,
E6, or E7 quantity was established.  Equations and executable guards are
validated independently of parameter availability.

Final classification:
`{CLASSIFICATION}`.

The methodology is methodologically informed by publicly available imec
SSTS/imec.netzero bottom-up semiconductor sustainability methodology.  This is
not imec certification, compliance, endorsement, or standardization.

## Required questions

1. **Which v3 quantities became newly populated?** Five matched physical-flow
   observations per U0/E0 architecture now carry implementation, netlist,
   configuration, constraint, workload, and activity hashes; route area,
   wirelength, vias, setup/hold slack, vectorless power components, macro-level
   geometry, deterministic activity traces, one partial-annotation diagnostic
   energy/service value, and RTL service latency/II are populated.
2. **Which measurements reached E5?** None.  The E5 count is zero.
3. **Which remained E4/E3/E2/E1/E0?** New records contain E4 post-route
   diagnostics, E3 RTL/analytical service and activity semantics, {len(literature)} E2
   literature datasets in native mismatched boundaries, no E1 parameter values,
   and E0 structural missingness for physical rates, Qcrit, bitcell mapping,
   nontrivial interleaving, lifecycle carbon, CSCI, and MRCC.
4. **Was matched post-route energy established?** A matched seed-11 diagnostic
   energy per requested service was derived from partial-annotation post-route
   power and the 512-service/5.12 us trace.  Qualified activity-complete E5
   energy was not established.  Read, write, correction, retry, and scrub energy
   remain unavailable; the diagnostic total is not lifecycle energy.
5. **Was service latency established?** Yes at E3 inside the RTL service
   boundary: one synchronous 10 ns cycle for normal and corrected reads.  A
   post-route analog/service-latency distribution was not measured.
6. **Was initiation interval separately established?** Yes, one cycle at E3.
   The nominal initiation capacity is 100 million services/s and is not called
   maximum sustainable throughput.
7. **Was SRAM geometry established?** Only macro origin/orientation/extent and
   electrical array organization were established.  Bitcell xy coordinates and
   address/column-select-to-cell mapping remain unavailable.
8. **Was Qcrit estimated?** No.
9. **What exactly does Qcrit establish and NOT establish?** A defensible Qcrit
   would establish conditional circuit susceptibility at a declared node, PVT,
   state, and injection waveform.  It would not establish particle flux,
   spectrum, charge deposition/collection distribution, topology probability,
   SER, FIT, SDC, or DUE.
10. **Which SBU/MBU literature datasets were collected?** Pieper 5-nm SRAM,
    Perez-Celis/Wirthlin FPGA neutron MCU, Ibe CORIMS scaling, Yahagi 130/180-nm
    neutron MCU, and the NASA Kintex UltraScale heavy-ion report.
11. **Which are technology-matched?** None is independently matched to SKY130
    SRAM22 geometry/process/PVT.
12. **Which are technology-mismatched?** All {len(literature)} records.
13. **Was any literature numeric value transferred to SKY130?** No.
14. **Was any physical event-rate model qualified?** No.
15. **Can physical SDC now be calculated?** No: `PHYSICAL_SDC_DUE_BLOCKED`.
16. **Can physical DUE now be calculated?** No: `PHYSICAL_SDC_DUE_BLOCKED`.
17. **Can FIT now be calculated?** No.  Logical mask frequency is never used as
    an event rate.
18. **Was an interleaver physically implemented?** No nontrivial interleaver.
    I0 is the routed baseline; I1/I2 remain explicit proposals.
19. **What physical overhead did it incur?** I0 has zero added interleaver
    overhead by definition.  I1/I2 area, routing, buffers, energy, latency,
    timing, and congestion are unavailable.
20. **Can any reliability benefit be attributed to it?** No.
21. **What remains structurally missing?** Complete bitcell geometry/mapping,
    calibrated SKY130 SBU/DBU/MBU topology/rate data, Qcrit, activity-complete
    post-route power with disjoint operation attribution, saturated throughput,
    a routed interleaver, SKY130 manufacturing inventory, and lifetime policy.
22. **What is the new highest-value measurement?** A fluence-linked particle
    experiment on the matched SRAM implementation that releases event
    coordinates and is joined to a verified bitcell/logical mapping.
23. **Can CSCI now be populated?** No.
24. **Can MRCC now be populated?** No.
25. **Is any sustainability Pareto frontier qualified?** No.  The emitted exact
    front is `DIAGNOSTIC_FRONT` only.
26. **Is any architecture winner qualified?** No:
    `NO_GLOBAL_WINNER_QUALIFIED`.
27. **What claims are now appropriate for ISCAS?** An evidence-aware cross-layer
    method; a reproducible five-seed matched physical baseline; explicit power,
    energy, latency, and II separation; macro-geometry recovery; a physical
    topology-to-decoder interface; technology-mismatch guards; and exact gated
    diagnostic enumeration.
28. **What claims remain forbidden?** E5 energy, silicon/radiation validation,
    absolute SKY130 SDC/DUE/SER/FIT, Qcrit, physical interleaver benefit, absolute
    manufacturing/lifecycle carbon, CSCI/MRCC, a sustainability-qualified Pareto
    front, imec endorsement, or any global architecture winner.

## Scientific interpretation

The campaign advances population, not outcome certainty.  The correct causal
path remains physical event topology -> logical corruption -> ECC/interleaving
response -> correct service -> operational resource cost -> lifecycle scenario.
The first physical probability term is still missing, so downstream physical
reliability and sustainability selection remain blocked.
"""


def artifact_paths() -> list[Path]:
    return [
        BASE / name
        for name in (
            "MATRIX_P_V3_1.json",
            "MATRIX_P_V3_1.csv",
            "MATRIX_E_V3_1.json",
            "MATRIX_E_V3_1.csv",
            "MATRIX_S_V3_1.json",
            "MATRIX_S_V3_1.csv",
            "GREEN_MATRIX_V3_1_VIEW.json",
            "GREEN_MATRIX_V3_1_VIEW.csv",
            "PHYSICAL_FAULT_TOPOLOGY.json",
            "PHYSICAL_RELIABILITY_BRIDGE.json",
            "POST_ROUTE_ACTIVITY.json",
            "SERVICE_METRICS.json",
            "INTERLEAVER_PHYSICAL_RESULTS.json",
            "LITERATURE_FAULT_EVIDENCE.json",
            "CIRCUIT_UPSET_SUSCEPTIBILITY.json",
            "QUALIFICATION_ASSESSMENT_V3_1.json",
            "VALUE_OF_INFORMATION_V3_1.json",
            "EXACT_PARETO_V3_1.json",
            "SYSTEM_BOUNDARIES_V3_1.json",
            "FROZEN_FOUNDATION_MANIFEST.json",
            "CAMPAIGN_STATUS.json",
            "FINAL_REPORT.md",
        )
    ]


def build_all() -> None:
    parent_p = _load(FOUNDATION / "MATRIX_P.json")
    parent_e = _load(FOUNDATION / "MATRIX_E.json")
    parent_s = _load(FOUNDATION / "MATRIX_S.json")
    new_physical = _new_physical_rows()
    new_evidence = _new_evidence_rows(new_physical)
    literature = _literature_records()
    qualification = _qualification(new_evidence)

    physical_records = [dict(row, record_origin="V3_FOUNDATION") for row in parent_p["records"]] + new_physical
    evidence_records = [dict(row, record_origin="V3_FOUNDATION") for row in parent_e["records"]] + new_evidence
    sustainability_records = [dict(row, record_origin="V3_FOUNDATION") for row in parent_s["records"]]

    matrix_p = {
        "schema_version": SCHEMA_VERSION,
        "matrix_symbol": "M_P",
        "parent_schema_version": parent_p["schema_version"],
        "parent_commit": FOUNDATION_COMMIT,
        "records": physical_records,
        "row_count": len(physical_records),
        "new_row_count": len(new_physical),
    }
    matrix_e = {
        "schema_version": SCHEMA_VERSION,
        "matrix_symbol": "M_E",
        "parent_schema_version": parent_e["schema_version"],
        "parent_commit": FOUNDATION_COMMIT,
        "records": evidence_records,
        "row_count": len(evidence_records),
        "new_row_count": len(new_evidence),
    }
    matrix_s = {
        "schema_version": SCHEMA_VERSION,
        "matrix_symbol": "M_S",
        "parent_schema_version": parent_s["schema_version"],
        "parent_commit": FOUNDATION_COMMIT,
        "records": sustainability_records,
        "row_count": len(sustainability_records),
        "new_row_count": 0,
        "status": "UNCHANGED_BLOCKED_TRANSLATIONS_NO_QUALIFIED_NEW_LIFECYCLE_INPUT",
    }
    for stem, matrix in (("MATRIX_P_V3_1", matrix_p), ("MATRIX_E_V3_1", matrix_e), ("MATRIX_S_V3_1", matrix_s)):
        _write_json(f"{stem}.json", matrix)
        _write_csv(f"{stem}.csv", matrix["records"])

    activity, manifest, workloads = _activity_sources()
    energy_by_architecture: dict[str, float] = {}
    activity_rows: list[dict[str, Any]] = []
    read_workload = next(row for row in workloads if row["workload_id"] == "read_dominant")
    for workload in workloads:
        for architecture in ARCHITECTURES:
            trace = workload["activity"][architecture]
            activity_rows.append(
                {
                    "architecture_id": architecture,
                    "workload_id": workload["workload_id"],
                    "workload_hash": workload["trace_sha256"],
                    "activity_file": trace["file"],
                    "activity_file_hash": trace["sha256"],
                    "testbench_hash": trace["testbench_sha256"],
                    "cycles": workload["cycles"],
                    "duration_s": workload["duration_s"],
                    "read_count": trace["simulation_counts"].get("read", 0),
                    "write_count": trace["simulation_counts"].get("write", 0),
                    "corrected_reads": trace["simulation_counts"].get("corrected_reads", 0),
                    "due_reads": trace["simulation_counts"].get("due_reads", 0),
                    "sdc_reads": trace["simulation_counts"].get("sdc_reads", 0),
                    "unknown_value_events": trace["unknown_value_events"],
                    "evidence_tier": "E3",
                    "evidence_kind": "ANALYTICAL",
                    "qualification_status": "DETERMINISTIC_MATCHED_RTL_ACTIVITY",
                    "physical_fault_semantics": workload["fault_scope"],
                }
            )
    postroute_rows: list[dict[str, Any]] = []
    for architecture in ARCHITECTURES:
        row = activity[architecture]
        energy = derive_energy_from_power(
            row["power_total_w"],
            read_workload["duration_s"],
            read_workload["cycles"],
            source_kind="POST_ROUTE_ESTIMATE",
            functional_unit="one requested read-or-write memory service in the matched read_dominant trace",
        )
        energy_by_architecture[architecture] = energy.energy_per_service_j
        postroute_rows.append(
            dict(
                row,
                measurement_boundary="whole routed wrapper; incomplete pin annotation and default activity on unmatched pins",
                duration_s=read_workload["duration_s"],
                service_count=read_workload["cycles"],
                functional_unit=energy.functional_unit,
                diagnostic_window_energy_j=energy.window_energy_j,
                diagnostic_energy_per_requested_service_j=energy.energy_per_service_j,
                energy_evidence_tier="E4",
                energy_evidence_kind="POST_ROUTE_ESTIMATE",
                energy_qualification_status="DIAGNOSTIC_ONLY_NOT_E5",
                read_energy_j="UNAVAILABLE",
                write_energy_j="UNAVAILABLE",
                correction_energy_j="UNAVAILABLE",
                retry_energy_j="UNAVAILABLE",
                scrub_energy_j="UNAVAILABLE",
                idle_leakage_energy_per_requested_service_j=row["power_leakage_w"] * read_workload["duration_s"] / read_workload["cycles"],
                accounting_rule="internal + switching + leakage = total; total is not added to its components",
            )
        )
    _write_json(
        "POST_ROUTE_ACTIVITY.json",
        {
            "schema_version": SCHEMA_VERSION,
            "classification": "MATCHED_RTL_ACTIVITY_WITH_PARTIAL_POST_ROUTE_ANNOTATION_ENERGY_E4_DIAGNOSTIC",
            "workload_count": len(workloads),
            "rtl_activity_row_count": len(activity_rows),
            "postroute_row_count": len(postroute_rows),
            "rtl_activity_rows": activity_rows,
            "postroute_rows": postroute_rows,
            "tool_version": _load(ATTEMPT10 / "energy" / "POSTROUTE_ACTIVITY_DIAGNOSTIC.json")["tool_version"],
            "source_manifest_classification": manifest["classification"],
            "e5_established": False,
        },
    )

    service_rows = list(_service_metrics().values())
    _write_json("SERVICE_METRICS.json", {"schema_version": SCHEMA_VERSION, "records": service_rows})

    macro_audit = _load(ATTEMPT10 / "interleaving" / "MACRO_ORGANIZATION_AUDIT.json")
    mapping = _load(ATTEMPT10 / "interleaving" / "BIT_INTERLEAVING_MAP.json")
    _write_json(
        "PHYSICAL_FAULT_TOPOLOGY.json",
        {
            "schema_version": SCHEMA_VERSION,
            "topology_families": [
                "SBU",
                "ADJACENT_DBU",
                "NON_ADJACENT_DBU",
                "HORIZONTAL_MCU",
                "VERTICAL_MCU",
                "CLUSTERED_MCU",
                "BURST_SPAN_K_MCU",
                "BANK_CROSSING_EVENT",
                "CODEWORD_CROSSING_EVENT",
            ],
            "event_object_schema": {
                "event_id": "string",
                "physical_cells": ["cell_id"],
                "example_shape_only": [["r", "c"], ["r", "c+1"], ["r+1", "c"]],
                "required_cell_fields": ["row", "column", "bit_index", "codeword", "word", "bank", "x_um", "y_um", "neighbors", "source_hash"],
            },
            "macro_geometry_records": macro_audit["rows"],
            "macro_geometry_status": "POST_ROUTE_MACRO_PLACEMENT_AND_ELECTRICAL_ORGANIZATION_AVAILABLE",
            "bitcell_geometry_status": "UNAVAILABLE",
            "physical_events": [],
            "blocking_reason": "complete address/column-select-to-GDS-bitcell map and calibrated event clusters are unavailable",
        },
    )
    _write_json(
        "PHYSICAL_RELIABILITY_BRIDGE.json",
        {
            "schema_version": SCHEMA_VERSION,
            "formula": "P(outcome) = sum_f P(outcome | f, ECC, interleaving, policy) * P(f | technology, geometry, PVT, environment)",
            "outcomes": list(OUTCOMES),
            "stage_1_physical_event_model": {"status": "E0_UNAVAILABLE", "probabilities": None},
            "stage_2_conditional_ecc_model": {
                "status": "E3_EXACT_LOGICAL_MODEL_AVAILABLE_AFTER_MAPPING",
                "source": "Attempt10 topology_reliability.py and frozen Hsiao decoder",
                "physical_mapping_status": "E0_UNAVAILABLE",
            },
            "physical_sdc": "PHYSICAL_SDC_DUE_BLOCKED",
            "physical_due": "PHYSICAL_SDC_DUE_BLOCKED",
            "ser": "BLOCKED",
            "fit": "BLOCKED",
            "logical_enumeration_semantics": "ENUMERATED_MASK_FREQUENCY_NOT_EVENT_RATE",
            "literature_transfer": "NO_NUMERIC_VALUE_TRANSFERRED_TO_SKY130",
        },
    )
    _write_json(
        "INTERLEAVER_PHYSICAL_RESULTS.json",
        {
            "schema_version": SCHEMA_VERSION,
            "records": mapping["configurations"],
            "baseline": "I0 routed macro-level organization; no added external interleaver",
            "implemented_nontrivial_interleaver_count": 0,
            "reliability_benefit_qualified": False,
            "classification": "I0_BASELINE_PHYSICAL_I1_I2_PROPOSALS_NOT_IMPLEMENTED",
        },
    )
    _write_json(
        "CIRCUIT_UPSET_SUSCEPTIBILITY.json",
        {
            "schema_version": SCHEMA_VERSION,
            "sram_spice_available": True,
            "spice_source": str((ATTEMPT09 / "source_checkout" / "sram22_256x64m4w8" / "sram22_256x64m4w8.spice").relative_to(REPO)).replace("\\", "/"),
            "model_card_bundle_qualified_in_campaign": False,
            "transient_injection_waveform_provenance": "UNAVAILABLE",
            "qcrit_c": None,
            "qcrit_status": "E0_BLOCKED",
            "blocking_reason": "no reproducible isolated-bitcell injection deck, qualified PDK model-card bundle, state/PVT sweep, convergence audit, or waveform provenance was executed",
            "causal_separation": ["particle generation", "charge deposition", "charge collection", "circuit upset", "logical word corruption", "ECC outcome"],
            "forbidden_inference": "SPICE current injection is not a measured particle spectrum or event rate",
        },
    )
    _write_json(
        "LITERATURE_FAULT_EVIDENCE.json",
        {
            "schema_version": SCHEMA_VERSION,
            "records": literature,
            "record_count": len(literature),
            "technology_matched_count": 0,
            "technology_mismatched_count": len(literature),
            "numeric_values_transferred_to_sky130": 0,
        },
    )

    means: dict[str, dict[str, float]] = {}
    for architecture in ARCHITECTURES:
        subset = [row for row in new_physical if row["architecture_id"] == architecture]
        means[architecture] = {
            "mean_routed_total_area_um2": fmean(float(row["routed_total_area_um2"]) for row in subset),
            "mean_wirelength_um": fmean(float(row["wirelength_um"]) for row in subset),
            "mean_vectorless_power_w": fmean(float(row["power_total_vectorless_w"]) for row in subset),
            "diagnostic_energy_per_requested_service_j": energy_by_architecture[architecture],
        }
    points = [[means[architecture]["mean_routed_total_area_um2"], means[architecture]["diagnostic_energy_per_requested_service_j"]] for architecture in ARCHITECTURES]
    indices = exact_pareto_indices(points)
    front_class = classify_pareto_front(["E4"], physical_probabilities_qualified=False, sustainability_qualified=False)
    pareto = {
        "schema_version": SCHEMA_VERSION,
        "enumeration": "EXACT",
        "objectives": ["mean_routed_total_area_um2", "diagnostic_energy_per_requested_service_j"],
        "objective_directions": ["minimize", "minimize"],
        "front_classification": front_class,
        "front_architectures": [ARCHITECTURES[index] for index in indices],
        "publication_grade": False,
        "global_winner_qualified": False,
        "reason": "diagnostic E4 energy with incomplete activity annotation; physical reliability and lifecycle sustainability are blocked",
    }
    _write_json("EXACT_PARETO_V3_1.json", pareto)
    view_rows = []
    for architecture in ARCHITECTURES:
        view_rows.append(
            {
                "architecture_id": architecture,
                **means[architecture],
                "route_evidence_tier": "E4",
                "diagnostic_energy_evidence_tier": "E4",
                "service_latency_s": _service_metrics()[architecture]["registered_service_latency_s"],
                "service_latency_evidence_tier": "E3",
                "initiation_interval_cycles": 1,
                "maximum_sustainable_throughput_services_per_s": "",
                "physical_sdc_probability": "",
                "physical_due_probability": "",
                "fit": "",
                "manufacturing_carbon_kgco2e": "",
                "csci_kgco2e_per_correct_service": "",
                "mrcc_kgco2e_per_additional_correct_service": "",
                "pareto_status": front_class,
                "on_diagnostic_front": architecture in pareto["front_architectures"],
                "global_winner_qualified": False,
            }
        )
    view = {"schema_version": SCHEMA_VERSION, "records": view_rows, "row_count": len(view_rows)}
    _write_json("GREEN_MATRIX_V3_1_VIEW.json", view)
    _write_csv("GREEN_MATRIX_V3_1_VIEW.csv", view_rows)

    _write_json("QUALIFICATION_ASSESSMENT_V3_1.json", qualification)
    _write_json(
        "VALUE_OF_INFORMATION_V3_1.json",
        {
            "schema_version": SCHEMA_VERSION,
            "priority_measurement": "MATCHED_SKY130_SRAM_PARTICLE_BEAM_EVENT_COORDINATES_FLUENCE_AND_VERIFIED_BITCELL_LOGICAL_MAP",
            "reason": "one matched dataset would populate P(f), enable physical topology replay, and unlock distinct SDC/DUE feasibility before sustainability comparison",
            "structural_missingness_not_a_confidence_interval": True,
            "next_measurements": [
                "activity-complete glitch-aware multi-seed post-route read/write/correction power with validated SRAM internal models",
                "isolated-bitcell Qcrit PVT/state study with explicit parametric waveform provenance",
                "routed I1 interleaver with complete physical mapping and overhead",
                "SKY130-native manufacturing inventory",
            ],
        },
    )
    _write_json(
        "SYSTEM_BOUNDARIES_V3_1.json",
        {
            "schema_version": SCHEMA_VERSION,
            "parent": "../green_matrix_v3_imec_aligned/SYSTEM_BOUNDARIES.json",
            "boundaries": [
                {
                    "boundary_id": BOUNDARY,
                    "technology": "SKY130HD_WITH_SRAM22_RESEARCH_MACROS",
                    "pvt": "TT/25C/1.8V",
                    "clock": "10 ns, 0.1 ns uncertainty",
                    "physical_flow": "Attempt09 upstream-original ORFS",
                    "workload": "Attempt10 deterministic read_dominant trace, seed 11 for partial post-route activity",
                    "functional_unit": "one requested payload-bearing memory service; correct-service qualification remains blocked",
                    "excluded": ["manufacturing", "packaging", "lifetime", "external recovery"],
                }
            ],
        },
    )

    frozen_files = [
        "FRAMEWORK_SPECIFICATION.md", "FINAL_REPORT.md", "CSCI_DEFINITION.md", "CSCI_MATHEMATICAL_AUDIT.md",
        "MRCC_DEFINITION.md", "MRCC_MATHEMATICAL_AUDIT.md", "EVIDENCE_TAXONOMY.md", "QUALIFICATION_RULES.json",
        "MATRIX_P.json", "MATRIX_P.csv", "MATRIX_E.json", "MATRIX_E.csv", "MATRIX_S.json", "MATRIX_S.csv",
        "SYSTEM_BOUNDARIES.json", "FAULT_MODEL_REGISTRY.json", "INTERLEAVING_REGISTRY.json", "WORKLOAD_REGISTRY.json",
        "SERVICE_POLICY_REGISTRY.json", "TECHNOLOGY_REGISTRY.json", "SOURCE_REGISTRY.json", "SOURCE_REGISTRY.csv",
        "UNCERTAINTY_MODEL.json", "uncertainty/VALUE_OF_INFORMATION.json",
    ]
    manifest_rows = [
        {"path": str((FOUNDATION / name).relative_to(REPO)).replace("\\", "/"), "sha256": _sha(FOUNDATION / name)}
        for name in frozen_files
    ]
    _write_json(
        "FROZEN_FOUNDATION_MANIFEST.json",
        {
            "schema_version": SCHEMA_VERSION,
            "foundation_commit": FOUNDATION_COMMIT,
            "requested_starting_baseline_commit": REQUESTED_BASELINE_COMMIT,
            "records": manifest_rows,
            "legacy_v1_v2_modified": False,
        },
    )
    _write_json(
        "CAMPAIGN_STATUS.json",
        {
            "schema_version": SCHEMA_VERSION,
            "classification": CLASSIFICATION,
            "foundation_commit": FOUNDATION_COMMIT,
            "requested_starting_baseline_commit": REQUESTED_BASELINE_COMMIT,
            "architectures": list(ARCHITECTURES),
            "physical_seed_count_per_architecture": len(SEEDS),
            "matched_workload_count": len(workloads),
            "parent_matrix_counts": {"M_P": len(parent_p["records"]), "M_E": len(parent_e["records"]), "M_S": len(parent_s["records"])},
            "new_matrix_counts": {"M_P": len(new_physical), "M_E": len(new_evidence), "M_S": 0},
            "new_evidence_tier_counts": qualification["new_evidence_tier_counts"],
            "newly_qualified_metrics": ["RTL_SERVICE_LATENCY_E3", "RTL_INITIATION_INTERVAL_E3", "MATCHED_ROUTE_DIAGNOSTICS_E4", "MATCHED_RTL_ACTIVITY_E3"],
            "still_blocked_metrics": ["E5_OPERATIONAL_ENERGY", "BITCELL_GEOMETRY", "QCRIT", "PHYSICAL_EVENT_PROBABILITY", "PHYSICAL_SDC", "PHYSICAL_DUE", "FIT", "NONTRIVIAL_PHYSICAL_INTERLEAVER", "MANUFACTURING_CARBON", "CSCI", "MRCC", "SUSTAINABILITY_PARETO"],
            "highest_value_remaining_measurement": "MATCHED_SKY130_SRAM_PARTICLE_BEAM_EVENT_COORDINATES_FLUENCE_AND_VERIFIED_BITCELL_LOGICAL_MAP",
            "global_architecture_winner": "NO_GLOBAL_WINNER_QUALIFIED",
        },
    )
    (BASE / "FINAL_REPORT.md").write_text(_final_report(qualification, literature), encoding="utf-8")


if __name__ == "__main__":
    build_all()
