"""SRAM-specific advisory ML helpers.

This module keeps deterministic SRAM selection as the primary decision path and
reuses the shared ML prediction/gating utilities for optional advisory output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ml.predict import predict_with_model, resolve_thresholds


_ML_POLICIES = {"carbon_min", "fit_min", "energy_min", "utility_balanced"}


def _scheme_from_code(code: str) -> str:
    parts = str(code).split("-")
    if len(parts) >= 3 and parts[0] == "sram":
        return parts[1]
    return "unknown"


def build_sram_feature_row(
    candidate: Mapping[str, object],
    *,
    size_kb: int,
    word_bits: int,
    fault_model: str,
    iterations: int,
) -> dict[str, object]:
    """Build an SRAM-aware feature row from selector candidate/scenario fields."""

    fit_val = float(candidate.get("FIT", 0.0))
    return {
        # Core selector-compatible features.
        "code": str(candidate.get("code", "")),
        "node": candidate.get("node"),
        "vdd": candidate.get("vdd"),
        "temp": candidate.get("temp"),
        "capacity_gib": candidate.get("capacity_gib"),
        "ci": candidate.get("ci"),
        "bitcell_um2": candidate.get("bitcell_um2"),
        "scrub_s": candidate.get("scrub_s"),
        "latency_ns": candidate.get("latency_ns"),
        "area_logic_mm2": candidate.get("area_logic_mm2"),
        "area_macro_mm2": candidate.get("area_macro_mm2"),
        # SRAM-specific advisory context.
        "size_kb": int(size_kb),
        "word_bits": int(word_bits),
        "scheme": _scheme_from_code(str(candidate.get("code", ""))),
        "fault_model": str(fault_model),
        "iterations": int(iterations),
        "redundancy_overhead_pct": candidate.get("redundancy_overhead_pct"),
        "reliability_success": max(0.0, 1.0 - fit_val * 1e-9),
        "sdc_rate": fit_val * 1e-12,
        "correction_rate": candidate.get("correction_rate", 0.0),
        "detection_rate": candidate.get("detection_rate", 0.0),
        "energy_proxy": candidate.get("E_scrub_kWh"),
        "latency_proxy": candidate.get("latency_ns"),
        "utility": candidate.get("NESII"),
    }


def _pick_advisory_candidate(
    entries: list[dict[str, object]],
    policy: str,
) -> dict[str, object]:
    if not entries:
        raise ValueError("No eligible advisory entries")

    policy_norm = str(policy).strip().lower()
    if policy_norm == "fit_min":
        return min(entries, key=lambda e: float(e["prediction"]["predictions"].get("FIT", float("inf"))))
    if policy_norm == "energy_min":
        return min(entries, key=lambda e: float(e["prediction"]["predictions"].get("energy_kWh", float("inf"))))
    if policy_norm == "utility_balanced":
        fits = [float(e["prediction"]["predictions"].get("FIT", float("inf"))) for e in entries]
        carbons = [float(e["prediction"]["predictions"].get("carbon_kg", float("inf"))) for e in entries]
        energies = [float(e["prediction"]["predictions"].get("energy_kWh", float("inf"))) for e in entries]

        def _norm(vals: list[float], value: float) -> float:
            lo = min(vals)
            hi = max(vals)
            if hi <= lo:
                return 0.0
            return (value - lo) / (hi - lo)

        return min(
            entries,
            key=lambda e: (
                _norm(fits, float(e["prediction"]["predictions"].get("FIT", float("inf"))))
                + _norm(carbons, float(e["prediction"]["predictions"].get("carbon_kg", float("inf"))))
                + _norm(energies, float(e["prediction"]["predictions"].get("energy_kWh", float("inf")))),
            ),
        )

    return min(entries, key=lambda e: float(e["prediction"]["predictions"].get("carbon_kg", float("inf"))))


def run_sram_advisory(
    *,
    model_dir: Path,
    candidates: list[dict[str, object]],
    baseline_choice: str | None,
    size_kb: int,
    word_bits: int,
    fault_model: str = "adjacent",
    iterations: int = 1,
    confidence_min_override: float | None = None,
    ood_threshold_override: float | None = None,
    policy_override: str | None = None,
) -> dict[str, object]:
    """Evaluate SRAM candidates with shared ML gating and return advisory metadata."""

    resolved_thresholds = resolve_thresholds(
        {},
        model_dir=model_dir,
        confidence_min_override=confidence_min_override,
        ood_threshold_override=ood_threshold_override,
        policy_override=policy_override,
    )
    policy = str(resolved_thresholds.get("ml_policy", "carbon_min"))
    if policy not in _ML_POLICIES:
        policy = "carbon_min"

    eligible: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []

    for rec in candidates:
        row = build_sram_feature_row(
            rec,
            size_kb=size_kb,
            word_bits=word_bits,
            fault_model=fault_model,
            iterations=iterations,
        )
        pred = predict_with_model(
            model_dir,
            row,
            confidence_min_override=confidence_min_override,
            ood_threshold_override=ood_threshold_override,
            policy_override=policy_override,
        )
        diag = {
            "code": rec.get("code"),
            "confidence": float(pred.get("confidence", 0.0)),
            "ood_score": float(pred.get("ood_score", 0.0)),
        }
        if bool(pred.get("ood", False)) or bool(pred.get("low_confidence", False)):
            rejected.append(diag)
        else:
            eligible.append({"record": rec, "prediction": pred, "diag": diag})

    advisory_choice = None
    advisory_prediction = None
    if eligible:
        picked = _pick_advisory_candidate(eligible, policy)
        advisory_choice = str(picked["record"].get("code"))
        advisory_prediction = picked["prediction"]

    fallback_used = advisory_prediction is None
    final_choice_reason = "deterministic_baseline_primary"
    if fallback_used:
        final_choice_reason = "ml_rejected_fallback_to_deterministic_baseline"
    elif advisory_choice != baseline_choice:
        final_choice_reason = "deterministic_baseline_primary_ml_advisory_only"

    return {
        "ml_requested": True,
        "ml_used": advisory_prediction is not None,
        "fallback_used": fallback_used,
        "baseline_choice": baseline_choice,
        "advisory_choice": advisory_choice,
        "advisory_confidence": (
            float(advisory_prediction.get("confidence", 0.0)) if advisory_prediction else None
        ),
        "advisory_ood_score": (
            float(advisory_prediction.get("ood_score", 0.0)) if advisory_prediction else None
        ),
        "advisory_policy": policy,
        "final_choice": baseline_choice,
        "final_choice_reason": final_choice_reason,
        "advisory_rejected_candidates": rejected,
    }

