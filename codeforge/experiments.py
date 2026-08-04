"""Authoritative experiment identities for apples-to-apples ECC comparisons."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .faults import FaultDistribution


def _canonical_hash(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def distribution_fingerprint(distribution: FaultDistribution) -> dict[str, Any]:
    patterns = [
        {
            "pattern_id": pattern.pattern_id,
            "positions": list(pattern.positions),
            "family": pattern.family,
            "probability": float(pattern.probability),
            "metadata": dict(pattern.metadata),
        }
        for pattern in distribution.patterns
    ]
    universe = [
        {"positions": item["positions"], "family": item["family"], "metadata": item["metadata"]}
        for item in patterns
    ]
    pmf = [{"positions": item["positions"], "probability": item["probability"]} for item in patterns]
    return {
        "distribution_id": distribution.distribution_id,
        "bit_width": distribution.bit_width,
        "raw_fit": distribution.raw_fit,
        "normalization": "conditional_finite_error_universe_probability_mass_equals_one",
        "error_universe_sha256": _canonical_hash(universe),
        "pmf_sha256": _canonical_hash(pmf),
        "pattern_count": len(patterns),
    }


def make_experiment_identity(
    *,
    k: int,
    r: int,
    distribution: FaultDistribution,
    physical_bit_order: Sequence[int] | None = None,
    decoder_semantics: str = "execute_syndrome_action_then_compare_systematic_data_or_declare_due",
    outcome_definitions_version: int = 1,
    reliability_units: str = "conditional_probability_and_raw_fit_times_conditional_residual_mass",
    error_universe_document: Mapping[str, Any] | None = None,
    ambiguity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    n = int(k) + int(r)
    order = list(range(n)) if physical_bit_order is None else [int(value) for value in physical_bit_order]
    if sorted(order) != list(range(n)):
        raise ValueError("physical_bit_order must be a permutation of [0,n)")
    fingerprint = distribution_fingerprint(distribution)
    if fingerprint["bit_width"] != n:
        raise ValueError("distribution width does not match experiment dimensions")
    modeled_universe = (
        {
            "bit_width": int(error_universe_document["bit_width"]),
            "pattern_count": int(error_universe_document["pattern_count"]),
            "support_sha256": str(error_universe_document["support_sha256"]),
        }
        if error_universe_document is not None
        else {
            "bit_width": fingerprint["bit_width"],
            "pattern_count": fingerprint["pattern_count"],
            "support_sha256": fingerprint["error_universe_sha256"],
        }
    )
    ambiguity_identity = None
    if ambiguity is not None:
        ambiguity_identity = {
            "ambiguity_id": ambiguity.get("ambiguity_id"),
            "type": ambiguity["type"],
            "radius": float(ambiguity.get("radius", 0.0)),
            "configuration_sha256": _canonical_hash(dict(ambiguity)),
        }
    basis = {
        "identity_version": 1,
        "dimensions": {"k": int(k), "r": int(r), "n": n},
        "fault_distribution": fingerprint,
        "modeled_error_universe": modeled_universe,
        "ambiguity": ambiguity_identity,
        "physical_bit_order": order,
        "decoder_semantics": decoder_semantics,
        "outcome_definitions_version": int(outcome_definitions_version),
        "normalization": fingerprint["normalization"],
        "reliability_units": reliability_units,
    }
    return {**basis, "experiment_id": _canonical_hash(basis)[:20]}


def attach_experiment_identity(record: Mapping[str, Any], identity: Mapping[str, Any]) -> dict[str, Any]:
    return {**dict(record), "experiment_identity": dict(identity), "experiment_id": identity["experiment_id"]}


def matrix_identifier(code: Mapping[str, Any]) -> str:
    """Content identifier for the algebraic matrix, independent of its label."""

    basis = {
        "k": int(code["k"]),
        "r": int(code["r"]),
        "n": int(code["n"]),
        "H": code["H"],
        "G": code["G"],
    }
    return "matrix-" + _canonical_hash(basis)[:20]


def decoder_policy_identifier(actions: Mapping[int, int], *, syndrome_bits: int) -> str:
    basis = {
        "syndrome_bits": int(syndrome_bits),
        "actions": [
            {"syndrome": int(syndrome), "correction_mask": int(mask)}
            for syndrome, mask in sorted(actions.items())
        ],
        "missing_nonzero_syndrome_semantics": "abstain_due",
    }
    return "policy-" + _canonical_hash(basis)[:20]


def metric_context(
    *,
    experiment_identity: Mapping[str, Any],
    code: Mapping[str, Any],
    actions: Mapping[int, int],
    pmf_id: str,
    ambiguity: Mapping[str, Any],
    error_universe_id: str,
    metric_scope: str,
    physical_mapping: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Construct the mandatory context attached to every hardened-study metric."""

    if metric_scope not in {"nominal", "held_out", "worst_case"}:
        raise ValueError("metric_scope must be nominal, held_out, or worst_case")
    n = int(code["n"])
    mapping = list(range(n)) if physical_mapping is None else [int(value) for value in physical_mapping]
    if sorted(mapping) != list(range(n)):
        raise ValueError("physical_mapping must be a permutation of [0,n)")
    return {
        "experiment_id": str(experiment_identity["experiment_id"]),
        "matrix_id": matrix_identifier(code),
        "decoder_policy_id": decoder_policy_identifier(actions, syndrome_bits=int(code["r"])),
        "pmf_id": str(pmf_id),
        "ambiguity_set_type": str(ambiguity["type"]),
        "ambiguity_radius": float(ambiguity.get("radius", 0.0)),
        "error_pattern_universe": str(error_universe_id),
        "parity_budget": int(code["r"]),
        "physical_mapping": mapping,
        "metric_scope": metric_scope,
    }


