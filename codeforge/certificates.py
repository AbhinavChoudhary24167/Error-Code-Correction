"""Independent, solver-free verification of SafeForge risk certificates."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .ambiguity import SupportPattern, geometry_distance
from .gf2 import bit_string, is_zero_matrix, matmul, rank, transpose, validate_matrix
from .robust import decoder_actions, execute_policy_losses


def canonical_hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def support_from_document(document: Mapping[str, Any]) -> tuple[SupportPattern, ...]:
    return tuple(
        SupportPattern(
            pattern_id=str(item["pattern_id"]),
            positions=tuple(int(value) for value in item["positions"]),
            family=str(item["family"]),
            metadata=dict(item.get("metadata", {})),
            nominal_probability=float(item["nominal_probability"]),
            source_distribution_ids=tuple(str(value) for value in item.get("source_distribution_ids", [])),
        )
        for item in document["patterns"]
    )


def _close(left: float, right: float, tolerance: float, label: str, failures: list[str]) -> None:
    if not math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance):
        failures.append(f"{label}: {left!r} != {right!r}")


def _basic_probability_checks(values: Sequence[float], label: str, tolerance: float) -> list[str]:
    failures = []
    if any(not math.isfinite(float(value)) or float(value) < -tolerance for value in values):
        failures.append(f"{label} contains a negative or non-finite probability")
    _close(sum(float(value) for value in values), 1.0, tolerance, f"{label} normalization", failures)
    return failures


def verify_risk_certificate(
    certificate: Mapping[str, Any],
    support: Sequence[SupportPattern],
    *,
    bit_width: int,
    tolerance: float = 1e-8,
) -> dict[str, Any]:
    """Check feasibility, objective tightness, dual bound, and certificate hash."""

    failures: list[str] = []
    payload = dict(certificate)
    supplied_hash = str(payload.pop("certificate_sha256", ""))
    expected_hash = canonical_hash(payload)
    if supplied_hash != expected_hash:
        failures.append("certificate_sha256 does not match canonical certificate contents")

    loss = [int(value) for value in certificate["loss_vector"]]
    nominal = [float(value) for value in certificate["nominal_pmf"]]
    adversarial = [float(value) for value in certificate["adversarial_pmf"]]
    if not (len(loss) == len(nominal) == len(adversarial) == len(support)):
        failures.append("loss/PMF/support lengths differ")
        return {"verification_status": "failed", "failures": failures}
    if any(value not in (0, 1) for value in loss):
        failures.append("loss vector is not binary")
    failures.extend(_basic_probability_checks(nominal, "nominal PMF", tolerance))
    failures.extend(_basic_probability_checks(adversarial, "adversarial PMF", tolerance))
    for index, item in enumerate(support):
        _close(nominal[index], item.nominal_probability, tolerance, f"nominal[{index}]", failures)
    nominal_risk = sum(probability * value for probability, value in zip(nominal, loss))
    primal = sum(probability * value for probability, value in zip(adversarial, loss))
    _close(nominal_risk, certificate["nominal_risk"], tolerance, "nominal risk", failures)
    _close(primal, certificate["worst_case_risk"], tolerance, "primal objective", failures)

    kind = str(certificate["ambiguity_type"])
    radius = float(certificate["radius"])
    dual = float(certificate["dual_bound"])
    if kind == "total_variation":
        distance = 0.5 * sum(abs(left - right) for left, right in zip(nominal, adversarial))
        if distance > radius + tolerance:
            failures.append("adversarial PMF exceeds the total-variation radius")
        has_risk = any(loss)
        has_safe = not all(loss)
        expected_dual = nominal_risk if not (has_risk and has_safe) else min(1.0, nominal_risk + radius)
        _close(dual, expected_dual, tolerance, "TV dual bound", failures)
    elif kind == "geometry_wasserstein":
        geometry = dict(certificate["geometry"])
        row_mass = [0.0] * len(support)
        column_mass = [0.0] * len(support)
        transport_cost = 0.0
        for record in certificate["transport_plan"]:
            source, target, mass = int(record["source"]), int(record["target"]), float(record["mass"])
            if mass < -tolerance or not (0 <= source < len(support) and 0 <= target < len(support)):
                failures.append("invalid Wasserstein transport entry")
                continue
            cost = geometry_distance(support[source], support[target], bit_width=bit_width, config=geometry)
            row_mass[source] += mass
            column_mass[target] += mass
            transport_cost += mass * cost
        for index in range(len(support)):
            _close(row_mass[index], nominal[index], tolerance, f"transport row {index}", failures)
            _close(column_mass[index], adversarial[index], tolerance, f"transport column {index}", failures)
        if transport_cost > radius + tolerance:
            failures.append("transport plan exceeds the Wasserstein radius")
        multiplier = float(certificate["dual_multiplier"])
        if multiplier < -tolerance:
            failures.append("Wasserstein dual multiplier is negative")
        expected_dual = multiplier * radius + sum(
            nominal[source]
            * max(
                loss[target]
                - multiplier
                * geometry_distance(
                    support[source], support[target], bit_width=bit_width, config=geometry
                )
                for target in range(len(support))
            )
            for source in range(len(support))
        )
        _close(dual, expected_dual, tolerance, "Wasserstein dual bound", failures)
    elif kind == "structured_interval":
        lower = [float(value) for value in certificate["pattern_lower_bounds"]]
        upper = [float(value) for value in certificate["pattern_upper_bounds"]]
        if len(lower) != len(support) or len(upper) != len(support):
            failures.append("structured pattern-bound lengths differ from support")
        else:
            for index, probability in enumerate(adversarial):
                if probability < lower[index] - tolerance or probability > upper[index] + tolerance:
                    failures.append(f"adversarial[{index}] violates structured pattern bounds")
        for constraint in certificate["category_constraints"]:
            mass = sum(adversarial[int(index)] for index in constraint["indexes"])
            if mass < float(constraint["lower"]) - tolerance or mass > float(constraint["upper"]) + tolerance:
                failures.append(f"category constraint {constraint['name']} is violated")
        dual_data = certificate["dual"]
        inequalities: list[list[float]] = []
        bounds: list[float] = []
        for constraint in certificate["category_constraints"]:
            row = [1.0 if index in set(constraint["indexes"]) else 0.0 for index in range(len(support))]
            inequalities.extend([row, [-value for value in row]])
            bounds.extend([float(constraint["upper"]), -float(constraint["lower"])])
        inequality_marginals = [float(value) for value in dual_data["inequality_marginals"]]
        equality = float(dual_data["equality_marginals"][0])
        lower_marginals = [float(value) for value in dual_data["lower_marginals"]]
        upper_marginals = [float(value) for value in dual_data["upper_marginals"]]
        if any(value > tolerance for value in inequality_marginals + upper_marginals):
            failures.append("structured <=/upper-bound dual marginal has invalid sign")
        if any(value < -tolerance for value in lower_marginals):
            failures.append("structured lower-bound dual marginal has invalid sign")
        if len(inequality_marginals) != len(bounds):
            failures.append("structured inequality dual length differs from constraints")
        else:
            for variable in range(len(support)):
                stationarity = -float(loss[variable]) - equality
                stationarity -= sum(
                    inequalities[row][variable] * inequality_marginals[row]
                    for row in range(len(inequalities))
                )
                stationarity -= lower_marginals[variable] + upper_marginals[variable]
                if abs(stationarity) > tolerance:
                    failures.append(f"structured dual stationarity fails at variable {variable}")
            dual_minimum = (
                sum(bound * marginal for bound, marginal in zip(bounds, inequality_marginals))
                + equality
                + sum(value * marginal for value, marginal in zip(lower, lower_marginals))
                + sum(value * marginal for value, marginal in zip(upper, upper_marginals))
            )
            _close(dual, -dual_minimum, tolerance, "structured dual bound", failures)
    else:
        failures.append(f"unsupported ambiguity type {kind!r}")

    if primal > dual + tolerance:
        failures.append("reported dual bound is below the feasible primal objective")
    _close(abs(dual - primal), certificate["optimality_gap"], tolerance, "optimality gap", failures)
    return {
        "verification_status": "passed" if not failures else "failed",
        "ambiguity_type": kind,
        "primal_objective": primal,
        "dual_bound": dual,
        "optimality_gap": abs(dual - primal),
        "certificate_sha256": supplied_hash,
        "failures": failures,
    }


def verify_safety_certificate(document: Mapping[str, Any], *, tolerance: float = 1e-8) -> dict[str, Any]:
    """Independently execute an externally supplied matrix/policy and check all risk proofs."""

    failures: list[str] = []
    basis = dict(document)
    supplied_hash = str(basis.pop("safety_certificate_sha256", ""))
    expected_hash = canonical_hash(basis)
    if supplied_hash != expected_hash:
        failures.append("safety_certificate_sha256 does not match document contents")
    support = support_from_document(document["support"])
    bit_width = int(document["support"]["bit_width"])
    code = document["compiled_code"]
    support_patterns = [
        {"positions": list(item.positions), "family": item.family} for item in support
    ]
    if canonical_hash(support_patterns) != str(document["support"].get("support_sha256", "")):
        failures.append("support_sha256 does not match the ordered physical error support")
    if canonical_hash([item.nominal_probability for item in support]) != str(
        document["support"].get("nominal_pmf_sha256", "")
    ):
        failures.append("nominal_pmf_sha256 does not match support probabilities")
    if int(document["support"].get("pattern_count", -1)) != len(support):
        failures.append("support pattern_count does not match the pattern list")
    masks = [item.mask for item in support]
    if any(mask <= 0 or mask >= (1 << bit_width) for mask in masks) or len(masks) != len(set(masks)):
        failures.append("support contains an invalid or duplicate error vector")
    try:
        h_r, h_n = validate_matrix(code["H"], name="certificate H")
        g_k, g_n = validate_matrix(code["G"], name="certificate G")
        if (h_r, h_n, g_k, g_n) != (
            int(code["r"]),
            int(code["n"]),
            int(code["k"]),
            int(code["n"]),
        ):
            failures.append("compiled-code matrix dimensions differ from k/r/n")
        if h_n != bit_width:
            failures.append("compiled-code width differs from ambiguity support")
        if rank(code["H"]) != int(code["r"]):
            failures.append("compiled parity-check matrix is not full rank")
        if not is_zero_matrix(matmul(code["G"], transpose(code["H"]))):
            failures.append("compiled G*H^T is nonzero")
        if any(
            int(code["G"][row][column]) != int(row == column)
            for row in range(int(code["k"]))
            for column in range(int(code["k"]))
        ):
            failures.append("compiled generator is not systematic in the declared data positions")
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(f"compiled-code matrix validation failed: {exc}")
    actions = decoder_actions(code)
    executed = execute_policy_losses(code, support, actions)
    policy_losses = document["loss_vectors"]
    for name in ("sdc", "due", "correct"):
        if [int(value) for value in policy_losses[name]] != executed[name]:
            failures.append(f"executed {name} loss vector differs from certificate")
    r = int(code["r"])
    identity_basis = {
        "code_id": document.get("source_code_id"),
        "ambiguity_id": document.get("ambiguity", {}).get("ambiguity_id"),
        "entries": [
            {
                "syndrome": bit_string(syndrome, r),
                "action": "correct" if syndrome in actions else "DUE",
                "correction_mask": int(actions.get(syndrome, 0)),
            }
            for syndrome in range(1, 1 << r)
        ],
    }
    computed_policy_hash = canonical_hash(identity_basis)
    if computed_policy_hash != str(document.get("policy_sha256", "")):
        failures.append("policy_sha256 does not match the compiled syndrome-action table")
    if str(document.get("policy_id", "")) != "safe-" + computed_policy_hash[:20]:
        failures.append("policy_id does not match policy_sha256")
    risk_reports = {}
    for name in ("sdc", "due", "residual"):
        report = verify_risk_certificate(
            document["risk_certificates"][name], support, bit_width=bit_width, tolerance=tolerance
        )
        risk_reports[name] = report
        if report["verification_status"] != "passed":
            failures.extend(f"{name}: {message}" for message in report["failures"])
    sdc_risk = float(document["risk_certificates"]["sdc"]["worst_case_risk"])
    if sdc_risk > float(document["sdc_limit"]) + tolerance:
        failures.append("certified worst-case SDC exceeds the configured limit")
    residual_fit_limit = document.get("residual_fit_limit")
    if residual_fit_limit is not None:
        raw_fit = document.get("raw_fit")
        if raw_fit is None:
            failures.append("residual FIT limit is present but raw_fit is absent")
        elif float(raw_fit) * float(document["risk_certificates"]["residual"]["worst_case_risk"]) > float(residual_fit_limit) + tolerance:
            failures.append("certified worst-case residual FIT exceeds the configured limit")
    return {
        "schema_version": 1,
        "verification_status": "passed" if not failures else "failed",
        "policy_id": document.get("policy_id"),
        "certificate_id": supplied_hash,
        "risk_certificates": risk_reports,
        "executed_pattern_count": len(support),
        "failures": failures,
    }


def finalize_safety_certificate(document: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(document)
    payload["safety_certificate_sha256"] = canonical_hash(payload)
    return payload
