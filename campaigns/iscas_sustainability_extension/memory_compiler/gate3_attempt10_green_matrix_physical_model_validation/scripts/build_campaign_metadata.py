#!/usr/bin/env python3
"""Build Attempt10 environment, status, README, and artifact manifests."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path


CAMPAIGN = "gate3_attempt10_green_matrix_physical_model_validation"
PARENT_COMMIT = "9968f9b15f949d38faf944a3546ea736cfab63df"
BRANCH = "codex/gate3-attempt10-green-matrix-physical-model-validation"
IMAGE = "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
SRAM22_COMMIT = "75cbe961e18ee00d5a6c73fa455505f0bcdf4c05"
SEEDS = [11, 13, 17, 19, 23]

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parents[1]
ATTEMPT09 = HERE.parent / "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def hash_files(paths: list[Path]) -> dict[str, str]:
    return {rel(path): sha256(path) for path in paths if path.is_file()}


def load(relative: str) -> dict:
    return json.loads((HERE / relative).read_text(encoding="utf-8"))


def phase(
    phase_id: str,
    title: str,
    classification: str,
    proven: list[str],
    unproven: list[str],
    original_corrected: str,
    matched: str,
    robustness: str,
    ppa: str,
    energy: str,
    reliability: str,
    carbon: str,
    green: str,
    iscas: str,
    unsupported: list[str],
    integrity: str,
    next_action: str,
) -> dict:
    return {
        "phase": phase_id,
        "title": title,
        "exact_classification": classification,
        "proven": proven,
        "unproven": unproven,
        "original_vs_corrected_model": original_corrected,
        "u0_e0_matched_results": matched,
        "five_seed_robustness": robustness,
        "effect_on_ppa": ppa,
        "effect_on_energy": energy,
        "effect_on_reliability": reliability,
        "effect_on_carbon": carbon,
        "effect_on_green_ranking": green,
        "impact_on_iscas_claims": iscas,
        "new_unsupported_claims": unsupported,
        "repository_integrity_status": integrity,
        "recommended_next_action": next_action,
    }


def build_environment() -> dict:
    source_paths = [
        ATTEMPT09 / "rtl" / "unprotected_sram_256x64_sram22.sv",
        ATTEMPT09 / "rtl" / "ecc_sram_256x72_sram22.sv",
        ATTEMPT09 / "rtl" / "hsiao_secded_72_64_v1_encoder.sv",
        ATTEMPT09 / "rtl" / "hsiao_secded_72_64_v1_syndrome.sv",
        ATTEMPT09 / "rtl" / "hsiao_secded_72_64_v2_algorithmic_decoder.sv",
        ATTEMPT09 / "source_checkout" / "sram22_256x64m4w8" / "sram22_256x64m4w8.v",
        ATTEMPT09 / "source_checkout" / "sram22_256x8m8w1" / "sram22_256x8m8w1.v",
    ]
    constraint_paths = [
        ATTEMPT09 / "openroad" / "common.mk",
        ATTEMPT09 / "openroad" / "u0" / "config.mk",
        ATTEMPT09 / "openroad" / "u0" / "constraint.sdc",
        ATTEMPT09 / "openroad" / "u0" / "macro_placement.tcl",
        ATTEMPT09 / "openroad" / "e0" / "config.mk",
        ATTEMPT09 / "openroad" / "e0" / "constraint.sdc",
        ATTEMPT09 / "openroad" / "e0" / "macro_placement.tcl",
    ]
    liberty_audit = load("liberty/LIBERTY_TRANSITION_MODEL_AUDIT.json")
    sram_liberties = {}
    for view in liberty_audit["views"]:
        source = view["source_relative_to_attempt09"]
        sram_liberties[source] = view["source_sha256"]
    scripts = sorted(HERE.glob("scripts/*"))
    configurations = sorted(HERE.glob("openroad/**/*"))
    return {
        "schema_version": 1,
        "campaign": CAMPAIGN,
        "generated_on": "2026-09-07",
        "repository": {
            "parent_commit": PARENT_COMMIT,
            "branch": BRANCH,
            "worktree_path": str(ROOT),
            "campaign_path": rel(HERE),
            "attempt09_frozen_path": rel(ATTEMPT09),
        },
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "wsl_distribution": "Ubuntu-24.04",
            "wsl_release": "24.04.4 LTS",
            "wsl_kernel": "6.18.33.2-microsoft-standard-WSL2",
        },
        "tools": {
            "openroad": "26Q3-1080-gab6fd26351",
            "opensta": "3.1.0",
            "orfs_revision": "ORFS_VERSION_NOT_EXPOSED_BY_FROZEN_IMAGE",
            "orfs_executable_provenance": IMAGE,
            "docker_image": IMAGE,
            "docker_image_created_utc": "2026-08-10T13:38:16.013541933Z",
            "docker_base_label": "22.04",
        },
        "technology": {
            "platform": "sky130hd",
            "pdk_release": "PDK_RELEASE_NOT_EXPOSED_BY_FROZEN_IMAGE",
            "pvt": "SKY130HD TT/25C/1.8V",
            "routing_stack": ["met1", "met2", "met3", "met4", "met5"],
            "standard_cell_liberty": {
                "container_path": "/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
                "sha256": "ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9",
            },
        },
        "sram22": {"upstream_commit": SRAM22_COMMIT, "liberty_sha256": sram_liberties},
        "experiment": {
            "clock_period_ns": 10.0,
            "clock_frequency_mhz": 100.0,
            "clock_uncertainty_ns": 0.1,
            "seeds": SEEDS,
            "architectures": ["U0", "E0"],
            "liberty_models": ["UPSTREAM_ORIGINAL", "RESEARCH_CORRECTED_DIAGNOSTIC", "PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL"],
            "constraint_relaxation": False,
            "raw_orfs_evidence_root": "/var/tmp/green-ecc-attempt10/orfs",
        },
        "rtl_sha256": hash_files(source_paths),
        "constraint_and_frozen_config_sha256": hash_files(constraint_paths),
        "attempt10_script_sha256": hash_files([p for p in scripts if p.is_file()]),
        "attempt10_openroad_config_sha256": hash_files([p for p in configurations if p.is_file()]),
        "provenance_limits": [
            "The frozen image exposes exact executable versions and an immutable image digest, but no ORFS git checkout metadata.",
            "The frozen image does not expose a separately attributable PDK release identifier; platform, PVT, path, and Liberty hash are recorded.",
        ],
    }


def build_status() -> dict:
    sensitivity = load("liberty/LIBERTY_SENSITIVITY_RESULTS.json")
    rstb = load("rstb/RSTB_INTERFACE_CHARACTERIZATION.json")
    physical = load("green_matrix/GREEN_MATRIX_PHYSICAL.json")
    carbon = load("carbon/CARBON_RESULTS.json")
    pareto = load("pareto/PARETO_RESULTS.json")
    summaries = [
        phase("A", "Liberty output-transition model sensitivity", sensitivity["classification"],
              ["All six frozen SRAM22 Liberty views and 24 output transition tables were audited.", "The global 0.04 ns value conflicts with every supplied output transition table.", "All 30 strict configurations were executed; 20 completed and 10 diagnostic U0 runs aborted deterministically at RSZ-0090.", "Corrected and no-global E0 PPA are identical across all five seeds."],
              ["Foundry accuracy of either diagnostic view.", "Corrected/counterfactual U0 PPA because strict runs abort before completion."],
              "UPSTREAM_ORIGINAL is retained as production evidence; isolated research-corrected and no-global views are sensitivity-only.",
              "Original U0/E0 reproduce Attempt09 for five seeds. Diagnostic E0 completes; diagnostic U0 aborts before PPA.",
              "Original 10/10 and diagnostic E0 10/10 complete; diagnostic U0 10/10 aborts (strict plus retained non-qualifying continuation evidence).",
              "For E0, corrected versus original means: standard-cell area -6.7524%, wirelength +0.7381%, vias -7.5332%, tool power -0.5083%; U0 is not qualified.",
              "No activity-qualified energy conclusion; only post-route tool-power sensitivity.", "No reliability effect measured.", "No qualified carbon effect.", "No ranking is permitted while source objectives are unqualified.",
              "Supports a physically observed optimizer sensitivity claim for E0 and a deterministic feasibility-boundary claim for U0.",
              ["Foundry-corrected Liberty", "Diagnostic U0 PPA equivalence", "Gate-3 closure"], "PASS at baseline; final integrity is recorded separately.",
              "Independently re-characterize SRAM output constraints and investigate U0 RSZ-0090 without changing Gate-3 limits."),
        phase("B", "256x64 data-rstb physical characterization", rstb["classification"],
              ["The 256x64 rise capacitance is 0.448008 pF versus 0.250926 pF for 256x8 (1.785419x).", "Macro pin load dominates measured routed wire capacitance.", "Zero-wire and localized strongest-driver tests still miss 0.351 ns for the 256x64 macro; the 256x8 comparison can pass.", "OpenSTA and table interpolation agree within 4.34e-8 ns."],
              ["A universal frozen-interface impossibility proof.", "That the 0.351 ns input limit is invalid."],
              "This phase retains upstream input constraints and does not use the output-transition diagnostic correction.",
              "Attempt09 seed11 is reproduced: U0 0.619147718 ns, E0 data 0.615635812 ns, E0 ECC 0.307288498 ns.",
              "Five-seed historical closure remains 5/5 setup/hold and 0/5 external-DRV clean; controlled diagnostics are characterization experiments.",
              "No retained implementation PPA replacement.", "No energy result.", "Explains a physical parameter relevant to fault-protection implementation but changes no reliability rate.", "No carbon result.", "No ranking effect.",
              "Supports the narrower-macro load explanation while preserving an explicit evidence limit.", ["Frozen interface impossibility", "Constraint provenance inconsistency"], "PASS at baseline; final integrity is recorded separately.",
              "Obtain independent macro input-slew characterization including internal RC/transient evidence."),
        phase("C", "Physical GREEN matrix schema", "SCHEMA_COMPLETE_WITH_EXPLICIT_MISSINGNESS", ["The required physical, reliability, energy, carbon, and score fields have typed semantics and explicit sentinel values.", f"The physical table contains {physical['row_count']} provenance-linked rows."], ["Missing quantities are not measurements."], "Rows explicitly label original or research-corrected Liberty.", "U0/E0 rows remain separate by architecture, model, and seed.", "Five canonical seeds are represented for each baseline/model combination that can be populated.", "Measured physical fields are preserved without imputation.", "Unqualified energy stays NOT_QUALIFIED.", "Physical rates stay NOT_QUALIFIED.", "Carbon stays NOT_QUALIFIED.", "No scores are computed.", "Provides the auditable data contract for later ISCAS evaluation.", [], "PASS at baseline; final integrity is recorded separately.", "Populate currently missing fields only from traceable experiments."),
        phase("D", "U0/E0 matched GREEN baseline", "PROVENANCE_AWARE_PHYSICAL_BASELINE_POPULATED", ["Original five-seed U0/E0 metrics and completed corrected E0 metrics are populated.", "Diagnostic U0 abort rows retain explicit NOT_MEASURED values."], ["Corrected U0 physical comparison.", "Gate-3 pass."], "Both baselines coexist; no silent substitution.", "Ten upstream-original rows plus ten research-corrected rows are represented.", "Original five seeds complete for both; corrected E0 five seeds complete; corrected U0 five runs abort.", "E0 material changes are quantified; U0 diagnostic change is unqualified.", "Energy fields remain gated.", "Reliability fields remain gated.", "Carbon fields remain gated.", "Rows are excluded from ranking while required objectives remain unavailable.", "Provides a defensible matched physical baseline.", ["Macro-internal DRC", "Independent LVS", "Qualified energy"], "PASS at baseline; final integrity is recorded separately.", "Close the corrected U0 feasibility gap or retain it as an excluded design point."),
        phase("E", "Activity-qualified energy", "RTL_ACTIVITY_COMPLETE_ENERGY_NOT_QUALIFIED", ["Eight workloads execute identically for U0 and E0 with checked outputs and no unknowns.", "A seed-11 upstream-original post-route diagnostic records exact annotation coverage and power-component tool estimates."], ["Activity-qualified energy/access.", "Five-seed and corrected-model activity power.", "Validated macro read/write internal energy.", "Glitch-aware gate activity and disjoint component attribution."], "Activity traces do not change Liberty; sensitivity models were not used for the post-route diagnostic.", "Workload traces are matched; post-route coverage is U0 48.68% and E0 4.35%.", "RTL activity is deterministic, but post-route activity power is only seed11.", "No physical implementation changes were made in this phase.", "Energy values remain NOT_QUALIFIED.", "No rate effect.", "No carbon values may consume the partial estimate.", "No GREEN score may consume the partial estimate.", "Defines a reproducible workload-to-activity chain and documents why power-to-energy remains incomplete.", ["Energy per access", "Architecture energy advantage", "Macro power-model accuracy"], "PASS at baseline; final integrity is recorded separately.", "Run mapped, glitch-aware, five-seed activity with independently validated macro power and explicit component partitioning."),
        phase("F", "Physical bit interleaving", "PHYSICAL_TOPOLOGY_MAPPING_INCOMPLETE", ["I0 macro placements and macro dimensions are extracted from frozen DEF/LEF evidence.", "I1/I2 are explicit banking and transpose proposals with stated implementation requirements."], ["Bitcell coordinates or address-to-physical-bit maps.", "Physical separation, routing, area, energy, and latency for I1/I2."], "Independent of Liberty model.", "Both architectures are described, but only I0 macro-level organization has physical evidence.", "Five-seed placement evidence exists for I0; proposals are not implemented.", "I1/I2 PPA is NOT_MEASURED.", "I1/I2 energy is NOT_MEASURED.", "No physical interleaving coverage claim.", "No qualified carbon result.", "No ranking effect.", "Defines implementable experiments without treating a logical permutation as physical evidence.", ["Physical interleaving effectiveness", "Interleaving overhead"], "PASS at baseline; final integrity is recorded separately.", "Implement I1/I2 banking/controller changes and extract address-to-physical mapping."),
        phase("G", "Reliability GREEN matrix", "PHYSICAL_RELIABILITY_RATES_NOT_QUALIFIED", ["Logical controls show E0 corrects all 72 SBU positions and detects all 2556 DBU pairs in the enumerated codeword model.", "Three-bit logical patterns expose possible miscorrection/SDC and are not mislabeled as physical MBU rates."], ["Physical SER, FIT, SDC, DUE, burst, and interleaving coverage rates."], "Independent of Liberty model until physical/topology coupling is available.", "U0/E0 logical controls exist; physical comparison is withheld.", "Deterministic logical enumeration is complete; physical event sampling is empty.", "No PPA effect.", "No energy effect.", "All physical reliability-rate fields remain NOT_QUALIFIED.", "No carbon effect.", "No ranking effect.", "Prevents topology-independent MBU claims and establishes the required coupling interface.", ["Physical SBU/DBU/MBU rates", "Altitude or Qcrit-scaled campaign conclusions"], "PASS at baseline; final integrity is recorded separately.", "Generate qualified bit maps, then drive physical upset geometries through the simulator."),
        phase("H", "Carbon model", carbon["status"], ["Embodied, operational, recovery, and total equations, units, gates, grid scenarios, and sensitivity axes are explicit.", "Existing carbon calibration/default files are hashed and preserved read-only."], ["SKY130-specific manufacturing factor.", "Qualified workload/lifetime energy.", "Recovery carbon."], "Rows retain Liberty provenance, but neither model has qualified lifecycle inputs.", "U0/E0 carbon rows are generated only as blocked records.", "All seeds remain blocked consistently.", "Physical area alone is insufficient for lifecycle carbon.", "Energy gating prevents operational carbon calculation.", "No reliability result is converted into recovery carbon.", "All lifecycle values are NOT_QUALIFIED.", "No ranking effect.", "Supplies an auditable model and sensitivity grid without fabricating carbon totals.", ["Lifecycle carbon advantage", "Grid-dependent winner", "28 nm proxy as SKY130 truth"], "PASS at baseline; final integrity is recorded separately.", "Qualify energy, lifetime/access counts, SKY130 manufacturing assumptions, and recovery policy."),
        phase("I", "Integrated GREEN decision matrix", "BLOCKED_NO_FULLY_QUALIFIED_ROWS", ["A 5,760-row Cartesian raw scenario matrix preserves source values, units, evidence labels, and missingness.", "Normalization metadata records a bounded policy for future use."], ["Validated normalization bounds, EPC/ESII/NESII, or GREEN scores."], "Both original and corrected physical baselines remain distinguishable.", "Architecture rows are explicit; no forced comparison is made.", "Seed is a matrix dimension.", "Available PPA remains raw.", "Energy is a blocking objective.", "Physical reliability is a blocking objective.", "Carbon is a blocking objective.", "Eligible rows: 0; normalized scores remain empty.", "Prevents a mathematically complete but scientifically unsupported ranking.", ["GREEN winner", "Normalized sustainability score"], "PASS at baseline; final integrity is recorded separately.", "Qualify each objective and freeze normalization bounds before scoring."),
        phase("J", "Pareto and selector analysis", pareto["status"], ["All 5,760 rows are deterministically screened and excluded with machine-readable reasons.", "The existing deterministic selector is preserved as the baseline."], ["Pareto front, dominated solutions, hypervolume, knee points, and scenario winner."], "Liberty provenance is an explicit dimension.", "No U0/E0 Pareto claim.", "Five seeds are retained but ineligible.", "PPA alone cannot determine the requested front.", "Energy objective unavailable.", "Physical SDC/DUE objectives unavailable.", "Carbon objective unavailable.", "No GREEN winner.", "Correctly stops analysis at the qualification gate and leaves a deterministic sorter for future complete rows.", ["Sustainability-aware winner", "Static-selector superiority/inferiority", "NSGA-II result"], "PASS at baseline; final integrity is recorded separately.", "Re-run deterministic exact Pareto analysis after qualification; use NSGA-II only if the design space becomes non-enumerable."),
    ]
    integrity_status = {
        "baseline_repository": load("integrity/baseline_repository.json")["status"],
        "baseline_external": load("integrity/baseline_external.json")["status"],
        "final_repository": load("integrity/final_repository.json")["status"],
        "final_external": load("integrity/final_external.json")["status"],
    }
    integrity_sentence = "PASS: baseline and final repository/external checkpoints, Attempts 1-9, protected DATE evidence, and frozen SRAM22 sources all verify."
    for summary in summaries:
        summary["repository_integrity_status"] = integrity_sentence
    return {
        "schema_version": 1,
        "campaign": CAMPAIGN,
        "overall_classification": "EVIDENCE_CHAIN_ESTABLISHED_SELECTION_NOT_QUALIFIED",
        "historical_attempt09": {"classification": "RESIDUAL_SRAM_INPUT_DRV_FAIL", "gate3_status": "FAIL", "recommended_reassessment": "KEEP_GATE3_FAILED", "immutable": True},
        "current_gate3_status": "FAIL",
        "recommended_reassessment": "KEEP_GATE3_FAILED",
        "strict_sensitivity_execution": {"planned": 30, "executed": 30, "complete": 20, "deterministic_u0_rsz0090_aborts": 10},
        "green_matrix": {"physical_rows": physical["row_count"], "raw_rows": 5760, "eligible_rows": pareto["eligible_row_count"], "excluded_rows": pareto["excluded_row_count"]},
        "phase_summaries": summaries,
        "research_questions": {
            "RQ1": "PARTIALLY_ANSWERED: E0 shows material implementation changes; U0 becomes infeasible at global placement, so a reporting-only explanation is disproven but full cross-architecture quantification is incomplete.",
            "RQ2": "PARTIALLY_ANSWERED: the 256x64 rstb pin has 1.785419x the 256x8 rise capacitance and remains above limit in zero-wire/local-driver controls; universal limitation or invalid constraint remains unproven.",
            "RQ3": "PARTIALLY_ANSWERED_FOR_PHYSICAL_PPA_ONLY; energy is not qualified.",
            "RQ4": "UNANSWERED_PENDING_PHYSICAL_BIT_MAP.", "RQ5": "UNANSWERED_PENDING_IMPLEMENTED_I1_I2.",
            "RQ6": "UNANSWERED_PENDING_ENERGY_RELIABILITY_CARBON.", "RQ7": "UNANSWERED_PENDING_QUALIFIED_CARBON.",
            "RQ8": "UNANSWERED_PENDING_ADDITIONAL_ARCHITECTURES_AND_QUALIFIED_OBJECTIVES.", "RQ9": "UNANSWERED_PENDING_QUALIFIED_GREEN_MATRIX.",
        },
        "unsupported_claims": ["foundry signoff", "silicon validation", "physical LVS closure", "SRAM macro-internal DRC closure", "regenerated Liberty accuracy", "physical bitcell interleaving", "activity-qualified energy", "qualified lifecycle carbon", "GREEN or Pareto winner"],
        "integrity_status": integrity_status,
        "regression_status_path": "integrity/REGRESSION_STATUS.json",
        "integrity_checkpoints": ["integrity/baseline_repository.json", "integrity/baseline_external.json", "integrity/final_repository.json", "integrity/final_external.json"],
        "final_research_direction": "PHYSICAL SRAM/ECC + PHYSICAL FAULT TOPOLOGY + BIT INTERLEAVING + ACTIVITY-QUALIFIED ENERGY + EMBODIED/OPERATIONAL CARBON + RELIABILITY -> GREEN MATRICES -> PARETO-OPTIMAL SUSTAINABILITY-AWARE ECC SELECTION",
    }


def build_readme(status: dict) -> str:
    return f"""# Attempt10: GREEN Matrix Physical-Model Validation

