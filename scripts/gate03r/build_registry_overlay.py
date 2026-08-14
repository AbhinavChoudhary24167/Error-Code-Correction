#!/usr/bin/env python3
"""Build the explicit Gate 03R registry overlay without changing defaults."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from green_ecc_phy.hashing import canonical_hash, manifest_sha256, scientific_file_sha256
from green_ecc_phy.registry import EccRegistry


REGISTRY = ROOT / "green_ecc_physical_simulation" / "registry"
IMPLEMENTATIONS = REGISTRY / "implementations"
OVERLAY = REGISTRY / "registry_gate03r.json"
PIPELINED_ID = "secded-rtl-pipelined-72-64-v1"
BCH_ID = "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def bind_sources(payload: dict[str, Any], sources: list[str]) -> None:
    payload["source_files"] = sources
    payload["source_hashes"] = {
        source: scientific_file_sha256(ROOT / source) for source in sources
    }
    payload["source_provenance"] = [
        {"path": source, "role": "Gate 03R RTL/contract/proof evidence"} for source in sources
    ]


def make_pipelined() -> dict[str, Any]:
    payload = copy.deepcopy(read(IMPLEMENTATIONS / "secded-rtl-combinational-72-64-v1.json"))
    payload.update(
        {
            "implementation_id": PIPELINED_ID,
            "version": "1.0.0-gate03r",
            "architecture_style": "pipelined",
            "pipeline_stages": 2,
            "initiation_interval": 1,
            "encoder_latency": 2,
            "decoder_latency": 2,
            "encoder_top": "secded_pipelined_72_64_v1_encoder",
            "decoder_top": "secded_pipelined_72_64_v1_decoder",
            "wrapper_module": None,
            "clock_reset": {"clock_required": True, "reset_required": False},
            "transaction_protocol": {
                "kind": "valid_aligned_registered_pipeline",
                "backpressure": False,
            },
            "evidence_level": "rtl_exact_identity_proof_pending_gate03r_acceptance",
            "verified_capabilities": [
                "exact encoder identity",
                "all-single-bit correction",
                "all-double-bit detection",
                "initiation interval one",
            ],
            "unsupported_capabilities": [
                "weight>=2 correction",
                "weight>=3 detection",
                "physical PPA until pinned ORFS completes",
            ],
            "verification_evidence": [
                {
                    "kind": "exact_affine_and_latency_aligned_proof",
                    "path": "docs/date2027/rigour_gate_03r/EXACT_PROOF_SUMMARY.json",
                    "status": "partial_environment_blocked",
                    "test_id": "gate03r-secded-exact-identity",
                }
            ],
            "capability_claims": {
                "mathematical": "byte-identical extended-hamming-secded-72-64-v1",
                "hardware_structure_id": "factored-balanced-xor-two-stage-pipeline-72-64-v1",
                "data_independence_proof": "linearity and latency-aligned decoder equivalence",
                "physical_characterization": None,
                "rtl": "valid-aligned two-stage full-throughput implementation",
            },
        }
    )
    bind_sources(
        payload,
        [
            "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
            "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md",
            "scripts/gate03r/run_rtl_verification.py",
        ],
    )
    payload["manifest_sha256"] = manifest_sha256(payload)
    return payload


def make_bch() -> dict[str, Any]:
    payload = copy.deepcopy(
        read(IMPLEMENTATIONS / "shortened-bch-78-64-t2-v1-reference-decoder.json")
    )
    payload.update(
        {
            "implementation_id": BCH_ID,
            "version": "1.0.0-gate03r",
            "architecture_style": "combinational",
            "pipeline_stages": 0,
            "encoder_latency": 0,
            "decoder_latency": 0,
            "encoder_top": "bch_78_64_t2_v1_encoder",
            "decoder_top": "bch_78_64_t2_v1_decoder",
            "wrapper_module": None,
            "evidence_level": "rtl_and_exact_symbolic_functional",
            "verified_capabilities": [
                "all-weight-1 correction",
                "all-weight-2 correction",
                "3082 fixed-mask arbitrary-symbolic-payload proofs",
            ],
            "unsupported_capabilities": [
                "guaranteed correction beyond t=2",
                "weight-3 correction claims",
                "physical PPA until pinned ORFS completes",
            ],
            "verification_evidence": [
                {
                    "kind": "exact_affine_symbolic_payload_per_mask",
                    "path": "docs/date2027/rigour_gate_03r/FORMAL_PROOF_INDEX.csv",
                    "status": "passed",
                    "test_id": "bch-3082-symbolic-mask-jobs",
                },
                {
                    "kind": "independent_identity_reconstruction",
                    "path": "docs/date2027/rigour_gate_03r/BCH_IDENTITY_RECONSTRUCTION.json",
                    "status": "passed",
                    "test_id": "bch-matrix-hash-d518cab4",
                },
            ],
            "capability_claims": {
                "mathematical": "primitive shortened BCH(78,64,t=2)",
                "hardware_structure_id": "unoptimized-combinational-syndrome-locator-chien-v1",
                "data_independence_proof": "exact affine GF(2) proof for every weight-0/1/2 mask",
                "physical_characterization": None,
                "rtl": "S1..S4, bounded two-error locator, 78-coordinate Chien search, syndrome recheck",
            },
        }
    )
    bind_sources(
        payload,
        [
            "asic/rtl/bch/bch_78_64_t2_v1.sv",
            "docs/date2027/rigour_gate_03r/BCH_78_64_T2_CONTRACT.md",
            "scripts/gate03r/verify_bch_identity.py",
            "scripts/gate03r/prove_exact_identity.py",
        ],
    )
    payload["manifest_sha256"] = manifest_sha256(payload)
    return payload


def main() -> int:
    default_path = REGISTRY / "registry.json"
    default_bytes = default_path.read_bytes()
    write(IMPLEMENTATIONS / f"{PIPELINED_ID}.json", make_pipelined())
    write(IMPLEMENTATIONS / f"{BCH_ID}.json", make_bch())
    overlay = copy.deepcopy(read(default_path))
    overlay["registry_id"] = "green-ecc-phy-gate03r-overlay-v1"
    overlay["implementations"].extend(
        [f"implementations/{PIPELINED_ID}.json", f"implementations/{BCH_ID}.json"]
    )
    overlay["catalogue_sha256"] = canonical_hash(
        {key: value for key, value in overlay.items() if key != "catalogue_sha256"}
    )
    write(OVERLAY, overlay)
    if default_path.read_bytes() != default_bytes:
        raise AssertionError("default registry bytes changed while building overlay")
    loaded_default = EccRegistry.load(default_path, repo_root=ROOT)
    loaded_overlay = EccRegistry.load(OVERLAY, repo_root=ROOT)
    summary = {
        "default_registry_implementation_count": len(loaded_default.implementations),
        "overlay_registry_implementation_count": len(loaded_overlay.implementations),
        "default_registry_unchanged": default_path.read_bytes() == default_bytes,
        "added_implementation_ids": [PIPELINED_ID, BCH_ID],
        "overlay_path": OVERLAY.relative_to(ROOT).as_posix(),
        "status": "PASS",
    }
    output = ROOT / "docs" / "date2027" / "rigour_gate_03r" / "REGISTRY_OVERLAY_RESULTS.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
