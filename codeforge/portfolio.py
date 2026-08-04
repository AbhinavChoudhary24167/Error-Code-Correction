"""Alternating matrix/shared-XOR portfolio co-synthesis."""

from __future__ import annotations

import copy
import math
import random
import shutil
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .faults import ErrorPattern, FaultDistribution
from .gf2 import bit_string, matrix_columns_as_ints, systematic_matrices
from .hardware import structural_cost
from .scalable import _greedy_decoder, synthesize_scalable
from .shared_graph import portfolio_shared_graph, sequential_graph_baseline
from .verify import verify_code_document


def _mix_distributions(
    portfolio_id: str,
    regimes: Sequence[tuple[str, float, FaultDistribution]],
) -> FaultDistribution:
    probabilities: dict[tuple[int, ...], float] = {}
    families: dict[tuple[int, ...], set[str]] = {}
    bit_width = regimes[0][2].bit_width
    for _, regime_weight, distribution in regimes:
        if distribution.bit_width != bit_width:
            raise ValueError("all portfolio distributions must share bit_width")
        for pattern in distribution.patterns:
            probabilities[pattern.positions] = probabilities.get(pattern.positions, 0.0) + regime_weight * pattern.probability
            families.setdefault(pattern.positions, set()).add(pattern.family)
    patterns = tuple(
        ErrorPattern(
            pattern_id=f"mixture-{index:04d}",
            positions=positions,
            probability=probabilities[positions],
            family=(next(iter(families[positions])) if len(families[positions]) == 1 else "mixed"),
            metadata={"component_families": sorted(families[positions])},
        )
        for index, positions in enumerate(sorted(probabilities, key=lambda item: (len(item), item)))
    )
    raw_fits = [distribution.raw_fit for _, _, distribution in regimes]
    raw_fit = (
        math.fsum(weight * float(value) for (_, weight, _), value in zip(regimes, raw_fits))
        if all(value is not None for value in raw_fits)
        else None
    )
    return FaultDistribution(
        distribution_id=f"{portfolio_id}-weighted-regime-mixture",
        bit_width=bit_width,
        patterns=patterns,
        provenance={
            "kind": "synthetic",
            "description": "Portfolio regime-probability mixture used for the one-general-code baseline.",
            "seed": None,
        },
        raw_fit=raw_fit,
    )


def _odd_column_secded(k: int, r: int) -> dict[str, Any]:
    parity = {1 << row for row in range(r)}
    data_columns = [
        value for value in range(1, 1 << r)
        if value.bit_count() % 2 == 1 and value not in parity
    ][:k]
    if len(data_columns) != k:
        raise ValueError("dimensions cannot form an odd-column SEC-DED fallback")
    h, g = systematic_matrices(data_columns, r)
    columns = matrix_columns_as_ints(h)
    decoder = {syn: 1 << position for position, syn in enumerate(columns)}
    return {
        "schema_version": 1,
        "code_id": f"odd-column-secded-{k}-{k+r}-fallback",
        "code_class": "binary_systematic_linear_block",
        "k": k,
        "r": r,
        "n": k + r,
        "systematic": True,
        "H": h,
        "G": g,
        "column_syndromes": [bit_string(value, r) for value in columns],
        "decoder": {
            "type": "hard_decision_syndrome_table",
            "correction_entries": [
                {
                    "syndrome": bit_string(syn, r),
                    "positions": [position],
                }
                for position, syn in enumerate(columns)
            ],
        },
        "constraints": {},
        "structural_hardware": structural_cost(h, g, decoder, max_xor_fanin=2),
    }


