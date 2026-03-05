"""Explainability helpers for ML-assisted ECC decisions."""

from __future__ import annotations

from typing import Any


def top_feature_importances(bundle: dict[str, Any], top_k: int = 5) -> list[tuple[str, float]]:
    """Return top global feature importances from the classifier model."""

    clf = bundle.get("classifier")
    if clf is None:
        return []

    model = clf.named_steps.get("model")
    preprocess = clf.named_steps.get("preprocess")
    if not hasattr(model, "feature_importances_") or preprocess is None:
        return []

    names = list(preprocess.get_feature_names_out())
    vals = list(getattr(model, "feature_importances_", []))
    pairs = sorted(zip(names, vals), key=lambda t: t[1], reverse=True)
    return [(name, float(val)) for name, val in pairs[:top_k]]


def format_decision_explanation(
    *,
    baseline_code: str,
    ml_code: str,
    confidence: float,
    fallback_reason: str | None,
    hard_constraints_ok: bool,
) -> str:
    """Build a compact explanation string for CLI output."""

    lines: list[str] = []
    lines.append(f"baseline={baseline_code}")
    lines.append(f"ml={ml_code} (confidence={confidence:.3f})")
    lines.append(f"hard_constraints_ok={hard_constraints_ok}")
    if fallback_reason:
        lines.append(f"fallback={fallback_reason}")
    else:
        lines.append("fallback=none")
    return "; ".join(lines)
