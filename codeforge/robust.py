"""Risk-limiting syndrome policy compiler for finite SRAM fault supports."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .ambiguity import SupportPattern, certified_safety_radius, solve_worst_case
from .gf2 import bit_string, matrix_columns_as_ints, mask_to_positions, positions_to_mask, syndrome_from_columns


def _hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def decoder_actions(code: Mapping[str, Any]) -> dict[int, int]:
    n = int(code["n"])
    actions: dict[int, int] = {}
    for entry in code.get("decoder", {}).get("correction_entries", []):
        syndrome = int(str(entry["syndrome"]), 2)
        if syndrome in actions:
            raise ValueError(f"duplicate decoder action for syndrome {entry['syndrome']}")
        actions[syndrome] = positions_to_mask(entry["positions"], n)
    return actions


def code_with_actions(
    code: Mapping[str, Any], actions: Mapping[int, int], *, code_id_suffix: str
) -> dict[str, Any]:
    result = copy.deepcopy(dict(code))
    r = int(result["r"])
    n = int(result["n"])
    result["code_id"] = str(result.get("code_id", "external")) + code_id_suffix
    result["decoder"] = {
        "type": "hard_decision_syndrome_table",
        "correction_entries": [
            {
                "syndrome": bit_string(int(syndrome), r),
                "positions": list(mask_to_positions(int(mask), n)),
            }
            for syndrome, mask in sorted(actions.items())
        ],
    }
    return result


def execute_policy_losses(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    actions: Mapping[int, int],
) -> dict[str, Any]:
    """Execute every supplied error vector; no distance-only approximation."""

    k = int(code["k"])
    r = int(code["r"])
    n = int(code["n"])
    h_columns = matrix_columns_as_ints(code["H"])
    if len(h_columns) != n:
        raise ValueError("code H width does not match n")
    outcomes = []
    sdc: list[int] = []
    due: list[int] = []
    correct: list[int] = []
    for index, pattern in enumerate(support):
        error = pattern.mask
        syndrome = syndrome_from_columns(error, h_columns)
        if syndrome == 0:
            outcome = "correct" if error & ((1 << k) - 1) == 0 else "silent_corruption"
            correction = 0
        elif syndrome not in actions:
            outcome = "detected_uncorrectable"
            correction = 0
        else:
            correction = int(actions[syndrome])
            if syndrome_from_columns(correction, h_columns) != syndrome:
                raise ValueError(
                    f"correction mask for syndrome {bit_string(syndrome, r)} has a different syndrome"
                )
            residual = error ^ correction
            outcome = "corrected" if residual & ((1 << k) - 1) == 0 else "silent_corruption"
        is_sdc = int(outcome == "silent_corruption")
        is_due = int(outcome == "detected_uncorrectable")
        is_correct = int(outcome in {"correct", "corrected"})
        sdc.append(is_sdc)
        due.append(is_due)
        correct.append(is_correct)
        outcomes.append(
            {
                "support_index": index,
                "pattern_id": pattern.pattern_id,
                "positions": list(pattern.positions),
                "syndrome": bit_string(syndrome, r),
                "action": (
                    {"kind": "DUE", "correction_positions": []}
                    if syndrome not in actions
                    else {
                        "kind": "correct",
                        "correction_positions": list(mask_to_positions(correction, n)),
                    }
                ),
                "outcome": outcome,
            }
        )
    if any(a + b + c != 1 for a, b, c in zip(sdc, due, correct)):
        raise AssertionError("decoder outcomes do not partition the supplied support")
    return {"sdc": sdc, "due": due, "correct": correct, "outcomes": outcomes}


def evaluate_actions(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    actions: Mapping[int, int],
    ambiguity: Mapping[str, Any],
    *,
    bit_width: int,
) -> dict[str, Any]:
    executed = execute_policy_losses(code, support, actions)
    nominal = [item.nominal_probability for item in support]
    nominal_sdc = sum(value * probability for value, probability in zip(executed["sdc"], nominal))
    nominal_due = sum(value * probability for value, probability in zip(executed["due"], nominal))
    residual_loss = [int(sdc or due) for sdc, due in zip(executed["sdc"], executed["due"])]
    certificates = {
        "sdc": solve_worst_case(
            support, executed["sdc"], ambiguity, bit_width=bit_width
        ),
        "due": solve_worst_case(
            support, executed["due"], ambiguity, bit_width=bit_width
        ),
        "residual": solve_worst_case(
            support, residual_loss, ambiguity, bit_width=bit_width
        ),
    }
    return {
        "nominal": {
            "corrected": 1.0 - nominal_sdc - nominal_due,
            "due": nominal_due,
            "sdc": nominal_sdc,
            "residual": nominal_sdc + nominal_due,
        },
        "worst_case": {
            "sdc": certificates["sdc"]["worst_case_risk"],
            "due": certificates["due"]["worst_case_risk"],
            "residual": certificates["residual"]["worst_case_risk"],
        },
        "certificates": certificates,
        "outcomes": executed["outcomes"],
        "loss_vectors": {key: executed[key] for key in ("sdc", "due", "correct")},
    }


def nominal_ml_actions(
    code: Mapping[str, Any], support: Sequence[SupportPattern]
) -> dict[int, int]:
    columns = matrix_columns_as_ints(code["H"])
    grouped: dict[int, list[SupportPattern]] = {}
    for pattern in support:
        syndrome = syndrome_from_columns(pattern.mask, columns)
        if syndrome:
            grouped.setdefault(syndrome, []).append(pattern)
    return {
        syndrome: max(
            patterns,
            key=lambda pattern: (
                pattern.nominal_probability,
                -len(pattern.positions),
                -pattern.mask,
            ),
        ).mask
        for syndrome, patterns in grouped.items()
    }


def minimum_weight_actions(
    code: Mapping[str, Any], support: Sequence[SupportPattern]
) -> dict[int, int]:
    columns = matrix_columns_as_ints(code["H"])
    grouped: dict[int, list[SupportPattern]] = {}
    for pattern in support:
        syndrome = syndrome_from_columns(pattern.mask, columns)
        if syndrome:
            grouped.setdefault(syndrome, []).append(pattern)
    return {
        syndrome: min(patterns, key=lambda pattern: (len(pattern.positions), pattern.mask)).mask
        for syndrome, patterns in grouped.items()
    }


def _indicator_bound(
    support: Sequence[SupportPattern],
    selected: Sequence[int],
    ambiguity: Mapping[str, Any],
    *,
    bit_width: int,
) -> tuple[float, float]:
    indicator = [int(index in selected) for index in range(len(support))]
    upper = solve_worst_case(support, indicator, ambiguity, bit_width=bit_width)["worst_case_risk"]
    complement = [1 - value for value in indicator]
    lower = 1.0 - solve_worst_case(
        support, complement, ambiguity, bit_width=bit_width
    )["worst_case_risk"]
    return max(0.0, lower), min(1.0, upper)


def _candidate_records(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    *,
    bit_width: int,
) -> tuple[dict[int, int], dict[int, list[dict[str, Any]]]]:
    columns = matrix_columns_as_ints(code["H"])
    r = int(code["r"])
    by_syndrome: dict[int, list[int]] = {}
    for index, pattern in enumerate(support):
        syndrome = syndrome_from_columns(pattern.mask, columns)
        if syndrome:
            by_syndrome.setdefault(syndrome, []).append(index)
    proposals: dict[int, int] = {}
    evaluations: dict[int, list[dict[str, Any]]] = {}
    nominal = [item.nominal_probability for item in support]
    for syndrome, indexes in sorted(by_syndrome.items()):
        syndrome_nominal = sum(nominal[index] for index in indexes)
        _, syndrome_upper = _indicator_bound(
            support, indexes, ambiguity, bit_width=bit_width
        )
        records = []
        masks = sorted({support[index].mask for index in indexes})
        for mask in masks:
            matching = [index for index in indexes if support[index].mask == mask]
            candidate_nominal = sum(nominal[index] for index in matching)
            candidate_lower, _ = _indicator_bound(
                support, matching, ambiguity, bit_width=bit_width
            )
            collision_indexes = [index for index in indexes if support[index].mask != mask]
            _, collision_upper = _indicator_bound(
                support, collision_indexes, ambiguity, bit_width=bit_width
            ) if collision_indexes else (0.0, 0.0)
            records.append(
                {
                    "syndrome": bit_string(syndrome, r),
                    "correction_mask": mask,
                    "correction_positions": list(mask_to_positions(mask, int(code["n"]))),
                    "nominal_confidence": (
                        candidate_nominal / syndrome_nominal if syndrome_nominal else 0.0
                    ),
                    "worst_case_confidence_lower_bound": (
                        candidate_lower / syndrome_upper if syndrome_upper > 0 else 0.0
                    ),
                    "worst_case_sdc_contribution": collision_upper,
                    "worst_case_due_contribution_if_abstaining": syndrome_upper,
                    "candidate_nominal_mass": candidate_nominal,
                }
            )
        records.sort(
            key=lambda item: (
                item["worst_case_sdc_contribution"],
                -item["worst_case_confidence_lower_bound"],
                -item["candidate_nominal_mass"],
                len(item["correction_positions"]),
                item["correction_mask"],
            )
        )
        proposals[syndrome] = int(records[0]["correction_mask"])
        evaluations[syndrome] = records
    return proposals, evaluations


def compile_safe_decoder(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    *,
    sdc_limit: float,
    residual_fit_limit: float | None = None,
    raw_fit: float | None = None,
    exact_subset_limit: int = 12,
) -> dict[str, Any]:
    """Compile a correction/abstain table under a strict safety-first hierarchy."""

    if not 0 <= sdc_limit <= 1:
        raise ValueError("sdc_limit must be in [0,1]")
    bit_width = int(code["n"])
    proposals, candidate_evaluations = _candidate_records(
        code, support, ambiguity, bit_width=bit_width
    )

    cache: dict[tuple[tuple[int, int], ...], dict[str, Any]] = {}

    def evaluate(actions: Mapping[int, int]) -> dict[str, Any]:
        key = tuple(sorted((int(syndrome), int(mask)) for syndrome, mask in actions.items()))
        if key not in cache:
            cache[key] = evaluate_actions(
                code, support, actions, ambiguity, bit_width=bit_width
            )
        return cache[key]

    def feasible(report: Mapping[str, Any]) -> bool:
        if report["worst_case"]["sdc"] > sdc_limit + 1e-15:
            return False
        if residual_fit_limit is not None:
            if raw_fit is None:
                return False
            if raw_fit * report["worst_case"]["residual"] > residual_fit_limit + 1e-12:
                return False
        return True

    def key(actions: Mapping[int, int], report: Mapping[str, Any]) -> tuple[float, float, int, tuple]:
        return (
            float(report["worst_case"]["due"]),
            float(report["nominal"]["due"]),
            len(actions),
            tuple(sorted(actions.items())),
        )

    syndromes = sorted(proposals)
    selected: dict[int, int] = {}
    search_status = "verified_greedy"
    optimality_proven = False
    candidates_evaluated = 0
    if sdc_limit == 0.0:
        columns = matrix_columns_as_ints(code["H"])
        data_mask = (1 << int(code["k"])) - 1
        grouped: dict[int, list[SupportPattern]] = {}
        for pattern in support:
            syndrome = syndrome_from_columns(pattern.mask, columns)
            if syndrome:
                grouped.setdefault(syndrome, []).append(pattern)
        for syndrome, records in candidate_evaluations.items():
            safe_records = [
                record
                for record in records
                if all(
                    ((pattern.mask ^ int(record["correction_mask"])) & data_mask) == 0
                    for pattern in grouped.get(syndrome, [])
                )
            ]
            if safe_records:
                selected[syndrome] = int(safe_records[0]["correction_mask"])
        final = evaluate(selected)
        candidates_evaluated = 1
        search_status = "optimal_support_universal_zero_sdc_actions"
        optimality_proven = True
        if not feasible(final):
            raise ValueError(
                "no decoder can meet strict zero SDC because an uncorrectable zero-syndrome "
                "data error or residual-FIT violation exists on the declared support"
            )
    elif len(syndromes) <= exact_subset_limit:
        search_status = "optimal_exhaustive_abstain_subset"
        optimality_proven = True
        best: tuple[tuple[Any, ...], dict[int, int], dict[str, Any]] | None = None
        for selector in range(1 << len(syndromes)):
            actions = {
                syndrome: proposals[syndrome]
                for bit, syndrome in enumerate(syndromes)
                if (selector >> bit) & 1
            }
            report = evaluate(actions)
            candidates_evaluated += 1
            if feasible(report):
                candidate = (key(actions, report), actions, report)
                if best is None or candidate[0] < best[0]:
                    best = candidate
        if best is None:
            raise ValueError("no decoder policy satisfies the configured robust constraints")
        selected = best[1]
        final = best[2]
    else:
        final = evaluate(selected)
        candidates_evaluated += 1
        while True:
            best_addition = None
            for syndrome in syndromes:
                if syndrome in selected:
                    continue
                actions = {**selected, syndrome: proposals[syndrome]}
                report = evaluate(actions)
                candidates_evaluated += 1
                if feasible(report):
                    candidate = (key(actions, report), syndrome, actions, report)
                    if best_addition is None or candidate[0] < best_addition[0]:
                        best_addition = candidate
            if best_addition is None or best_addition[0] >= key(selected, final):
                break
            selected = best_addition[2]
            final = best_addition[3]
        if not feasible(final):
            raise ValueError("all-abstain decoder unexpectedly violates robust constraints")

    r = int(code["r"])
    entries = []
    for syndrome in range(1, 1 << r):
        if syndrome in selected:
            chosen = next(
                record
                for record in candidate_evaluations[syndrome]
                if int(record["correction_mask"]) == int(selected[syndrome])
            )
            entries.append(
                {
                    **chosen,
                    "action": "correct",
                    "correct": True,
                    "abstain": False,
                    "reason": "selected_by_global_safety_first_optimization",
                }
            )
        else:
            records = candidate_evaluations.get(syndrome, [])
            entries.append(
                {
                    "syndrome": bit_string(syndrome, r),
                    "action": "DUE",
                    "correct": False,
                    "abstain": True,
                    "correction_mask": 0,
                    "correction_positions": [],
                    "nominal_confidence": max(
                        (record["nominal_confidence"] for record in records), default=0.0
                    ),
                    "worst_case_confidence_lower_bound": max(
                        (
                            record["worst_case_confidence_lower_bound"]
                            for record in records
                        ),
                        default=0.0,
                    ),
                    "worst_case_sdc_contribution": 0.0,
                    "worst_case_due_contribution_if_abstaining": max(
                        (
                            record["worst_case_due_contribution_if_abstaining"]
                            for record in records
                        ),
                        default=0.0,
                    ),
                    "reason": (
                        "no_modeled_error_for_syndrome"
                        if not records
                        else "abstention_required_or_preferred_by_robust_constraints"
                    ),
                }
            )
    safety_radius = certified_safety_radius(
        support,
        final["loss_vectors"]["sdc"],
        ambiguity,
        bit_width=bit_width,
        risk_limit=sdc_limit,
        maximum_radius=float(ambiguity.get("maximum_radius", 1.0)),
    )
    identity_basis = {
        "code_id": code.get("code_id"),
        "ambiguity_id": ambiguity.get("ambiguity_id"),
        "entries": [
            {
                "syndrome": entry["syndrome"],
                "action": entry["action"],
                "correction_mask": entry["correction_mask"],
            }
            for entry in entries
        ],
    }
    policy_id = "safe-" + _hash(identity_basis)[:20]
    robust_code = code_with_actions(code, selected, code_id_suffix="-safe")
    return {
        "schema_version": 1,
        "policy_id": policy_id,
        "code_id": str(code.get("code_id", "external-code")),
        "compiled_code_id": robust_code["code_id"],
        "ambiguity_id": str(ambiguity.get("ambiguity_id", "anonymous-ambiguity")),
        "ambiguity_type": ambiguity["type"],
        "configured_radius": float(ambiguity.get("radius", 0.0)),
        "sdc_limit": float(sdc_limit),
        "residual_fit_limit": residual_fit_limit,
        "raw_fit": raw_fit,
        "entries": entries,
        "selected_correction_count": len(selected),
        "abstention_count": (1 << r) - 1 - len(selected),
        "search": {
            "status": search_status,
            "optimality_proven": optimality_proven,
            "candidate_policies_evaluated": candidates_evaluated,
            "hierarchy": [
                "worst_case_sdc_constraint",
                "worst_case_residual_fit_constraint",
                "minimize_worst_case_due",
                "minimize_nominal_due",
                "minimize_correction_entries",
            ],
        },
        "metrics": {
            "nominal": final["nominal"],
            "worst_case": final["worst_case"],
            "worst_case_residual_fit": (
                float(raw_fit) * float(final["worst_case"]["residual"])
                if raw_fit is not None
                else None
            ),
        },
        "certified_safety_radius": safety_radius,
        "certificates": final["certificates"],
        "outcomes": final["outcomes"],
        "compiled_code": robust_code,
        "candidate_action_evaluations": {
            bit_string(syndrome, r): records
            for syndrome, records in candidate_evaluations.items()
        },
        "policy_sha256": _hash(identity_basis),
    }
