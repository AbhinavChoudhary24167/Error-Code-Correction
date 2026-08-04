"""Fair multi-dimensional comparison and physical-evidence selection."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping

from .backends import CharacterizationStore
from .hashing import canonical_hash
from .registry import EccRegistry


PHYSICAL_EVIDENCE = {"physical_characterized", "post_route", "post_synthesis_characterized"}


def build_comparison_views(store: CharacterizationStore) -> dict[str, Any]:
    registry = store.registry
    views: dict[str, Callable[[Mapping[str, Any]], object]] = {
        "equal_data_width": lambda row: row["k"],
        "equal_codeword_width": lambda row: row["n"],
        "equal_redundancy": lambda row: row["redundancy"],
        "equal_guaranteed_reliability": lambda row: _reliability_identity(registry, str(row["code_id"])),
        "equal_timing_target": lambda row: canonical_hash(row["timing_constraints"]),
        "equal_area_budget": lambda row: None,
        "equal_workload": lambda row: row["workload_id"],
        "same_code_different_implementations": lambda row: row["code_id"],
        "same_implementation_across_corners": lambda row: row["implementation_id"],
        "same_code_across_deployment_architectures": lambda row: row["code_id"],
    }
    output: dict[str, Any] = {}
    for view, key_fn in views.items():
        groups: dict[str, list[str]] = defaultdict(list)
        for row in store.results:
            key = key_fn(row)
            groups[json.dumps(key, sort_keys=True)].append(str(row["result_id"]))
        output[view] = {
            "groups": [
                {"comparison_key": json.loads(key), "result_ids": sorted(ids), "candidate_count": len(ids)}
                for key, ids in sorted(groups.items())
            ],
            "fairness_rule": _fairness_rule(view),
        }
    return output


def select_physical(
    store: CharacterizationStore,
    scenario: Mapping[str, Any],
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    objective = str(scenario.get("objective", "encoder_energy"))
    direction = str(scenario.get("direction", "min"))
    if direction not in {"min", "max"}:
        raise ValueError("scenario direction must be min or max")
    basis = str(scenario.get("comparison_basis", "equal_data_width"))
    views = build_comparison_views(store)
    if basis not in views:
        raise ValueError(f"unknown comparison_basis: {basis}")
    _require_basis_parameter(basis, scenario)
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in store.results:
        reasons: list[str] = []
        if row["evidence_level"] not in PHYSICAL_EVIDENCE:
            reasons.append("not physical characterization")
        if row.get(objective) is None:
            reasons.append(f"objective {objective} is unsupported")
        required_k = scenario.get("k")
        if required_k is not None and int(row["k"]) != int(required_k):
            reasons.append("data width differs")
        required_workload = scenario.get("workload_id")
        if required_workload is not None and row["workload_id"] != required_workload:
            reasons.append("workload differs")
        reasons.extend(_basis_reasons(row, basis, scenario, store.registry))
        if reasons:
            rejected.append({"result_id": row["result_id"], "reasons": reasons})
        else:
            candidates.append(row)
    winner = None
    if candidates:
        chosen = (min if direction == "min" else max)(candidates, key=lambda row: float(row[objective]))
        winner = {
            "result_id": chosen["result_id"],
            "objective": objective,
            "value": chosen[objective],
            "dimensions": {
                "code": chosen["code_id"],
                "implementation": chosen["implementation_id"],
                "architecture": chosen["architecture_id"],
                "technology_corner": {
                    "backend": chosen["backend_id"], "technology": chosen["technology"],
                    "library": chosen["library"], "corner": chosen["corner"],
                    "voltage": chosen["voltage"], "temperature": chosen["temperature"],
                },
                "workload": chosen["workload_id"],
            },
        }
    proxy_winner = scenario.get("proxy_winner")
    report: dict[str, Any] = {
        "schema_version": 1,
        "comparison_basis": basis,
        "objective": objective,
        "direction": direction,
        "candidate_count": len(candidates),
        "rejected": rejected,
        "winner": winner,
        "proxy_winner": proxy_winner,
        "proxy_to_physical_winner_changed": (
            None if winner is None or proxy_winner is None else proxy_winner != winner["dimensions"]["implementation"]
        ),
        "comparison_views": views,
        "scientific_interpretation": (
            "No physical winner is available; structural-only and unavailable backends are excluded."
            if winner is None else "Winner is conditional on all five recorded dimensions and the declared fairness basis."
        ),
    }
    report["selection_sha256"] = canonical_hash(report)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _reliability_identity(registry: EccRegistry, code_id: str) -> str:
    code = registry.code(code_id)
    return canonical_hash(
        {
            "correction": code["guaranteed_correction_set"],
            "detection": code["guaranteed_detection_set"],
            "unsupported": code["unsupported_error_classes"],
        }
    )


def _require_basis_parameter(basis: str, scenario: Mapping[str, Any]) -> None:
    required = {
        "equal_data_width": "k",
        "equal_codeword_width": "n",
        "equal_redundancy": "redundancy",
        "equal_guaranteed_reliability": "guaranteed_reliability_identity",
        "equal_timing_target": "timing_constraints",
        "equal_area_budget": "area_budget",
        "equal_workload": "workload_id",
        "same_code_different_implementations": "code_id",
        "same_implementation_across_corners": "implementation_id",
        "same_code_across_deployment_architectures": "code_id",
    }[basis]
    if required not in scenario:
        raise ValueError(f"comparison basis {basis} requires scenario field {required}")


def _basis_reasons(
    row: Mapping[str, Any], basis: str, scenario: Mapping[str, Any], registry: EccRegistry
) -> list[str]:
    reasons: list[str] = []
    if basis == "equal_codeword_width" and int(row["n"]) != int(scenario["n"]):
        reasons.append("codeword width differs")
    elif basis == "equal_redundancy" and int(row["redundancy"]) != int(scenario["redundancy"]):
        reasons.append("redundancy differs")
    elif basis == "equal_guaranteed_reliability":
        identity = _reliability_identity(registry, str(row["code_id"]))
        if identity != scenario["guaranteed_reliability_identity"]:
            reasons.append("guaranteed reliability differs")
    elif basis == "equal_timing_target" and canonical_hash(row["timing_constraints"]) != canonical_hash(scenario["timing_constraints"]):
        reasons.append("timing target differs")
    elif basis == "equal_area_budget":
        area = row["routed_area"] if row["routed_area"] is not None else row["cell_area"]
        if area is None:
            reasons.append("area budget cannot be checked without characterized area")
        elif float(area) > float(scenario["area_budget"]):
            reasons.append("area budget exceeded")
    elif basis == "same_code_different_implementations" and row["code_id"] != scenario["code_id"]:
        reasons.append("code differs")
    elif basis == "same_implementation_across_corners" and row["implementation_id"] != scenario["implementation_id"]:
        reasons.append("implementation differs")
    elif basis == "same_code_across_deployment_architectures" and row["code_id"] != scenario["code_id"]:
        reasons.append("code differs")
    return reasons


def _fairness_rule(view: str) -> str:
    return {
        "equal_data_width": "compare only identical k",
        "equal_codeword_width": "compare only identical n",
        "equal_redundancy": "compare only identical n-k",
        "equal_guaranteed_reliability": "compare only identical declared guaranteed correction/detection domains",
        "equal_timing_target": "compare only identical timing-constraint identities",
        "equal_area_budget": "requires an explicit scenario area budget and non-null characterized area",
        "equal_workload": "compare only identical workload/activity identities",
        "same_code_different_implementations": "hold code_id fixed and vary implementation_id",
        "same_implementation_across_corners": "hold implementation_id fixed and vary backend/corner",
        "same_code_across_deployment_architectures": "hold code_id fixed and vary architecture_id",
    }[view]
