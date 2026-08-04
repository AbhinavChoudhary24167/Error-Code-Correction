"""Unit-consistent conversion between decoder risk and system SDC requirements.

The conversion is intentionally separate from fault-distribution ``raw_fit`` fields:
those fields have no usable exposure semantics unless a configuration declares a
rate basis explicitly.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


def _hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _finite_nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


def _positive(value: Any, name: str) -> float:
    result = _finite_nonnegative(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def target_sdc_rate_per_hour(target: Mapping[str, Any], *, mission_hours: float) -> dict[str, Any]:
    """Return the constant-hazard SDC-rate requirement in failures/hour."""

    kind = str(target["kind"])
    if kind == "system_sdc_fit":
        value = _finite_nonnegative(target["value"], "target.value")
        rate = value * 1.0e-9
        formula = "system_sdc_fit * 1e-9 hours^-1"
    elif kind == "failures_per_hour":
        rate = _finite_nonnegative(target["value"], "target.value")
        formula = "declared failures_per_hour"
    elif kind == "mission_sdc_probability":
        probability = float(target["value"])
        if not 0.0 <= probability < 1.0:
            raise ValueError("mission_sdc_probability must be in [0,1)")
        rate = -math.log1p(-probability) / _positive(mission_hours, "mission_hours")
        formula = "-log(1 - mission_sdc_probability) / mission_hours"
    else:
        raise ValueError(f"unsupported target kind {kind!r}")
    return {
        "kind": kind,
        "rate_upper_per_hour": rate,
        "system_sdc_fit": rate * 1.0e9,
        "formula": formula,
    }


def exposure_event_rate_per_hour(exposure: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve an upper confidence bound on relevant fault events per system-hour.

    Access and scrub rates are accepted only as *system-wide word decode
    opportunities*.  The caller must ensure they are disjoint; persistent faults
    must be represented by a first-detection hazard rather than counted at every
    later access.
    """

    kind = str(exposure["kind"])
    terms: dict[str, float] = {}
    if kind == "system_event_rate_per_hour":
        rate = _finite_nonnegative(exposure["event_rate_upper_per_hour"], "event_rate_upper_per_hour")
        formula = "declared system-wide event_rate_upper_per_hour"
    elif kind == "system_event_fit":
        terms["system_event_fit"] = _finite_nonnegative(exposure["event_fit_upper"], "event_fit_upper")
        rate = terms["system_event_fit"] * 1.0e-9
        formula = "system_event_fit * 1e-9 events/hour"
    elif kind == "per_word_event_rate_per_hour":
        terms["protected_words"] = _positive(exposure["protected_words"], "protected_words")
        terms["per_word_rate"] = _finite_nonnegative(
            exposure["event_rate_upper_per_word_hour"], "event_rate_upper_per_word_hour"
        )
        rate = terms["protected_words"] * terms["per_word_rate"]
        formula = "protected_words * event_rate_upper_per_word_hour"
    elif kind == "per_bit_event_rate_per_hour":
        terms["protected_words"] = _positive(exposure["protected_words"], "protected_words")
        terms["bits_per_word"] = _positive(exposure["bits_per_word"], "bits_per_word")
        terms["per_bit_rate"] = _finite_nonnegative(
            exposure["event_rate_upper_per_bit_hour"], "event_rate_upper_per_bit_hour"
        )
        rate = terms["protected_words"] * terms["bits_per_word"] * terms["per_bit_rate"]
        formula = "protected_words * bits_per_word * event_rate_upper_per_bit_hour"
    elif kind == "per_decode_opportunity":
        terms["accesses_per_hour"] = _finite_nonnegative(
            exposure.get("system_word_accesses_upper_per_hour", 0.0),
            "system_word_accesses_upper_per_hour",
        )
        terms["scrubs_per_hour"] = _finite_nonnegative(
            exposure.get("system_word_scrubs_upper_per_hour", 0.0),
            "system_word_scrubs_upper_per_hour",
        )
        terms["event_probability"] = float(exposure["event_probability_upper_per_opportunity"])
        if not 0.0 <= terms["event_probability"] <= 1.0:
            raise ValueError("event_probability_upper_per_opportunity must be in [0,1]")
        if not exposure.get("opportunities_are_disjoint", False):
            raise ValueError("per-decode exposure requires opportunities_are_disjoint=true")
        rate = (terms["accesses_per_hour"] + terms["scrubs_per_hour"]) * terms["event_probability"]
        formula = "(system word accesses/hour + scrubs/hour) * event probability/opportunity"
    else:
        raise ValueError(f"unsupported exposure kind {kind!r}")
    confidence = exposure.get("confidence")
    if confidence is None:
        confidence_status = "declared_upper_bound_without_statistical_confidence"
    else:
        level = float(confidence["level"])
        if not 0.0 < level < 1.0:
            raise ValueError("exposure confidence.level must be in (0,1)")
        confidence_status = "statistical_upper_confidence_bound"
    return {
        "kind": kind,
        "event_rate_upper_per_hour": rate,
        "event_fit_upper": rate * 1.0e9,
        "formula": formula,
        "terms": terms,
        "confidence": confidence,
        "confidence_status": confidence_status,
    }


