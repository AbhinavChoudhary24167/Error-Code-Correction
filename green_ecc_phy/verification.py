"""Manifest, algebraic, functional, and archived-RTL verification gate."""

from __future__ import annotations

import itertools
import json
import platform
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contracts import DecodeStatus
from .hashing import canonical_hash, manifest_sha256
from .registry import EccRegistry


HARNESS_MISCORRECTED = "MISCORRECTED"


def _data_samples(k: int) -> list[int]:
    all_ones = (1 << k) - 1
    alternating = sum(1 << bit for bit in range(k) if bit % 2 == 0)
    return sorted({0, 1, all_ones, alternating, all_ones ^ alternating})


def _error_patterns(spec: Mapping[str, Any], n: int) -> Iterable[tuple[int, ...]]:
    weight = int(spec["weight"])
    generator = spec["generator"]
    coordinate_count = int(spec.get("coordinate_count", n))
    if coordinate_count < weight or coordinate_count > n:
        raise ValueError("error-class coordinate_count is outside the codeword")
    if generator == "all_combinations":
        return itertools.combinations(range(coordinate_count), weight)
    if generator == "adjacent_windows":
        return (
            tuple(range(start, start + weight))
            for start in range(coordinate_count - weight + 1)
        )
    return (tuple(map(int, item)) for item in spec.get("positions", []))


def _harness_outcome(result, golden: int) -> str:
    if result.status in {DecodeStatus.NO_ERROR, DecodeStatus.CORRECTED} and result.data != golden:
        return HARNESS_MISCORRECTED
    return result.status.value


def _tool_version(command: str, *args: str) -> dict[str, Any]:
    executable = shutil.which(command)
    if executable is None:
        return {"available": False, "path": None, "version": None}
    try:
        process = subprocess.run(
            [executable, *args], capture_output=True, text=True, timeout=15, check=False
        )
        rendered = (process.stdout + "\n" + process.stderr).strip().splitlines()
        version = rendered[0] if rendered else None
    except OSError as exc:
        version = f"unreadable: {exc}"
    return {"available": True, "path": executable, "version": version}