def validate_metric_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    """Reject incomplete, mixed-identity, or mixed-scope metric rows."""

    if not rows:
        raise ValueError("at least one metric row is required")
    required = {
        "experiment_id",
        "matrix_id",
        "decoder_policy_id",
        "pmf_id",
        "ambiguity_set_type",
        "ambiguity_radius",
        "error_pattern_universe",
        "parity_budget",
        "physical_mapping",
        "metric_scope",
        "metrics",
    }
    for index, row in enumerate(rows):
        missing = sorted(required - set(row))
        if missing:
            raise ValueError(f"metric row {index} missing context fields: {missing}")
        scope = str(row["metric_scope"])
        metrics = dict(row["metrics"])
        if scope in {"nominal", "held_out"}:
            expected = {"corrected", "due", "sdc"}
            if not expected <= set(metrics):
                raise ValueError(f"{scope} metric row {index} lacks a probability partition")
            total = sum(float(metrics[key]) for key in expected)
            if not abs(total - 1.0) <= 1e-10:
                raise ValueError(f"{scope} metric row {index} does not sum to one")
        elif scope == "worst_case":
            if "corrected" in metrics:
                raise ValueError(
                    "worst_case rows must not mix nominal/held-out correction with separate risk maxima"
                )
            if not {"due", "sdc"} <= set(metrics):
                raise ValueError("worst_case rows require due and sdc bounds")
            adversarial_ids = dict(row.get("adversarial_pmf_ids", {}))
            if not {"due", "sdc"} <= set(adversarial_ids):
                raise ValueError(
                    "worst_case rows require separate adversarial PMF IDs for due and sdc"
                )
        else:
            raise ValueError(f"unknown metric scope {scope!r}")
    identifiers = {str(row["experiment_id"]) for row in rows}
    if len(identifiers) != 1:
        raise ValueError(f"mismatched experiment identities in metric rows: {sorted(identifiers)}")
    return next(iter(identifiers))


def metric_rows_table(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    experiment_id = validate_metric_rows(rows)
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "validation": "passed",
        "row_semantics": (
            "nominal and held-out rows are probability partitions; worst-case SDC and DUE "
            "are separately maximized bounds with separate adversarial PMF IDs and are not "
            "presented as a partition"
        ),
        "rows": [dict(row) for row in rows],
    }


def assert_comparable(records: Sequence[Mapping[str, Any]]) -> str:
    if not records:
        raise ValueError("at least one comparison record is required")
    missing = [index for index, record in enumerate(records) if "experiment_id" not in record]
    if missing:
        raise ValueError(f"comparison records missing experiment_id at indexes {missing}")
    identifiers = {str(record["experiment_id"]) for record in records}
    if len(identifiers) != 1:
        details = [
            {
                "strategy_id": record.get("strategy_id"),
                "experiment_id": record.get("experiment_id"),
            }
            for record in records
        ]
        raise ValueError(f"mismatched experiment identities: {details}")
    return next(iter(identifiers))


def comparison_table(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    experiment_id = assert_comparable(records)
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "comparability_assertion": "passed",
        "candidate_count": len(records),
        "records": [dict(record) for record in records],
    }
