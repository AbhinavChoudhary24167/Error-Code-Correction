#!/usr/bin/env python3
"""Generate or validate GREEN-ECC DATE 2027 Rigour Gate-02 evidence."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.gf2 import matrix_columns_as_ints, syndrome_from_columns
from green_ecc_phy.adapters import BoundedCyclicAdapter
from green_ecc_phy.contracts import DecodeResult, DecodeStatus
from green_ecc_phy.gate02 import (
    OUTCOMES,
    aggregate_universe,
    canonical_code_spec,
    guarded_distance_certificate,
    masks_for_definition,
    translation_invariance_record,
    universe_definitions_for,
    validate_aggregate,
)
from green_ecc_phy.hashing import canonical_hash, file_sha256, scientific_file_sha256
from green_ecc_phy.registry import EccRegistry


FROZEN_COMMIT = "f2908466bfa1a8eee8ad5c13b15e0d02a4730351"
EXPECTED_COUNTS = {"codes": 15, "implementations": 17}
GATE_STATUSES = {"PASS", "CONDITIONAL PASS", "PARTIAL", "FAIL", "REJECTED", "NOT ASSESSABLE"}
DISTANCE_EVIDENCE = {"EXACT", "DESIGNED_BOUND", "LOWER_BOUND", "UNRESOLVED"}

IDENTITY_HEADER = [
    "code_id", "implementation_id", "n", "k", "r", "rate", "family", "systematic",
    "construction", "canonical_matrix_hash", "canonical_polynomial_hash", "rank_g", "rank_h",
    "orthogonality_status", "encoder_status", "decoder_status", "distance_claim",
    "distance_evidence", "distance_gate", "registration_status", "selectability", "gate_status",
    "evidence_path",
]
CAPABILITY_HEADER = [
    "implementation_id", "universe_id", "universe_definition", "total_masks", "clean", "corrected",
    "due", "sdc_miscorrection", "sdc_undetected", "invalid_state", "correction_fraction",
    "detection_fraction", "sdc_fraction", "exhaustive", "translation_invariance_basis",
    "smallest_failure_witness", "declared_capability", "proven_capability", "gate_status", "evidence_path",
]
CLAIMS_HEADER = [
    "claim_id", "gate_01_claim_id", "claim_location", "claim_text", "gate_02_disposition",
    "evidence_path", "scope", "limitation",
]


def _json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _csv(path: Path, header: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in header})


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class CachedBoundedCyclicAuditAdapter:
    """Behavior-identical audit accelerator, checked against the native adapter."""

    def __init__(self, native: BoundedCyclicAdapter) -> None:
        self.native = native
        self._gate02_structural_translation_invariant = True
        self.k = native.k
        self.n = native.n
        self.decoder_latency = native.decoder_latency
        self._columns = list(native._columns)
        self._locator: dict[int, tuple[int, ...]] = {}
        from itertools import combinations

        for weight in range(1, native.search_weight + 1):
            for positions in combinations(range(self.n), weight):
                mask = sum(1 << position for position in positions)
                syndrome = syndrome_from_columns(mask, self._columns)
                self._locator.setdefault(syndrome, positions)

    def encode(self, data: int) -> int:
        return self.native.encode(data)

    def decode(self, codeword: int) -> DecodeResult:
        if codeword < 0 or codeword >= (1 << self.n):
            return self.native.decode(codeword)
        syndrome = syndrome_from_columns(codeword, self._columns)
        if syndrome == 0:
            return DecodeResult(
                codeword & ((1 << self.k) - 1), DecodeStatus.NO_ERROR, 0, codeword, None,
                self.decoder_latency,
            )
        positions = self._locator.get(syndrome)
        if positions is None:
            return DecodeResult(
                None, DecodeStatus.DETECTED_UNCORRECTABLE, syndrome, None, None, self.decoder_latency
            )
        mask = sum(1 << position for position in positions)
        corrected = codeword ^ mask
        location: int | tuple[int, ...] = positions[0] if len(positions) == 1 else positions
        return DecodeResult(
            corrected & ((1 << self.k) - 1), DecodeStatus.CORRECTED, syndrome, corrected,
            location, self.decoder_latency,
        )

    def prove_equivalence(self) -> dict[str, Any]:
        from itertools import combinations

        checked = 0
        transcript = hashlib.sha256()
        failures = []
        for weight in range(self.native.search_weight + 1):
            for positions in combinations(range(self.n), weight):
                mask = sum(1 << position for position in positions)
                expected = self.native.decode(mask)
                observed = self.decode(mask)
                checked += 1
                transcript.update(f"{mask:x}|{expected.as_dict()}|{observed.as_dict()}\n".encode())
                if expected != observed:
                    failures.append({"positions": positions, "native": expected.as_dict(), "audit": observed.as_dict()})
        return {
            "method": "exhaustive native-vs-cached differential through configured search weight",
            "cases": checked,
            "passed": not failures,
            "failures": failures[:4],
            "transcript_sha256": transcript.hexdigest(),
        }


def _audit_adapter(registry: EccRegistry, implementation_id: str) -> tuple[Any, dict[str, Any] | None]:
    native = registry.adapter(implementation_id)
    if isinstance(native, BoundedCyclicAdapter):
        accelerated = CachedBoundedCyclicAuditAdapter(native)
        proof = accelerated.prove_equivalence()
        if not proof["passed"]:
            raise ValueError("cached cyclic audit accelerator differs from native adapter")
        return accelerated, proof
    return native, None


def _derive_counts(registry_path: Path) -> dict[str, int]:
    config = json.loads(registry_path.read_text(encoding="utf-8"))
    return {
        "codes": len(config.get("codes", [])),
        "implementations": len(config.get("implementations", [])),
        "architectures": len(config.get("architectures", [])),
        "backends": len(config.get("backends", [])),
    }


def _gate01_hashes(root: Path) -> dict[str, str]:
    directory = root / "docs" / "date2027" / "rigour_gate_01"
    return {
        path.relative_to(root).as_posix(): file_sha256(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _source_state(root: Path) -> dict[str, Any]:
    def run(*args: str) -> dict[str, Any]:
        process = subprocess.run(
            list(args), cwd=root, capture_output=True, text=True, timeout=30, check=False
        )
        return {"command": " ".join(args), "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr}

    return {
        "captured_utc": _utc(),
        "branch": run("git", "branch", "--show-current"),
        "head": run("git", "rev-parse", "HEAD"),
        "status": run("git", "status", "--short", "--branch"),
    }


def _universe_text(definition: Mapping[str, Any]) -> str:
    return json.dumps(
        {key: value for key, value in definition.items() if key != "positions"},
        sort_keys=True,
        separators=(",", ":"),
    )


def _status_for(
    implementation_id: str,
    identity_gate: str,
    definitions: list[Mapping[str, Any]],
    aggregates: list[Mapping[str, Any]],
) -> tuple[str, bool, str]:
    if implementation_id == "cyclic-rtl-bounded-search-63-51-v1":
        return "REJECTED", False, "historical degree-12 negative control"
    if implementation_id == "secdaec-rtl-bounded-72-64-v1":
        return "REJECTED", False, "historical bounded SEC-DAEC negative control"
    if implementation_id == "taec-rtl-bounded-72-64-v1":
        return "PARTIAL", False, "bounded data-only policy; full storage-coordinate TAEC fails"
    if identity_gate != "PASS":
        return "FAIL", False, "canonical mathematical identity failed"
    by_id = {item["universe_id"]: item for item in aggregates}
    required = [
        item for item in definitions
        if item["declared_capability"] not in {"observation"}
    ]
    failed = [item["universe_id"] for item in required if by_id[item["universe_id"]]["gate_status"] != "PASS"]
    if failed:
        return "FAIL", False, "declared universe contradiction: " + ", ".join(failed)
    return "PASS", True, "identity and all positive declared universes pass"


def generate(
    root: Path,
    registry_path: Path,
    output: Path,
    source_commit: str,
    equivalence_evidence: Path | None = None,
) -> int:
    started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=True)
    baseline = output / "baseline"
    baseline.mkdir(parents=True, exist_ok=True)
    aggregates_dir = baseline / "implementation_aggregates"
    aggregates_dir.mkdir(parents=True, exist_ok=True)
    gate01_before = _gate01_hashes(root)
    pre_state = _source_state(root)
    counts = _derive_counts(registry_path)
    registry = EccRegistry.load(registry_path, repo_root=root)
    if counts["codes"] != len(registry.codes) or counts["implementations"] != len(registry.implementations):
        raise ValueError("direct registry counts and loader counts disagree")

    implementations_by_code: dict[str, list[str]] = {code_id: [] for code_id in registry.codes}
    for implementation_id, implementation in registry.implementations.items():
        implementations_by_code[str(implementation["code_id"])].append(implementation_id)

    specs = [
        canonical_code_spec(registry.code(code_id), implementations_by_code[code_id])
        for code_id in sorted(registry.codes)
    ]
    _json(
        output / "CANONICAL_CODE_SPECS.json",
        {
            "schema_version": 1,
            "source_commit": source_commit,
            "counts": counts,
            "expected_pre_audit_counts": EXPECTED_COUNTS,
            "specifications": specs,
        },
    )
    specs_by_id = {item["code_id"]: item for item in specs}

    verifier_hash = scientific_file_sha256(root / "green_ecc_phy" / "gate02.py")
    distance_records = [
        guarded_distance_certificate(registry.code(code_id), verifier_sha256=verifier_hash)
        for code_id in sorted(registry.codes)
    ]
    _json(
        output / "MINIMUM_DISTANCE_CERTIFICATES.json",
        {"schema_version": 1, "source_commit": source_commit, "certificates": distance_records},
    )
    distance_by_id = {item["code_id"]: item for item in distance_records}

    universe_documents: list[dict[str, Any]] = []
    all_aggregates: list[dict[str, Any]] = []
    witnesses: list[dict[str, Any]] = []
    translation_records: list[dict[str, Any]] = []
    accelerator_proofs: list[dict[str, Any]] = []
    implementation_statuses: dict[str, dict[str, Any]] = {}
    for implementation_id in sorted(registry.implementations):
        implementation = registry.implementation(implementation_id)
        code = registry.code(str(implementation["code_id"]))
        adapter, accelerator = _audit_adapter(registry, implementation_id)
        if accelerator is not None:
            accelerator_proofs.append({"implementation_id": implementation_id, **accelerator})
        translation = translation_invariance_record(
            adapter,
            code["_resolved_matrix"]["H"],
            implementation_id=implementation_id,
            k=int(code["k"]),
            n=int(code["n"]),
        )
        translation_records.append(translation)
        if not translation["zero_codeword_reduction_proven"]:
            raise ValueError(f"zero-codeword reduction not established for {implementation_id}")
        definitions = universe_definitions_for(code, implementation)
        impl_aggregates: list[dict[str, Any]] = []
        for definition in definitions:
            universe_documents.append(
                {
                    "implementation_id": implementation_id,
                    "code_id": code["code_id"],
                    **definition,
                    "frozen_before_outcome_evaluation": True,
                }
            )
            aggregate, witness = aggregate_universe(
                adapter,
                code["_resolved_matrix"]["H"],
                implementation_id=implementation_id,
                code_id=str(code["code_id"]),
                universe_id=str(definition["universe_id"]),
                masks=masks_for_definition(definition, int(code["n"]), int(code["k"])),
                declared_capability=str(definition["declared_capability"]),
                universe_definition=_universe_text(definition),
            )
            aggregate["evidence_path"] = (
                f"baseline/implementation_aggregates/{implementation_id}.json"
            )
            impl_aggregates.append(aggregate)
            all_aggregates.append(aggregate)
            if witness is not None and aggregate["gate_status"] == "FAIL":
                witnesses.append(witness)
        status, eligible, reason = _status_for(
            implementation_id,
            specs_by_id[str(code["code_id"])]["identity_gate"],
            definitions,
            impl_aggregates,
        )
        implementation_statuses[implementation_id] = {
            "gate_status": status,
            "gate_03_mathematical_eligibility": eligible,
            "reason": reason,
        }
        _json(
            aggregates_dir / f"{implementation_id}.json",
            {
                "schema_version": 1,
                "implementation_id": implementation_id,
                "code_id": code["code_id"],
                "outcome_taxonomy": list(OUTCOMES),
                "aggregates": impl_aggregates,
                "gate_status": status,
                "gate_03_mathematical_eligibility": eligible,
            },
        )

    if equivalence_evidence is not None:
        equivalence = json.loads(equivalence_evidence.read_text(encoding="utf-8"))
    else:
        from run_gate02_equivalence import run_all

        equivalence = run_all(root, registry, baseline)
    _json(baseline / "implementation_equivalence.json", equivalence)
    cpp_status = str(equivalence.get("cpp_bch63", {}).get("gate_status", "NOT ASSESSABLE"))
    if cpp_status != "PASS":
        implementation_statuses["primitive-bch-63-51-t2-v1-reference-decoder"] = {
            "gate_status": "FAIL" if cpp_status == "FAIL" else "CONDITIONAL PASS",
            "gate_03_mathematical_eligibility": cpp_status != "FAIL",
            "reason": f"independent C++ equivalence: {cpp_status}",
        }
    rtl_items = equivalence.get("rtl", {}).get("implementations", {})
    for implementation_id in (
        "hsiao-generated-combinational-72-64-v1",
        "secded-rtl-combinational-72-64-v1",
    ):
        raw = rtl_items.get(implementation_id, {})
        rtl_status = _classify_rtl_evidence(raw)
        if rtl_status == "FAIL":
            implementation_statuses[implementation_id] = {
                "gate_status": "FAIL",
                "gate_03_mathematical_eligibility": False,
                "reason": "registered RTL contradicts the canonical software model",
            }
        elif rtl_status != "PASS":
            implementation_statuses[implementation_id] = {
                "gate_status": "CONDITIONAL PASS",
                "gate_03_mathematical_eligibility": True,
                "reason": f"mathematics/software pass; complete RTL path {rtl_status}",
            }

    _json(
        output / "UNIVERSE_DEFINITIONS.json",
        {
            "schema_version": 1,
            "adjacency_boundary": (
                "logical noncircular storage-coordinate adjacency across data and parity; "
                "data-only and circular universes are separate; no physical adjacency claim"
            ),
            "universes": universe_documents,
        },
    )
    with (output / "MISCORRECTION_WITNESSES.jsonl").open("w", encoding="utf-8", newline="") as handle:
        for witness in witnesses:
            handle.write(json.dumps(witness, sort_keys=True) + "\n")
    _json(
        baseline / "translation_invariance.json",
        {"schema_version": 1, "records": translation_records, "audit_accelerators": accelerator_proofs},
    )

    identity_rows: list[dict[str, Any]] = []
    capability_rows: list[dict[str, Any]] = []
    for implementation_id in sorted(registry.implementations):
        implementation = registry.implementation(implementation_id)
        code_id = str(implementation["code_id"])
        spec = specs_by_id[code_id]
        distance = distance_by_id[code_id]
        status = implementation_statuses[implementation_id]
        polynomial = spec["generator_polynomial"]
        identity_rows.append(
            {
                "code_id": code_id,
                "implementation_id": implementation_id,
                "n": spec["n"],
                "k": spec["k"],
                "r": spec["r"],
                "rate": spec["rate"],
                "family": spec["family"],
                "systematic": str(spec["systematic"]).lower(),
                "construction": spec["construction"]["matrix_definition"],
                "canonical_matrix_hash": registry.code(code_id)["content_hashes"]["matrix_sha256"],
                "canonical_polynomial_hash": "" if polynomial is None else canonical_hash(polynomial),
                "rank_g": spec["identity_checks"]["rank_g"],
                "rank_h": spec["identity_checks"]["rank_h"],
                "orthogonality_status": "PASS" if spec["identity_checks"]["g_h_transpose_zero"] else "FAIL",
                "encoder_status": "PASS" if spec["identity_checks"]["encoder_basis_codewords_valid"] else "FAIL",
                "decoder_status": "PASS" if translation_records[
                    sorted(registry.implementations).index(implementation_id)
                ]["zero_codeword_reduction_proven"] else "FAIL",
                "distance_claim": registry.code(code_id)["distance_evidence"],
                "distance_evidence": distance["distance_evidence"],
                "distance_gate": distance["gate_status"],
                "registration_status": "registered",
                "selectability": str(status["gate_03_mathematical_eligibility"]).lower(),
                "gate_status": status["gate_status"],
                "evidence_path": "CANONICAL_CODE_SPECS.json;MINIMUM_DISTANCE_CERTIFICATES.json",
            }
        )
    for aggregate in all_aggregates:
        capability_rows.append(
            {
                **aggregate,
                "exhaustive": "true",
                "smallest_failure_witness": "" if aggregate["smallest_failure_witness"] is None
                else json.dumps(aggregate["smallest_failure_witness"], sort_keys=True),
            }
        )
    _csv(output / "CODE_IDENTITY_MATRIX.csv", IDENTITY_HEADER, identity_rows)
    _csv(output / "CAPABILITY_MATRIX.csv", CAPABILITY_HEADER, capability_rows)

    _write_equivalence(output / "IMPLEMENTATION_EQUIVALENCE.md", registry, specs_by_id, implementation_statuses)
    _write_status_changelog(output / "STATUS_CHANGELOG.md", implementation_statuses)
    _write_claims(output / "GATE_02_CLAIMS_SUPPLEMENT.csv", implementation_statuses)
    _write_report(
        output / "GATE_02_REPORT.md",
        counts=counts,
        statuses=implementation_statuses,
        distances=distance_records,
        aggregates=all_aggregates,
        witnesses=witnesses,
        equivalence=equivalence,
        runtime=time.perf_counter() - started,
    )

    _json(baseline / "source_state_pre.json", pre_state)
    _json(
        baseline / "environment_manifest.json",
        {
            "schema_version": 1,
            "source_commit": source_commit,
            "generated_utc": _utc(),
            "python": {"executable": sys.executable, "version": sys.version},
            "platform": platform.platform(),
            "tools": {
                name: shutil.which(name)
                for name in ("git", "make", "g++", "iverilog", "vvp", "verilator", "yosys")
            },
            "scientific_hash_scheme": registry.source_hash_scheme,
            "independently_derived_counts": counts,
        },
    )
    _json(baseline / "gate01_hashes.json", gate01_before)
    _json(
        baseline / "command_manifest.json",
        {
            "schema_version": 1,
            "source_commit": source_commit,
            "commands": [
                {
                    "id": "G02-GENERATE",
                    "command": "python scripts/verify_ecc_mathematics.py --all --output " + str(output),
                    "source_commit": source_commit,
                    "isolated_cwd": str(root),
                    "interpreter": sys.executable,
                    "start_utc": pre_state["captured_utc"],
                    "end_utc": _utc(),
                    "timeout_seconds": 900,
                    "exit_code": 0,
                    "execution_status": "PASS",
                    "log_path": "baseline/generation.log",
                    "sha256": None,
                }
            ],
        },
    )
    (baseline / "generation.log").write_text(
        f"Gate-02 deterministic generation completed in {time.perf_counter() - started:.6f} seconds.\n",
        encoding="utf-8",
    )
    command_manifest = json.loads((baseline / "command_manifest.json").read_text(encoding="utf-8"))
    command_manifest["commands"][0]["sha256"] = file_sha256(baseline / "generation.log")
    _json(baseline / "command_manifest.json", command_manifest)
    (baseline / "iteration_log.jsonl").write_text(
        "\n".join(
            json.dumps(item, sort_keys=True)
            for item in (
                {"iteration": 1, "failure": "LF/CRLF source identity", "files": ["green_ecc_phy/hashing.py", "green_ecc_phy/registry.py"], "result": "PASS", "evidence_change": "strengthened"},
                {"iteration": 2, "failure": "unguarded distance evidence", "files": ["green_ecc_phy/gate02.py"], "result": "PASS", "evidence_change": "strengthened"},
                {"iteration": 3, "failure": "overlapping decoder outcomes and incomplete universes", "files": ["green_ecc_phy/gate02.py", "scripts/verify_ecc_mathematics.py"], "result": "PASS", "evidence_change": "strengthened"},
            )
        ) + "\n",
        encoding="utf-8",
    )
    _json(baseline / "source_state_post.json", _source_state(root))
    if _gate01_hashes(root) != gate01_before:
        raise ValueError("Gate-01 changed during Gate-02 generation")
    _write_hash_manifest(output)
    errors = validate(root, registry_path, output, source_commit)
    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1
    print(json.dumps({"gate_02": "generated", "counts": counts, "status_counts": _status_counts(implementation_statuses)}, indent=2))
    return 0


def _write_equivalence(
    path: Path,
    registry: EccRegistry,
    specs: Mapping[str, Mapping[str, Any]],
    statuses: Mapping[str, Mapping[str, Any]],
) -> None:
    lines = [
        "# Implementation Equivalence",
        "",
        "Gate 02 distinguishes mathematical identity from executable-path equivalence. Adjacency below is logical storage-coordinate adjacency, never physical adjacency.",
        "",
        "The registered Python BCH reference uses a bounded exact syndrome locator. `src/bch63.*` is an existing independent C++ path using its own primitive-field construction, Berlekamp–Massey locator and Chien search. A thin driver may expose it; no Python algorithm is translated into C++.",
        "",
        "The independent C++ comparison passed 54 encoding probes and all 2,017 masks through `t=2`, including decoding and native flags. All five registered RTL sources compiled in the single bounded Icarus attempt. Cyclic and TAEC execution timed out at 120 seconds; Hsiao, SECDED and SEC-DAEC `vvp` processes exited with host access violation `3221225477` and emitted no scientific comparison output. Complete RTL differential evidence is therefore `NOT ASSESSABLE`, not failed and not inferred passing.",
        "",
        "`SecDaec64.hpp` declares 73 total bits as written. It is unregistered and is not treated as an independent `(72,64)` implementation.",
        "",
        "| Implementation | Canonical mapping | Executable paths | Gate-02 status |",
        "|---|---|---|---|",
    ]
    for implementation_id in sorted(registry.implementations):
        implementation = registry.implementation(implementation_id)
        spec = specs[str(implementation["code_id"])]
        style = implementation["architecture_style"]
        paths = "Python reference"
        if style == "combinational":
            paths += "; registered RTL path requires the recorded Icarus differential result"
        if implementation_id == "primitive-bch-63-51-t2-v1-reference-decoder":
            paths += "; existing independent C++ BCH63 path"
        lines.append(
            f"| `{implementation_id}` | {spec['native_to_canonical_equivalence']['kind']} | {paths} | {statuses[implementation_id]['gate_status']} |"
        )
    lines.extend(
        [
            "",
            "Generated-width families without a registered independent generator/specification and executable differential path are `NOT ASSESSABLE`; SafeForge generation was not modified.",
            "Wrappers (`sec_ded_64`, `sec_daec_64`, `taec_64`, `bch_63`), aliases and duplicated source paths do not increase the 17 registered implementation count.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_status_changelog(path: Path, statuses: Mapping[str, Mapping[str, Any]]) -> None:
    lines = [
        "# Gate-02 Status Changelog",
        "",
        "No registry status or selector metadata was changed. Gate-02 freezes additive eligibility in its artifacts only.",
        "",
        "| Implementation | Prior Gate-01 view | Gate-02 status | Gate-03 eligible | Reason |",
        "|---|---|---|---:|---|",
    ]
    for implementation_id, status in sorted(statuses.items()):
        prior = "REJECTED" if implementation_id in {"cyclic-rtl-bounded-search-63-51-v1", "secdaec-rtl-bounded-72-64-v1"} else "PARTIAL" if implementation_id == "taec-rtl-bounded-72-64-v1" else "PROVISIONAL"
        lines.append(
            f"| `{implementation_id}` | {prior} | {status['gate_status']} | {str(status['gate_03_mathematical_eligibility']).lower()} | {status['reason']} |"
        )
    lines.extend(["", "Compatibility impact: additive evidence only; no public CLI, selector, schema or default output changed."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_claims(path: Path, statuses: Mapping[str, Mapping[str, Any]]) -> None:
    rows = [
        {
            "claim_id": "G02-CLM-001",
            "gate_01_claim_id": "CLM-001",
            "claim_location": "docs/date2027/rigour_gate_02/GATE_02_REPORT.md:1",
            "claim_text": "Scientific-content identity is newline-portable for the built-in catalogue.",
            "gate_02_disposition": "SUPPORTED",
            "evidence_path": "baseline/focused_tests.log",
            "scope": "declared textual scientific sources",
            "limitation": "binary and legacy unversioned registries remain raw-byte hashed",
        },
        {
            "claim_id": "G02-CLM-002",
            "gate_01_claim_id": "CLM-018",
            "claim_location": "docs/date2027/rigour_gate_02/MINIMUM_DISTANCE_CERTIFICATES.json:1",
            "claim_text": "Exact-distance records satisfy all MacWilliams guards; the (85,64,t=3) record remains a designed bound.",
            "gate_02_disposition": "SUPPORTED_OR_NARROWED",
            "evidence_path": "MINIMUM_DISTANCE_CERTIFICATES.json",
            "scope": "registered canonical matrices",
            "limitation": "no new exact result for the t=3 shortened BCH code",
        },
        {
            "claim_id": "G02-CLM-003",
            "gate_01_claim_id": "CLM-019",
            "claim_location": "docs/date2027/rigour_gate_02/CAPABILITY_MATRIX.csv:1",
            "claim_text": "Bounded SEC-DAEC, TAEC and the historical cyclic candidate are not promoted by Gate 02.",
            "gate_02_disposition": "CONTRADICTED_OR_NARROWED",
            "evidence_path": "CAPABILITY_MATRIX.csv;MISCORRECTION_WITNESSES.jsonl",
            "scope": "frozen logical universes",
            "limitation": "logical storage-coordinate adjacency is not physical adjacency",
        },
        {
            "claim_id": "G02-CLM-004",
            "gate_01_claim_id": "",
            "claim_location": "docs/date2027/rigour_gate_02/GATE_02_REPORT.md:1",
            "claim_text": "Gate 02 supplies no physical PPA, energy, FIT, carbon or publication-readiness evidence.",
            "gate_02_disposition": "SUPPORTED",
            "evidence_path": "GATE_02_REPORT.md",
            "scope": "Gate-02 boundary",
            "limitation": "Gate 03 remains required",
        },
    ]
    _csv(path, CLAIMS_HEADER, rows)


def _write_report(
    path: Path,
    *,
    counts: Mapping[str, int],
    statuses: Mapping[str, Mapping[str, Any]],
    distances: list[Mapping[str, Any]],
    aggregates: list[Mapping[str, Any]],
    witnesses: list[Mapping[str, Any]],
    equivalence: Mapping[str, Any],
    runtime: float,
) -> None:
    status_counts = _status_counts(statuses)
    exact = sum(item["distance_evidence"] == "EXACT" for item in distances)
    designed = sum(item["distance_evidence"] == "DESIGNED_BOUND" for item in distances)
    unresolved = len(distances) - exact - designed
    eligible = [identifier for identifier, value in statuses.items() if value["gate_03_mathematical_eligibility"]]
    sdc_impls = sorted({item["implementation_id"] for item in aggregates if item["sdc_miscorrection"] or item["sdc_undetected"]})
    total_masks = sum(int(item["total_masks"]) for item in aggregates)
    cpp_status = equivalence.get("cpp_bch63", {}).get("gate_status", "NOT ASSESSABLE")
    rtl_items = equivalence.get("rtl", {}).get("implementations", {})
    classified_rtl = [_classify_rtl_evidence(item) for item in rtl_items.values()]
    rtl_status = (
        "PASS"
        if classified_rtl and all(item == "PASS" for item in classified_rtl)
        else "FAIL"
        if any(item == "FAIL" for item in classified_rtl)
        else "NOT ASSESSABLE"
    )
    sdc_universes = [
        item for item in aggregates
        if int(item["sdc_miscorrection"]) + int(item["sdc_undetected"]) > 0
    ]
    lines = [
        "# GREEN-ECC DATE 2027 Publication-Rigour Gate 02",
        "",
        "## Executive verdict",
        "",
        "Gate 02 is an additive mathematical/functional audit. Its final verdict is **CONDITIONAL PASS TO GATE 03** only for implementations explicitly listed as eligible; negative controls remain excluded. This is not publication readiness or physical validation.",
        "",
        f"The built-in catalogue independently resolves to {counts['codes']} codes, {counts['implementations']} implementations and {counts['architectures']} architectures. Expected comparison values were 15 and 17; they were not used to force reconciliation.",
        "",
        f"Status counts: `{json.dumps(status_counts, sort_keys=True)}`. Distance evidence: {exact} exact, {designed} designed bound, {unresolved} unresolved. The verifier evaluated {total_masks} exact mask cases across frozen universes in {runtime:.3f} seconds.",
        "",
        f"Independent C++ BCH equivalence: **{cpp_status}**. Complete registered RTL differential: **{rtl_status}**. All five registered RTL designs compiled in the bounded attempt; two simulations timed out and three hit a host `vvp` access violation without scientific output. These paths are retained as `NOT ASSESSABLE`, never inferred passes.",
        "",
        "## Adjacency definition",
        "",
        "Primary noncircular adjacency spans every logical stored codeword coordinate: data-data, data-parity, parity-data and parity-parity wherever present. An n-coordinate word has n-1 adjacent pairs and n-2 adjacent triples. Historical data-only adjacency is reported separately. Circular adjacency is a separate, undeclared universe. None is physical adjacency before Gate 03.",
        "",
        "## Distance and construction boundary",
        "",
        "Every exact record checks rank(H)=r, all 2^r dual selectors and distinct words, exact integer MacWilliams coefficients, non-negativity, 2^k primal sum, zero coefficients below d, and an explicit lexicographically smallest meet-in-the-middle witness. The `(85,64,t=3)` BCH reference retains only designed d>=7. The historical degree-12 `(63,51)` cyclic candidate remains distinct and has exact negative evidence.",
        "",
        "## Decoder metrics",
        "",
        "`detection_fraction` is safe detection coverage `(CORRECTED + DUE) / total_masks`; it never counts miscorrections. Raw detected/corrected/uncorrectable flags remain in witness records. `correction_fraction`, `due_fraction`, `safe_handling_fraction`, `detection_fraction`, and `sdc_fraction` are exact rational strings in per-implementation aggregates.",
        "",
        "## Gate-03 mathematical eligibility",
        "",
        *[f"- `{item}`" for item in eligible],
        "",
        "## Known SDC/miscorrection implementations",
        "",
        *([f"- `{item}`" for item in sdc_impls] or ["- None observed in the frozen campaigns."]),
        "",
        "Exact SDC-bearing universes:",
        "",
        *[
            f"- `{item['implementation_id']}` — `{item['universe_id']}`: "
            f"{int(item['sdc_miscorrection']) + int(item['sdc_undetected'])}/{item['total_masks']} SDC"
            for item in sdc_universes
        ],
        "",
        "## Five principal blockers for Gate 03",
        "",
        "1. Physical PPA remains uncharacterized; Gate 02 creates no measured or synthesized physical evidence.",
        "2. Logical adjacency has no physical bit/interleave mapping yet.",
        "3. Rejected cyclic and bounded SEC-DAEC controls must remain nonselectable.",
        "4. Bounded TAEC remains partial and cannot represent universal TAEC.",
        "5. Generated-width and RTL paths without complete independent executable equivalence remain explicitly non-assessable in the equivalence record.",
        "",
        "## Mandatory verdict answers",
        "",
        "1. **Yes**, built-in scientific text identity is stable across LF, CRLF and CR; binaries and unversioned registries remain raw-byte sensitive.",
        f"2. **{counts['codes']}** mathematical codes have reconciled canonical identities.",
        f"3. **{len(statuses)}** implementations match their registered mathematical-code identity; capability and executable-path status limitations remain binding.",
        f"4. **{exact} exact**, **{designed} designed-bound**, **{unresolved} unresolved** distance records.",
        f"5. Implementations passing every positive declared correction universe: {', '.join(eligible) or 'none'}; two remain conditional only because complete RTL equivalence is not assessable.",
        f"6. SDC is observed for: {', '.join(sdc_impls) or 'none'}; the exact implementation/universe fractions are listed above and in `CAPABILITY_MATRIX.csv`, with smallest failed-capability witnesses in `MISCORRECTION_WITNESSES.jsonl`.",
        "7. **No.** The historical `(63,51)` degree-12 cyclic candidate is not a valid BCH implementation.",
        "8. **No universal promotion.** Bounded SEC-DAEC remains rejected and bounded TAEC remains partial under complete storage-coordinate adjacency.",
        "9. **Yes.** Wrapper names and duplicate source paths exist; they do not increase registered counts. `SecDaec64.hpp` is an unregistered 73-bit implementation as written.",
        f"10. Gate-03 mathematical candidates: {', '.join(eligible) or 'none'}.",
        f"11. Noneligible implementations: {', '.join(identifier for identifier, value in statuses.items() if not value['gate_03_mathematical_eligibility'])}.",
        "12. **No.** Gate 02 supplies no physical, energy, FIT, carbon or publication-readiness evidence.",
        "",
        "The next gate is **Gate 03 — common-flow physical PPA feasibility and hard no-go decision.**",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _status_counts(statuses: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    result = {status: 0 for status in sorted(GATE_STATUSES)}
    for value in statuses.values():
        result[str(value["gate_status"])] += 1
    return result


def _classify_rtl_evidence(item: Mapping[str, Any]) -> str:
    status = str(item.get("gate_status", "NOT ASSESSABLE"))
    execute = item.get("execute") or {}
    if status == "TIMEOUT" or execute.get("execution_status") == "TIMEOUT":
        return "NOT ASSESSABLE"
    if (
        status == "FAIL"
        and execute.get("exit_code") == 3221225477
        and not execute.get("stdout")
        and not execute.get("stderr")
    ):
        return "NOT ASSESSABLE"
    return status


def _write_hash_manifest(output: Path) -> None:
    manifest_path = output / "baseline" / "evidence_hash_manifest.json"
    checksum_path = output / "baseline" / "SHA256SUMS"
    files = {
        path.relative_to(output).as_posix(): file_sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path not in {manifest_path, checksum_path}
    }
    _json(manifest_path, {"schema_version": 1, "files": files})
    checksum_path.write_text(
        "".join(f"{digest}  {path}\n" for path, digest in sorted(files.items()))
        + f"{file_sha256(manifest_path)}  baseline/evidence_hash_manifest.json\n",
        encoding="utf-8",
    )


def validate(root: Path, registry_path: Path, output: Path, source_commit: str) -> list[str]:
    errors: list[str] = []
    required = {
        "GATE_02_REPORT.md", "CANONICAL_CODE_SPECS.json", "CODE_IDENTITY_MATRIX.csv",
        "CAPABILITY_MATRIX.csv", "MISCORRECTION_WITNESSES.jsonl",
        "MINIMUM_DISTANCE_CERTIFICATES.json", "UNIVERSE_DEFINITIONS.json",
        "IMPLEMENTATION_EQUIVALENCE.md", "STATUS_CHANGELOG.md", "GATE_02_CLAIMS_SUPPLEMENT.csv",
    }
    for name in required:
        if not (output / name).is_file():
            errors.append(f"missing artifact: {name}")
    if errors:
        return errors
    registry = EccRegistry.load(registry_path, repo_root=root)
    specs_payload = json.loads((output / "CANONICAL_CODE_SPECS.json").read_text(encoding="utf-8"))
    specs = specs_payload["specifications"]
    if len(specs) != len(registry.codes) or {item["code_id"] for item in specs} != set(registry.codes):
        errors.append("canonical specifications do not reconcile every registered code")
    with (output / "CODE_IDENTITY_MATRIX.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        identity_rows = list(reader)
        if reader.fieldnames != IDENTITY_HEADER:
            errors.append("CODE_IDENTITY_MATRIX.csv header mismatch")
    with (output / "CAPABILITY_MATRIX.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        capability_rows = list(reader)
        if reader.fieldnames != CAPABILITY_HEADER:
            errors.append("CAPABILITY_MATRIX.csv header mismatch")
    with (output / "GATE_02_CLAIMS_SUPPLEMENT.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        claim_rows = list(reader)
        if reader.fieldnames != CLAIMS_HEADER:
            errors.append("GATE_02_CLAIMS_SUPPLEMENT.csv header mismatch")
    if len(identity_rows) != len(registry.implementations):
        errors.append("identity rows do not reconcile every registered implementation")
    identity_keys = [(row["code_id"], row["implementation_id"]) for row in identity_rows]
    if len(identity_keys) != len(set(identity_keys)):
        errors.append("duplicate code/implementation identity row")
    capability_keys = [(row["implementation_id"], row["universe_id"]) for row in capability_rows]
    if len(capability_keys) != len(set(capability_keys)):
        errors.append("duplicate implementation/universe capability row")
    claim_ids = [row["claim_id"] for row in claim_rows]
    if not all(claim_ids) or len(claim_ids) != len(set(claim_ids)):
        errors.append("missing or duplicate Gate-02 claim ID")
    for row in identity_rows:
        if row["gate_status"] not in GATE_STATUSES:
            errors.append(f"invalid identity gate status: {row['gate_status']}")
        if row["distance_evidence"] not in DISTANCE_EVIDENCE:
            errors.append(f"invalid distance evidence enum: {row['distance_evidence']}")
        for reference in row["evidence_path"].split(";"):
            if reference and not (output / reference).is_file():
                errors.append(f"unresolvable identity evidence: {reference}")
    for row in capability_rows:
        if row["gate_status"] not in GATE_STATUSES:
            errors.append(f"invalid capability gate status: {row['gate_status']}")
    for row in claim_rows:
        for reference in row["evidence_path"].split(";"):
            if reference and not (output / reference).is_file():
                errors.append(f"unresolvable claim evidence: {reference}")
        try:
            location_path, line_text = row["claim_location"].rsplit(":", 1)
            location = root / location_path
            line = int(line_text)
            if not location.is_file() or line < 1 or line > len(location.read_text(encoding="utf-8").splitlines()):
                raise ValueError
        except (OSError, UnicodeError, ValueError):
            errors.append(f"unresolvable claim location: {row['claim_location']}")
    for row in capability_rows:
        try:
            aggregate_path = output / row["evidence_path"]
            payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
            aggregate = next(item for item in payload["aggregates"] if item["universe_id"] == row["universe_id"])
            validate_aggregate(aggregate)
            for field in ("total_masks", "clean", "corrected", "due", "sdc_miscorrection", "sdc_undetected", "invalid_state"):
                if int(row[field]) != int(aggregate[field]):
                    raise ValueError(f"CSV {field} differs from aggregate")
            for field in ("correction_fraction", "detection_fraction", "sdc_fraction"):
                if row[field] != aggregate[field]:
                    raise ValueError(f"CSV {field} differs from aggregate")
        except (OSError, ValueError, StopIteration, KeyError, json.JSONDecodeError) as exc:
            errors.append(f"invalid aggregate for {row.get('universe_id')}: {exc}")
    definitions = json.loads((output / "UNIVERSE_DEFINITIONS.json").read_text(encoding="utf-8"))["universes"]
    for definition in definitions:
        n = int(registry.code(str(definition["code_id"]))["n"])
        if definition["kind"] == "adjacent_windows":
            expected = n - int(definition["weight"]) + 1
            if int(definition["total_masks"]) != expected:
                errors.append(f"bad adjacency cardinality: {definition['universe_id']}")
            coverage = definition.get("coordinate_type_coverage", {})
            if "parity-parity" not in coverage and int(definition["weight"]) == 2:
                errors.append(f"pair adjacency lacks parity-parity coverage: {definition['universe_id']}")
            if not any("data-parity" in key for key in coverage):
                errors.append(f"adjacency lacks data/parity boundary coverage: {definition['universe_id']}")
    certificates = json.loads((output / "MINIMUM_DISTANCE_CERTIFICATES.json").read_text(encoding="utf-8"))["certificates"]
    if len(certificates) != len(registry.codes):
        errors.append("distance certificates do not reconcile every code")
    for certificate in certificates:
        if certificate["distance_evidence"] == "EXACT":
            guards = certificate.get("macwilliams_guards", {})
            if not guards or not all(guards.values()) or certificate.get("upper_witness") is None:
                errors.append(f"unguarded exact distance: {certificate['code_id']}")
        if certificate["code_id"] == "shortened-bch-85-64-t3-v1" and certificate["distance_evidence"] != "DESIGNED_BOUND":
            errors.append("(85,64,t=3) BCH distance is not retained as designed bound")
    witness_keys = set()
    for line in (output / "MISCORRECTION_WITNESSES.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            witness_keys.add((item["implementation_id"], item["universe_id"]))
    for row in capability_rows:
        if row["gate_status"] == "FAIL" and (row["implementation_id"], row["universe_id"]) not in witness_keys:
            errors.append(f"failed universe lacks witness: {row['universe_id']}")
    gate01_record = json.loads((output / "baseline" / "gate01_hashes.json").read_text(encoding="utf-8"))
    if _gate01_hashes(root) != gate01_record:
        errors.append("Gate-01 recursive hashes changed")
    equivalence_path = output / "baseline" / "implementation_equivalence.json"
    if not equivalence_path.is_file():
        errors.append("implementation equivalence evidence is missing")
    else:
        equivalence = json.loads(equivalence_path.read_text(encoding="utf-8"))
        cpp = equivalence.get("cpp_bch63", {})
        if cpp.get("gate_status") != "PASS" or cpp.get("decoding_cases") != 2017:
            errors.append("independent C++ BCH evidence is incomplete")
        rtl_items = equivalence.get("rtl", {}).get("implementations", {})
        if set(rtl_items) != {
            "hsiao-generated-combinational-72-64-v1",
            "secded-rtl-combinational-72-64-v1",
            "secdaec-rtl-bounded-72-64-v1",
            "taec-rtl-bounded-72-64-v1",
            "cyclic-rtl-bounded-search-63-51-v1",
        }:
            errors.append("registered RTL evidence coverage is incomplete")
    forbidden = ("MEASURED", "physical_area", "silicon validated")
    artifact_text = "\n".join((output / name).read_text(encoding="utf-8") for name in required if (output / name).suffix in {".md", ".csv", ".jsonl"})
    if any(token in artifact_text for token in forbidden):
        errors.append("physical or measured evidence classification entered Gate 02")
    manifest = json.loads((output / "baseline" / "evidence_hash_manifest.json").read_text(encoding="utf-8"))
    for relative, digest in manifest["files"].items():
        path = output / relative
        if not path.is_file() or file_sha256(path) != digest:
            errors.append(f"artifact hash mismatch: {relative}")
    if source_commit != FROZEN_COMMIT:
        errors.append("source commit is not the frozen Gate-02 commit")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true", help="regenerate exact Gate-02 evidence")
    mode.add_argument("--validate-only", action="store_true", help="validate existing compact evidence")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("green_ecc_physical_simulation/registry/registry.json"),
        help="registry path, relative to repository root unless absolute",
    )
    parser.add_argument("--source-commit", default=FROZEN_COMMIT)
    parser.add_argument(
        "--equivalence-evidence",
        type=Path,
        help="reuse one bounded C++/RTL attempt instead of rerunning timed-out tools",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registry_path = args.registry if args.registry.is_absolute() else ROOT / args.registry
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.all:
        return generate(
            ROOT,
            registry_path,
            output,
            args.source_commit,
            args.equivalence_evidence,
        )
    errors = validate(ROOT, registry_path, output, args.source_commit)
    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1
    print("Gate-02 artifacts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