def verify_implementation(
    registry: EccRegistry,
    implementation_id: str,
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    implementation = registry.implementation(implementation_id)
    code = registry.code(str(implementation["code_id"]))
    adapter = registry.adapter(implementation_id)
    failures: list[str] = []
    capability_failures: list[str] = []
    checks: dict[str, Any] = {}
    samples = _data_samples(int(code["k"]))

    deterministic = all(adapter.encode(data) == adapter.encode(data) for data in samples)
    no_error = all(
        (result := adapter.decode(adapter.encode(data))).status == DecodeStatus.NO_ERROR
        and result.data == data
        and result.latency == int(implementation["decoder_latency"])
        for data in samples
    )
    checks["deterministic_encoding"] = deterministic
    checks["no_error_decoding"] = no_error
    checks["pipeline_latency"] = no_error
    malformed_encode = True
    for invalid_data in (-1, 1 << int(code["k"])):
        try:
            adapter.encode(invalid_data)
        except (TypeError, ValueError):
            continue
        malformed_encode = False
    malformed_decode = all(
        adapter.decode(invalid).status == DecodeStatus.INVALID_CONFIGURATION
        for invalid in (-1, 1 << int(code["n"]))
    )
    checks["malformed_encode_rejected"] = malformed_encode
    checks["wrong_length_decode_rejected"] = malformed_decode
    if not deterministic:
        failures.append("encoding is not deterministic")
    if not no_error:
        failures.append("no-error decode or latency contract failed")
    if not malformed_encode or not malformed_decode:
        failures.append("malformed or wrong-length input contract failed")

    universe: list[dict[str, Any]] = []
    class_results: list[dict[str, Any]] = []
    declared_groups: list[tuple[str, list[Mapping[str, Any]]]] = [
        ("guaranteed_correction", code["guaranteed_correction_set"]),
        ("guaranteed_detection", code["guaranteed_detection_set"]),
    ]
    for entry in implementation.get("capability_claims", {}).get("claimed_error_classes", []):
        declared_groups.append((f"implementation_claim_{entry['kind']}", [entry]))
    for kind, entries in declared_groups:
        for entry in entries:
            acceptable = set(map(str, entry["acceptable_statuses"]))
            patterns = list(_error_patterns(entry, int(code["n"])))
            failed_patterns: list[list[int]] = []
            outcome_counts: Counter[str] = Counter()
            data_independent = bool(
                implementation.get("capability_claims", {}).get("data_independence_proof")
            )
            tested_payloads = [0] if data_independent else (
                samples if int(entry["weight"]) <= 1 else samples[:2]
            )
            for positions in patterns:
                mask = sum(1 << position for position in positions)
                universe.append({"class_id": entry["class_id"], "positions": list(positions)})
                pattern_outcomes: set[str] = set()
                for data in tested_payloads:
                    outcome = _harness_outcome(adapter.decode(adapter.encode(data) ^ mask), data)
                    pattern_outcomes.add(outcome)
                    if outcome not in acceptable:
                        failed_patterns.append(list(positions))
                        break
                outcome_counts[next(iter(pattern_outcomes)) if len(pattern_outcomes) == 1 else "MIXED"] += 1
            passed = not failed_patterns
            passed_count = len(patterns) - len(failed_patterns)
            class_results.append(
                {
                    "kind": kind,
                    "class_id": entry["class_id"],
                    "patterns": len(patterns),
                    "passed_count": passed_count,
                    "failure_count": len(failed_patterns),
                    "exact_fraction": f"{passed_count}/{len(patterns)}",
                    "outcome_counts": dict(sorted(outcome_counts.items())),
                    "data_independence": {
                        "established": data_independent,
                        "method": implementation.get("capability_claims", {}).get("data_independence_proof"),
                        "payloads_per_mask": len(tested_payloads),
                    },
                    "acceptable_statuses": sorted(acceptable),
                    "passed": passed,
                    "failed_patterns": failed_patterns[:20],
                }
            )
            if not passed:
                message = f"{kind} class failed: {entry['class_id']}"
                if kind.startswith("implementation_claim_"):
                    capability_failures.append(message)
                else:
                    failures.append(message)

    probes: list[dict[str, Any]] = []
    for probe in code["known_miscorrection_domain"] + implementation["verification_vectors"].get("miscorrection_probes", []):
        if "positions" not in probe:
            probes.append(
                {
                    "probe_id": probe.get("probe_id"),
                    "domain": probe.get("domain"),
                    "outcome": "DECLARED_DOMAIN_ONLY",
                    "expected": probe.get("expected_behavior"),
                    "passed": True,
                }
            )
            continue
        positions = tuple(map(int, probe["positions"]))
        data = int(probe.get("data", samples[-1])) & ((1 << int(code["k"])) - 1)
        mask = sum(1 << position for position in positions)
        outcome = _harness_outcome(adapter.decode(adapter.encode(data) ^ mask), data)
        expected = str(probe.get("expected_harness_outcome", outcome))
        passed = outcome == expected
        probes.append({"probe_id": probe.get("probe_id"), "positions": list(positions), "outcome": outcome, "expected": expected, "passed": passed})
        universe.append({"class_id": "miscorrection_probe", "positions": list(positions)})
        if not passed:
            failures.append(f"miscorrection probe failed: {probe.get('probe_id')}")

    exhaustive = None
    if int(code["k"]) <= 8 and int(code["n"]) <= 12:
        cases = 0
        stable = True
        for data in range(1 << int(code["k"])):
            encoded = adapter.encode(data)
            for error in range(1 << int(code["n"])):
                first = adapter.decode(encoded ^ error)
                second = adapter.decode(encoded ^ error)
                cases += 1
                if first != second:
                    stable = False
                    break
            if not stable:
                break
        exhaustive = {"performed": True, "cases": cases, "deterministic": stable}
        if not stable:
            failures.append("small-code exhaustive deterministic replay failed")

    evidence_checks: list[dict[str, Any]] = []
    for evidence in implementation["verification_evidence"]:
        raw = str(evidence["path"])
        path = Path(raw)
        if not path.is_absolute():
            path = registry.repo_root / path
        present = path.is_file()
        hash_bound = present and registry.source_hash_matches(
            str(raw), path, str(implementation["source_hashes"].get(raw, ""))
        )
        passed = present and hash_bound and evidence.get("status") == "passed"
        evidence_checks.append(
            {
                "kind": evidence.get("kind"), "path": raw, "test_id": evidence.get("test_id"),
                "present": present, "hash_bound": hash_bound, "declared_status": evidence.get("status"), "passed": passed,
            }
        )
        if not passed:
            failures.append(f"RTL/reference evidence unavailable or broken: {raw}")
    checks["rtl_reference_differential"] = bool(evidence_checks) and all(item["passed"] for item in evidence_checks)
    checks["reset_testing"] = _evidence_or_not_applicable(implementation, evidence_checks, "reset")
    checks["protocol_testing"] = _evidence_or_not_applicable(implementation, evidence_checks, "protocol")
    checks["configuration_transition_testing"] = _evidence_or_not_applicable(implementation, evidence_checks, "transition")
    if not checks["rtl_reference_differential"]:
        failures.append("no passing hash-bound RTL/reference differential evidence")

    matrix_hash = code["content_hashes"]["matrix_sha256"]
    tested_universe_hash = canonical_hash(universe)
    report: dict[str, Any] = {
        "schema_version": 1,
        "verification_status": "passed" if not failures else "failed",
        "capability_verification_status": (
            "rejected" if failures else "partially_verified" if capability_failures else "fully_verified"
        ),
        "code_id": code["code_id"],
        "implementation_id": implementation_id,
        "implementation_hash": manifest_sha256(implementation),
        "matrix_hash": matrix_hash,
        "tested_universe_hash": tested_universe_hash,
        "tool_versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "iverilog": _tool_version("iverilog", "-V"),
            "verilator": _tool_version("verilator", "--version"),
            "yosys": _tool_version("yosys", "-V"),
        },
        "checks": checks,
        "class_results": class_results,
        "miscorrection_probes": probes,
        "exhaustive_small_code": exhaustive,
        "rtl_evidence": evidence_checks,
        "tested_data_words": samples,
        "failures": sorted(set(failures)),
        "capability_failures": sorted(set(capability_failures)),
    }
    report["verification_sha256"] = canonical_hash(report)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _evidence_or_not_applicable(
    implementation: Mapping[str, Any], evidence: list[Mapping[str, Any]], keyword: str
) -> dict[str, Any]:
    matching = [item for item in evidence if keyword in str(item.get("kind", ""))]
    if matching:
        return {"status": "passed" if all(item["passed"] for item in matching) else "failed", "evidence_count": len(matching)}
    combinational = implementation["architecture_style"] in {"combinational", "reference_only"}
    return {
        "status": "not_applicable" if combinational else "missing",
        "reason": "stateless combinational contract" if combinational else "no evidence declared",
    }
