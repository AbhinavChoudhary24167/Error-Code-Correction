"""Frozen Gate-03 identifiers, schemas, and decision vocabulary."""

from __future__ import annotations

ELIGIBLE_IMPLEMENTATIONS = (
    "forge-hotspot-8-4-v1-archived-table-decoder",
    "forge-spatial-hotspot-72-64-v1-archived-table-decoder",
    "forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder",
    "forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder",
    "hsiao-generated-combinational-72-64-v1",
    "odd-column-secded-4-8-archived-table-decoder",
    "odd-column-secded-64-72-archived-table-decoder",
    "primitive-bch-63-51-t2-v1-reference-decoder",
    "safeforge-robust-72-64-mapping-v1-archived-table-decoder",
    "safeforge-robust-8-4-v1-archived-table-decoder",
    "secded-rtl-combinational-72-64-v1",
    "shortened-bch-71-64-t1-v1-reference-decoder",
    "shortened-bch-78-64-t2-v1-reference-decoder",
    "shortened-bch-85-64-t3-v1-reference-decoder",
)

EXCLUDED_IMPLEMENTATIONS = (
    "cyclic-rtl-bounded-search-63-51-v1",
    "secdaec-rtl-bounded-72-64-v1",
    "taec-rtl-bounded-72-64-v1",
)

SENTINELS = (
    "secded-rtl-combinational-72-64-v1",
    "hsiao-generated-combinational-72-64-v1",
    "shortened-bch-78-64-t2-v1-reference-decoder",
)

STAGES = (
    "rtl_elaboration",
    "functional_simulation",
    "gate02_identity_reconciliation",
    "technology_mapping",
    "mapped_netlist_verification",
    "static_timing_analysis",
    "primary_activity_trace",
    "primary_activity_power",
    "placement_and_routing",
    "parasitic_extraction",
    "post_route_timing",
    "post_route_power",
)

EVIDENCE_ENUMS = (
    "MEASURED",
    "SYNTHESIZED",
    "SIMULATED",
    "DERIVED",
    "ASSUMED",
    "PROXY",
    "UNRESOLVED",
)

WORKLOADS = {
    "verification-stress-v1": {
        "purpose": "verification_only",
        "clean_fraction": "4/5",
        "single_error_fraction": "1/10",
        "double_error_fraction": "1/10",
        "eligible_for_primary_power": False,
    },
    "normal-clean-random-v1": {
        "purpose": "primary_power",
        "clean_fraction": "1/1",
        "single_error_fraction": "0/1",
        "double_error_fraction": "0/1",
        "eligible_for_primary_power": True,
    },
    "conditional-single-v1": {
        "purpose": "conditional_power_only",
        "clean_fraction": "0/1",
        "single_error_fraction": "1/1",
        "double_error_fraction": "0/1",
        "eligible_for_primary_power": False,
    },
    "conditional-double-v1": {
        "purpose": "conditional_power_only",
        "clean_fraction": "0/1",
        "single_error_fraction": "0/1",
        "double_error_fraction": "1/1",
        "eligible_for_primary_power": False,
    },
}
WORKLOAD_SEED = "0x475245454E454343"
WARMUP_CYCLES = 256
MEASURED_CYCLES = 8192

RTL_MATRIX_HEADER = (
    "implementation_id", "mathematical_code_id", "canonical_identity_hash",
    "n", "k", "r", "eligibility", "source_model", "encoder_rtl_present",
    "decoder_rtl_present", "rtl_source_paths", "encoder_top", "decoder_top",
    "parameters", "synthesizable", "organization", "pipeline_depth",
    "encoder_latency_cycles", "decoder_latency_cycles", "initiation_interval_cycles",
    "protocol", "clock_required", "reset_required", "generated_status",
    "gate02_identity_status", "existing_equivalence_evidence", "hardware_structure_id",
    "duplicate_or_alias_of", "missing_hardware", "physical_feasibility_status",
    "evidence_paths", "notes",
)

