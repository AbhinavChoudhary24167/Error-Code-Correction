#!/usr/bin/env python3
"""Freeze, hash, canonicalize, and compare the two Gate-03E ORFS runs."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import struct
from pathlib import Path, PurePosixPath
from typing import Any


TEXT_SUFFIXES = {
    ".csv", ".def", ".json", ".lef", ".lib", ".log", ".manifest",
    ".mk", ".rpt", ".sdc", ".spef", ".tcl", ".txt", ".v", ".yaml", ".yml",
}
GDS_ELEMENT_STARTS = {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x15, 0x2D}
GDS_BGNLIB = 0x01
GDS_BGNSTR = 0x05
GDS_ENDSTR = 0x07
GDS_ENDEL = 0x11
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    for rule in policy["canonicalization"]["recognized_metadata_substitutions"]:
        re.compile(rule["pattern"])
    for pattern in policy["canonicalization"]["json_metadata_key_patterns"]:
        re.compile(pattern)
    for pattern in policy["metric_rules"]["exact_path_patterns"]:
        re.compile(pattern)
    for rule in policy["metric_rules"]["tolerance_path_patterns"]:
        re.compile(rule["pattern"])
    return policy


def is_metadata_key(key: str, policy: dict[str, Any]) -> bool:
    return any(
        re.search(pattern, key)
        for pattern in policy["canonicalization"]["json_metadata_key_patterns"]
    )


def normalize_text(text: str, policy: dict[str, Any]) -> tuple[str, list[str]]:
    applied: list[str] = []
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized != text:
        applied.append("line_endings")
    stripped = re.sub(r"[ \t]+$", "", normalized, flags=re.MULTILINE)
    if stripped != normalized:
        applied.append("trailing_horizontal_whitespace")
    normalized = stripped
    for run_root in policy["run_roots"]:
        if run_root in normalized:
            normalized = normalized.replace(run_root, policy["run_root_token"])
            if "absolute_run_root" not in applied:
                applied.append("absolute_run_root")
    for rule in policy["canonicalization"]["recognized_metadata_substitutions"]:
        normalized, count = re.subn(rule["pattern"], rule["replacement"], normalized)
        if count:
            applied.append(rule["name"])
    return normalized, applied


def normalize_json_value(value: Any, policy: dict[str, Any], applied: set[str]) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key in sorted(value):
            if is_metadata_key(key, policy):
                result[key] = "<METADATA>"
                applied.add(f"json_metadata_key:{key.lower()}")
            else:
                result[key] = normalize_json_value(value[key], policy, applied)
        return result
    if isinstance(value, list):
        return [normalize_json_value(item, policy, applied) for item in value]
    if isinstance(value, str):
        normalized, actions = normalize_text(value, policy)
        applied.update(actions)
        return normalized
    return value


def parse_gds_records(data: bytes) -> list[tuple[int, bytes]]:
    records: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError(f"truncated GDS record header at byte {offset}")
        length, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if length < 4 or length % 2 or offset + length > len(data):
            raise ValueError(f"invalid GDS record length {length} at byte {offset}")
        raw = data[offset : offset + length]
        if record_type in {GDS_BGNLIB, GDS_BGNSTR}:
            raw = raw[:4] + bytes(length - 4)
        records.append((record_type, raw))
        offset += length
    return records


def canonicalize_structure(records: list[tuple[int, bytes]]) -> bytes:
    if not records or records[0][0] != GDS_BGNSTR or records[-1][0] != GDS_ENDSTR:
        raise ValueError("malformed GDS structure boundaries")
    header: list[bytes] = []
    elements: list[bytes] = []
    index = 0
    while index < len(records) - 1 and records[index][0] not in GDS_ELEMENT_STARTS:
        header.append(records[index][1])
        index += 1
    while index < len(records) - 1:
        if records[index][0] not in GDS_ELEMENT_STARTS:
            raise ValueError(
                f"unrecognized inter-element GDS record type 0x{records[index][0]:02x}"
            )
        element: list[bytes] = []
        while index < len(records) - 1:
            element.append(records[index][1])
            record_type = records[index][0]
            index += 1
            if record_type == GDS_ENDEL:
                break
        else:
            raise ValueError("GDS element lacks ENDEL")
        if not element or records[index - 1][0] != GDS_ENDEL:
            raise ValueError("GDS element lacks ENDEL")
        elements.append(b"".join(element))
    return b"".join(header) + b"".join(sorted(elements)) + records[-1][1]


def canonicalize_gds(data: bytes) -> bytes:
    records = parse_gds_records(data)
    prefix: list[bytes] = []
    structures: list[bytes] = []
    suffix: list[bytes] = []
    index = 0
    seen_structure = False
    while index < len(records):
        if records[index][0] == GDS_BGNSTR:
            seen_structure = True
            structure: list[tuple[int, bytes]] = []
            while index < len(records):
                structure.append(records[index])
                record_type = records[index][0]
                index += 1
                if record_type == GDS_ENDSTR:
                    break
            else:
                raise ValueError("GDS structure lacks ENDSTR")
            structures.append(canonicalize_structure(structure))
        else:
            (suffix if seen_structure else prefix).append(records[index][1])
            index += 1
    return b"".join(prefix) + b"".join(sorted(structures)) + b"".join(suffix)


def canonicalize_file(path: Path, policy: dict[str, Any]) -> tuple[bytes, list[str]]:
    raw = path.read_bytes()
    if path.suffix.lower() == ".gds":
        canonical = canonicalize_gds(raw)
        return canonical, ["gds_bgnlib_bgnstr_dates_and_order"] if canonical != raw else []
    if path.suffix.lower() == ".json":
        value = json.loads(raw.decode("utf-8"))
        applied: set[str] = set()
        normalized = normalize_json_value(value, policy, applied)
        canonical = (json.dumps(normalized, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if canonical != raw:
            applied.add("json_object_key_order_and_encoding")
        return canonical, sorted(applied)
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"metrics", "metadata"}:
        normalized, applied = normalize_text(raw.decode("utf-8", errors="strict"), policy)
        return normalized.encode("utf-8"), applied
    return raw, []


def make_inventory(root: Path, policy_path: Path, run_label: str) -> dict[str, Any]:
    policy = read_policy(policy_path)
    root = root.resolve()
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raw = os.readlink(path).encode("utf-8")
            canonical = raw
            applied: list[str] = []
            kind = "symlink"
        elif path.is_file():
            raw = path.read_bytes()
            canonical, applied = canonicalize_file(path, policy)
            kind = "file"
        else:
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "kind": kind,
                "size_bytes": len(raw),
                "raw_sha256": sha256_bytes(raw),
                "canonical_sha256": sha256_bytes(canonical),
                "normalizations_applied": applied,
            }
        )
    return {
        "schema_version": 1,
        "run_label": run_label,
        "run_root": root.as_posix(),
        "policy_sha256": sha256_bytes(policy_path.read_bytes()),
        "artifact_count": len(entries),
        "artifacts": entries,
    }


def metric_rule(path: str, policy: dict[str, Any]) -> dict[str, Any]:
    for pattern in policy["metric_rules"]["exact_path_patterns"]:
        if re.search(pattern, path):
            return {"classification": "exact_invariant", "absolute_tolerance": 0.0}
    for rule in policy["metric_rules"]["tolerance_path_patterns"]:
        if re.search(rule["pattern"], path):
            return rule
    return {"classification": "unclassified_numeric_exact", "absolute_tolerance": 0.0}


def compare_json_metrics(
    left: Any,
    right: Any,
    path: str,
    policy: dict[str, Any],
    checks: list[dict[str, Any]],
) -> list[str]:
    issues: list[str] = []
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return [f"{path}: JSON keys differ"]
        for key in sorted(left):
            child = f"{path}.{key}" if path else key
            if is_metadata_key(key, policy):
                continue
            issues.extend(compare_json_metrics(left[key], right[key], child, policy, checks))
        return issues
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [f"{path}: JSON list lengths differ"]
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            issues.extend(
                compare_json_metrics(left_item, right_item, f"{path}[{index}]", policy, checks)
            )
        return issues
    if isinstance(left, bool) or isinstance(right, bool):
        if left != right:
            issues.append(f"{path}: boolean/status differs ({left!r} != {right!r})")
        return issues
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        rule = metric_rule(path, policy)
        delta = abs(float(left) - float(right))
        passed = delta <= float(rule["absolute_tolerance"])
        checks.append(
            {
                "path": path,
                "run_1": left,
                "run_2": right,
                "absolute_delta": delta,
                "classification": rule["classification"],
                "absolute_tolerance": rule["absolute_tolerance"],
                "pass": passed,
            }
        )
        if not passed:
            issues.append(f"{path}: delta {delta} exceeds {rule['absolute_tolerance']}")
        return issues
    if left != right:
        issues.append(f"{path}: value differs ({left!r} != {right!r})")
    return issues


def compare_text_with_tolerances(
    left: str, right: str, relative: str, policy: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]], str]:
    left_lines = left.splitlines()
    right_lines = right.splitlines()
    if len(left_lines) != len(right_lines):
        return False, [], "canonical line counts differ"
    checks: list[dict[str, Any]] = []
    for line_number, (left_line, right_line) in enumerate(zip(left_lines, right_lines), 1):
        if left_line == right_line:
            continue
        left_numbers = NUMBER_RE.findall(left_line)
        right_numbers = NUMBER_RE.findall(right_line)
        if (
            len(left_numbers) != len(right_numbers)
            or NUMBER_RE.sub("<NUMBER>", left_line) != NUMBER_RE.sub("<NUMBER>", right_line)
        ):
            return False, checks, f"line {line_number} has a nonnumeric canonical difference"
        context = f"{relative}:line-{line_number}:{NUMBER_RE.sub('', left_line)}"
        rule = metric_rule(context, policy)
        for index, (left_number, right_number) in enumerate(zip(left_numbers, right_numbers)):
            delta = abs(float(left_number) - float(right_number))
            passed = delta <= float(rule["absolute_tolerance"])
            checks.append(
                {
                    "path": f"{relative}:line-{line_number}:number-{index}",
                    "run_1": left_number,
                    "run_2": right_number,
                    "absolute_delta": delta,
                    "classification": rule["classification"],
                    "absolute_tolerance": rule["absolute_tolerance"],
                    "pass": passed,
                }
            )
            if not passed:
                return False, checks, f"line {line_number} has a tolerance breach"
    return True, checks, "all canonical differences are within frozen numeric tolerances"


def is_semantic_artifact(path: str, policy: dict[str, Any]) -> bool:
    candidate = PurePosixPath(path)
    return any(
        candidate.match(pattern)
        for pattern in policy["semantic_artifacts"]["required_exact_canonical_globs"]
    )


def compare_runs(
    run_1_manifest: Path,
    run_2_manifest: Path,
    policy_path: Path,
) -> dict[str, Any]:
    policy = read_policy(policy_path)
    first = json.loads(run_1_manifest.read_text(encoding="utf-8"))
    second = json.loads(run_2_manifest.read_text(encoding="utf-8"))
    expected_policy_hash = sha256_bytes(policy_path.read_bytes())
    if first["policy_sha256"] != expected_policy_hash or second["policy_sha256"] != expected_policy_hash:
        raise ValueError("run inventory policy hash does not match frozen policy")
    first_by_path = {item["path"]: item for item in first["artifacts"]}
    second_by_path = {item["path"]: item for item in second["artifacts"]}
    shared = sorted(set(first_by_path) & set(second_by_path))
    missing = sorted(set(first_by_path) - set(second_by_path))
    additional = sorted(set(second_by_path) - set(first_by_path))
    root_1 = Path(first["run_root"])
    root_2 = Path(second["run_root"])
    raw_differences: list[dict[str, Any]] = []
    metric_checks: list[dict[str, Any]] = []
    failures: list[str] = []
    for relative in shared:
        left = first_by_path[relative]
        right = second_by_path[relative]
        if left["raw_sha256"] == right["raw_sha256"]:
            continue
        row: dict[str, Any] = {
            "path": relative,
            "run_1_raw_sha256": left["raw_sha256"],
            "run_2_raw_sha256": right["raw_sha256"],
            "run_1_canonical_sha256": left["canonical_sha256"],
            "run_2_canonical_sha256": right["canonical_sha256"],
        }
        if left["canonical_sha256"] == right["canonical_sha256"]:
            actions = sorted(
                set(left["normalizations_applied"]) | set(right["normalizations_applied"])
            )
            row.update(
                {
                    "classification": "predeclared_metadata_or_ordering",
                    "explanation": ", ".join(actions) or "canonical encodings are identical",
                    "pass": True,
                }
            )
        elif is_semantic_artifact(relative, policy):
            row.update(
                {
                    "classification": "semantic_canonical_mismatch",
                    "explanation": "required semantic artifact canonical hashes differ",
                    "pass": False,
                }
            )
            failures.append(f"{relative}: semantic canonical hash mismatch")
        elif Path(relative).suffix.lower() == ".json":
            left_json = json.loads((root_1 / relative).read_text(encoding="utf-8"))
            right_json = json.loads((root_2 / relative).read_text(encoding="utf-8"))
            local_checks: list[dict[str, Any]] = []
            issues = compare_json_metrics(left_json, right_json, relative, policy, local_checks)
            metric_checks.extend(local_checks)
            row.update(
                {
                    "classification": "predeclared_metric_rules" if not issues else "unexplained_or_tolerance_breach",
                    "explanation": "; ".join(issues) if issues else "all JSON differences satisfy frozen metadata/exact/tolerance rules",
                    "pass": not issues,
                }
            )
            failures.extend(issues)
        elif (root_1 / relative).suffix.lower() in TEXT_SUFFIXES:
            left_text, _ = normalize_text((root_1 / relative).read_text(encoding="utf-8"), policy)
            right_text, _ = normalize_text((root_2 / relative).read_text(encoding="utf-8"), policy)
            passed, local_checks, explanation = compare_text_with_tolerances(
                left_text, right_text, relative, policy
            )
            metric_checks.extend(local_checks)
            row.update(
                {
                    "classification": "predeclared_metric_rules" if passed else "unexplained_or_tolerance_breach",
                    "explanation": explanation,
                    "pass": passed,
                }
            )
            if not passed:
                failures.append(f"{relative}: {explanation}")
        else:
            row.update(
                {
                    "classification": "unexplained_binary_difference",
                    "explanation": "no predeclared canonical or tolerance rule explains this binary difference",
                    "pass": False,
                }
            )
            failures.append(f"{relative}: unexplained binary difference")
        raw_differences.append(row)

    # Record numeric exact/tolerance checks even when the containing JSON bytes match.
    for relative in shared:
        if Path(relative).suffix.lower() != ".json":
            continue
        left_json = json.loads((root_1 / relative).read_text(encoding="utf-8"))
        right_json = json.loads((root_2 / relative).read_text(encoding="utf-8"))
        checks: list[dict[str, Any]] = []
        issues = compare_json_metrics(left_json, right_json, relative, policy, checks)
        metric_checks.extend(checks)
        failures.extend(issue for issue in issues if issue not in failures)

    if missing:
        failures.append(f"{len(missing)} artifacts are missing from run 2")
    if additional:
        failures.append(f"{len(additional)} artifacts are additional in run 2")
    unexplained = [row for row in raw_differences if not row["pass"]]
    semantic_matches = [
        {
            "path": relative,
            "run_1_canonical_sha256": first_by_path[relative]["canonical_sha256"],
            "run_2_canonical_sha256": second_by_path[relative]["canonical_sha256"],
            "pass": first_by_path[relative]["canonical_sha256"]
            == second_by_path[relative]["canonical_sha256"],
        }
        for relative in shared
        if is_semantic_artifact(relative, policy)
    ]
    if not semantic_matches:
        failures.append("no required semantic artifacts were found")
    return {
        "schema_version": 1,
        "policy_sha256": expected_policy_hash,
        "reproducibility_pass": not failures,
        "artifact_counts": {
            "run_1": len(first_by_path),
            "run_2": len(second_by_path),
            "raw_hash_differences": len(raw_differences),
            "unexplained_raw_hash_differences": len(unexplained),
        },
        "missing_from_run_2": missing,
        "additional_in_run_2": additional,
        "raw_hash_differences": raw_differences,
        "semantic_artifact_comparisons": semantic_matches,
        "metric_comparisons": metric_checks,
        "failures": failures,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze_bundle(policy_path: Path, implementation: Path, destination: Path) -> None:
    if destination.exists():
        raise SystemExit(f"freeze destination already exists: {destination}")
    destination.mkdir(parents=True)
    frozen_policy = destination / policy_path.name
    frozen_implementation = destination / implementation.name
    shutil.copyfile(policy_path, frozen_policy)
    shutil.copyfile(implementation, frozen_implementation)
    hashes = {
        frozen_policy.name: sha256_bytes(frozen_policy.read_bytes()),
        frozen_implementation.name: sha256_bytes(frozen_implementation.read_bytes()),
    }
    write_json(destination / "frozen-bundle.json", {"schema_version": 1, "files": hashes})
    (destination / "frozen-bundle.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items())),
        encoding="ascii",
    )
    read_policy(frozen_policy)
    print(json.dumps(hashes, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--policy", type=Path, required=True)
    freeze.add_argument("--implementation", type=Path, required=True)
    freeze.add_argument("--destination", type=Path, required=True)
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--root", type=Path, required=True)
    inventory.add_argument("--policy", type=Path, required=True)
    inventory.add_argument("--run-label", required=True)
    inventory.add_argument("--output", type=Path, required=True)
    compare = subparsers.add_parser("compare")
    compare.add_argument("--run-1", type=Path, required=True)
    compare.add_argument("--run-2", type=Path, required=True)
    compare.add_argument("--policy", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze_bundle(args.policy, args.implementation, args.destination)
        return 0
    if args.command == "inventory":
        result = make_inventory(args.root, args.policy, args.run_label)
        write_json(args.output, result)
        print(json.dumps({"artifact_count": result["artifact_count"]}, sort_keys=True))
        return 0
    result = compare_runs(args.run_1, args.run_2, args.policy)
    write_json(args.output, result)
    print(json.dumps(result["artifact_counts"], sort_keys=True))
    return 0 if result["reproducibility_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