def derive_system_sdc_budget(config: Mapping[str, Any]) -> dict[str, Any]:
    """Derive total and modeled-support conditional SDC budgets.

    If ``eta`` is the probability outside the modeled universe and ``b`` bounds
    conditional SDC in that tail, the total conditional risk is bounded by
    ``(1-eta) * r_support + eta * b``.  An absent tail bound is fail-closed.
    """

    mission_hours = _positive(config["mission_hours"], "mission_hours")
    target = target_sdc_rate_per_hour(config["target"], mission_hours=mission_hours)
    exposure = exposure_event_rate_per_hour(config["exposure"])
    event_rate = float(exposure["event_rate_upper_per_hour"])
    if event_rate == 0.0:
        total_budget = 1.0
    else:
        total_budget = min(1.0, float(target["rate_upper_per_hour"]) / event_rate)

    tail = dict(config.get("tail", {}))
    tail_status: str
    support_budget: float | None
    feasible: bool
    if "probability_upper" not in tail or "sdc_probability_upper" not in tail:
        eta = None
        tail_sdc = None
        support_budget = None
        feasible = False
        tail_status = "unbounded_tail_fail_closed"
    else:
        eta = float(tail["probability_upper"])
        tail_sdc = float(tail["sdc_probability_upper"])
        if not 0.0 <= eta <= 1.0:
            raise ValueError("tail.probability_upper must be in [0,1]")
        if not 0.0 <= tail_sdc <= 1.0:
            raise ValueError("tail.sdc_probability_upper must be in [0,1]")
        if eta == 1.0:
            support_budget = None
            feasible = tail_sdc <= total_budget
        else:
            numerator = total_budget - eta * tail_sdc
            support_budget = min(1.0, numerator / (1.0 - eta)) if numerator >= 0.0 else None
            feasible = support_budget is not None
        tail_status = (
            "bounded_with_statistical_confidence"
            if tail.get("confidence") is not None
            else "bounded_engineering_assumption"
        )

    document = {
        "schema_version": 1,
        "system_target_id": str(config.get("system_target_id", "anonymous-system-target")),
        "mission_hours": mission_hours,
        "target": target,
        "exposure": exposure,
        "conditional_sdc_budget_total": total_budget,
        "conditional_sdc_budget_modeled_support": support_budget,
        "tail": {
            "probability_upper": eta,
            "sdc_probability_upper": tail_sdc,
            "status": tail_status,
            "confidence": tail.get("confidence"),
            "formula": "p_total <= (1-eta)*p_support + eta*p_tail_upper",
        },
        "deployment_feasible_from_declared_bounds": feasible,
        "assumptions": list(config.get("assumptions", [])),
        "target_basis": config.get("target_basis"),
    }
    document["budget_sha256"] = _hash(document)
    return document


def project_system_sdc(
    budget: Mapping[str, Any], *, support_conditional_sdc: float
) -> dict[str, Any]:
    """Project a certified support risk through the declared tail and exposure."""

    risk = float(support_conditional_sdc)
    if not 0.0 <= risk <= 1.0:
        raise ValueError("support_conditional_sdc must be in [0,1]")
    tail = budget["tail"]
    eta = tail.get("probability_upper")
    tail_sdc = tail.get("sdc_probability_upper")
    if eta is None or tail_sdc is None:
        conditional_upper = 1.0
        status = "unbounded_tail_fail_closed"
    else:
        conditional_upper = (1.0 - float(eta)) * risk + float(eta) * float(tail_sdc)
        status = str(tail["status"])
    event_rate = float(budget["exposure"]["event_rate_upper_per_hour"])
    sdc_rate = event_rate * conditional_upper
    mission_hours = float(budget["mission_hours"])
    return {
        "support_conditional_sdc": risk,
        "total_conditional_sdc_upper": conditional_upper,
        "system_sdc_rate_upper_per_hour": sdc_rate,
        "system_sdc_fit_upper": sdc_rate * 1.0e9,
        "mission_sdc_probability_upper": -math.expm1(-sdc_rate * mission_hours),
        "tail_status": status,
        "meets_system_target": sdc_rate <= float(budget["target"]["rate_upper_per_hour"]) + 1e-24,
    }