def _mode_from_columns(
    *,
    code_id: str,
    columns: Sequence[int],
    template: Mapping[str, Any],
    distribution: FaultDistribution,
) -> dict[str, Any] | None:
    k, r = int(template["k"]), int(template["r"])
    h, g = systematic_matrices(columns, r)
    matrix_cfg = template.get("matrix_constraints", {})
    row_weights = [sum(row) for row in h]
    if any(
        weight < int(matrix_cfg.get("min_row_weight", 1))
        or weight > int(matrix_cfg.get("max_row_weight", k + r))
        for weight in row_weights
    ):
        return None
    decoder_policy = template.get("decoder_policy", {})
    mandatory_names = set(decoder_policy.get("mandatory_correct_families", []))
    detect_names = set(decoder_policy.get("detect_only_families", []))
    mandatory = [pattern for pattern in distribution.patterns if pattern.family in mandatory_names]
    detect_only = [pattern for pattern in distribution.patterns if pattern.family in detect_names]
    constraints = template.get("constraints", {})
    selected = _greedy_decoder(
        h,
        distribution,
        mandatory,
        detect_only,
        float(constraints.get("max_sdc_probability", 1.0)),
    )
    if selected is None:
        return None
    decoder, probability = selected
    cost = structural_cost(
        h,
        g,
        decoder,
        max_xor_fanin=int(template.get("hardware_model", {}).get("max_xor_fanin", 2)),
    )
    max_matrix_xors = constraints.get("max_matrix_xor_gates")
    if max_matrix_xors is not None and cost["matrix_xor_gates"] > int(max_matrix_xors):
        return None
    entries = [
        {
            "syndrome": bit_string(syn, r),
            "positions": [position for position in range(k + r) if (mask >> position) & 1],
        }
        for syn, mask in sorted(decoder.items())
    ]
    return {
        "schema_version": 1,
        "code_id": code_id,
        "code_class": "binary_systematic_linear_block",
        "k": k,
        "r": r,
        "n": k + r,
        "systematic": True,
        "H": h,
        "G": g,
        "column_syndromes": [bit_string(value, r) for value in matrix_columns_as_ints(h)],
        "decoder": {"type": "hard_decision_syndrome_table", "correction_entries": entries},
        "constraints": dict(constraints),
        "synthesis_distribution_id": distribution.distribution_id,
        "synthesis_probability_mass": probability,
        "structural_hardware": cost,
    }


def _portfolio_metrics(codes: Sequence[Mapping[str, Any]], regime_weights: Sequence[float]) -> dict[str, Any]:
    graph = portfolio_shared_graph(codes)
    weighted_residual = math.fsum(
        float(weight) * (
            float(code["synthesis_probability_mass"]["due"])
            + float(code["synthesis_probability_mass"]["sdc"])
        )
        for code, weight in zip(codes, regime_weights)
    )
    total_decoder_entries = sum(
        int(code["structural_hardware"]["decoder"]["syndrome_table_entries"])
        for code in codes
    )
    return {
        "weighted_residual_probability": weighted_residual,
        "shared_xor_gates": graph["total_xor_gates"],
        "max_xor_depth": graph["max_estimated_depth"],
        "total_decoder_entries": total_decoder_entries,
        "graph": graph,
    }


def _metric_key(metrics: Mapping[str, Any]) -> tuple[float, int, int, int]:
    return (
        round(float(metrics["weighted_residual_probability"]), 15),
        int(metrics["shared_xor_gates"]),
        int(metrics["max_xor_depth"]),
        int(metrics["total_decoder_entries"]),
    )


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    keys = ("weighted_residual_probability", "shared_xor_gates", "max_xor_depth", "total_decoder_entries")
    no_worse = all(float(left[key]) <= float(right[key]) + 1e-15 for key in keys)
    better = any(float(left[key]) < float(right[key]) - 1e-15 for key in keys)
    return no_worse and better


def _catalogue_baselines() -> list[dict[str, Any]]:
    return [
        {
            "baseline": "SECDED",
            "status": "evaluated_as_equal-dimension odd-column systematic code",
        },
        {
            "baseline": "SEC-DAEC",
            "status": "not_fairly_comparable",
            "reason": "existing repository implementation uses a different 73-bit layout and lacks the new exhaustive matrix certificate",
        },
        {
            "baseline": "TAEC",
            "status": "not_fairly_comparable",
            "reason": "existing repository TAEC model is coverage-level rather than a supplied 72x8 parity-check matrix and executable decoder certificate",
        },
        {
            "baseline": "BCH",
            "status": "not_equal_redundancy",
            "reason": "the existing BCH(63,51) implementation has different dimensions and decoding structure",
        },
        {
            "baseline": "best fixed catalogue GREEN-ECC choice",
            "status": "requires deployment-specific physical cost characterization",
        },
    ]