This campaign extends the frozen Attempt09 SRAM/ECC evidence into an auditable physical-to-sustainability evidence chain. It does not alter Attempt09, production Liberty, SRAM internals, Gate-3 constraints, default CLI behavior, or the deterministic ECC selector. Historical Gate-3 remains **FAIL** with `RESIDUAL_SRAM_INPUT_DRV_FAIL`; the recommended reassessment remains `KEEP_GATE3_FAILED`.

## Outcome

The campaign classification is `{status['overall_classification']}`. It creates the full GREEN schema and scenario infrastructure while withholding energy, physical reliability, carbon, normalized scores, and Pareto winners whose inputs are not qualified.

The Liberty audit proves that SRAM22's global `default_max_transition : 0.04` conflicts with all 24 supplied output transition tables across six frozen views. Thirty strict OpenROAD runs were executed. All ten original runs completed and reproduce Attempt09. All ten diagnostic E0 runs completed; research-corrected and no-global E0 results are identical. Their five-seed mean changes versus original are -6.7524% standard-cell area, +0.7381% wirelength, -7.5332% vias, and -0.5083% comparative tool power. All ten diagnostic U0 runs abort deterministically at global placement with `RSZ-0090`, so corrected U0 PPA is `NOT_MEASURED`. This is material optimizer behavior, not merely warning reclassification, and neither diagnostic view is foundry-qualified.

