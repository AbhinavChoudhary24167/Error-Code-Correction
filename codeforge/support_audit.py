"""Support-conditional decoder audits and explicit open-support tail bounds.

This module deliberately separates finite-support certification from claims about
errors outside that support.  It contains no synthesis or learning machinery.
"""

from __future__ import annotations

from collections import Counter
import itertools
import math
from typing import Any, Iterable, Mapping, Sequence

from .ambiguity import SupportPattern, certified_safety_radius, solve_worst_case, support_document
from .gf2 import matrix_columns_as_ints, syndrome_from_columns
from .robust import execute_policy_losses


OUTCOME_KEYS = ("correct", "due", "sdc_miscorrection", "undetected")


def error_masks(n: int, *, minimum_weight: int = 1, maximum_weight: int | None = None) -> Iterable[int]:
    """Yield nonzero error masks in deterministic weight/lexicographic order."""

    upper = n if maximum_weight is None else int(maximum_weight)
    if n <= 0 or minimum_weight < 1 or upper < minimum_weight or upper > n:
        raise ValueError("invalid error-mask weight range")
    for weight in range(int(minimum_weight), upper + 1):
        for positions in itertools.combinations(range(n), weight):
            yield sum(1 << position for position in positions)


def support_from_masks(
    masks: Iterable[int],
    *,
    bit_width: int,
    nominal_support: Sequence[SupportPattern],
    universe_id: str,
) -> tuple[SupportPattern, ...]:
    """Expand a normalized nominal PMF onto a larger zero-mass finite universe."""

    nominal_by_mask = {item.mask: float(item.nominal_probability) for item in nominal_support}
    source_by_mask = {item.mask: tuple(item.source_distribution_ids) for item in nominal_support}
    selected = sorted(set(int(mask) for mask in masks))
    missing = sorted(
        mask for mask, probability in nominal_by_mask.items()
        if probability > 0.0 and mask not in set(selected)
    )
    if missing:
        raise ValueError(f"universe {universe_id!r} omits {len(missing)} nominal-PMF patterns")
    result = tuple(
        SupportPattern(
            pattern_id=f"{universe_id}-mask-{mask:x}",
            positions=tuple(index for index in range(bit_width) if (mask >> index) & 1),
            family=f"weight_{mask.bit_count()}",
            metadata={"universe_id": universe_id, "hamming_weight": mask.bit_count()},
            nominal_probability=nominal_by_mask.get(mask, 0.0),
            source_distribution_ids=source_by_mask.get(mask, (universe_id,)),
        )
        for mask in selected
    )
    if not math.isclose(sum(item.nominal_probability for item in result), 1.0, abs_tol=1e-12):
        raise ValueError("expanded universe does not retain a normalized nominal PMF")
    return result


def classify_error_mask(
    code: Mapping[str, Any], actions: Mapping[int, int], mask: int
) -> str:
    """Return one of four disjoint execution outcomes for a nonzero error."""

    if mask <= 0 or mask >= (1 << int(code["n"])):
        raise ValueError("error mask must be nonzero and fit the code width")
    columns = matrix_columns_as_ints(code["H"])
    syndrome = syndrome_from_columns(mask, columns)
    data_mask = (1 << int(code["k"])) - 1
    if syndrome == 0:
        return "correct" if mask & data_mask == 0 else "undetected"
    if syndrome not in actions:
        return "due"
    correction = int(actions[syndrome])
    if syndrome_from_columns(correction, columns) != syndrome:
        raise ValueError("decoder action does not match its syndrome")
    return "correct" if ((mask ^ correction) & data_mask) == 0 else "sdc_miscorrection"


def audit_finite_universe(
    code: Mapping[str, Any],
    actions: Mapping[int, int],
    support: Sequence[SupportPattern],
    *,
    universe_id: str,
    ambiguity: Mapping[str, Any],
    sdc_limit: float = 0.0,
) -> dict[str, Any]:
    """Execute and certify a decoder on every pattern of one finite universe."""

    executed = execute_policy_losses(code, support, actions)
    counts = Counter()
    by_weight: dict[str, Counter[str]] = {}
    for item, outcome in zip(support, executed["outcomes"]):
        if outcome["outcome"] in {"correct", "corrected"}:
            label = "correct"
        elif outcome["outcome"] == "detected_uncorrectable":
            label = "due"
        elif outcome["syndrome"] == "0" * int(code["r"]):
            label = "undetected"
        else:
            label = "sdc_miscorrection"
        counts[label] += 1
        by_weight.setdefault(str(len(item.positions)), Counter())[label] += 1
    sdc_loss = [int(value) for value in executed["sdc"]]
    risk = solve_worst_case(support, sdc_loss, ambiguity, bit_width=int(code["n"]))
    radius = certified_safety_radius(
        support,
        sdc_loss,
        ambiguity,
        bit_width=int(code["n"]),
        risk_limit=float(sdc_limit),
        maximum_radius=float(ambiguity.get("maximum_radius", 1.0)),
    )
    totals = {key: int(counts[key]) for key in OUTCOME_KEYS}
    totals["sdc_total"] = totals["sdc_miscorrection"] + totals["undetected"]
    if sum(totals[key] for key in OUTCOME_KEYS) != len(support):
        raise AssertionError("four-class audit does not partition the universe")
    return {
        "universe_id": universe_id,
        "universe": support_document(support, bit_width=int(code["n"])),
        "pattern_count": len(support),
        "outcome_counts": totals,
        "outcome_counts_by_weight": {
            weight: {
                **{key: int(values[key]) for key in OUTCOME_KEYS},
                "sdc_total": int(values["sdc_miscorrection"] + values["undetected"]),
            }
            for weight, values in sorted(by_weight.items(), key=lambda item: int(item[0]))
        },
        "nominal_sdc": sum(
            item.nominal_probability * loss for item, loss in zip(support, sdc_loss)
        ),
        "configured_ambiguity": dict(ambiguity),
        "worst_case_sdc_at_configured_radius": risk["worst_case_risk"],
        "certified_radius": radius,
        "claim_scope": "finite_support_only",
    }


