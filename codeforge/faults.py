"""Versioned finite error-pattern probability distributions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .gf2 import positions_to_mask


@dataclass(frozen=True)
class ErrorPattern:
    pattern_id: str
    positions: tuple[int, ...]
    probability: float
    family: str
    metadata: Mapping[str, Any]

    def mask(self, n: int) -> int:
        return positions_to_mask(self.positions, n)


@dataclass(frozen=True)
class FaultDistribution:
    distribution_id: str
    bit_width: int
    patterns: tuple[ErrorPattern, ...]
    provenance: Mapping[str, Any]
    raw_fit: float | None
    schema_version: int = 1

    @property
    def probability_sum(self) -> float:
        return math.fsum(pattern.probability for pattern in self.patterns)

    def by_id(self) -> dict[str, ErrorPattern]:
        return {pattern.pattern_id: pattern for pattern in self.patterns}


def _schema_path(repo_root: Path) -> Path:
    return repo_root / "schemas" / "fault-distribution.schema.json"


def load_fault_distribution(path: str | Path, *, repo_root: str | Path) -> FaultDistribution:
    source = Path(path)
    if not source.is_absolute():
        source = Path(repo_root) / source
    payload = json.loads(source.read_text(encoding="utf-8"))
    schema = json.loads(_schema_path(Path(repo_root)).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    patterns = tuple(
        ErrorPattern(
            pattern_id=str(item["pattern_id"]),
            positions=tuple(int(position) for position in item["positions"]),
            probability=float(item["probability"]),
            family=str(item["family"]),
            metadata=dict(item.get("metadata", {})),
        )
        for item in payload["patterns"]
    )
    distribution = FaultDistribution(
        distribution_id=str(payload["distribution_id"]),
        bit_width=int(payload["bit_width"]),
        patterns=patterns,
        provenance=dict(payload["provenance"]),
        raw_fit=float(payload["raw_fit"]) if payload.get("raw_fit") is not None else None,
        schema_version=int(payload["schema_version"]),
    )
    _validate_distribution(distribution)
    return distribution


def _validate_distribution(distribution: FaultDistribution) -> None:
    if distribution.bit_width <= 0:
        raise ValueError("fault distribution bit_width must be positive")
    identifiers: set[str] = set()
    masks: set[int] = set()
    for pattern in distribution.patterns:
        if pattern.pattern_id in identifiers:
            raise ValueError(f"duplicate pattern_id {pattern.pattern_id!r}")
        identifiers.add(pattern.pattern_id)
        mask = pattern.mask(distribution.bit_width)
        if mask == 0:
            raise ValueError(f"pattern {pattern.pattern_id!r} must contain at least one flipped bit")
        if mask in masks:
            raise ValueError(f"duplicate error vector for pattern {pattern.pattern_id!r}")
        masks.add(mask)
        if not math.isfinite(pattern.probability) or pattern.probability < 0:
            raise ValueError(f"pattern {pattern.pattern_id!r} has invalid probability")
    if not math.isclose(distribution.probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(
            f"fault distribution probabilities sum to {distribution.probability_sum:.17g}, expected 1"
        )
    kind = str(distribution.provenance.get("kind", ""))
    if kind not in {"measured", "fitted", "projected", "synthetic"}:
        raise ValueError("fault distribution provenance.kind must be measured, fitted, projected, or synthetic")


def distribution_to_document(distribution: FaultDistribution) -> dict[str, Any]:
    return {
        "schema_version": distribution.schema_version,
        "distribution_id": distribution.distribution_id,
        "bit_width": distribution.bit_width,
        "raw_fit": distribution.raw_fit,
        "provenance": dict(distribution.provenance),
        "normalization": {
            "probability_sum": distribution.probability_sum,
            "tolerance": 1e-12,
            "valid": math.isclose(distribution.probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-12),
        },
        "patterns": [
            {
                "pattern_id": pattern.pattern_id,
                "positions": list(pattern.positions),
                "probability": pattern.probability,
                "family": pattern.family,
                "metadata": dict(pattern.metadata),
            }
            for pattern in distribution.patterns
        ],
    }
