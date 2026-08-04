"""End-to-end architecture-aware GREEN-ECC evaluation and deployment flow."""

from __future__ import annotations

import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping, Sequence

from visualization_runtime import configure_matplotlib_cache

configure_matplotlib_cache()
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analysis.pareto import pareto_frontier
from ecc_selector import _nsga2_sort

from .carbon import EmbodiedCarbonAssumptions, carbon_breakdown
from .deployment import (
    emit_systemverilog_package,
    fit_to_mission_failure_probability,
    record_energy_j,
    reconfiguration_overhead,
)
from .mux import (
    compare_topology_logical_resources,
    default_selection_paths,
    evaluate_selection_fabric,
    metadata_failure_probability,
    physical_container_layout,
    protected_metadata_bits,
    system_failure_probability,
)
from .providers import LegacySelectorProjectedProvider, MuxCharacterizationProvider
from .robustness import monte_carlo_robustness
from .selection import (
    apply_hard_constraints,
    benchmark_exact_pareto_scaling,
    score_diagnostics,
    select_baselines,
)
from .types import CandidateRegistry, ECCConfiguration, MetricProvenance, Scenario


def _git_hash(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _git_dirty(repo_root: Path) -> bool | None:
    try:
        return bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _source_file_hashes(repo_root: Path) -> dict[str, str]:
    paths = [
        repo_root / "eccsim.py",
        repo_root / "ecc_selector.py",
        repo_root / "esii.py",
        repo_root / "scores.py",
        repo_root / "gs.py",
        repo_root / "energy_model.py",
        repo_root / "ser_model.py",
        repo_root / "fit.py",
        repo_root / "mbu.py",
        repo_root / "analysis" / "pareto.py",
        *sorted((repo_root / "architecture").glob("*.py")),
    ]
    return {
        str(path.relative_to(repo_root)).replace("\\", "/"): _sha256(path)
        for path in paths
        if path.is_file()
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        if not fields:
            stream.write("\n")
            return
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _validate_input_config(payload: object, repo_root: Path) -> None:
    import jsonschema

    schema_path = repo_root / "schemas" / "architecture-dse-config.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


def _load_mux_characterization(
    config: Mapping[str, object], config_path: Path, scenario: Scenario
):
    raw_path = config.get("mux_characterization_path")
    if not raw_path:
        return None, None
    path = Path(str(raw_path))
    if not path.is_absolute():
        path = (config_path.parent / path).resolve()
    provider = MuxCharacterizationProvider.from_json(path)
    architecture = dict(config["architecture"])
    characterization = provider.resolve(
        node_nm=scenario.node_nm,
        vdd=scenario.vdd,
        temperature_c=scenario.temperature_c,
        process_corner=str(architecture.get("process_corner", "tt")),
    )
    return characterization, path


def _embodied_assumptions(raw: Mapping[str, object] | None) -> EmbodiedCarbonAssumptions | None:
    if not raw:
        return None
    return EmbodiedCarbonAssumptions(
        manufacturing_intensity_kgco2e_per_cm2=float(raw["manufacturing_intensity_kgco2e_per_cm2"]),
        yield_allocation_factor=float(raw["yield_allocation_factor"]),
        die_allocation_factor=float(raw.get("die_allocation_factor", 1.0)),
        packaging_allocation_kgco2e=float(raw.get("packaging_allocation_kgco2e", 0.0)),
        amortized_systems=int(raw.get("amortized_systems", 1)),
        source=str(raw.get("source", "user_supplied")),
    )


def _ancillary_complete(architecture: Mapping[str, object]) -> bool:
    ancillary = dict(architecture.get("ancillary_characterization", {}))
    required = {
        "controller_area_um2",
        "controller_energy_j_per_access",
        "controller_delay_ns",
        "controller_leakage_power_w",
        "metadata_energy_j_per_access",
        "metadata_delay_ns",
        "metadata_leakage_power_w",
        "source",
    }
    return required.issubset(ancillary)


def _path_delay(fabric: Mapping[str, object], names: set[str]) -> float | None:
    values = [
        item["delay_ns"]
        for item in fabric["paths"]
        if item["name"] in names
    ]
    if not values or any(value is None for value in values):
        return None
    return max(float(value) for value in values)


def _architecture_record(
    raw_record: Mapping[str, object],
    *,
    config: ECCConfiguration,
    all_records: Sequence[Mapping[str, object]],
    all_configs: Sequence[ECCConfiguration],
    scenario: Scenario,
    architecture: Mapping[str, object],
    characterization,
    embodied_assumptions: EmbodiedCarbonAssumptions | None,
) -> tuple[dict, dict]:
    topology = str(architecture["topology"])
    configurable = topology != "fixed"
    modes = len(all_configs) if configurable else 1
    layout = physical_container_layout(all_configs if configurable else [config], scenario.logical_width_bits)
    layout_entry = next(
        item for item in layout["entries"] if item["config_id"] == config.config_id
    )
    metadata = protected_metadata_bits(modes, str(architecture.get("metadata_protection", "triplicated")))
    status_width = int(architecture.get("status_width_bits", 4))
    paths = default_selection_paths(
        topology=topology,
        modes=modes,
        logical_width_bits=scenario.logical_width_bits,
        container_bits=int(layout["container_bits"]),
        status_width_bits=status_width,
        path_overrides=dict(architecture.get("path_overrides", {})),
    )
    fabric = evaluate_selection_fabric(
        paths,
        implementation=str(architecture.get("mux_implementation", "pruned")),
        characterization=characterization,
    )

    base_area = float(raw_record.get("area_logic_mm2", 0.0)) + float(
        raw_record.get("area_macro_mm2", 0.0)
    )
    engine_areas = [
        float(item.get("area_logic_mm2", 0.0)) + float(item.get("area_macro_mm2", 0.0))
        for item in all_records
    ]
    if topology in {"parallel", "gated_parallel"}:
        engine_area = sum(engine_areas)
    elif topology == "shared_reconfigurable":
        engine_area = max(engine_areas)
    else:
        engine_area = base_area

    ancillary = dict(architecture.get("ancillary_characterization", {}))
    ancillary_complete = _ancillary_complete(architecture) if configurable else True
    metadata_area_um2 = metadata["stored_bits"] * scenario.bitcell_area_um2
    if configurable and fabric["area_um2_total"] is not None and ancillary_complete:
        incremental_fabric_area_um2 = (
            float(fabric["area_um2_total"])
            + float(ancillary["controller_area_um2"])
            + metadata_area_um2
        )
        architecture_area_mm2 = engine_area + incremental_fabric_area_um2 / 1e6
    elif not configurable:
        incremental_fabric_area_um2 = 0.0
        architecture_area_mm2 = base_area
    else:
        incremental_fabric_area_um2 = None
        architecture_area_mm2 = None

    base_energy = record_energy_j(raw_record)
    if configurable and fabric["dynamic_energy_j_per_operation_total"] is not None and ancillary_complete:
        accesses = scenario.workload.total_accesses
        lifetime_seconds = scenario.lifetime_hours * 3600.0
        fabric_energy = (
            float(fabric["dynamic_energy_j_per_operation_total"]) * accesses
            + float(fabric["leakage_power_w_total"]) * lifetime_seconds
        )
        controller_energy = (
            (float(ancillary["controller_energy_j_per_access"]) + float(ancillary["metadata_energy_j_per_access"]))
            * accesses
            + (float(ancillary["controller_leakage_power_w"]) + float(ancillary["metadata_leakage_power_w"]))
            * lifetime_seconds
        )
        others = [item for item in all_records if item.get("config_id") != config.config_id]
        inactive_glitch = float(architecture.get("inactive_glitch_activity", 0.0)) * sum(
            3.6e6 * float(item.get("E_dyn_kWh", 0.0) or 0.0) for item in others
        )
        inactive_leakage = float(architecture.get("inactive_leakage_factor", 1.0)) * sum(
            3.6e6 * float(item.get("E_leak_kWh", 0.0) or 0.0) for item in others
        )
        incremental_energy = fabric_energy + controller_energy + inactive_glitch + inactive_leakage
        architecture_energy = base_energy + incremental_energy
    elif not configurable:
        incremental_energy = 0.0
        architecture_energy = base_energy
    else:
        incremental_energy = None
        architecture_energy = None

    memory_read = float(scenario.memory_read_latency_ns or 0.0)
    memory_write = float(scenario.memory_write_latency_ns or 0.0)
    latency_scope = (
        "end_to_end_memory_plus_ecc"
        if scenario.memory_read_latency_ns is not None and scenario.memory_write_latency_ns is not None
        else "ecc_and_selection_fabric_only"
    )
    base_latency = float(raw_record["latency_ns"])
    if configurable and fabric["physical_metrics_characterized"] and ancillary_complete:
        read_mux = _path_delay(fabric, {"read_data_mux", "read_status_mux", "shared_input_route"})
        write_mux = _path_delay(fabric, {"write_codeword_mux", "shared_input_route"})
        control_delay = float(ancillary["controller_delay_ns"])
        metadata_delay = float(ancillary["metadata_delay_ns"])
        read_latency = memory_read + base_latency + float(read_mux) + control_delay + metadata_delay
        write_latency = control_delay + base_latency + float(write_mux) + memory_write + metadata_delay
        architecture_latency = max(read_latency, write_latency)
    elif not configurable:
        read_latency = memory_read + base_latency
        write_latency = base_latency + memory_write
        architecture_latency = max(read_latency, write_latency)
    else:
        read_latency = write_latency = architecture_latency = None

    base_carbon = float(raw_record["carbon_kg"])
    carbon = carbon_breakdown(
        base_system_carbon_kg=base_carbon,
        incremental_energy_j=incremental_energy,
        incremental_area_um2=incremental_fabric_area_um2,
        carbon_intensity_kgco2e_per_kwh=scenario.carbon_intensity_kgco2e_per_kwh,
        total_accesses=scenario.workload.total_accesses,
        embodied_assumptions=embodied_assumptions,
    )
    architecture_carbon = (
        base_carbon if not configurable else carbon["absolute_system_carbon_kgco2e"]
    )

    ecc_probability = fit_to_mission_failure_probability(float(raw_record["FIT"]), scenario.lifetime_hours)
    metadata_probability = metadata_failure_probability(
        modes,
        str(architecture.get("metadata_protection", "triplicated")),
        scenario.bit_failure_probability,
    )
    reliability = system_failure_probability(
        ecc_probability,
        mux_failure_probability=(
            float(architecture["mux_failure_probability"])
            if architecture.get("mux_failure_probability") is not None
            else None
        ),
        controller_failure_probability=(
            float(architecture["controller_failure_probability"])
            if architecture.get("controller_failure_probability") is not None
            else None
        ),
        metadata_failure_probability_value=metadata_probability,
    )

    record = dict(raw_record)
    record.update(
        {
            "scenario_id": scenario.scenario_id,
            "topology": topology,
            "selection_granularity": str(architecture.get("selection_granularity", "design")),
            "container_bits": layout["container_bits"],
            "padding_bits": layout_entry["padding_bits"],
            "capacity_efficiency": (
                scenario.logical_width_bits / int(layout_entry["physical_bits_used"])
                if not configurable
                else layout_entry["capacity_efficiency"]
            ),
            "metadata_bits": metadata["stored_bits"],
            "mux_2to1_count": fabric["mux_2to1_count_total"],
            "architecture_area_mm2": architecture_area_mm2,
            "architecture_energy_j": architecture_energy,
            "architecture_latency_ns": architecture_latency,
            "read_latency_ns": read_latency,
            "write_latency_ns": write_latency,
            "latency_scope": latency_scope,
            "architecture_carbon_kg": architecture_carbon,
            "incremental_architecture_energy_j": incremental_energy,
            "incremental_architecture_area_um2": incremental_fabric_area_um2,
            "architecture_physical_metrics_complete": (
                not configurable
                or (fabric["physical_metrics_characterized"] and ancillary_complete)
            ),
            "system_failure_probability": reliability["system_failure_probability"],
            "metric_provenance": {
                **dict(raw_record.get("metric_provenance", {})),
                "selection_fabric_logical": MetricProvenance(
                    source="analytical",
                    technology_node_nm=scenario.node_nm,
                    vdd_volts=scenario.vdd,
                    temperature_c=scenario.temperature_c,
                    notes="Exact balanced-tree depth and 2:1 cell-count equations.",
                ).to_dict(),
                "selection_fabric_physical": (
                    {
                        "source": characterization.source,
                        "technology_node_nm": characterization.node_nm,
                        "standard_cell_library": characterization.library,
                        "process_corner": characterization.process_corner,
                        "vdd_volts": characterization.vdd,
                        "temperature_c": characterization.temperature_c,
                        "tool": characterization.tool,
                        "tool_version": characterization.tool_version,
                        "calibration_source": characterization.calibration_source,
                    }
                    if characterization is not None
                    else {
                        "source": "uncharacterized",
                        "technology_node_nm": scenario.node_nm,
                        "process_corner": str(architecture.get("process_corner", "tt")),
                        "vdd_volts": scenario.vdd,
                        "temperature_c": scenario.temperature_c,
                        "notes": "No exact-PVT MUX characterization was supplied; physical overhead is null.",
                    }
                ),
            },
        }
    )
    detail = {
        "layout": layout,
        "metadata": metadata,
        "fabric": fabric,
        "carbon": carbon,
        "reliability_fault_tree": reliability,
    }
    return record, detail


def _plot_selection_summary(rows: Sequence[Mapping[str, object]], out_path: Path) -> None:
    complete = [row for row in rows if row.get("architecture_carbon_kg") is not None]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    if complete:
        for scenario_id in sorted({str(row["scenario_id"]) for row in complete}):
            subset = [row for row in complete if row["scenario_id"] == scenario_id]
            ax.scatter(
                [float(row["architecture_carbon_kg"]) for row in subset],
                [float(row["FIT"]) for row in subset],
                label=scenario_id,
            )
            for row in subset:
                ax.annotate(str(row["config_id"]), (float(row["architecture_carbon_kg"]), float(row["FIT"])), fontsize=7)
        ax.set_yscale("log")
        ax.legend(fontsize=7)
    else:
        ax.text(0.5, 0.5, "Physical fabric PPA uncharacterized\nExact logical counts remain available", ha="center", va="center")
    ax.set_xlabel("Architecture-aware carbon (kg CO2e)")
    ax.set_ylabel("FIT")
    ax.set_title("GREEN-ECC architecture-aware candidate space")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, format="svg")
    plt.close(fig)


def _plot_topology_comparison(rows: Sequence[Mapping[str, object]], out_path: Path) -> None:
    labels = [str(item["topology"]).replace("_", "\n") for item in rows]
    counts = [int(item["mux_2to1_count"]) for item in rows]
    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    bars = ax.bar(labels, counts, color=["#4c78a8", "#f58518", "#e45756", "#72b7b2"])
    ax.bar_label(bars, padding=3)
    ax.set_ylim(0, max(counts or [1]) * 1.12)
    ax.set_ylabel("Exact 2:1 MUX cell count")
    ax.set_title("Selection-fabric topology comparison (five modes)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, format="svg")
    fig.savefig(out_path.with_suffix(".png"), dpi=180)
    plt.close(fig)


def run_architecture_dse(config_path: Path, outdir: Path, *, repo_root: Path) -> dict:
    start = time.perf_counter()
    config_path = config_path.resolve()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_input_config(payload, repo_root)
    repository_commit = _git_hash(repo_root)
    repository_dirty = _git_dirty(repo_root)
    source_files = _source_file_hashes(repo_root)
    source_tree_sha256 = hashlib.sha256(
        json.dumps(source_files, sort_keys=True).encode("utf-8")
    ).hexdigest()
    input_config_sha256 = _sha256(config_path)
    result_run_id = hashlib.sha256(
        f"{repository_commit}:{source_tree_sha256}:{input_config_sha256}".encode("utf-8")
    ).hexdigest()[:16]
    candidates = [ECCConfiguration.from_mapping(item) for item in payload["candidates"]]
    registry = CandidateRegistry.from_configurations(candidates)
    architecture = dict(payload["architecture"])
    topology = str(architecture["topology"])
    configured_deployment_mode = str(
        architecture.get("deployment_mode", "boot_time_or_bank_configurable")
    )
    if topology not in {"fixed", "parallel", "gated_parallel", "shared_reconfigurable"}:
        raise ValueError(f"Unknown architecture topology: {topology}")
    if (configured_deployment_mode == "design_time_fixed") != (topology == "fixed"):
        raise ValueError(
            "design_time_fixed requires topology=fixed, and topology=fixed requires design_time_fixed"
        )
    safe_fallback = str(architecture["safe_fallback_config_id"])
    registry.get(safe_fallback)
    scenarios = [Scenario.from_mapping(item) for item in payload["scenarios"]]
    provider = LegacySelectorProjectedProvider()
    preference_weights = dict(payload.get("preference_weights", {}))
    uncertainty = dict(payload.get("uncertainty", {}))
    embodied = _embodied_assumptions(payload.get("embodied_carbon"))

    outdir.mkdir(parents=True, exist_ok=True)
    data_dir, figure_dir, deploy_dir = outdir / "data", outdir / "figures", outdir / "deployment"
    for directory in (data_dir, figure_dir, deploy_dir):
        directory.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    scenario_reports: list[dict] = []
    policy: dict[str, str] = {}
    differing_cases: list[dict] = []
    polar_membership: list[dict] = []

    for scenario in scenarios:
        base_records = provider.evaluate(candidates, scenario)
        by_config = {str(item["config_id"]): item for item in base_records}
        active_configs = [item for item in candidates if item.config_id in by_config]
        if not active_configs:
            scenario_reports.append({"scenario_id": scenario.scenario_id, "status": "no_supported_candidates"})
            continue
        characterization, characterization_path = _load_mux_characterization(payload, config_path, scenario)
        records: list[dict] = []
        details: dict[str, dict] = {}
        for candidate in active_configs:
            record, detail = _architecture_record(
                by_config[candidate.config_id],
                config=candidate,
                all_records=base_records,
                all_configs=active_configs,
                scenario=scenario,
                architecture=architecture,
                characterization=characterization,
                embodied_assumptions=embodied,
            )
            for provenance in record.get("metric_provenance", {}).values():
                if isinstance(provenance, dict):
                    provenance.setdefault("technology_node_nm", scenario.node_nm)
                    provenance.setdefault("standard_cell_library", None)
                    provenance.setdefault("device_model", None)
                    provenance.setdefault("process_corner", str(architecture.get("process_corner", "unspecified")))
                    provenance.setdefault("vdd_volts", scenario.vdd)
                    provenance.setdefault("temperature_c", scenario.temperature_c)
                    provenance.setdefault("tool", "GREEN-ECC architecture pipeline")
                    provenance.setdefault("tool_version", None)
                    provenance.setdefault("calibration_source", None)
                    provenance.setdefault(
                        "uncertainty", dict(uncertainty.get("relative_intervals", {}))
                    )
                    provenance["repository_commit"] = repository_commit
                    provenance["repository_dirty"] = repository_dirty
                    provenance["source_tree_sha256"] = source_tree_sha256
                    provenance["input_config"] = str(config_path)
                    provenance["input_config_sha256"] = input_config_sha256
                    provenance["result_run_id"] = result_run_id
            records.append(record)
            details[candidate.config_id] = detail

        feasible, infeasible = apply_hard_constraints(records, scenario.constraints)
        constraint_annotations = {
            str(item["config_id"]): {
                "constraint_violations": item["constraint_violations"],
                "constraint_margins": item["constraint_margins"],
                "feasible": item["feasible"],
            }
            for item in feasible + infeasible
        }
        for record in records:
            record.update(constraint_annotations[str(record["config_id"])])
        baseline_report = select_baselines(
            feasible,
            fault_regime=scenario.fault_regime,
            preference_weights=preference_weights,
        )
        selected_id = baseline_report.get("selections", {}).get("green_ecc_policy")
        if selected_id is None:
            selected_id = safe_fallback
        policy[scenario.scenario_id] = selected_id
        if baseline_report.get("green_differs_from_lookup"):
            active_objectives = baseline_report.get("active_objectives", [])
            differing_cases.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "green_ecc": selected_id,
                    "fault_regime_lookup": baseline_report["selections"]["fault_regime_lookup"],
                    "active_objectives": active_objectives,
                    "reason": (
                        "Exact modeled reliability changes the choice; adaptive physical PPA is uncharacterized, "
                        "so this is not evidence of a lifecycle-carbon advantage."
                        if active_objectives == ["FIT"]
                        else "Hard constraints, exact Pareto membership, and declared lifecycle preferences."
                    ),
                }
            )

        selected_record = next((item for item in records if item["config_id"] == selected_id), None)
        fallback_record = next(item for item in records if item["config_id"] == safe_fallback)
        reconfiguration = (
            reconfiguration_overhead(
                old_record=fallback_record,
                new_record=selected_record or fallback_record,
                scenario=scenario,
                container_bits=int(details[safe_fallback]["layout"]["container_bits"]),
                control_energy_j_per_transition=(
                    float(dict(architecture.get("ancillary_characterization", {}))["controller_energy_j_per_access"])
                    if _ancillary_complete(architecture)
                    else None
                ),
            )
            if configured_deployment_mode == "runtime_adaptive"
            else {
                "transitions": 0,
                "migrated_words_total": 0,
                "energy_j_total": 0.0,
                "latency_ns_total": 0.0,
                "temporary_capacity_bits": 0,
                "amortized_energy_j_per_access": 0.0,
                "model": (
                    "Design-time fixed ECC; no mode transition hardware or migration."
                    if configured_deployment_mode == "design_time_fixed"
                    else "Boot/bank configuration occurs before data placement; recurring migration is not charged."
                ),
            }
        )
        score_report = score_diagnostics(feasible)
        robustness = monte_carlo_robustness(
            records,
            constraints=scenario.constraints,
            preference_weights=preference_weights,
            relative_intervals=dict(uncertainty.get("relative_intervals", {})),
            samples=int(uncertainty.get("samples", 200)),
            seed=int(uncertainty.get("seed", 1)),
        )
        pareto_ids = set(baseline_report.get("pareto_configurations", []))
        for candidate in active_configs:
            if candidate.family.upper().startswith("POLAR"):
                polar_record = by_config[candidate.config_id]
                dominated_by = []
                for other in base_records:
                    if other["config_id"] == candidate.config_id:
                        continue
                    no_worse = (
                        float(other["FIT"]) <= float(polar_record["FIT"])
                        and float(other["carbon_kg"]) <= float(polar_record["carbon_kg"])
                        and float(other["latency_ns"]) <= float(polar_record["latency_ns"])
                    )
                    strictly_better = (
                        float(other["FIT"]) < float(polar_record["FIT"])
                        or float(other["carbon_kg"]) < float(polar_record["carbon_kg"])
                        or float(other["latency_ns"]) < float(polar_record["latency_ns"])
                    )
                    if no_worse and strictly_better:
                        dominated_by.append(str(other["config_id"]))
                polar_membership.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "config_id": candidate.config_id,
                        "pareto_member": candidate.config_id in pareto_ids,
                        "fit": by_config[candidate.config_id]["FIT"],
                        "carbon_kg": by_config[candidate.config_id]["carbon_kg"],
                        "latency_ns": by_config[candidate.config_id]["latency_ns"],
                        "model_status": "legacy projected short-block SC-decoder assumptions",
                        "dominated_by_on_legacy_fit_carbon_latency": dominated_by,
                    }
                )
        all_rows.extend(records)
        scenario_reports.append(
            {
                "scenario_id": scenario.scenario_id,
                "status": "ok",
                "scenario": asdict(scenario),
                "candidates_evaluated": len(records),
                "feasible": len(feasible),
                "infeasible": len(infeasible),
                "selected_configuration": selected_id,
                "safe_fallback": safe_fallback,
                "selection": baseline_report,
                "score_diagnostics": score_report,
                "robustness": robustness,
                "reconfiguration": reconfiguration,
                "physical_metrics_complete": all(
                    bool(item["architecture_physical_metrics_complete"]) for item in records
                ),
                "mux_characterization_path": str(characterization_path) if characterization_path else None,
                "candidate_details": details,
            }
        )

    selected_configurations = {
        scenario_id: registry.get(config_id).to_dict() for scenario_id, config_id in policy.items()
    }
    selected_results = {}
    scenario_decisions = {}
    for report in scenario_reports:
        if report.get("status") != "ok":
            continue
        scenario_id = str(report["scenario_id"])
        selected_id = str(report["selected_configuration"])
        selected = next(
            row
            for row in all_rows
            if row["scenario_id"] == scenario_id and row["config_id"] == selected_id
        )
        selected_results[scenario_id] = selected
        scenario_decisions[scenario_id] = {
            "selected_config_id": selected_id,
            "runner_up_config_id": report["robustness"].get("second_best_fallback"),
            "recommendation_confidence": report["robustness"].get("recommendation_confidence"),
            "constraint_violations": selected.get("constraint_violations", []),
            "constraint_margins": selected.get("constraint_margins", {}),
            "baseline_regret": report["selection"].get("regret", {}),
            "reconfiguration": report["reconfiguration"],
            "architecture_breakdown": report["candidate_details"][selected_id],
            "counterfactual": next(
                (item for item in differing_cases if item["scenario_id"] == scenario_id),
                None,
            ),
        }

    representative_report = next(
        (item for item in scenario_reports if item.get("status") == "ok"), None
    )
    representative_detail = (
        representative_report["candidate_details"][safe_fallback]
        if representative_report is not None
        else None
    )
    deployment_mode = configured_deployment_mode
    deployment = {
        "schema_version": 1,
        "architecture_mode": deployment_mode,
        "hardware_topology": topology,
        "selection_granularity": architecture.get("selection_granularity", "design"),
        "safe_fallback_config_id": safe_fallback,
        "metadata_format": {
            **protected_metadata_bits(
                len(candidates) if topology != "fixed" else 1,
                str(architecture.get("metadata_protection", "triplicated")),
            ),
            "mode_encoding": "binary",
            "illegal_mode_action": "force_safe_fallback",
        },
        "mode_policy": policy,
        "selected_configurations": selected_configurations,
        "selected_results": selected_results,
        "scenario_decisions": scenario_decisions,
        "selection_fabric": {
            "mux_implementation": str(architecture.get("mux_implementation", "pruned")),
            "logical_model": representative_detail["fabric"] if representative_detail else None,
            "container_layout": representative_detail["layout"] if representative_detail else None,
            "physical_characterization_required_for_ppa": bool(
                representative_detail
                and not representative_detail["fabric"]["physical_metrics_characterized"]
            ),
        },
        "controller_configuration": {
            "safe_fallback_config_id": safe_fallback,
            "illegal_mode_action": "force_safe_fallback",
            "transition_commit_condition": "target region quiesced and migrated data verified",
            "metadata_protection": str(architecture.get("metadata_protection", "triplicated")),
        },
        "register_map": {
            "ECC_MODE": {"offset": "0x00", "access": "RW", "reset": safe_fallback},
            "ECC_MODE_STATUS": {"offset": "0x04", "access": "RO"},
            "ECC_TRANSITION_REQUEST": {"offset": "0x08", "access": "WO"},
            "ECC_TRANSITION_STATUS": {"offset": "0x0C", "access": "RO"},
        },
        "transition_safety": (
            "Quiesce target region, read/decode old mode, encode/write new mode, verify, then commit protected metadata."
        ),
        "validation_level": (
            "conditional_projected" if any(not report.get("physical_metrics_complete", False) for report in scenario_reports if report.get("status") == "ok") else "characterized_input"
        ),
        "provenance": {
            "repository_commit": repository_commit,
            "repository_dirty": repository_dirty,
            "source_tree_sha256": source_tree_sha256,
            "result_run_id": result_run_id,
            "input_config": str(config_path),
            "input_config_sha256": input_config_sha256,
        },
    }

    _write_json(data_dir / "all_candidates.json", all_rows)
    _write_csv(
        data_dir / "all_candidates.csv",
        [
            {key: value for key, value in row.items() if not isinstance(value, (dict, list))}
            for row in all_rows
        ],
    )
    _write_json(data_dir / "scenario_reports.json", scenario_reports)
    _write_json(
        data_dir / "score_diagnostics.json",
        {
            str(report["scenario_id"]): report["score_diagnostics"]
            for report in scenario_reports
            if report.get("status") == "ok"
        },
    )
    _write_json(data_dir / "baseline_counterfactuals.json", differing_cases)
    _write_json(data_dir / "polar_ablation.json", polar_membership)
    topology_comparison = compare_topology_logical_resources(
        candidates,
        logical_width_bits=scenarios[0].logical_width_bits,
        status_width_bits=int(architecture.get("status_width_bits", 4)),
        implementation=str(architecture.get("mux_implementation", "pruned")),
        metadata_protection=str(architecture.get("metadata_protection", "triplicated")),
    )
    _write_json(data_dir / "topology_comparison.json", topology_comparison)
    _plot_topology_comparison(
        topology_comparison, figure_dir / "topology_mux_comparison.svg"
    )
    first_report = next(
        (item for item in scenario_reports if item.get("status") == "ok"), None
    )
    configured_topology = next(
        item for item in topology_comparison if item["topology"] == topology
    )
    deployment_modes = [
        {
            "deployment_mode": "design_time_fixed",
            "hardware_topology": "fixed",
            "mux_2to1_count": 0,
            "protected_metadata_bits": 0,
            "reconfiguration_charged": False,
            "interpretation": "Only the selected ECC is instantiated; selector and migration overhead are zero.",
        },
        {
            "deployment_mode": "boot_time_or_bank_configurable",
            "hardware_topology": topology,
            "mux_2to1_count": configured_topology["mux_2to1_count"],
            "protected_metadata_bits": configured_topology["metadata_bits"],
            "reconfiguration_charged": False,
            "interpretation": "MUX/controller/metadata are required; recurring data migration is not charged.",
        },
        {
            "deployment_mode": "runtime_adaptive",
            "hardware_topology": topology,
            "mux_2to1_count": configured_topology["mux_2to1_count"],
            "protected_metadata_bits": configured_topology["metadata_bits"],
            "reconfiguration_charged": True,
            "example_reconfiguration": first_report.get("reconfiguration") if first_report else None,
            "interpretation": "Selector execution, protected mode state, safe transition, and migration are charged.",
        },
    ]
    _write_json(data_dir / "deployment_mode_comparison.json", deployment_modes)
    scalability = benchmark_exact_pareto_scaling()
    _write_json(data_dir / "scalability_benchmark.json", scalability)
    first_scenario_id = next(iter(policy), None)
    optimizer_validation = {
        "status": "not_run",
        "algorithm_under_test": "legacy deterministic non-dominated sort (not an evolutionary NSGA-II run)",
    }
    if first_scenario_id is not None:
        comparison_rows = [
            {
                "code": str(item["config_id"]),
                "FIT": float(item["FIT"]),
                "carbon_kg": float(item["carbon_kg"]),
                "latency_ns": float(item["latency_ns"]),
            }
            for item in all_rows
            if item["scenario_id"] == first_scenario_id
        ]
        exact_started = time.perf_counter()
        exact_front = pareto_frontier(comparison_rows)
        exact_seconds = time.perf_counter() - exact_started
        sort_started = time.perf_counter()
        fronts, *_ = _nsga2_sort(comparison_rows)
        sort_seconds = time.perf_counter() - sort_started
        exact_ids = {str(item["code"]) for item in exact_front}
        sort_ids = {str(comparison_rows[index]["code"]) for index in fronts[0]}
        optimizer_validation = {
            "status": "ok",
            "scenario_id": first_scenario_id,
            "candidate_count": len(comparison_rows),
            "objectives": {"FIT": "min", "carbon_kg": "min", "latency_ns": "min"},
            "exact_front": sorted(exact_ids),
            "legacy_sort_front": sorted(sort_ids),
            "agreement": exact_ids == sort_ids,
            "symmetric_difference_count": len(exact_ids ^ sort_ids),
            "exact_runtime_seconds": exact_seconds,
            "legacy_sort_runtime_seconds": sort_seconds,
            "warning": "Timing is host-dependent; this validates first-front membership only.",
        }
    _write_json(data_dir / "optimizer_validation.json", optimizer_validation)
    _write_json(deploy_dir / "selected_configuration.json", deployment)
    _write_json(deploy_dir / "register_map.json", deployment["register_map"])
    emit_systemverilog_package(
        deploy_dir / "green_ecc_config_pkg.sv",
        package_name="green_ecc_config_pkg",
        candidates=candidates,
        safe_fallback_config_id=safe_fallback,
        scenario_modes=policy,
        metadata_protection=str(architecture.get("metadata_protection", "triplicated")),
    )
    _plot_selection_summary(all_rows, figure_dir / "architecture_candidate_space.svg")

    completed_scenarios = sum(report.get("status") == "ok" for report in scenario_reports)
    family_count = len({item.family for item in candidates})
    summary = {
        "schema_version": 1,
        "scenario_count": len(scenarios),
        "completed_scenarios": completed_scenarios,
        "ecc_family_count": family_count,
        "ecc_configuration_count": len(candidates),
        "candidate_scenario_evaluations": len(all_rows),
        "selection_algorithm": "exact Pareto enumeration plus declared preference cost",
        "theoretical_time_complexity": "O(S*C^2) for S scenarios and C feasible configurations",
        "theoretical_memory_complexity": "O(S*C)",
        "observed_runtime_seconds": time.perf_counter() - start,
        "green_vs_lookup_differences": len(differing_cases),
        "polar_pareto_memberships": sum(bool(item["pareto_member"]) for item in polar_membership),
        "limitations": [
            "No manuscript or thesis LaTeX sources are present in this checkout.",
            "No characterized MUX/library/PVT record is shipped; adaptive physical PPA remains null unless supplied.",
            "Legacy selector candidate area and latency are projected constants, not synthesis results.",
            "Legacy selector dynamic and leakage energy are unavailable; only scrub energy is populated.",
            "Monte Carlo uses declared independent uniform intervals and is a robustness stress test.",
        ],
    }
    _write_json(outdir / "architecture_summary.json", summary)
    _write_json(outdir / "resolved_input_config.json", payload)

    manifest_files = [
        data_dir / "all_candidates.json",
        data_dir / "all_candidates.csv",
        data_dir / "scenario_reports.json",
        data_dir / "score_diagnostics.json",
        data_dir / "baseline_counterfactuals.json",
        data_dir / "polar_ablation.json",
        data_dir / "topology_comparison.json",
        data_dir / "deployment_mode_comparison.json",
        data_dir / "scalability_benchmark.json",
        data_dir / "optimizer_validation.json",
        deploy_dir / "selected_configuration.json",
        deploy_dir / "register_map.json",
        deploy_dir / "green_ecc_config_pkg.sv",
        figure_dir / "architecture_candidate_space.svg",
        figure_dir / "topology_mux_comparison.svg",
        figure_dir / "topology_mux_comparison.png",
        outdir / "architecture_summary.json",
        outdir / "resolved_input_config.json",
    ]
    manifest = {
        "manifest_version": 1,
        "repository_commit": repository_commit,
        "repository_dirty": repository_dirty,
        "source_tree_sha256": source_tree_sha256,
        "source_files": source_files,
        "result_run_id": result_run_id,
        "input_config": str(config_path),
        "input_config_sha256": input_config_sha256,
        "metric_sources": sorted(
            {
                str(provenance["source"])
                for row in all_rows
                for provenance in row.get("metric_provenance", {}).values()
                if isinstance(provenance, dict) and provenance.get("source")
            }
        ),
        "files": {
            str(path.relative_to(outdir)).replace("\\", "/"): _sha256(path)
            for path in manifest_files
        },
        "reproduction_command": f"python eccsim.py architecture --config {config_path} --outdir {outdir}",
    }
    _write_json(outdir / "result_manifest.json", manifest)
    return {"summary": summary, "deployment": deployment, "manifest": manifest}
