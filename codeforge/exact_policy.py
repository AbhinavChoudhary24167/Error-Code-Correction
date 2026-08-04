"""Exact finite-domain robust compiler for fixed syndrome decoders.

The matrix is immutable.  The compiler chooses one declared action per observed
nonzero syndrome and solves a finite robust MILP by adversarial constraint
generation.  Each separation problem is independently certifiable by the existing
finite-support ambiguity machinery.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .ambiguity import SupportPattern, solve_worst_case, support_document
from .certificates import canonical_hash, verify_risk_certificate
from .gf2 import bit_string, matrix_columns_as_ints, mask_to_positions, syndrome_from_columns
from .robust import code_with_actions, decoder_actions, evaluate_actions, execute_policy_losses


def _hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _action_domain(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    *,
    verified_fallback_available: bool,
) -> dict[str, Any]:
    n, k, r = int(code["n"]), int(code["k"]), int(code["r"])
    columns = matrix_columns_as_ints(code["H"])
    conventional = decoder_actions(code)
    by_syndrome: dict[int, list[int]] = {}
    syndrome_by_index: list[int] = []
    for index, pattern in enumerate(support):
        syndrome = syndrome_from_columns(pattern.mask, columns)
        syndrome_by_index.append(syndrome)
        if syndrome:
            by_syndrome.setdefault(syndrome, []).append(index)

    records: list[dict[str, Any]] = []
    groups: dict[int, list[int]] = {}
    for syndrome, indexes in sorted(by_syndrome.items()):
        groups[syndrome] = []
        candidates = sorted({support[index].mask for index in indexes})
        action_specs: list[tuple[str, int, bool]] = [("abstain", 0, False)]
        for mask in candidates:
            has_fallback = bool(
                verified_fallback_available and conventional.get(syndrome) == mask
            )
            action_specs.append(("correct", mask, has_fallback))
        fallback = conventional.get(syndrome)
        if verified_fallback_available and fallback is not None and fallback not in candidates:
            action_specs.append(("verified_fallback", int(fallback), True))

        for kind, mask, fallback_capable in action_specs:
            sdc = [0] * len(support)
            due = [0] * len(support)
            if kind == "abstain":
                for index in indexes:
                    due[index] = 1
            else:
                if syndrome_from_columns(mask, columns) != syndrome:
                    raise ValueError("declared correction representative has inconsistent syndrome")
                for index in indexes:
                    residual = support[index].mask ^ mask
                    sdc[index] = int(bool(residual & ((1 << k) - 1)))
            record_index = len(records)
            records.append(
                {
                    "record_index": record_index,
                    "syndrome": syndrome,
                    "syndrome_bits": bit_string(syndrome, r),
                    "kind": kind,
                    "correction_mask": mask,
                    "correction_positions": list(mask_to_positions(mask, n)),
                    "verified_fallback_capable": fallback_capable,
                    "sdc_loss": sdc,
                    "due_loss": due,
                }
            )
            groups[syndrome].append(record_index)

    fixed_sdc = [
        int(syndrome_by_index[index] == 0 and bool(pattern.mask & ((1 << k) - 1)))
        for index, pattern in enumerate(support)
    ]
    return {
        "records": records,
        "groups": groups,
        "syndrome_by_index": syndrome_by_index,
        "fixed_sdc": fixed_sdc,
        "fallback_available": bool(verified_fallback_available),
    }


def _scenario_hash(probabilities: Sequence[float]) -> str:
    return _hash([round(float(value), 16) for value in probabilities])


def _solve_master(
    domain: Mapping[str, Any],
    scenarios: Sequence[Sequence[float]],
    *,
    sdc_limit: float,
    max_correction_entries: int | None,
    mip_rel_gap: float,
    time_limit_seconds: float | None,
) -> dict[str, Any]:
    try:
        import numpy as np
        import scipy
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("exact policy compilation requires scipy.optimize.milp") from exc

    records = domain["records"]
    variable_count = len(records) + 1
    t_index = variable_count - 1
    objective = np.zeros(variable_count)
    objective[t_index] = 1.0
    lower_bounds = np.zeros(variable_count)
    upper_bounds = np.ones(variable_count)
    integrality = np.zeros(variable_count)
    integrality[: len(records)] = 1
    rows: list[list[float]] = []
    lower: list[float] = []
    upper: list[float] = []

    for indexes in domain["groups"].values():
        row = [0.0] * variable_count
        for index in indexes:
            row[index] = 1.0
        rows.append(row)
        lower.append(1.0)
        upper.append(1.0)

    if max_correction_entries is not None:
        if max_correction_entries < 0:
            raise ValueError("max_correction_entries must be nonnegative")
        row = [0.0] * variable_count
        for index, record in enumerate(records):
            row[index] = float(record["kind"] != "abstain")
        rows.append(row)
        lower.append(-np.inf)
        upper.append(float(max_correction_entries))

    for probabilities in scenarios:
        if len(probabilities) != len(domain["fixed_sdc"]):
            raise ValueError("scenario PMF length differs from support")
        fixed_sdc = sum(
            float(probability) * int(loss)
            for probability, loss in zip(probabilities, domain["fixed_sdc"])
        )
        sdc_row = [0.0] * variable_count
        due_row = [0.0] * variable_count
        for index, record in enumerate(records):
            sdc_row[index] = sum(
                float(probability) * int(loss)
                for probability, loss in zip(probabilities, record["sdc_loss"])
            )
            due_row[index] = sum(
                float(probability) * int(loss)
                for probability, loss in zip(probabilities, record["due_loss"])
            )
        rows.append(sdc_row)
        lower.append(-np.inf)
        upper.append(float(sdc_limit) - fixed_sdc)
        due_row[t_index] = -1.0
        rows.append(due_row)
        lower.append(-np.inf)
        upper.append(0.0)

    options: dict[str, Any] = {"mip_rel_gap": float(mip_rel_gap), "presolve": True}
    if time_limit_seconds is not None:
        options["time_limit"] = float(time_limit_seconds)
    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(np.asarray(rows), np.asarray(lower), np.asarray(upper)),
        options=options,
    )
    if not result.success or result.x is None:
        raise ValueError(f"robust policy master MILP failed or is infeasible: {result.message}")
    selected = [index for index in range(len(records)) if float(result.x[index]) > 0.5]
    if len(selected) != len(domain["groups"]):
        raise AssertionError("master solution does not select exactly one action per syndrome")
    return {
        "selected_record_indexes": selected,
        "objective": float(result.fun),
        "dual_bound": float(getattr(result, "mip_dual_bound", result.fun)),
        "mip_gap": float(getattr(result, "mip_gap", 0.0)),
        "node_count": int(getattr(result, "mip_node_count", 0)),
        "solver": "scipy.optimize.milp_highs",
        "solver_version": scipy.__version__,
        "solver_status": str(result.message),
    }


def _actions_from_selection(
    domain: Mapping[str, Any], selected_record_indexes: Sequence[int]
) -> dict[int, int]:
    actions: dict[int, int] = {}
    for index in selected_record_indexes:
        record = domain["records"][int(index)]
        if record["kind"] != "abstain":
            actions[int(record["syndrome"])] = int(record["correction_mask"])
    return actions


def compile_exact_robust_policy(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    *,
    sdc_limit: float,
    verified_fallback_available: bool = False,
    max_correction_entries: int | None = None,
    mip_rel_gap: float = 1e-9,
    separation_tolerance: float = 1e-9,
    max_iterations: int = 128,
    time_limit_seconds: float | None = None,
) -> dict[str, Any]:
    """Minimize worst-case DUE for the declared fixed matrix and action domain."""

    if not 0.0 <= sdc_limit <= 1.0:
        raise ValueError("sdc_limit must be in [0,1]")
    if not support:
        raise ValueError("support must be nonempty")
    domain = _action_domain(
        code, support, verified_fallback_available=verified_fallback_available
    )
    nominal = [float(pattern.nominal_probability) for pattern in support]
    scenarios: list[list[float]] = [nominal]
    scenario_kinds: list[str] = ["nominal"]
    seen = {_scenario_hash(nominal)}
    master: dict[str, Any] | None = None
    final_sdc: dict[str, Any] | None = None
    final_due: dict[str, Any] | None = None
    actions: dict[int, int] = {}

    tv_zero_sdc_presolve = (
        str(ambiguity["type"]) == "total_variation"
        and float(ambiguity.get("radius", 0.0)) > sdc_limit + separation_tolerance
    )
    if tv_zero_sdc_presolve:
        if any(domain["fixed_sdc"]):
            raise ValueError(
                "the TV radius exceeds the SDC limit and a zero-syndrome data error makes "
                "zero support-SDC infeasible"
            )
        selected: list[int] = []
        for indexes in domain["groups"].values():
            safe = [
                index
                for index in indexes
                if not any(domain["records"][index]["sdc_loss"])
            ]
            if not safe:
                raise AssertionError("abstention must always be a zero-SDC action")
            selected.append(
                min(
                    safe,
                    key=lambda index: (
                        sum(
                            probability * loss
                            for probability, loss in zip(
                                nominal, domain["records"][index]["due_loss"]
                            )
                        ),
                        domain["records"][index]["kind"] == "abstain",
                        domain["records"][index]["kind"] == "verified_fallback",
                        index,
                    ),
                )
            )
        if max_correction_entries is not None:
            correcting = [
                index for index in selected if domain["records"][index]["kind"] != "abstain"
            ]
            if len(correcting) > max_correction_entries:
                def benefit(index: int) -> tuple[float, int]:
                    syndrome = int(domain["records"][index]["syndrome"])
                    abstain = next(
                        candidate
                        for candidate in domain["groups"][syndrome]
                        if domain["records"][candidate]["kind"] == "abstain"
                    )
                    nominal_mass = sum(
                        probability * loss
                        for probability, loss in zip(
                            nominal, domain["records"][abstain]["due_loss"]
                        )
                    )
                    support_count = sum(domain["records"][abstain]["due_loss"])
                    return nominal_mass, support_count

                ranked = sorted(
                    correcting,
                    key=lambda index: (-benefit(index)[0], -benefit(index)[1], index),
                )
                keep = set(ranked[:max_correction_entries])
                for offset, index in enumerate(selected):
                    if index in correcting and index not in keep:
                        syndrome = int(domain["records"][index]["syndrome"])
                        selected[offset] = next(
                            candidate
                            for candidate in domain["groups"][syndrome]
                            if domain["records"][candidate]["kind"] == "abstain"
                        )
        actions = _actions_from_selection(domain, selected)
        losses = execute_policy_losses(code, support, actions)
        final_sdc = solve_worst_case(
            support, losses["sdc"], ambiguity, bit_width=int(code["n"])
        )
        final_due = solve_worst_case(
            support, losses["due"], ambiguity, bit_width=int(code["n"])
        )
        due_adversary = list(final_due["adversarial_pmf"])
        if _scenario_hash(due_adversary) not in seen:
            scenarios.append(due_adversary)
            scenario_kinds.append("due_closed_form_extreme")
        master = {
            "selected_record_indexes": selected,
            "objective": float(final_due["worst_case_risk"]),
            "dual_bound": float(final_due["dual_bound"]),
            "mip_gap": 0.0,
            "node_count": 0,
            "solver": "exact_total_variation_zero_sdc_decomposition",
            "solver_version": "1",
            "solver_status": "optimal",
        }
        iteration = 0
    else:
        for iteration in range(1, max_iterations + 1):
            master = _solve_master(
                domain,
                scenarios,
                sdc_limit=sdc_limit,
                max_correction_entries=max_correction_entries,
                mip_rel_gap=mip_rel_gap,
                time_limit_seconds=time_limit_seconds,
            )
            actions = _actions_from_selection(domain, master["selected_record_indexes"])
            losses = execute_policy_losses(code, support, actions)
            final_sdc = solve_worst_case(
                support, losses["sdc"], ambiguity, bit_width=int(code["n"])
            )
            final_due = solve_worst_case(
                support, losses["due"], ambiguity, bit_width=int(code["n"])
            )
            additions: list[tuple[str, list[float]]] = []
            if float(final_sdc["worst_case_risk"]) > sdc_limit + separation_tolerance:
                additions.append(("sdc_separation", list(final_sdc["adversarial_pmf"])))
            if float(final_due["worst_case_risk"]) > float(master["objective"]) + separation_tolerance:
                additions.append(("due_separation", list(final_due["adversarial_pmf"])))
            new_count = 0
            for kind, probabilities in additions:
                identity = _scenario_hash(probabilities)
                if identity not in seen:
                    seen.add(identity)
                    scenarios.append(probabilities)
                    scenario_kinds.append(kind)
                    new_count += 1
            if not additions:
                break
            if new_count == 0:
                raise RuntimeError("separation returned a violating scenario already enforced by the master")
        else:
            raise RuntimeError("robust policy constraint generation did not converge")

    assert master is not None and final_sdc is not None and final_due is not None
    evaluation = evaluate_actions(code, support, actions, ambiguity, bit_width=int(code["n"]))
    selected_records = [domain["records"][index] for index in master["selected_record_indexes"]]
    entries = [
        {
            "syndrome": record["syndrome_bits"],
            "action": record["kind"],
            "correction_mask": int(record["correction_mask"]),
            "correction_positions": list(record["correction_positions"]),
            "verified_fallback_capable": bool(record["verified_fallback_capable"]),
        }
        for record in selected_records
    ]
    matrix_identity = {
        "n": int(code["n"]),
        "k": int(code["k"]),
        "r": int(code["r"]),
        "H": code["H"],
    }
    support_identity = support_document(support, bit_width=int(code["n"]))
    experiment_distribution_ids = sorted(
        {
            distribution_id
            for pattern in support
            for distribution_id in pattern.source_distribution_ids
        }
    )
    policy_basis = {
        "matrix_sha256": _hash(matrix_identity),
        "support_sha256": support_identity["support_sha256"],
        "ambiguity_sha256": _hash(dict(ambiguity)),
        "sdc_limit": float(sdc_limit),
        "entries": entries,
    }
    policy_sha256 = _hash(policy_basis)
    robust_due_upper = float(final_due["worst_case_risk"])
    lower_bound = float(master["dual_bound"])
    report = {
        "schema_version": 1,
        "compiler": "exact_finite_syndrome_action_robust_milp_constraint_generation",
        "policy_id": "exact-safe-" + policy_sha256[:20],
        "policy_sha256": policy_sha256,
        "source_code_id": str(code.get("code_id", "external-code")),
        "matrix_sha256": policy_basis["matrix_sha256"],
        "support_sha256": support_identity["support_sha256"],
        "nominal_pmf_sha256": support_identity["nominal_pmf_sha256"],
        "ambiguity_id": str(ambiguity.get("ambiguity_id", "anonymous-ambiguity")),
        "ambiguity_sha256": policy_basis["ambiguity_sha256"],
        "sdc_limit_modeled_support": float(sdc_limit),
        "entries": entries,
        "selected_correction_count": len(actions),
        "observed_syndrome_count": len(domain["groups"]),
        "action_candidate_count": len(domain["records"]),
        "verified_fallback_available": bool(verified_fallback_available),
        "max_correction_entries": max_correction_entries,
        "certificate_scope": {
            "matrix_sha256": policy_basis["matrix_sha256"],
            "policy_sha256": policy_sha256,
            "placement_id": code.get("placement", {}).get("placement_id"),
            "placement_sha256": code.get("placement", {}).get("placement_sha256"),
            "error_universe": {
                "kind": "finite_enumerated_support",
                "pattern_count": len(support),
                "support_sha256": support_identity["support_sha256"],
            },
            "ambiguity_id": str(ambiguity.get("ambiguity_id", "anonymous-ambiguity")),
            "ambiguity_sha256": policy_basis["ambiguity_sha256"],
            "tail_treatment": "not covered; deployment requires a separately bound system-tail certificate",
            "experiment_identity": {
                "source_distribution_ids": experiment_distribution_ids,
                "identity_kind": "declared distribution artifacts, not necessarily raw experiments",
            },
        },
        "compiled_code": code_with_actions(code, actions, code_id_suffix="-exact-safe"),
        "metrics": evaluation,
        "optimization": {
            "status": "robust_optimal_with_a_posteriori_gap",
            "proof_method": (
                "exact_total_variation_zero_sdc_decomposition"
                if tv_zero_sdc_presolve
                else "robust_milp_adversarial_constraint_generation"
            ),
            "optimality_scope": (
                "fixed supplied matrix; finite declared support; abstain plus each modeled "
                "same-syndrome representative and declared verified conventional fallback; "
                "configured finite-support ambiguity set"
            ),
            "iterations": iteration,
            "scenario_count": len(scenarios),
            "scenario_kinds": scenario_kinds,
            "scenario_sha256": [_scenario_hash(item) for item in scenarios],
            "scenario_pmfs": scenarios,
            "master_objective": float(master["objective"]),
            "master_dual_bound": lower_bound,
            "robust_due_upper_bound": robust_due_upper,
            "a_posteriori_absolute_gap": max(0.0, robust_due_upper - lower_bound),
            "mip_gap": float(master["mip_gap"]),
            "node_count": int(master["node_count"]),
            "solver": master["solver"],
            "solver_version": master["solver_version"],
            "solver_status": master["solver_status"],
        },
        "risk_certificates": {"sdc": final_sdc, "due": final_due},
        "limitations": [
            "No claim is made for error vectors outside the declared support.",
            "The action domain is finite and does not enumerate arbitrary decoder circuits.",
            "The reported lower bound is scoped to the fixed matrix and declared action domain.",
        ],
    }
    report["certificate_sha256"] = _hash(report)
    return report


def verify_exact_policy_certificate(
    code: Mapping[str, Any],
    support: Sequence[SupportPattern],
    ambiguity: Mapping[str, Any],
    certificate: Mapping[str, Any],
    *,
    tolerance: float = 1e-8,
) -> dict[str, Any]:
    """Freshly rebuild the domain, replay risks, and re-solve the master lower bound."""

    failures: list[str] = []
    payload = dict(certificate)
    supplied_hash = str(payload.pop("certificate_sha256", ""))
    if _hash(payload) != supplied_hash:
        failures.append("certificate_sha256 does not match certificate contents")
    matrix_hash = _hash(
        {"n": int(code["n"]), "k": int(code["k"]), "r": int(code["r"]), "H": code["H"]}
    )
    support_identity = support_document(support, bit_width=int(code["n"]))
    if matrix_hash != str(certificate.get("matrix_sha256")):
        failures.append("matrix identity differs from certificate")
    if support_identity["support_sha256"] != str(certificate.get("support_sha256")):
        failures.append("support identity differs from certificate")
    if support_identity["nominal_pmf_sha256"] != str(certificate.get("nominal_pmf_sha256")):
        failures.append("nominal PMF identity differs from certificate")
    if _hash(dict(ambiguity)) != str(certificate.get("ambiguity_sha256")):
        failures.append("ambiguity identity differs from certificate")

    domain = _action_domain(
        code,
        support,
        verified_fallback_available=bool(certificate.get("verified_fallback_available", False)),
    )
    actions: dict[int, int] = {}
    selected_keys = set()
    selected_record_indexes: list[int] = []
    for entry in certificate["entries"]:
        syndrome = int(str(entry["syndrome"]), 2)
        kind = str(entry["action"])
        mask = int(entry["correction_mask"])
        matching = [
            record
            for record in domain["records"]
            if int(record["syndrome"]) == syndrome
            and str(record["kind"]) == kind
            and int(record["correction_mask"]) == mask
        ]
        if len(matching) != 1:
            failures.append(f"entry for syndrome {entry['syndrome']} is outside the rebuilt action domain")
            continue
        selected_record_indexes.append(int(matching[0]["record_index"]))
        if syndrome in selected_keys:
            failures.append(f"duplicate selected syndrome {entry['syndrome']}")
        selected_keys.add(syndrome)
        if kind != "abstain":
            actions[syndrome] = mask
    if selected_keys != set(domain["groups"]):
        failures.append("certificate does not select one action for every observed syndrome")

    executed = execute_policy_losses(code, support, actions)
    risk_reports: dict[str, Any] = {}
    for name in ("sdc", "due"):
        supplied = certificate["risk_certificates"][name]
        if [int(value) for value in supplied["loss_vector"]] != executed[name]:
            failures.append(f"{name} loss vector differs from fresh policy execution")
        verified = verify_risk_certificate(
            supplied, support, bit_width=int(code["n"]), tolerance=tolerance
        )
        risk_reports[name] = verified
        if verified["verification_status"] != "passed":
            failures.extend(f"{name}: {item}" for item in verified["failures"])
    sdc_risk = float(certificate["risk_certificates"]["sdc"]["worst_case_risk"])
    if sdc_risk > float(certificate["sdc_limit_modeled_support"]) + tolerance:
        failures.append("worst-case SDC exceeds the declared support limit")

    if certificate["optimization"].get("proof_method") == "exact_total_variation_zero_sdc_decomposition":
        if str(ambiguity["type"]) != "total_variation" or not (
            float(ambiguity.get("radius", 0.0))
            > float(certificate["sdc_limit_modeled_support"]) + tolerance
        ):
            failures.append("zero-SDC TV decomposition precondition is false")
        if any(domain["fixed_sdc"]):
            failures.append("zero-SDC TV decomposition has a fixed zero-syndrome SDC")
        selected_set = set(selected_record_indexes)
        correction_budget = certificate.get("max_correction_entries")
        if correction_budget is None:
            for syndrome, indexes in domain["groups"].items():
                safe_correcting = [
                    index
                    for index in indexes
                    if domain["records"][index]["kind"] != "abstain"
                    and not any(domain["records"][index]["sdc_loss"])
                ]
                chosen = next((index for index in indexes if index in selected_set), None)
                if safe_correcting and (
                    chosen is None or domain["records"][chosen]["kind"] == "abstain"
                ):
                    failures.append(
                        f"syndrome {bit_string(syndrome, int(code['r']))} abstains despite a zero-SDC correction"
                    )
        else:
            candidates = []
            for syndrome, indexes in domain["groups"].items():
                safe_correcting = [
                    index
                    for index in indexes
                    if domain["records"][index]["kind"] != "abstain"
                    and not any(domain["records"][index]["sdc_loss"])
                ]
                if not safe_correcting:
                    continue
                abstain = next(
                    index for index in indexes if domain["records"][index]["kind"] == "abstain"
                )
                candidates.append(
                    (
                        syndrome,
                        sum(
                            probability * loss
                            for probability, loss in zip(
                                [item.nominal_probability for item in support],
                                domain["records"][abstain]["due_loss"],
                            )
                        ),
                        sum(domain["records"][abstain]["due_loss"]),
                    )
                )
            expected = {
                syndrome
                for syndrome, _, _ in sorted(
                    candidates, key=lambda item: (-item[1], -item[2], item[0])
                )[: int(correction_budget)]
            }
            actual = {
                int(domain["records"][index]["syndrome"])
                for index in selected_record_indexes
                if domain["records"][index]["kind"] != "abstain"
            }
            if actual != expected:
                failures.append("cardinality-budgeted zero-SDC decomposition is not benefit-optimal")
        fresh_master = {
            "dual_bound": float(certificate["risk_certificates"]["due"]["dual_bound"])
        }
    else:
        fresh_master = _solve_master(
            domain,
            certificate["optimization"]["scenario_pmfs"],
            sdc_limit=float(certificate["sdc_limit_modeled_support"]),
            max_correction_entries=certificate.get("max_correction_entries"),
            mip_rel_gap=1e-10,
            time_limit_seconds=None,
        )
    reported_lower = float(certificate["optimization"]["master_dual_bound"])
    if not math.isclose(float(fresh_master["dual_bound"]), reported_lower, abs_tol=tolerance):
        failures.append("fresh master lower bound differs from certificate")
    robust_upper = float(certificate["risk_certificates"]["due"]["worst_case_risk"])
    fresh_gap = max(0.0, robust_upper - float(fresh_master["dual_bound"]))
    if not math.isclose(
        fresh_gap,
        float(certificate["optimization"]["a_posteriori_absolute_gap"]),
        abs_tol=tolerance,
    ):
        failures.append("fresh a-posteriori gap differs from certificate")
    return {
        "schema_version": 1,
        "verification_status": "passed" if not failures else "failed",
        "certificate_sha256": supplied_hash,
        "fresh_master_dual_bound": float(fresh_master["dual_bound"]),
        "fresh_robust_due_upper_bound": robust_upper,
        "fresh_a_posteriori_absolute_gap": fresh_gap,
        "risk_verification": risk_reports,
        "failures": failures,
    }
