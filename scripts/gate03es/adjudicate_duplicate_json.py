#!/usr/bin/env python3
"""Read-only ordered-occurrence adjudication for Gate 03E-S JSON logs.

The frozen v3 comparator remains unchanged.  This tool reads the preserved run
artifacts without rewriting them and reports every JSON leaf occurrence, so a
producer that repeats an object key cannot hide an earlier scientific value
behind the JSON parser's usual last-value-wins behaviour.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXACT_UNIT_DECLARATIONS = {
    "run__flow__platform__capacitance_units",
    "run__flow__platform__current_units",
    "run__flow__platform__distance_units",
    "run__flow__platform__power_units",
    "run__flow__platform__resistance_units",
    "run__flow__platform__time_units",
    "run__flow__platform__voltage_units",
}


class OrderedObject(list[tuple[str, Any]]):
    """A JSON object represented as its original ordered key/value pairs."""


@dataclass(frozen=True)
class Leaf:
    occurrence_path: str
    schema_path: str
    direct_occurrence: int
    value: Any
    duplicate: bool


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_ordered(path: Path) -> OrderedObject:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedObject)
    if not isinstance(value, OrderedObject):
        raise ValueError(f"{path}: top-level JSON value is not an object")
    return value


def flatten(value: Any) -> list[Leaf]:
    leaves: list[Leaf] = []

    def visit(
        item: Any,
        occurrence_parts: list[str],
        schema_parts: list[str],
        inherited_duplicate: bool,
        direct_occurrence: int,
    ) -> None:
        if isinstance(item, OrderedObject):
            totals = Counter(key for key, _ in item)
            seen: Counter[str] = Counter()
            for key, child in item:
                seen[key] += 1
                child_duplicate = totals[key] > 1
                visit(
                    child,
                    [*occurrence_parts, f"{key}#{seen[key]}"],
                    [*schema_parts, key],
                    inherited_duplicate or child_duplicate,
                    seen[key],
                )
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(
                    child,
                    [*occurrence_parts, f"[{index}]"],
                    [*schema_parts, f"[{index}]"],
                    inherited_duplicate,
                    direct_occurrence,
                )
            return
        leaves.append(
            Leaf(
                occurrence_path=".".join(occurrence_parts).replace(".[", "["),
                schema_path=".".join(schema_parts).replace(".[", "["),
                direct_occurrence=direct_occurrence,
                value=item,
                duplicate=inherited_duplicate,
            )
        )

    visit(value, [], [], False, 1)
    return leaves


def compare_value(left: Any, right: Any, tolerance: float) -> tuple[bool, float | None]:
    numeric = (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    )
    if numeric:
        delta = abs(float(left) - float(right))
        return math.isfinite(delta) and delta <= tolerance, delta
    return left == right, None


def adjudicate(run_5: Path, run_6: Path, schema_path: Path) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    rules = {(row["artifact"], row["path"]): row for row in schema["metrics"]}
    left_paths = {path.relative_to(run_5).as_posix() for path in run_5.glob("logs/**/*.json")}
    right_paths = {path.relative_to(run_6).as_posix() for path in run_6.glob("logs/**/*.json")}
    shared = sorted(left_paths & right_paths)
    missing = sorted(left_paths - right_paths)
    additional = sorted(right_paths - left_paths)

    rows: list[dict[str, Any]] = []
    structural_failures: list[str] = []
    inputs: list[dict[str, Any]] = []
    for artifact in shared:
        left_path, right_path = run_5 / artifact, run_6 / artifact
        inputs.append(
            {
                "artifact": artifact,
                "run_5_sha256": sha256(left_path),
                "run_6_sha256": sha256(right_path),
            }
        )
        left = {leaf.occurrence_path: leaf for leaf in flatten(read_ordered(left_path))}
        right = {leaf.occurrence_path: leaf for leaf in flatten(read_ordered(right_path))}
        for identity in sorted(set(left) | set(right)):
            left_leaf, right_leaf = left.get(identity), right.get(identity)
            leaf = left_leaf or right_leaf
            assert leaf is not None
            rule = rules.get((artifact, leaf.schema_path))
            if rule is None and leaf.schema_path in EXACT_UNIT_DECLARATIONS:
                rule = {
                    "classification": "SCIENTIFIC_EXACT",
                    "gating": True,
                    "absolute_tolerance": 0.0,
                }
            present = left_leaf is not None and right_leaf is not None
            classification = rule["classification"] if rule else "UNRESOLVED"
            gating = bool(rule["gating"]) if rule else True
            tolerance = float(rule["absolute_tolerance"] or 0.0) if rule else 0.0
            if present:
                equal, delta = compare_value(left_leaf.value, right_leaf.value, 0.0)
                scientific_pass, _ = compare_value(left_leaf.value, right_leaf.value, tolerance)
            else:
                equal, delta, scientific_pass = False, None, False
                structural_failures.append(f"{artifact}:{identity}: occurrence missing from one run")
            passed = present and rule is not None and (not gating or scientific_pass)
            rows.append(
                {
                    "artifact": artifact,
                    "occurrence_path": identity,
                    "schema_path": leaf.schema_path,
                    "occurrence": leaf.direct_occurrence,
                    "duplicate_key_occurrence": bool(
                        (left_leaf and left_leaf.duplicate) or (right_leaf and right_leaf.duplicate)
                    ),
                    "run_5": left_leaf.value if left_leaf else None,
                    "run_6": right_leaf.value if right_leaf else None,
                    "exactly_equal": equal,
                    "absolute_delta": delta,
                    "classification": classification,
                    "gating": gating,
                    "absolute_tolerance": tolerance if gating else None,
                    "pass": passed,
                }
            )

    duplicate_rows = [row for row in rows if row["duplicate_key_occurrence"]]
    differing_rows = [row for row in rows if not row["exactly_equal"]]
    scientific_rows = [row for row in rows if row["gating"] and row["classification"] != "UNRESOLVED"]
    scientific_failures = [row for row in scientific_rows if not row["pass"]]
    unresolved = [row for row in rows if row["classification"] == "UNRESOLVED"]
    runtime_differences = [row for row in differing_rows if not row["gating"]]
    nonruntime_differences = [row for row in differing_rows if row["gating"]]
    duplicate_scientific_failures = [row for row in duplicate_rows if row["gating"] and not row["pass"]]

    passed = not (
        missing
        or additional
        or structural_failures
        or scientific_failures
        or unresolved
        or nonruntime_differences
    )
    return {
        "schema_version": 1,
        "adjudication": "gate03es-ordered-json-occurrences",
        "read_only_source_evidence": True,
        "run_5_root": str(run_5),
        "run_6_root": str(run_6),
        "metric_schema_sha256": sha256(schema_path),
        "input_hashes": inputs,
        "missing_from_run_6": missing,
        "additional_in_run_6": additional,
        "structural_failures": structural_failures,
        "summary": {
            "shared_json_artifacts": len(shared),
            "leaf_occurrence_comparisons": len(rows),
            "duplicate_key_occurrence_comparisons": len(duplicate_rows),
            "duplicate_scientific_occurrence_comparisons": sum(row["gating"] for row in duplicate_rows),
            "duplicate_scientific_failures": len(duplicate_scientific_failures),
            "scientific_occurrence_comparisons": len(scientific_rows),
            "scientific_failures": len(scientific_failures),
            "differing_occurrences": len(differing_rows),
            "runtime_resource_differing_occurrences": len(runtime_differences),
            "scientific_or_unresolved_differing_occurrences": len(nonruntime_differences),
            "unresolved_occurrences": len(unresolved),
            "pass": passed,
        },
        "unresolved_occurrences": unresolved,
        "duplicate_key_occurrences": duplicate_rows,
        "differing_occurrences": differing_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-5", type=Path, required=True)
    parser.add_argument("--run-6", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = adjudicate(args.run_5.resolve(), args.run_6.resolve(), args.schema.resolve())
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if result["summary"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