def complete_tail_bound(
    within_support_sdc_bound: float,
    *,
    outside_probability_upper: float,
    outside_sdc_upper: float = 1.0,
) -> dict[str, Any]:
    """Lift a conditional support bound to a complete-distribution SDC bound."""

    risk = float(within_support_sdc_bound)
    eta = float(outside_probability_upper)
    outside = float(outside_sdc_upper)
    if not 0 <= risk <= 1 or not 0 <= eta <= 1 or not 0 <= outside <= 1:
        raise ValueError("risk, eta, and outside_sdc_upper must be probabilities")
    # eta is an upper bound, not necessarily the exact tail probability.  The
    # affine mixture is maximized at eta_upper only when outside >= inside.
    # Otherwise the safe endpoint is eta=0.
    eta_used = eta if outside >= risk else 0.0
    total = (1.0 - eta_used) * risk + eta_used * outside
    return {
        "within_support_sdc_upper": risk,
        "outside_support_probability_upper": eta,
        "outside_support_sdc_upper": outside,
        "total_sdc_upper": total,
        "worst_case_outside_probability_used": eta_used,
        "formula": "R_SDC,S + eta_upper*max(0, R_SDC,outside-R_SDC,S)",
        "exact_mixture_formula": "(1-eta)*R_SDC,S + eta*R_SDC,outside",
        "is_complete_bound": True,
    }


def audit_weight_bounded_streaming(
    code: Mapping[str, Any],
    policies: Mapping[str, Mapping[int, int]],
    *,
    maximum_weight: int,
    outside_probability_upper: float | None,
) -> dict[str, Any]:
    """Stream a large bounded-weight universe without materializing patterns."""

    n, k = int(code["n"]), int(code["k"])
    columns = matrix_columns_as_ints(code["H"])
    data_mask = (1 << k) - 1
    counts: dict[str, Counter[str]] = {name: Counter() for name in policies}
    by_weight: dict[str, dict[str, Counter[str]]] = {
        name: {str(weight): Counter() for weight in range(1, maximum_weight + 1)}
        for name in policies
    }
    total = 0
    for weight in range(1, maximum_weight + 1):
        for positions in itertools.combinations(range(n), weight):
            total += 1
            mask = sum(1 << position for position in positions)
            syndrome = 0
            for position in positions:
                syndrome ^= columns[position]
            for name, actions in policies.items():
                if syndrome == 0:
                    label = "correct" if mask & data_mask == 0 else "undetected"
                elif syndrome not in actions:
                    label = "due"
                else:
                    correction = int(actions[syndrome])
                    if syndrome_from_columns(correction, columns) != syndrome:
                        raise ValueError(f"policy {name!r} has an invalid correction syndrome")
                    label = "correct" if ((mask ^ correction) & data_mask) == 0 else "sdc_miscorrection"
                counts[name][label] += 1
                by_weight[name][str(weight)][label] += 1
    expected = sum(math.comb(n, weight) for weight in range(1, maximum_weight + 1))
    if total != expected:
        raise AssertionError("bounded-weight enumeration count mismatch")
    results = {}
    for name in policies:
        outcome = {key: int(counts[name][key]) for key in OUTCOME_KEYS}
        outcome["sdc_total"] = outcome["sdc_miscorrection"] + outcome["undetected"]
        within_distribution_free = 0.0 if outcome["sdc_total"] == 0 else 1.0
        results[name] = {
            "outcome_counts": outcome,
            "outcome_counts_by_weight": {
                weight: {
                    **{key: int(values[key]) for key in OUTCOME_KEYS},
                    "sdc_total": int(values["sdc_miscorrection"] + values["undetected"]),
                }
                for weight, values in by_weight[name].items()
            },
            "distribution_free_sdc_upper_within_enumerated_universe": within_distribution_free,
            "tail_bound": (
                complete_tail_bound(
                    within_distribution_free,
                    outside_probability_upper=float(outside_probability_upper),
                )
                if outside_probability_upper is not None
                else {
                    "status": "unbounded_without_eta_upper",
                    "symbolic_bound": "P_SDC,total <= (1-eta_gt4)*R_SDC,weight<=4 + eta_gt4",
                    "eta_gt4_upper": None,
                    "total_sdc_upper": 1.0,
                }
            ),
        }
    return {
        "bit_width": n,
        "maximum_enumerated_weight": int(maximum_weight),
        "pattern_count": total,
        "expected_pattern_count_formula": "+".join(
            f"C({n},{weight})" for weight in range(1, maximum_weight + 1)
        ),
        "tail_scope": f"all error vectors with weight>{maximum_weight}",
        "policies": results,
    }
