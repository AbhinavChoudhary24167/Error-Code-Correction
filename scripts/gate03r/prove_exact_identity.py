#!/usr/bin/env python3
"""Generate exact Gate 03R proof and characterization evidence.

The BCH proof uses affine GF(2) expressions over all 64 payload bits.  One
proof job is emitted for each weight-0/1/2 error mask.  The proof is exact:
every encoded basis row has zero syndrome, so the decoder's syndrome and
locator depend only on the fixed mask while the payload remains symbolic.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from green_ecc_phy.bch import PrimitiveBCHAdapter, primitive_bch_systematic
from green_ecc_phy.contracts import DecodeStatus
from scripts.gate03r.verify_bch_identity import (
    EXPECTED_MATRIX_SHA256,
    N,
    SHORTENED_K,
    bounded_decode,
    encode,
    gf_pow,
    coordinate_exponent,
    reconstruct,
    syndrome,
    syndrome_column,
)


DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
RTL = ROOT / "asic" / "rtl" / "bch" / "bch_78_64_t2_v1.sv"
PROOF_COLUMNS = (
    "job_id",
    "family",
    "proof_scope",
    "mask_weight",
    "mask_positions",
    "mask_hex",
    "symbolic_payload_bits",
    "assertions",
    "command",
    "status",
    "result",
    "counterexample_id",
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, columns: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def mask_cases() -> Iterable[tuple[int, tuple[int, ...]]]:
    yield 0, ()
    for weight in (1, 2):
        for positions in combinations(range(N), weight):
            yield sum(1 << position for position in positions), positions


def validate_rtl_constants(identity: dict[str, Any]) -> dict[str, Any]:
    text = RTL.read_text(encoding="utf-8")
    generator_match = re.search(r"G_POLY\s*=\s*15'b([01]+)", text)
    if not generator_match:
        raise AssertionError("BCH RTL generator constant is absent")
    generator = int(generator_match.group(1), 2)
    syndrome_cases = {
        int(position): int(value, 16)
        for position, value in re.findall(
            r"7'd(\d+):\s*coordinate_syndrome\s*=\s*28'h([0-9a-fA-F]+)", text
        )
    }
    location_cases = {
        int(position): int(value, 16)
        for position, value in re.findall(
            r"7'd(\d+):\s*location_element\s*=\s*7'h([0-9a-fA-F]+)", text
        )
    }
    expected_syndromes = {position: syndrome_column(position) for position in range(N)}
    expected_locations = {
        position: gf_pow(2, coordinate_exponent(position)) for position in range(N)
    }
    checks = {
        "generator_matches": generator == int(identity["generator_polynomial"]),
        "all_78_syndrome_columns_match": syndrome_cases == expected_syndromes,
        "all_78_location_elements_match": location_cases == expected_locations,
        "injection_ports_absent": not re.search(
            r"\b(?:inject(?:ion)?|fault(?:_mask)?|error_mask_i)\b", text, re.IGNORECASE
        ),
        "unoptimized_combinational_core": (
            ("always_comb" in text or "always @(" in text) and "always_ff" not in text
        ),
    }
    if not all(checks.values()):
        raise AssertionError(f"BCH RTL constant/guard mismatch: {checks}")
    return checks


def bch_symbolic_proofs(identity: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    basis_is_codeword = all(syndrome(encode(1 << bit)) == 0 for bit in range(SHORTENED_K))
    systematic_mapping = all((encode(1 << bit) & ((1 << SHORTENED_K) - 1)) == 1 << bit for bit in range(SHORTENED_K))
    zero_holds = encode(0) == 0 and syndrome(0) == 0
    identity_holds = identity["matrix_sha256"] == EXPECTED_MATRIX_SHA256
    for index, (mask, positions) in enumerate(mask_cases()):
        decoded = bounded_decode(mask)
        expected_corrected = bool(positions)
        passed = all(
            (
                identity_holds,
                basis_is_codeword,
                systematic_mapping,
                zero_holds,
                decoded["data"] == 0,
                decoded["corrected_codeword"] == 0,
                decoded["correction_mask"] == mask,
                decoded["detected"] is expected_corrected,
                decoded["corrected"] is expected_corrected,
                decoded["uncorrectable"] is False,
                decoded["syndrome"] == syndrome(mask),
            )
        )
        job_id = f"bch-symbolic-mask-{index:04d}"
        counterexample = "" if passed else f"cex-{job_id}"
        result = (
            "affine payload cancels from S1..S4; exact locator returns the fixed mask; "
            "corrected systematic word equals encode(payload)"
            if passed
            else "one or more exact affine assertions failed"
        )
        rows.append(
            {
                "job_id": job_id,
                "family": "BCH_78_64_T2",
                "proof_scope": "arbitrary_symbolic_payload_and_fixed_error_mask",
                "mask_weight": len(positions),
                "mask_positions": ";".join(map(str, positions)),
                "mask_hex": f"{mask:020x}",
                "symbolic_payload_bits": 64,
                "assertions": "data;corrected_codeword;correction_mask;S1_S2_S3_S4;detected;corrected;uncorrectable;latency_0",
                "command": f"python3 scripts/gate03r/prove_exact_identity.py --proof-job {job_id}",
                "status": "PASS" if passed else "FAIL",
                "result": result,
                "counterexample_id": counterexample,
            }
        )
        if not passed:
            failures.append(
                {
                    "counterexample_id": counterexample,
                    "job_id": job_id,
                    "mask": f"{mask:020x}",
                    "positions": positions,
                    "decoded": decoded,
                }
            )
    if len(rows) != 3082:
        raise AssertionError(f"BCH proof job count is {len(rows)}, expected 3082")
    return rows, failures


def reference_adapter() -> PrimitiveBCHAdapter:
    matrix = primitive_bch_systematic(
        m=7, t=2, primitive_polynomial=0x83, shortened_k=64
    )
    return PrimitiveBCHAdapter(
        h=matrix["H"],
        g=matrix["G"],
        k=64,
        n=78,
        m=7,
        t=2,
        primitive_polynomial=0x83,
    )


def compare_one(reference: PrimitiveBCHAdapter, payload: int, mask: int) -> tuple[bool, str]:
    clean = encode(payload)
    received = clean ^ mask
    actual = bounded_decode(received)
    expected = reference.decode(received)
    if expected.status == DecodeStatus.CORRECTED:
        location = expected.error_location_optional
        positions = (location,) if isinstance(location, int) else tuple(location or ())
        expected_mask = sum(1 << position for position in positions)
        checks = (
            actual["corrected"],
            not actual["uncorrectable"],
            actual["correction_mask"] == expected_mask,
            actual["corrected_codeword"] == expected.corrected_codeword_optional,
            actual["data"] == expected.data,
            actual["syndrome"] == expected.syndrome,
        )
        return all(checks), "reference_corrected"
    checks = (
        expected.status == DecodeStatus.DETECTED_UNCORRECTABLE,
        actual["uncorrectable"],
        not actual["corrected"],
        actual["correction_mask"] == 0,
        actual["corrected_codeword"] == received,
        actual["data"] == (received & ((1 << 64) - 1)),
        actual["syndrome"] == expected.syndrome,
    )
    return all(checks), "reference_uncorrectable_pass_through"


def characterize_weight3() -> dict[str, Any]:
    reference = reference_adapter()
    counts = {"reference_corrected": 0, "reference_uncorrectable_pass_through": 0}
    failures: list[dict[str, Any]] = []
    triples = list(combinations(range(N), 3))
    for positions in triples:
        mask = sum(1 << position for position in positions)
        passed, classification = compare_one(reference, 0, mask)
        counts[classification] += 1
        if not passed:
            failures.append({"payload": 0, "positions": positions, "classification": classification})

    rng = random.Random(0x475245454E303352)
    sample_size = 1024
    for sample_index in range(sample_size):
        payload = rng.getrandbits(64)
        positions = triples[rng.randrange(len(triples))]
        mask = sum(1 << position for position in positions)
        passed, classification = compare_one(reference, payload, mask)
        if not passed:
            failures.append(
                {
                    "sample_index": sample_index,
                    "payload": f"{payload:016x}",
                    "positions": positions,
                    "classification": classification,
                }
            )
    return {
        "schema_version": 1,
        "claim_scope": "characterization_only_no_weight3_correction_claim",
        "reference": "frozen Gate 02 PrimitiveBCHAdapter identity shortened-bch-78-64-t2-v1",
        "zero_payload_weight3_masks_examined": len(triples),
        "expected_zero_payload_weight3_masks": 76076,
        "zero_payload_classifications": counts,
        "deterministic_sample_seed_hex": "475245454e303352",
        "deterministic_payload_mask_samples": sample_size,
        "failures": failures,
        "status": "PASS" if not failures and len(triples) == 76076 else "FAIL",
    }


def run_all() -> dict[str, Any]:
    identity = reconstruct()
    rtl_checks = validate_rtl_constants(identity)
    proof_rows, failures = bch_symbolic_proofs(identity)
    characterization = characterize_weight3()
    DOC.mkdir(parents=True, exist_ok=True)
    write_json(DOC / "BCH_IDENTITY_RECONSTRUCTION.json", identity)
    write_json(DOC / "BCH_RTL_CONSTANT_CHECK.json", rtl_checks)
    write_csv(DOC / "FORMAL_PROOF_INDEX.csv", PROOF_COLUMNS, proof_rows)
    with (DOC / "COUNTEREXAMPLES.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for failure in failures:
            stream.write(json.dumps(failure, sort_keys=True) + "\n")
    write_json(DOC / "BCH_WEIGHT3_CHARACTERIZATION.json", characterization)
    summary = {
        "schema_version": 1,
        "status": "PASS" if not failures and characterization["status"] == "PASS" else "FAIL",
        "matrix_sha256": identity["matrix_sha256"],
        "bch_symbolic_proof_jobs": len(proof_rows),
        "bch_symbolic_proof_failures": len(failures),
        "weight3_characterization_status": characterization["status"],
    }
    write_json(DOC / "EXACT_PROOF_SUMMARY.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-job", help="re-evaluate a named proof job")
    args = parser.parse_args()
    if args.proof_job:
        identity = reconstruct()
        rows, failures = bch_symbolic_proofs(identity)
        matches = [row for row in rows if row["job_id"] == args.proof_job]
        if len(matches) != 1:
            print(json.dumps({"status": "ERROR", "job_id": args.proof_job}))
            return 2
        print(json.dumps(matches[0], sort_keys=True))
        return 1 if failures or matches[0]["status"] != "PASS" else 0
    summary = run_all()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