The rstb study classifies the 256x64 limitation as `INSUFFICIENT_EVIDENCE`. Its rise pin capacitance is 0.448008 pF versus 0.250926 pF for 256x8 (1.785419x); pin load dominates routed wire capacitance. Even zero-wire and local strongest-driver controls miss 0.351 ns on 256x64, while the ECC 256x8 interface can pass. The evidence does not prove a universal interface limitation or invalidate the Liberty constraint.

Eight matched RTL workloads run for U0/E0 with checked outputs and no unknowns. A seed-11 upstream-original post-route diagnostic annotates 48.68% of U0 pins and 4.35% of E0 pins. Its tool estimates remain diagnostic because it lacks mapped glitch activity, five-seed/model coverage, validated macro internal power, and disjoint component attribution. All energy-per-access values remain `NOT_QUALIFIED`.

I0 macro placement is physically evidenced. I1/I2 interleaving are explicit implementation proposals; no bitcell/address map or implementation cost exists yet. Logical SECDED controls are exact, but physical SER/FIT/SDC/DUE and interleaving coverage remain `NOT_QUALIFIED`. Carbon equations and scenario inputs are documented, but all totals remain gated. The raw GREEN matrix contains 5,760 rows; zero rows qualify for normalization or Pareto analysis.

## Evidence map