def co_synthesize_portfolio(
    config: Mapping[str, Any],
    regimes: Sequence[tuple[str, float, FaultDistribution]],
    validation_distributions: Sequence[FaultDistribution],
    shifted_distributions: Sequence[FaultDistribution],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    template = copy.deepcopy(config["code_template"])
    template["k"] = int(config["k"])
    template["r"] = int(config["r"])
    template["method"] = "deterministic_beam"
    regime_weights = [weight for _, weight, _ in regimes]
    if not math.isclose(math.fsum(regime_weights), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("portfolio regime probabilities must sum to 1")

    independent_probability_only: list[dict[str, Any]] = []
    independent_hardware_aware: list[dict[str, Any]] = []
    for index, (regime_id, _, distribution) in enumerate(regimes):
        for aware, destination, suffix in (
            (False, independent_probability_only, "probability-only"),
            (True, independent_hardware_aware, "hardware-aware"),
        ):
            mode_cfg = copy.deepcopy(template)
            mode_cfg["code_id"] = f"{config['portfolio_id']}-{regime_id}-{suffix}"
            mode_cfg["hardware_model"]["hardware_aware"] = aware
            mode_cfg["search"]["seed"] = int(template["search"].get("seed", 0)) + index * 101
            result = synthesize_scalable(mode_cfg, distribution)
            if result.code is None:
                raise ValueError(f"independent synthesis failed for regime {regime_id}")
            destination.append(result.code)

    mixture_distribution = _mix_distributions(str(config["portfolio_id"]), regimes)
    general_cfg = copy.deepcopy(template)
    general_cfg["code_id"] = f"{config['portfolio_id']}-one-general-code"
    general_cfg["hardware_model"]["hardware_aware"] = True
    general_cfg["search"]["seed"] = int(template["search"].get("seed", 0)) + 909
    general_result = synthesize_scalable(general_cfg, mixture_distribution)
    if general_result.code is None:
        raise ValueError("one-general-code baseline synthesis failed")
    general_code = general_result.code
    general_reports = {
        regime_id: verify_code_document(general_code, distribution)
        for regime_id, _, distribution in regimes
    }
    general_weighted_residual = math.fsum(
        weight * report["probability_mass"]["residual"]
        for (_, weight, _), report in zip(regimes, general_reports.values())
    )

    joint_codes = copy.deepcopy(independent_hardware_aware)
    for index, (regime_id, _, distribution) in enumerate(regimes):
        joint_codes[index]["code_id"] = f"{config['portfolio_id']}-{regime_id}-joint"
        joint_codes[index]["synthesis_distribution_id"] = distribution.distribution_id
    current_metrics = _portfolio_metrics(joint_codes, regime_weights)
    cosynth_cfg = config.get("cosynthesis", {})
    rng = random.Random(int(cosynth_cfg.get("seed", 0)))
    iterations = int(cosynth_cfg.get("iterations", 10))
    candidates_per_mode = int(cosynth_cfg.get("candidates_per_mode", 8))
    timeout = float(cosynth_cfg.get("timeout_seconds", 60.0))
    r, k = int(config["r"]), int(config["k"])
    parity_columns = {1 << row for row in range(r)}
    matrix_cfg = template.get("matrix_constraints", {})
    pool = [
        value
        for value in range(1, 1 << r)
        if value not in parity_columns
        and int(matrix_cfg.get("min_data_column_weight", 1)) <= value.bit_count()
        <= int(matrix_cfg.get("max_data_column_weight", r))
    ]
    trajectory = [
        {
            "iteration": -1,
            "accepted": True,
            **{key: value for key, value in current_metrics.items() if key != "graph"},
        }
    ]
    archive: list[dict[str, Any]] = [
        {key: value for key, value in current_metrics.items() if key != "graph"}
    ]
    matrix_changes = 0
    timed_out = False
    for iteration in range(iterations):
        if time.perf_counter() - started >= timeout:
            timed_out = True
            break
        best_candidate: tuple[tuple[float, int, int, int], list[dict[str, Any]], dict[str, Any]] | None = None
        for mode_index, (regime_id, _, distribution) in enumerate(regimes):
            current_columns = tuple(matrix_columns_as_ints(joint_codes[mode_index]["H"])[:k])
            used = set(current_columns)
            for candidate_index in range(candidates_per_mode):
                proposal = list(current_columns)
                if candidate_index % 2 == 0:
                    left, right = rng.sample(range(k), 2)
                    proposal[left], proposal[right] = proposal[right], proposal[left]
                else:
                    position = rng.randrange(k)
                    available = [value for value in pool if value not in used]
                    if not available:
                        continue
                    proposal[position] = rng.choice(available)
                candidate_code = _mode_from_columns(
                    code_id=f"{config['portfolio_id']}-{regime_id}-joint",
                    columns=proposal,
                    template=template,
                    distribution=distribution,
                )
                if candidate_code is None:
                    continue
                candidate_codes = copy.deepcopy(joint_codes)
                candidate_codes[mode_index] = candidate_code
                metrics = _portfolio_metrics(candidate_codes, regime_weights)
                archive_point = {key: value for key, value in metrics.items() if key != "graph"}
                if not any(_dominates(point, archive_point) for point in archive):
                    archive = [point for point in archive if not _dominates(archive_point, point)]
                    archive.append(archive_point)
                candidate_key = _metric_key(metrics)
                if best_candidate is None or candidate_key < best_candidate[0]:
                    best_candidate = (candidate_key, candidate_codes, metrics)
        accepted = best_candidate is not None and best_candidate[0] < _metric_key(current_metrics)
        if accepted and best_candidate is not None:
            joint_codes = best_candidate[1]
            current_metrics = best_candidate[2]
            matrix_changes += 1
        trajectory.append(
            {
                "iteration": iteration,
                "accepted": accepted,
                **{key: value for key, value in current_metrics.items() if key != "graph"},
            }
        )

    mode_certificates: dict[str, Any] = {}
    for code, (regime_id, _, distribution) in zip(joint_codes, regimes):
        report = verify_code_document(code, distribution)
        if report["verification_status"] != "passed":
            raise ValueError(f"independent verifier rejected joint mode {regime_id}")
        mode_certificates[regime_id] = report

    distribution_sets = [distribution for _, _, distribution in regimes] + list(validation_distributions) + list(shifted_distributions)
    safety_cfg = config.get("safety", {})
    max_sdc = float(safety_cfg.get("max_sdc_probability", 0.0))
    max_residual_fit = safety_cfg.get("max_residual_fit")
    shift_results: dict[str, Any] = {}
    deployment_envelopes: dict[str, list[str]] = {}
    for code, (regime_id, _, synthesis_distribution) in zip(joint_codes, regimes):
        entries: dict[str, Any] = {}
        safe_ids: list[str] = []
        design_residual = None
        for distribution in distribution_sets:
            report = verify_code_document(code, distribution)
            residual_fit = report["fit"]["residual_fit"]
            safe = (
                report["probability_mass"]["sdc"] <= max_sdc + 1e-15
                and (
                    max_residual_fit is None
                    or (residual_fit is not None and residual_fit <= float(max_residual_fit) + 1e-15)
                )
            )
            if distribution.distribution_id == synthesis_distribution.distribution_id:
                design_residual = report["probability_mass"]["residual"]
            if safe:
                safe_ids.append(distribution.distribution_id)
            entries[distribution.distribution_id] = {
                "probability_mass": report["probability_mass"],
                "fit": report["fit"],
                "safe": safe,
                "degradation_vs_design_residual": None,
            }
        for entry in entries.values():
            if design_residual is not None:
                entry["degradation_vs_design_residual"] = (
                    entry["probability_mass"]["residual"] - design_residual
                )
        shift_results[regime_id] = entries
        deployment_envelopes[regime_id] = safe_ids

    fallback_code = _odd_column_secded(k, r)
    fallback_reports: dict[str, Any] = {}
    fallback_safe: dict[str, bool] = {}
    for distribution in distribution_sets:
        report = verify_code_document(fallback_code, distribution)
        residual_fit = report["fit"]["residual_fit"]
        safe = (
            report["probability_mass"]["sdc"] <= max_sdc + 1e-15
            and (
                max_residual_fit is None
                or (residual_fit is not None and residual_fit <= float(max_residual_fit) + 1e-15)
            )
        )
        fallback_reports[distribution.distribution_id] = report
        fallback_safe[distribution.distribution_id] = safe
    safety_decisions: dict[str, Any] = {}
    for regime_id, entries in shift_results.items():
        safety_decisions[regime_id] = {}
        for distribution_id, entry in entries.items():
            if entry["safe"]:
                decision = "specialized_mode"
            elif fallback_safe[distribution_id]:
                decision = "fallback_secded"
            else:
                decision = "reject_deployment_no_certified_fallback"
            safety_decisions[regime_id][distribution_id] = decision

    sequential = sequential_graph_baseline(independent_hardware_aware)
    separate_mux_proxy = (int(config["r"]) * 2) * (len(regimes) - 1)
    programmable = {
        "kind": "naive_fully_programmable_xor_fabric_structural_proxy",
        "xor_gates": int(config["r"]) * ((int(config["k"]) - 1) + (int(config["k"]) + int(config["r"]) - 1)),
        "configuration_bits": len(regimes) * int(config["r"]) * (2 * int(config["k"]) + int(config["r"])),
        "physical_ppa": None,
    }
    yosys = shutil.which("yosys")
    synthesis_tool_baseline = {
        "tool": "yosys/abc",
        "status": "unavailable" if yosys is None else "available_not_run_by_core_algorithm",
        "path": yosys,
        "physical_ppa": None,
        "claim_effect": "positive shared-hardware PPA claims are blocked until this baseline is run with a characterized flow",
    }
    joint_graph = current_metrics["graph"]
    baselines = {
        "catalogue": _catalogue_baselines(),
        "independent_probability_only": {
            "codes": independent_probability_only,
            "shared_graph_after_generation": portfolio_shared_graph(independent_probability_only),
        },
        "independent_hardware_aware": {
            "codes": independent_hardware_aware,
            "shared_graph_after_generation": portfolio_shared_graph(independent_hardware_aware),
        },
        "one_general_generated_code": {
            "code": general_code,
            "per_regime_reports": general_reports,
            "weighted_residual_probability": general_weighted_residual,
        },
        "separate_engines_plus_muxes": {
            "engine_xor_gates": sequential["total_xor_gates"],
            "selection_mux_2to1_proxy": separate_mux_proxy,
            "physical_ppa": None,
        },
        "naive_programmable_xor_fabric": programmable,
        "ordinary_combined_synthesis": synthesis_tool_baseline,
    }
    return {
        "schema_version": 1,
        "portfolio_id": str(config["portfolio_id"]),
        "k": int(config["k"]),
        "r": int(config["r"]),
        "n": int(config["k"]) + int(config["r"]),
        "modes": joint_codes,
        "assignments": {
            regime_id: code["code_id"] for code, (regime_id, _, _) in zip(joint_codes, regimes)
        },
        "regime_probabilities": {regime_id: weight for regime_id, weight, _ in regimes},
        "shared_graph": joint_graph,
        "objective_metrics": {key: value for key, value in current_metrics.items() if key != "graph"},
        "search": {
            "method": "alternating_matrix_and_shared_xor_graph_search",
            "selection_policy": "hard constraints, then lexicographic residual probability, shared XOR gates, depth, decoder entries",
            "iterations_requested": iterations,
            "iterations_completed": len(trajectory) - 1,
            "timed_out": timed_out,
            "matrix_changes_accepted": matrix_changes,
            "trajectory": trajectory,
            "nondominated_metric_archive": sorted(archive, key=_metric_key),
            "seed": int(cosynth_cfg.get("seed", 0)),
            "optimality_proven": False,
            "runtime_seconds": time.perf_counter() - started,
        },
        "certificates": mode_certificates,
        "baselines": baselines,
        "distribution_shift": shift_results,
        "safety_policy": {
            "max_sdc_probability": max_sdc,
            "max_residual_fit": max_residual_fit,
            "fallback_code": fallback_code,
            "fallback_reports": fallback_reports,
            "fallback_safe_by_distribution": fallback_safe,
            "rule": "use a specialized mode only when the estimated distribution_id is in its validated envelope; otherwise fall back",
            "validated_distribution_ids_by_regime": deployment_envelopes,
            "decisions": safety_decisions,
        },
        "physical_characterization": None,
        "hardware_claim_status": "unsupported_without_synthesis_tool_and_characterized_library",
        "scheduler_integration_status": "blocked_pending_physical_energy_latency_and_transition_characterization",
    }
