"""SafeForge scientific-hardening study with no new optimization proposal."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ambiguity import SupportPattern, build_support, support_document
from .certificates import verify_risk_certificate
from .experiments import (
    decoder_policy_identifier,
    make_experiment_identity,
    matrix_identifier,
    metric_context,
    metric_rows_table,
)
from .faults import load_fault_distribution
from .gf2 import matrix_columns_as_ints, systematic_matrices, syndrome_from_columns
from .hardware import structural_cost
from .robust import (
    code_with_actions,
    compile_safe_decoder,
    decoder_actions,
    evaluate_actions,
    minimum_weight_actions,
    nominal_ml_actions,
)
from .robust_synthesis import universally_safe_actions
from .safeforge_study import _heldout_metrics, _optimized_known_mapping
from .support_audit import (
    audit_finite_universe,
    audit_weight_bounded_streaming,
    classify_error_mask,
    complete_tail_bound,
    error_masks,
    support_from_masks,
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _gf2_inverse(matrix: Sequence[Sequence[int]]) -> list[list[int]]:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise ValueError("GF(2) inverse requires a square matrix")
    work = [
        [int(value) for value in matrix[row]] + [1 if row == col else 0 for col in range(size)]
        for row in range(size)
    ]
    for col in range(size):
        pivot = next((row for row in range(col, size) if work[row][col]), None)
        if pivot is None:
            raise ValueError("matrix is singular over GF(2)")
        work[col], work[pivot] = work[pivot], work[col]
        for row in range(size):
            if row != col and work[row][col]:
                work[row] = [left ^ right for left, right in zip(work[row], work[col])]
    return [row[size:] for row in work]


def _matmul_gf2(left: Sequence[Sequence[int]], right: Sequence[Sequence[int]]) -> list[list[int]]:
    return [
        [sum(int(a) * int(b) for a, b in zip(row, column)) & 1 for column in zip(*right)]
        for row in left
    ]


def conventional_extended_hamming_72_64() -> dict[str, Any]:
    """Return systematic SECDED(72,64) from conventional Hamming bit positions."""

    h_original = []
    for parity in range(7):
        h_original.append([((position >> parity) & 1) for position in range(1, 72)] + [0])
    h_original.append([1] * 71 + [1])
    parity_positions = [1, 2, 4, 8, 16, 32, 64, 72]
    data_positions = [position for position in range(1, 73) if position not in parity_positions]
    order = data_positions + parity_positions
    reordered = [[row[position - 1] for position in order] for row in h_original]
    parity_block = [[reordered[row][64 + col] for col in range(8)] for row in range(8)]
    h = _matmul_gf2(_gf2_inverse(parity_block), reordered)
    data_columns = matrix_columns_as_ints(h)[:64]
    h_systematic, g = systematic_matrices(data_columns, 8)
    if h_systematic != h:
        raise AssertionError("conventional extended-Hamming systematic conversion failed")
    code = {
        "schema_version": 1,
        "code_id": "conventional-extended-hamming-secded-72-64",
        "code_class": "binary_systematic_linear_block",
        "baseline_kind": "conventional extended-Hamming SECDED with Hamming-position placement",
        "k": 64,
        "r": 8,
        "n": 72,
        "systematic": True,
        "H": h,
        "G": g,
        "physical_mapping": {
            "systematic_index_to_hamming_position": order,
            "data_positions": data_positions,
            "parity_positions": parity_positions,
        },
        "decoder": {"type": "hard_decision_syndrome_table", "correction_entries": []},
        "constraints": {},
    }
    single_support = tuple(
        SupportPattern(
            pattern_id=f"sbu-{position}",
            positions=(position,),
            family="sbu",
            metadata={},
            nominal_probability=1 / 72,
            source_distribution_ids=("uniform-sbu",),
        )
        for position in range(72)
    )
    return code_with_actions(
        code, minimum_weight_actions(code, single_support), code_id_suffix=""
    )


def _tv_greedy_policy(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    *,
    radius: float,
    sdc_limit: float,
) -> dict[str, Any]:
    """Compile one certified feasible point using the existing syndrome-class logic."""

    columns = matrix_columns_as_ints(code["H"])
    data_mask = (1 << int(code["k"])) - 1
    nominal = [float(item.nominal_probability) for item in support]
    by_syndrome: dict[int, list[int]] = defaultdict(list)
    for index, item in enumerate(support):
        syndrome = syndrome_from_columns(item.mask, columns)
        if syndrome:
            by_syndrome[syndrome].append(index)
    universal = universally_safe_actions(code, support)
    chosen = dict(universal)
    items = []
    for syndrome, indexes in sorted(by_syndrome.items()):
        if syndrome in chosen:
            continue
        candidates = sorted({support[index].mask for index in indexes})
        best = None
        for correction in candidates:
            collision_indexes = [
                index
                for index in indexes
                if ((support[index].mask ^ correction) & data_mask) != 0
            ]
            sdc_mass = sum(nominal[index] for index in collision_indexes)
            correct_mass = sum(nominal[index] for index in indexes) - sdc_mass
            record = (
                sdc_mass,
                -correct_mass,
                correction.bit_count(),
                correction,
                collision_indexes,
            )
            if best is None or record < best:
                best = record
        assert best is not None
        syndrome_mass = sum(nominal[index] for index in indexes)
        items.append(
            {
                "syndrome": syndrome,
                "correction": int(best[3]),
                "sdc_mass": float(best[0]),
                "due_reduction": syndrome_mass,
                "has_collision": bool(best[4]),
            }
        )
    items.sort(
        key=lambda item: (
            item["sdc_mass"] / item["due_reduction"] if item["due_reduction"] else math.inf,
            -item["due_reduction"],
            item["syndrome"],
        )
    )
    base = evaluate_actions(
        code,
        support,
        chosen,
        {"type": "total_variation", "radius": 0.0},
        bit_width=int(code["n"]),
    )
    nominal_sdc = float(base["nominal"]["sdc"])
    any_collision = any(base["loss_vectors"]["sdc"])
    for item in items:
        candidate_nominal = nominal_sdc + float(item["sdc_mass"])
        candidate_collision = any_collision or bool(item["has_collision"])
        candidate_worst = (
            min(1.0, candidate_nominal + radius) if candidate_collision else 0.0
        )
        if candidate_worst <= sdc_limit + 1e-15:
            chosen[int(item["syndrome"])] = int(item["correction"])
            nominal_sdc = candidate_nominal
            any_collision = candidate_collision
    ambiguity = {
        "ambiguity_id": f"tv-radius-{radius:g}",
        "type": "total_variation",
        "radius": float(radius),
        "maximum_radius": 1.0,
    }
    evaluation = evaluate_actions(code, support, chosen, ambiguity, bit_width=int(code["n"]))
    feasible = evaluation["worst_case"]["sdc"] <= sdc_limit + 1e-12
    cost = structural_cost(code["H"], code["G"], chosen, max_xor_fanin=2)
    return {
        "method": "deterministic_syndrome_class_greedy_existing_compiler_rule",
        "status": (
            "certified_feasible"
            if feasible
            else "infeasible_unavoidable_zero_syndrome_or_uncorrectable_sdc"
        ),
        "global_optimality_claim": False,
        "policy_id": decoder_policy_identifier(chosen, syndrome_bits=int(code["r"])),
        "actions": chosen,
        "evaluation": evaluation,
        "configured_radius": float(radius),
        "sdc_limit": float(sdc_limit),
        "correcting_syndromes": len(chosen),
        "abstaining_syndromes": (1 << int(code["r"])) - 1 - len(chosen),
        "rtl_table_size": {
            "dense_entries": 1 << int(code["r"]),
            "dense_bits_correction_plus_valid": (1 << int(code["r"])) * (int(code["n"]) + 1),
            "sparse_action_entries": len(chosen),
        },
        "structural_hardware": cost,
    }


def _strategy_metric_rows(
    *,
    strategy_id: str,
    code: Mapping[str, Any],
    actions: Mapping[int, int],
    evaluation: Mapping[str, Any],
    heldout: Mapping[str, Any],
    identity: Mapping[str, Any],
    nominal_pmf_id: str,
    heldout_pmf_id: str,
    ambiguity: Mapping[str, Any],
    universe_id: str,
) -> list[dict[str, Any]]:
    common = {"strategy_id": strategy_id, "code_id": code["code_id"]}
    rows = []
    for scope, pmf_id, metrics in (
        ("nominal", nominal_pmf_id, evaluation["nominal"]),
        ("held_out", heldout_pmf_id, heldout),
        ("worst_case", "separate-adversarial-pmfs-by-risk", evaluation["worst_case"]),
    ):
        context = metric_context(
            experiment_identity=identity,
            code=code,
            actions=actions,
            pmf_id=pmf_id,
            ambiguity=ambiguity,
            error_universe_id=universe_id,
            metric_scope=scope,
        )
        scoped_metrics = (
            {key: float(metrics[key]) for key in ("corrected", "due", "sdc")}
            if scope != "worst_case"
            else {key: float(metrics[key]) for key in ("due", "sdc", "residual")}
        )
        row = {**common, **context, "metrics": scoped_metrics}
        if scope == "worst_case":
            row["adversarial_pmf_ids"] = {
                risk: "adversarial-"
                + evaluation["certificates"][risk]["certificate_sha256"][:20]
                for risk in ("sdc", "due", "residual")
            }
        rows.append(row)
    return rows


def _small_support_audit(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline = _read(root / "reports/code_synthesis/baselines/odd_column_secded_code.json")
    synthesized = _read(root / "reports/code_synthesis/code.json")
    robust_code = _read(root / "reports/safeforge_study/robust_cosynthesized_code.json")
    nominal = load_fault_distribution(
        "configs/fault_distributions/small_hotspot_8bit.json", repo_root=root
    )
    shifted = load_fault_distribution(
        "configs/fault_distributions/small_shifted_8bit.json", repo_root=root
    )
    declared = build_support(nominal, [shifted])
    heldout = build_support(shifted)
    ambiguity = _read(root / "configs/ambiguity/tv_small_example.json")
    robust_fixed = compile_safe_decoder(
        baseline, declared, ambiguity, sdc_limit=0.0, raw_fit=nominal.raw_fit
    )
    strategies = {
        "conventional_min_weight_fixed": (baseline, decoder_actions(baseline)),
        "nominal_ml_fixed": (baseline, nominal_ml_actions(baseline, declared)),
        "robust_abstain_fixed": (baseline, decoder_actions(robust_fixed["compiled_code"])),
        "nominal_synthesized": (synthesized, nominal_ml_actions(synthesized, declared)),
        "robust_cosynthesized": (robust_code, decoder_actions(robust_code)),
    }
    universes = {
        "declared_union_28": declared,
        "all_errors_weight_le_2": support_from_masks(
            error_masks(8, maximum_weight=2),
            bit_width=8,
            nominal_support=declared,
            universe_id="all-errors-weight-le-2",
        ),
        "all_errors_weight_le_3": support_from_masks(
            error_masks(8, maximum_weight=3),
            bit_width=8,
            nominal_support=declared,
            universe_id="all-errors-weight-le-3",
        ),
        "complete_nonzero_255": support_from_masks(
            range(1, 1 << 8),
            bit_width=8,
            nominal_support=declared,
            universe_id="complete-nonzero-255",
        ),
    }
    audits = {}
    metric_rows = []
    identity = make_experiment_identity(
        k=4,
        r=4,
        distribution=nominal,
        error_universe_document=support_document(declared, bit_width=8),
        ambiguity=ambiguity,
    )
    for strategy_id, (code, actions) in strategies.items():
        audits[strategy_id] = {
            universe_id: audit_finite_universe(
                code,
                actions,
                support,
                universe_id=universe_id,
                ambiguity=ambiguity,
                sdc_limit=0.0,
            )
            for universe_id, support in universes.items()
        }
        declared_evaluation = evaluate_actions(code, declared, actions, ambiguity, bit_width=8)
        metric_rows.extend(
            _strategy_metric_rows(
                strategy_id=strategy_id,
                code=code,
                actions=actions,
                evaluation=declared_evaluation,
                heldout=_heldout_metrics(code, actions, heldout),
                identity=identity,
                nominal_pmf_id=nominal.distribution_id,
                heldout_pmf_id=shifted.distribution_id,
                ambiguity=ambiguity,
                universe_id="declared_union_28",
            )
        )
    full_masks = set(range(1, 1 << 8))
    for strategy_id, strategy_audits in audits.items():
        for universe_id, result in strategy_audits.items():
            support_masks = {item.mask for item in universes[universe_id]}
            outside_masks = full_masks - support_masks
            outside_sdc_upper = 0.0
            if outside_masks:
                code, actions = strategies[strategy_id]
                outside_sdc_upper = float(
                    any(
                        classify_error_mask(code, actions, mask)
                        in {"sdc_miscorrection", "undetected"}
                        for mask in outside_masks
                    )
                )
            result["open_support_bounds"] = {
                str(eta): complete_tail_bound(
                    result["worst_case_sdc_at_configured_radius"],
                    outside_probability_upper=eta,
                    outside_sdc_upper=outside_sdc_upper,
                )
                for eta in (0.0, 0.001, 0.01, 0.1, 1.0)
            }
            result["outside_sdc_outcome_supremum_over_complete_8bit_complement"] = outside_sdc_upper
    return {
        "schema_version": 1,
        "claim": "all radii are conditional on the named finite universe",
        "experiment_id": identity["experiment_id"],
        "universes": {
            name: support_document(support, bit_width=8) for name, support in universes.items()
        },
        "strategies": audits,
    }, metric_rows_table(metric_rows)


def _controlled_ablations(root: Path) -> dict[str, Any]:
    baseline = _read(root / "reports/code_synthesis/baselines/odd_column_secded_code.json")
    synthesized = _read(root / "reports/code_synthesis/code.json")
    nominal = load_fault_distribution(
        "configs/fault_distributions/small_hotspot_8bit.json", repo_root=root
    )
    shifted = load_fault_distribution(
        "configs/fault_distributions/small_shifted_8bit.json", repo_root=root
    )
    support = build_support(nominal, [shifted])
    ambiguity = _read(root / "configs/ambiguity/tv_small_example.json")
    robust = compile_safe_decoder(baseline, support, ambiguity, sdc_limit=0.0)
    mapped = _optimized_known_mapping(baseline, support, ambiguity)
    uniform_support = tuple(
        SupportPattern(
            pattern_id=item.pattern_id,
            positions=item.positions,
            family=item.family,
            metadata=item.metadata,
            nominal_probability=1.0 / len(support),
            source_distribution_ids=("uniform-over-declared-support",),
        )
        for item in support
    )
    def single_bit_actions(code: Mapping[str, Any]) -> dict[int, int]:
        actions: dict[int, int] = {}
        for position, syndrome in enumerate(matrix_columns_as_ints(code["H"])):
            if syndrome:
                actions.setdefault(int(syndrome), 1 << position)
        return actions

    cases = {
        "baseline_single_bit_decoder": (baseline, single_bit_actions(baseline)),
        "synthesized_matrix_single_bit_decoder": (
            synthesized,
            single_bit_actions(synthesized),
        ),
        "baseline_unweighted_minimum_weight_coset": (
            baseline,
            minimum_weight_actions(baseline, support),
        ),
        "baseline_nominal_ml": (baseline, nominal_ml_actions(baseline, support)),
        "baseline_uniform_trained_ml": (baseline, nominal_ml_actions(baseline, uniform_support)),
        "baseline_robust_abstain": (baseline, decoder_actions(robust["compiled_code"])),
        "mapped_baseline_robust_abstain": (mapped["code"], mapped["actions"]),
    }
    evaluated = {
        name: evaluate_actions(code, support, actions, ambiguity, bit_width=8)
        for name, (code, actions) in cases.items()
    }
    pairs = {
        "parity_check_matrix": (
            "baseline_single_bit_decoder",
            "synthesized_matrix_single_bit_decoder",
        ),
        "physical_column_placement": (
            "baseline_robust_abstain",
            "mapped_baseline_robust_abstain",
        ),
        "syndrome_coset_leader_policy": (
            "baseline_single_bit_decoder",
            "baseline_unweighted_minimum_weight_coset",
        ),
        "abstention_policy": ("baseline_nominal_ml", "baseline_robust_abstain"),
        "fault_pmf_specialization": (
            "baseline_unweighted_minimum_weight_coset",
            "baseline_nominal_ml",
        ),
    }
    return {
        "schema_version": 1,
        "control_rule": "each named pair changes only the stated component or compilation rule",
        "code_equivalence_constraint": "the synthesized (8,4) matrix is extended-Hamming/Hsiao-equivalent; no new-code gain is claimed",
        "cases": {
            name: {
                "code_id": code["code_id"],
                "matrix_id": matrix_identifier(code),
                "decoder_policy_id": decoder_policy_identifier(actions, syndrome_bits=4),
                "nominal": evaluated[name]["nominal"],
                "worst_case": evaluated[name]["worst_case"],
            }
            for name, (code, actions) in cases.items()
        },
        "paired_effects": {
            component: {
                "from": before,
                "to": after,
                "nominal_corrected_delta": evaluated[after]["nominal"]["corrected"]
                - evaluated[before]["nominal"]["corrected"],
                "nominal_due_delta": evaluated[after]["nominal"]["due"]
                - evaluated[before]["nominal"]["due"],
                "worst_case_sdc_delta": evaluated[after]["worst_case"]["sdc"]
                - evaluated[before]["worst_case"]["sdc"],
            }
            for component, (before, after) in pairs.items()
        },
    }


def _fixed_72_study(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    nominal = load_fault_distribution(
        "configs/fault_distributions/benchmarks/spatial_hot_spots.json", repo_root=root
    )
    expansions = [
        load_fault_distribution(path, repo_root=root)
        for path in (
            "configs/fault_distributions/benchmarks/distribution_shift.json",
            "configs/fault_distributions/benchmarks/voltage_sensitive.json",
            "configs/fault_distributions/benchmarks/mixed_sbu_dbu_mbu.json",
        )
    ]
    support = build_support(nominal, expansions)
    codes = {
        "conventional_secded_72_64": conventional_extended_hamming_72_64(),
        "hsiao_secded_72_64": _read(
            root / "reports/code_synthesis_64/baselines/odd_column_secded_code.json"
        ),
        "existing_generated_spatial": _read(root / "reports/code_synthesis_64/code.json"),
        "existing_generated_geometry_portfolio": _read(
            root
            / "reports/portfolio_cosynthesis/codes/forge-sram-portfolio-72-64-v1-geometry-filtered-joint.json"
        ),
        "existing_generated_spatial_portfolio": _read(
            root
            / "reports/portfolio_cosynthesis/codes/forge-sram-portfolio-72-64-v1-spatial-hotspot-joint.json"
        ),
        "robust_physical_mapping": _read(root / "reports/safeforge_64_study/code.json"),
    }
    radii = [0.0, 0.001, 0.01, 0.025, 0.05, 0.1]
    limits = [0.0, 0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.2]
    frontiers: dict[str, list[dict[str, Any]]] = {}
    policy_catalogue: dict[str, dict[str, Any]] = {}
    for code_name, code in codes.items():
        points = []
        for radius in radii:
            for limit in limits:
                point = _tv_greedy_policy(
                    code, support, radius=radius, sdc_limit=limit
                )
                key = f"{code_name}:delta={radius:g}:epsilon={limit:g}"
                policy_catalogue[key] = point
                points.append(
                    {
                        "matrix_name": code_name,
                        "code_id": code["code_id"],
                        "matrix_id": matrix_identifier(code),
                        "policy_id": point["policy_id"],
                        "experiment_id": None,
                        "nominal_pmf_id": nominal.distribution_id,
                        "adversarial_pmf_id": "adversarial-"
                        + point["evaluation"]["certificates"]["sdc"]["certificate_sha256"][:20],
                        "adversarial_pmf_ids": {
                            risk: "adversarial-"
                            + point["evaluation"]["certificates"][risk]["certificate_sha256"][:20]
                            for risk in ("sdc", "due", "residual")
                        },
                        "ambiguity_set_type": "total_variation",
                        "ambiguity_radius": radius,
                        "error_pattern_universe": "72bit-expanded-synthetic-support",
                        "parity_budget": 8,
                        "physical_mapping": code.get(
                            "physical_mapping", list(range(72))
                        ),
                        "metric_semantics": {
                            "nominal_is_probability_partition": True,
                            "worst_case_sdc_and_due_are_separate_maxima": True,
                        },
                        "metric_scopes": {
                            "nominal": "nominal",
                            "worst_case_sdc": "worst_case",
                            "worst_case_due": "worst_case",
                        },
                        "sdc_limit": limit,
                        "nominal": point["evaluation"]["nominal"],
                        "worst_case": point["evaluation"]["worst_case"],
                        "certified_radius": (
                            point["configured_radius"]
                            if point["status"] == "certified_feasible"
                            else None
                        ),
                        "correcting_syndromes": point["correcting_syndromes"],
                        "abstaining_syndromes": point["abstaining_syndromes"],
                        "rtl_table_size": point["rtl_table_size"],
                        "global_optimality_claim": False,
                        "status": point["status"],
                    }
                )
        frontiers[code_name] = points
    identity = make_experiment_identity(
        k=64,
        r=8,
        distribution=nominal,
        error_universe_document=support_document(support, bit_width=72),
        ambiguity={"type": "total_variation", "radius": 0.05},
    )
    for points in frontiers.values():
        for point in points:
            point["experiment_id"] = identity["experiment_id"]
    nondominated_frontiers = {}
    for code_name, points in frontiers.items():
        by_radius = {}
        for radius in radii:
            candidates = [
                point
                for point in points
                if point["status"] == "certified_feasible"
                and abs(float(point["ambiguity_radius"]) - radius) <= 1e-15
            ]
            unique = {}
            for point in candidates:
                key = (
                    round(float(point["worst_case"]["sdc"]), 14),
                    round(float(point["worst_case"]["due"]), 14),
                    round(float(point["nominal"]["corrected"]), 14),
                )
                unique.setdefault(key, point)
            candidates = list(unique.values())
            by_radius[str(radius)] = [
                point
                for point in candidates
                if not any(
                    other is not point
                    and float(other["worst_case"]["sdc"])
                    <= float(point["worst_case"]["sdc"]) + 1e-14
                    and float(other["worst_case"]["due"])
                    <= float(point["worst_case"]["due"]) + 1e-14
                    and (
                        float(other["worst_case"]["sdc"])
                        < float(point["worst_case"]["sdc"]) - 1e-14
                        or float(other["worst_case"]["due"])
                        < float(point["worst_case"]["due"]) - 1e-14
                    )
                    for other in candidates
                )
            ]
        nondominated_frontiers[code_name] = by_radius
    # Policies selected only to exercise the bounded-weight audit; no preference is asserted.
    audit_policies = {
        "minimum_weight_conventional": decoder_actions(codes["conventional_secded_72_64"]),
        "nominal_ml_hsiao": nominal_ml_actions(codes["hsiao_secded_72_64"], support),
        "fixed_hsiao_zero_sdc": policy_catalogue[
            "hsiao_secded_72_64:delta=0.05:epsilon=0"
        ]["actions"],
        "fixed_hsiao_epsilon_0.1": policy_catalogue[
            "hsiao_secded_72_64:delta=0.05:epsilon=0.1"
        ]["actions"],
        "robust_physical_mapping_zero_sdc": policy_catalogue[
            "robust_physical_mapping:delta=0.05:epsilon=0"
        ]["actions"],
    }
    audit_code_by_policy = {
        "minimum_weight_conventional": codes["conventional_secded_72_64"],
        "nominal_ml_hsiao": codes["hsiao_secded_72_64"],
        "fixed_hsiao_zero_sdc": codes["hsiao_secded_72_64"],
        "fixed_hsiao_epsilon_0.1": codes["hsiao_secded_72_64"],
        "robust_physical_mapping_zero_sdc": codes["robust_physical_mapping"],
    }
    bounded_parts = {
        name: audit_weight_bounded_streaming(
            audit_code_by_policy[name],
            {name: actions},
            maximum_weight=4,
            outside_probability_upper=None,
        )
        for name, actions in audit_policies.items()
    }
    bounded = {
        "bit_width": 72,
        "maximum_enumerated_weight": 4,
        "pattern_count": 1_091_058,
        "expected_pattern_count_formula": "C(72,1)+C(72,2)+C(72,3)+C(72,4)",
        "tail_scope": "all error vectors with weight>4",
        "policies": {
            name: bounded_parts[name]["policies"][name] for name in audit_policies
        },
    }
    availability = {
        "SECDED_72_64": {
            "status": "evaluated",
            "artifact": "conventional_extended_hamming_72_64",
        },
        "Hsiao_SECDED_72_64": {
            "status": "evaluated",
            "artifact": "reports/code_synthesis_64/baselines/odd_column_secded_code.json",
        },
        "SEC_DAEC_72_64": {
            "status": "not_available_as_verified_dimension_matched_matrix",
            "reason": "the ASIC wrapper reuses the SECDED matrix and is not a separately verified SEC-DAEC linear-code artifact",
        },
        "TAEC_72_64": {
            "status": "negative_collision_artifact_only",
            "reason": "the modeled wrapper reuses SECDED; adjacent triples collide with single-error syndromes",
        },
        "BCH": {
            "status": "dimension_mismatch_and_unverified_distance",
            "reported_dimensions": {"n": 63, "k": 51, "r": 12},
            "reason": "the checked-in degree-12 example polynomial admits a demonstrated triple collision and is not used as BCH evidence",
        },
        "existing_generated_72_64": {
            "status": "evaluated",
            "artifact_count": 3,
        },
    }
    literature_ambiguities = {
        path.stem: _read(path)
        for path in (
            root / "configs/ambiguity/literature_pieper_5nm_alpha_72bit.json",
            root / "configs/ambiguity/literature_fpga_neutron_mcu_72bit.json",
            root / "configs/ambiguity/literature_fpga_bram_undervolt_72bit.json",
        )
    }
    literature_policies = {
        "nominal_ml_hsiao": audit_policies["nominal_ml_hsiao"],
        "fixed_hsiao_zero_sdc": audit_policies["fixed_hsiao_zero_sdc"],
        "fixed_hsiao_epsilon_0.1_tv_policy": audit_policies[
            "fixed_hsiao_epsilon_0.1"
        ],
    }
    literature_evaluation = {}
    for ambiguity_name, literature_ambiguity in literature_ambiguities.items():
        policy_results = {}
        for name, actions in literature_policies.items():
            evaluation = evaluate_actions(
                codes["hsiao_secded_72_64"],
                support,
                actions,
                literature_ambiguity,
                bit_width=72,
            )
            verification = {
                risk: verify_risk_certificate(
                    evaluation["certificates"][risk], support, bit_width=72
                )
                for risk in ("sdc", "due", "residual")
            }
            if any(item["verification_status"] != "passed" for item in verification.values()):
                raise AssertionError("literature-derived risk certificate failed verification")
            policy_results[name] = {
                "matrix_id": matrix_identifier(codes["hsiao_secded_72_64"]),
                "decoder_policy_id": decoder_policy_identifier(actions, syndrome_bits=8),
                "evaluation": evaluation,
                "independent_solver_free_verification": verification,
            }
        literature_evaluation[ambiguity_name] = {
            "ambiguity_id": literature_ambiguity["ambiguity_id"],
            "ambiguity_type": literature_ambiguity["type"],
            "error_pattern_universe": "72bit-expanded-synthetic-bit-support-constrained-by-literature-aggregate",
            "evidence_kind": "literature_derived_aggregate_constraints",
            "not_a_measured_bit_exact_pmf": True,
            "policies": policy_results,
        }
    comparison_specs = {
        "minimum_weight_decoder": (
            codes["conventional_secded_72_64"],
            audit_policies["minimum_weight_conventional"],
            "established_conventional_matrix",
        ),
        "nominal_maximum_probability_decoder": (
            codes["hsiao_secded_72_64"],
            audit_policies["nominal_ml_hsiao"],
            "established_hsiao_matrix",
        ),
        "fixed_code_robust_abstaining_epsilon_0": (
            codes["hsiao_secded_72_64"],
            audit_policies["fixed_hsiao_zero_sdc"],
            "established_hsiao_matrix",
        ),
        "fixed_code_robust_abstaining_epsilon_0.05": (
            codes["hsiao_secded_72_64"],
            policy_catalogue["hsiao_secded_72_64:delta=0.05:epsilon=0.05"]["actions"],
            "established_hsiao_matrix",
        ),
        "robust_physical_mapping_epsilon_0.05": (
            codes["robust_physical_mapping"],
            policy_catalogue["robust_physical_mapping:delta=0.05:epsilon=0.05"]["actions"],
            "fixed_matrix_with_heuristic_physical_mapping",
        ),
        "existing_matrix_decoder_cosynthesis_epsilon_0.05": (
            codes["existing_generated_spatial"],
            policy_catalogue["existing_generated_spatial:delta=0.05:epsilon=0.05"]["actions"],
            "existing_generated_matrix_with_compiled_policy",
        ),
    }
    comparison = {}
    comparison_ambiguity = {
        "ambiguity_id": "fixed-72-comparison-tv-0.05",
        "type": "total_variation",
        "radius": 0.05,
    }
    for name, (code, actions, matrix_scope) in comparison_specs.items():
        evaluation = evaluate_actions(
            code, support, actions, comparison_ambiguity, bit_width=72
        )
        comparison[name] = {
            "experiment_id": identity["experiment_id"],
            "matrix_id": matrix_identifier(code),
            "decoder_policy_id": decoder_policy_identifier(actions, syndrome_bits=8),
            "nominal_pmf_id": nominal.distribution_id,
            "adversarial_pmf_ids": {
                risk: "adversarial-"
                + evaluation["certificates"][risk]["certificate_sha256"][:20]
                for risk in ("sdc", "due")
            },
            "ambiguity_set_type": "total_variation",
            "ambiguity_radius": 0.05,
            "error_pattern_universe": "72bit-expanded-synthetic-support",
            "parity_budget": 8,
            "physical_mapping": code.get("physical_mapping", list(range(72))),
            "matrix_scope": matrix_scope,
            "metric_semantics": {
                "nominal_is_probability_partition": True,
                "worst_case_sdc_and_due_are_separate_maxima": True,
            },
            "metric_scopes": {
                "nominal": "nominal",
                "worst_case_sdc": "worst_case",
                "worst_case_due": "worst_case",
            },
            "nominal": evaluation["nominal"],
            "worst_case": evaluation["worst_case"],
        }
    return {
        "schema_version": 1,
        "experiment_id": identity["experiment_id"],
        "support": support_document(support, bit_width=72),
        "frontier_kind": "full achieved certified sweep plus Pareto-filtered risk frontiers; no global constrained-optimality claim",
        "frontiers": frontiers,
        "nondominated_frontiers_by_radius": nondominated_frontiers,
        "availability_audit": availability,
        "literature_derived_ambiguity_evaluation": literature_evaluation,
        "strategy_comparison_at_tv_radius_0.05": comparison,
        "matrix_cosynthesis_scalability_result": {
            "status": "negative",
            "claim": "practical 64-bit arbitrary-matrix co-synthesis is not demonstrated",
            "retained_heuristic": "reports/safeforge_64_study/heuristic_search.json",
        },
    }, bounded


def _plot_frontier(output: Path, study: Mapping[str, Any]) -> str:
    from visualization_runtime import configure_matplotlib_cache

    configure_matplotlib_cache()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_dir = output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    selected = {
        "conventional_secded_72_64": "Conventional SECDED",
        "hsiao_secded_72_64": "Hsiao SECDED",
        "existing_generated_spatial": "Generated matrix",
        "robust_physical_mapping": "Robust mapping",
    }
    for key, label in selected.items():
        points = list(study["nondominated_frontiers_by_radius"][key]["0.05"])
        points.sort(key=lambda item: (item["worst_case"]["sdc"], item["worst_case"]["due"]))
        ax.plot(
            [point["worst_case"]["sdc"] for point in points],
            [point["worst_case"]["due"] for point in points],
            marker="o",
            label=label,
        )
    ax.set_xlabel("Worst-case SDC upper bound (TV δ=0.05)")
    ax.set_ylabel("Worst-case DUE upper bound (separate maximization)")
    ax.set_title("SafeForge achieved SDC–DUE risk frontier")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = figure_dir / "sdc_due_risk_frontier.svg"
    fig.savefig(path, format="svg", metadata={"Creator": "GREEN-ECC SafeForge", "Date": None})
    plt.close(fig)
    return path.relative_to(output).as_posix()


def run_hardening_study(*, repo_root: str | Path, outdir: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    output = Path(outdir)
    if not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)
    small, contexts = _small_support_audit(root)
    ablations = _controlled_ablations(root)
    fixed, bounded = _fixed_72_study(root)
    figure = _plot_frontier(output, fixed)
    _write(output / "support_audit_8bit.json", small)
    _write(output / "metric_context_table.json", contexts)
    _write(output / "gain_source_ablations.json", ablations)
    _write(output / "fixed_72bit_risk_frontiers.json", fixed)
    _write(output / "weight_le4_72bit_audit.json", bounded)
    _write(output / "figure_manifest.json", {"format": "SVG vector", "figures": [figure]})
    files = {
        path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "result_manifest.json"
    }
    manifest = {
        "manifest_version": 1,
        "artifact_status": "scientific_hardening_with_frozen_novelty_scope",
        "files": files,
        "reproduction_command": "python scripts/run_safeforge_hardening.py",
        "source_files": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in (
                "codeforge/hardening.py",
                "codeforge/support_audit.py",
                "codeforge/experiments.py",
                "codeforge/robust.py",
                "codeforge/ambiguity.py",
            )
        },
    }
    manifest["source_tree_sha256"] = _hash(manifest["source_files"])
    _write(output / "result_manifest.json", manifest)
    return {
        "small_experiment_id": small["experiment_id"],
        "fixed_72_experiment_id": fixed["experiment_id"],
        "enumerated_72bit_patterns": bounded["pattern_count"],
        "figure": figure,
        "output_directory": str(output),
    }