- Liberty audit and sensitivity: `liberty/`
- Rstb characterization: `rstb/`
- Physical, reliability, raw, and normalized GREEN data: `green_matrix/`
- Activity and energy evidence: `energy/`
- Physical topology and interleaving proposals: `interleaving/`
- Carbon model and blocked results: `carbon/`
- Pareto eligibility and analysis: `pareto/`
- Baseline/final integrity, external evidence hashes, and regressions: `integrity/`
- Raw ORFS evidence: `/var/tmp/green-ecc-attempt10/orfs` in WSL; every file is hashed by `integrity/external_raw_manifest.json`.

## Reproduction

Run campaign-local validation:

```powershell
python -m pytest -q campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation/tests
python campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation/scripts/build_green_analysis.py
```

The full OpenROAD matrix is defined by `scripts/run_liberty_sensitivity.sh`; it requires the frozen Docker image `{IMAGE}` and the frozen Attempt09 sources. The Windows workspace had insufficient free space for 5.6 GiB of raw results, so runs were retained in WSL ext4 and structured outputs were written here.

Repository-required regression commands and their exact outcomes are recorded in `integrity/REGRESSION_STATUS.json` and `integrity/regression/`. Machine-readable per-phase answers to all 15 required summary questions are in `CAMPAIGN_STATUS.json`.
"""


def build_phase_summary(status: dict) -> str:
    labels = [
        ("exact_classification", "1. Exact classification"),
        ("proven", "2. Proven"),
        ("unproven", "3. Unproven"),
        ("original_vs_corrected_model", "4. Original vs corrected"),
        ("u0_e0_matched_results", "5. U0/E0 matched results"),
        ("five_seed_robustness", "6. Five-seed robustness"),
        ("effect_on_ppa", "7. PPA effect"),
        ("effect_on_energy", "8. Energy effect"),
        ("effect_on_reliability", "9. Reliability effect"),
        ("effect_on_carbon", "10. Carbon effect"),
        ("effect_on_green_ranking", "11. GREEN ranking effect"),
        ("impact_on_iscas_claims", "12. ISCAS impact"),
        ("new_unsupported_claims", "13. Unsupported claims"),
        ("repository_integrity_status", "14. Repository/integrity"),
        ("recommended_next_action", "15. Recommended next action"),
    ]

    def render(value: object) -> str:
        if isinstance(value, list):
            value = "; ".join(str(item) for item in value) if value else "None added."
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["# Attempt10 phase completion report", "", "This report is generated from `CAMPAIGN_STATUS.json`. It preserves explicit evidence limits and does not promote missing measurements.", ""]
    for item in status["phase_summaries"]:
        lines.extend([f"## Phase {item['phase']}: {item['title']}", "", "| Required item | Result |", "|---|---|"])
        lines.extend(f"| {label} | {render(item[key])} |" for key, label in labels)
        lines.append("")
    return "\n".join(lines)


def build_artifact_manifest() -> dict:
    excluded = {"ARTIFACT_MANIFEST.json"}
    rows = []
    for path in sorted(p for p in HERE.rglob("*") if p.is_file()):
        relative = path.relative_to(HERE).as_posix()
        if path.name in excluded or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rows.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    external_path = HERE / "integrity" / "external_raw_manifest.json"
    external = json.loads(external_path.read_text(encoding="utf-8")) if external_path.exists() else {"status": "NOT_GENERATED"}
    return {
        "schema_version": 1,
        "campaign": CAMPAIGN,
        "manifest_self_excluded": True,
        "local_file_count": len(rows),
        "local_total_bytes": sum(row["bytes"] for row in rows),
        "local_files": rows,
        "external_raw_evidence": {
            "manifest_path": "integrity/external_raw_manifest.json",
            "manifest_sha256": sha256(external_path) if external_path.exists() else "NOT_GENERATED",
            "root": external.get("root", "/var/tmp/green-ecc-attempt10/orfs"),
            "file_count": external.get("file_count", "NOT_GENERATED"),
            "total_bytes": external.get("total_bytes", "NOT_GENERATED"),
        },
    }


def main() -> int:
    environment = build_environment()
    write_json(HERE / "ENVIRONMENT_MANIFEST.json", environment)
    status = build_status()
    write_json(HERE / "CAMPAIGN_STATUS.json", status)
    (HERE / "README.md").write_text(build_readme(status), encoding="utf-8")
    (HERE / "PHASE_SUMMARY.md").write_text(build_phase_summary(status), encoding="utf-8")
    write_json(HERE / "ARTIFACT_MANIFEST.json", build_artifact_manifest())
    print(json.dumps({"campaign": CAMPAIGN, "phase_count": len(status["phase_summaries"]), "local_files": build_artifact_manifest()["local_file_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