PPA_HEADER = (
    "implementation_id", "mathematical_code_id", "canonical_identity_hash",
    "hardware_structure_id", "h2_identity_group", "h2_status", "physical_status",
    "technology", "library", "pvt_corner", "rtl_elaboration",
    "functional_verification", "technology_mapping", "sta_status",
    "primary_activity_trace", "primary_activity_power", "conditional_single_power",
    "conditional_double_power", "placement", "routing", "parasitic_extraction",
    "post_route_sta", "post_route_power", "repeat_run_status",
    "mapped_codec_stdcell_area_um2", "mapped_wrapper_stdcell_area_um2",
    "mapped_total_stdcell_area_um2", "postroute_stdcell_area_um2",
    "allocated_core_area_um2", "allocated_die_area_um2", "critical_path_delay_ns",
    "critical_path_limited_frequency_mhz", "common_target_slack_ns",
    "primary_internal_power_mw", "primary_switching_power_mw",
    "primary_leakage_power_mw", "primary_total_power_mw",
    "primary_energy_per_operation_pj", "conditional_single_energy_per_operation_pj",
    "conditional_double_energy_per_operation_pj", "evidence_classification",
    "config_id", "primary_activity_id", "toolchain_id", "run_ids",
    "raw_report_ids", "blocking_reason",
)

SENTINEL_HEADER = (
    "run_id", "repeat_index", "sentinel_id", "implementation_id",
    "hardware_structure_id", "stage", "attempt", "command_id", "status",
    "start_utc", "end_utc", "exit_code", "config_id", "rtl_sha256",
    "library_sha256", "activity_sha256", "workload_id", "toolchain_id",
    "raw_log_id", "output_artifact_ids", "failure_reason", "retry_of_command_id",
)

RAW_REPORT_HEADER = (
    "raw_report_id", "run_id", "command_id", "implementation_id", "stage",
    "report_type", "location_kind", "path", "size_bytes", "sha256",
    "producer_tool", "producer_version", "config_id", "rtl_sha256",
    "library_sha256", "activity_sha256", "workload_id", "retained_in_git", "notes",
)

EVIDENCE_HEADER = (
    "evidence_id", "implementation_id", "quantity", "raw_value", "unit",
    "classification", "scope", "source_report_id", "workload_id", "derivation",
    "limitations",
)

PREFREEZE = {
    "captured_utc": "2026-08-05T04:48:48.0287154Z",
    "branch": "main",
    "commit": "61b2eec71e900ce698831b3f26011bc200dead40",
    "upstream": "origin/main",
    "ahead": 0,
    "behind": 0,
    "tracked_count": 1114,
    "untracked": [],
    "repository_tree_sha256": "0b92512b5bdaf6c33eb4414500eca1583e5db3f42dc9dcdf625067a2e5f8991d",
    "gate01_tree_sha256": "13a2993d669b1fe54c344ed3836e3480724d4ea969e59d385e34fa50c2d132e2",
    "gate02_tree_sha256": "983cc2eb2c15ee452feca56c67c8dbbbd221d94cee7a00b1b7f3904ab4419b6c",
    "hash_scheme": "sha256(sorted utf8 path NUL size NUL raw_sha256 LF)",
    "gitlinks": [],
    "gitmodules_present": False,
    "lfs_files": [],
    "host": {
        "hostname": "BILLIONDOLLARS",
        "os": "Microsoft Windows NT 10.0.26200.0",
        "filesystem": "NTFS",
        "processor_count": 16,
        "timezone": "India Standard Time",
        "powershell": "5.1.26100.8875",
    },
    "line_endings": {
        "core.autocrlf": "file:D:/Git/etc/gitconfig true",
        "core.eol": None,
        "core.safecrlf": None,
    },
    "relevant_environment_names_only": ["LM_LICENSE_FILE"],
}
