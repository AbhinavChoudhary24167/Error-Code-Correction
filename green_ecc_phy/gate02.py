"""Deterministic mathematical evidence used by DATE 2027 Rigour Gate 02.

This module is deliberately internal.  It observes the public ``DecodeResult``
contract without changing it and derives a stricter, non-overlapping scientific
outcome taxonomy for audit evidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
from itertools import combinations
from math import comb
import time
from typing import Any, Iterable, Iterator, Mapping, Sequence

from codeforge.equivalence import primal_weight_enumerator_from_dual
from codeforge.gf2 import (
    bit_string,
    encode,
    is_zero_matrix,
    matmul,
    matrix_columns_as_ints,
    rank,
    syndrome_from_columns,
    transpose,
)

from .bch import BinaryExtensionField, primitive_bch_generator, primitive_bch_systematic
from .contracts import DecodeResult, DecodeStatus
from .hashing import canonical_hash


OUTCOMES = (
    "CLEAN",
    "CORRECTED",
    "DUE",
    "SDC_MISCORRECTION",
    "SDC_UNDETECTED",
    "INVALID_DECODER_STATE",
)


@dataclass(frozen=True)
class EvidenceObservation:
    transmitted_payload: int
    transmitted_codeword: int
    received_codeword: int
    error_mask: int
    decoded_payload: int | None
    reconstructed_codeword: int | None
    syndrome: int | str | None
    raw_status: str
    raw_detected: bool
    correction_attempted: bool
    raw_uncorrectable: bool
    output_valid: bool
    correction_action: int | tuple[int, ...] | None
    payload_matches: bool
    codeword_matches: bool
    outcome: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def observe_decode(
    result: DecodeResult,
    *,
    payload: int,
    codeword: int,
    received: int,
    error_mask: int,
    h: Sequence[Sequence[int]],
) -> EvidenceObservation:
    """Convert native flags into exactly one scientific outcome."""

    columns = matrix_columns_as_ints(h)
    reconstructed = result.corrected_codeword_optional
    output_valid = reconstructed is not None and syndrome_from_columns(reconstructed, columns) == 0
    payload_matches = result.data == payload
    codeword_matches = reconstructed == codeword
    raw_detected = result.status != DecodeStatus.NO_ERROR
    correction_attempted = (
        result.status == DecodeStatus.CORRECTED or result.error_location_optional is not None
    )
    raw_uncorrectable = result.status in {
        DecodeStatus.DETECTED_UNCORRECTABLE,
        DecodeStatus.ABSTAINED,
        DecodeStatus.UNSUPPORTED,
    }

    if error_mask == 0:
        outcome = (
            "CLEAN"
            if result.status == DecodeStatus.NO_ERROR
            and payload_matches
            and codeword_matches
            and output_valid
            else "INVALID_DECODER_STATE"
        )
    elif result.status == DecodeStatus.CORRECTED:
        outcome = "CORRECTED" if payload_matches and codeword_matches and output_valid else "SDC_MISCORRECTION"
    elif raw_uncorrectable:
        outcome = "DUE" if result.data is None and reconstructed is None else "INVALID_DECODER_STATE"
    elif result.status == DecodeStatus.NO_ERROR:
        outcome = "SDC_UNDETECTED" if not payload_matches else "INVALID_DECODER_STATE"
    else:
        outcome = "INVALID_DECODER_STATE"

    return EvidenceObservation(
        transmitted_payload=payload,
        transmitted_codeword=codeword,
        received_codeword=received,
        error_mask=error_mask,
        decoded_payload=result.data,
        reconstructed_codeword=reconstructed,
        syndrome=result.syndrome,
        raw_status=result.status.value,
        raw_detected=raw_detected,
        correction_attempted=correction_attempted,
        raw_uncorrectable=raw_uncorrectable,
        output_valid=output_valid,
        correction_action=result.error_location_optional,
        payload_matches=payload_matches,
        codeword_matches=codeword_matches,
        outcome=outcome,
    )


def exact_fraction(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        raise ValueError("fraction denominator must be positive")
    value = Fraction(numerator, denominator)
    return f"{value.numerator}/{value.denominator}"


def masks_of_weight(n: int, weight: int) -> Iterator[tuple[tuple[int, ...], int]]:
    for positions in combinations(range(n), weight):
        yield positions, sum(1 << position for position in positions)


def masks_for_positions(position_sets: Iterable[Sequence[int]]) -> Iterator[tuple[tuple[int, ...], int]]:
    seen: set[tuple[int, ...]] = set()
    for raw in position_sets:
        positions = tuple(sorted(map(int, raw)))
        if positions in seen:
            continue
        seen.add(positions)
        yield positions, sum(1 << position for position in positions)


def aggregate_universe(
    adapter: Any,
    h: Sequence[Sequence[int]],
    *,
    implementation_id: str,
    code_id: str,
    universe_id: str,
    masks: Iterable[tuple[tuple[int, ...], int]],
    declared_capability: str,
    universe_definition: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    transmitted_payload = 0
    transmitted_codeword = adapter.encode(transmitted_payload)
    counts = Counter({name: 0 for name in OUTCOMES})
    transcript = hashlib.sha256()
    first_failure: dict[str, Any] | None = None
    total = 0
    for positions, mask in masks:
        total += 1
        received = transmitted_codeword ^ mask
        observation = observe_decode(
            adapter.decode(received),
            payload=transmitted_payload,
            codeword=transmitted_codeword,
            received=received,
            error_mask=mask,
            h=h,
        )
        counts[observation.outcome] += 1
        transcript.update(
            f"{mask:x}|{observation.outcome}|{observation.raw_status}|"
            f"{observation.decoded_payload}|{observation.reconstructed_codeword}\n".encode("ascii")
        )
        acceptable = _outcome_acceptable(observation.outcome, declared_capability)
        if not acceptable and first_failure is None:
            first_failure = {
                "implementation_id": implementation_id,
                "code_id": code_id,
                "universe_id": universe_id,
                "payload": transmitted_payload,
                "codeword": transmitted_codeword,
                "error_positions": list(positions),
                "error_mask": mask,
                "received_word": received,
                "syndrome": observation.syndrome,
                "decoder_action": observation.correction_action,
                "decoded_output": observation.decoded_payload,
                "status_flags": {
                    "raw_status": observation.raw_status,
                    "detected": observation.raw_detected,
                    "correction_attempted": observation.correction_attempted,
                    "uncorrectable": observation.raw_uncorrectable,
                    "output_valid": observation.output_valid,
                },
                "expected_behavior": declared_capability,
                "observed_outcome": observation.outcome,
                "reproduction_command": (
                    "python scripts/verify_ecc_mathematics.py --all "
                    "--output docs/date2027/rigour_gate_02"
                ),
            }
    if total == 0:
        raise ValueError(f"empty universe: {implementation_id}/{universe_id}")
    corrected = counts["CORRECTED"]
    due = counts["DUE"]
    sdc = counts["SDC_MISCORRECTION"] + counts["SDC_UNDETECTED"]
    if declared_capability == "observation":
        gate_status = "FAIL" if counts["INVALID_DECODER_STATE"] else "PASS"
    else:
        gate_status = "PASS" if first_failure is None else "FAIL"
    aggregate = {
        "implementation_id": implementation_id,
        "code_id": code_id,
        "universe_id": universe_id,
        "universe_definition": universe_definition,
        "total_masks": total,
        "clean": counts["CLEAN"],
        "corrected": corrected,
        "due": due,
        "sdc_miscorrection": counts["SDC_MISCORRECTION"],
        "sdc_undetected": counts["SDC_UNDETECTED"],
        "invalid_state": counts["INVALID_DECODER_STATE"],
        "correction_fraction": exact_fraction(corrected, total),
        "due_fraction": exact_fraction(due, total),
        "safe_handling_fraction": exact_fraction(corrected + due, total),
        "detection_fraction": exact_fraction(corrected + due, total),
        "detection_fraction_definition": "safe detection coverage; CORRECTED + DUE only",
        "sdc_fraction": exact_fraction(sdc, total),
        "exhaustive": True,
        "translation_invariance_basis": "baseline/translation_invariance.json",
        "ordered_transcript_sha256": transcript.hexdigest(),
        "smallest_failure_witness": None if first_failure is None else {
            "error_positions": first_failure["error_positions"],
            "error_mask": first_failure["error_mask"],
            "observed_outcome": first_failure["observed_outcome"],
        },
        "declared_capability": declared_capability,
        "proven_capability": _proven_capability(counts, total),
        "gate_status": gate_status,
    }
    return aggregate, first_failure


def _outcome_acceptable(outcome: str, capability: str) -> bool:
    if capability == "clean":
        return outcome == "CLEAN"
    if capability in {"correction", "logical_storage_adjacency_correction_audit"}:
        return outcome == "CORRECTED"
    if capability in {"detection", "safe_handling"}:
        return outcome in {"CORRECTED", "DUE"}
    if capability == "observation":
        return outcome != "INVALID_DECODER_STATE"
    raise ValueError(f"unknown capability: {capability}")


def _proven_capability(counts: Mapping[str, int], total: int) -> str:
    if counts["CLEAN"] == total:
        return "clean"
    if counts["CORRECTED"] == total:
        return "correction"
    if counts["CORRECTED"] + counts["DUE"] == total:
        return "safe_handling"
    return "characterized_with_sdc_or_invalid_state"


def _xor_rows(row_masks: Sequence[int], selector: int) -> int:
    value = 0
    for index, row in enumerate(row_masks):
        if selector & (1 << index):
            value ^= row
    return value


def guarded_distance_certificate(
    code: Mapping[str, Any],
    *,
    verifier_sha256: str,
) -> dict[str, Any]:
    """Regenerate an exact guarded MacWilliams certificate or a designed bound."""

    h = code["_resolved_matrix"]["H"]
    g = code["_resolved_matrix"]["G"]
    n, k, r = int(code["n"]), int(code["k"]), int(code["redundancy"])
    claim = code["distance_evidence"]
    exact_claim = claim.get("exact_minimum_distance")
    started = time.perf_counter()
    matrix_hash = canonical_hash({"G": g, "H": h})
    common = {
        "code_id": code["code_id"],
        "n": n,
        "k": k,
        "r": r,
        "matrix_sha256": matrix_hash,
        "rank_h": rank(h),
        "rank_h_expected": r,
        "rank_h_guard": rank(h) == r,
        "verifier_sha256": verifier_sha256,
        "deterministic_configuration": {
            "dual_selector_order": "integer ascending",
            "witness_order": "lexicographic coordinate tuples",
            "integer_arithmetic": "Python arbitrary-precision integers only",
        },
    }
    if exact_claim is None:
        result = {
            **common,
            "distance_evidence": "DESIGNED_BOUND",
            "exact_minimum_distance": None,
            "designed_distance_lower_bound": claim.get("designed_distance_lower_bound"),
            "proof_method": claim.get("method"),
            "complete_checked_range": None,
            "lower_bound_proof": "BCH consecutive-root construction; not a primal enumerator",
            "upper_witness": None,
            "gate_status": "PASS" if common["rank_h_guard"] else "FAIL",
            "runtime_seconds": time.perf_counter() - started,
        }
        return result

    exact = int(exact_claim)
    if r > 16:
        return {
            **common,
            "distance_evidence": "UNRESOLVED",
            "exact_minimum_distance": None,
            "claimed_exact_minimum_distance": exact,
            "gate_status": "NOT ASSESSABLE",
            "blocking_guard": "complete dual enumeration is bounded to r<=16",
            "runtime_seconds": time.perf_counter() - started,
        }
    row_masks = [sum(int(bit) << position for position, bit in enumerate(row)) for row in h]
    dual_words = [_xor_rows(row_masks, selector) for selector in range(1 << r)]
    dual = [0] * (n + 1)
    for word in dual_words:
        dual[word.bit_count()] += 1
    primal = primal_weight_enumerator_from_dual(dual, r)
    primal_minimum = next((weight for weight, count in enumerate(primal[1:], 1) if count), None)
    witness_positions = lexicographic_zero_xor_support(matrix_columns_as_ints(h), exact)
    witness_mask = None if witness_positions is None else sum(1 << p for p in witness_positions)
    guards = {
        "rank_h_equals_r": rank(h) == r,
        "dual_selectors_enumerated": len(dual_words) == 1 << r,
        "dual_words_distinct": len(set(dual_words)) == 1 << r,
        "dual_sum_equals_2_pow_r": sum(dual) == 1 << r,
        "exact_integer_arithmetic": True,
        "primal_coefficients_nonnegative": all(value >= 0 for value in primal),
        "primal_sum_equals_2_pow_k": sum(primal) == 1 << k,
        "zero_coefficients_below_claim": all(primal[w] == 0 for w in range(1, exact)),
        "positive_coefficient_at_claim": primal[exact] > 0,
        "enumerator_minimum_matches_claim": primal_minimum == exact,
        "explicit_witness_exists": witness_positions is not None,
        "explicit_witness_weight_matches": witness_positions is not None and len(witness_positions) == exact,
        "explicit_witness_zero_syndrome": witness_mask is not None
        and syndrome_from_columns(witness_mask, matrix_columns_as_ints(h)) == 0,
        "enumerator_witness_agreement": witness_positions is not None and primal_minimum == len(witness_positions),
    }
    gate = "PASS" if all(guards.values()) else "FAIL"
    return {
        **common,
        "distance_evidence": "EXACT" if gate == "PASS" else "UNRESOLVED",
        "claimed_exact_minimum_distance": exact,
        "exact_minimum_distance": exact if gate == "PASS" else None,
        "proof_method": "complete dual enumeration + guarded exact MacWilliams + meet-in-the-middle witness",
        "complete_checked_range": [1, exact],
        "dual_selector_count": len(dual_words),
        "distinct_dual_word_count": len(set(dual_words)),
        "dual_weight_enumerator": dual,
        "primal_weight_enumerator": primal,
        "lower_bound_proof": {"zero_primal_weights": list(range(1, exact))},
        "upper_witness": {
            "positions": None if witness_positions is None else list(witness_positions),
            "mask": witness_mask,
            "mask_hex": None if witness_mask is None else hex(witness_mask),
            "weight": None if witness_positions is None else len(witness_positions),
            "syndrome": None if witness_mask is None else syndrome_from_columns(
                witness_mask, matrix_columns_as_ints(h)
            ),
        },
        "macwilliams_guards": guards,
        "gate_status": gate,
        "runtime_seconds": time.perf_counter() - started,
    }


def lexicographic_zero_xor_support(columns: Sequence[int], weight: int) -> tuple[int, ...] | None:
    """Find the lexicographically smallest zero-XOR support by exact MITM."""

    if weight < 1:
        raise ValueError("weight must be positive")
    left_weight = weight // 2
    right_weight = weight - left_weight
    right_by_xor: dict[int, list[tuple[int, ...]]] = defaultdict(list)
    for support in combinations(range(len(columns)), right_weight):
        value = 0
        for position in support:
            value ^= int(columns[position])
        right_by_xor[value].append(support)
    best: tuple[int, ...] | None = None
    for left in combinations(range(len(columns)), left_weight):
        value = 0
        for position in left:
            value ^= int(columns[position])
        for right in right_by_xor.get(value, ()):
            if set(left).isdisjoint(right):
                candidate = tuple(sorted((*left, *right)))
                if len(candidate) == weight and (best is None or candidate < best):
                    best = candidate
    return best


def verify_bch_construction(code: Mapping[str, Any]) -> dict[str, Any] | None:
    definition = code["matrix_definition"].get("deterministic_generator")
    if not definition or definition.get("callable") != "green_ecc_phy.bch:primitive_bch_systematic":
        return None
    parameters = dict(definition["parameters"])
    m = int(parameters["m"])
    t = int(parameters["t"])
    primitive = int(parameters["primitive_polynomial"])
    constructed = primitive_bch_systematic(**parameters)
    metadata = primitive_bch_generator(m=m, t=t, primitive_polynomial=primitive)
    generator = int(metadata["generator_polynomial"])
    parent_n = int(metadata["n_parent"])
    dividend = (1 << parent_n) | 1
    remainder = polynomial_remainder(dividend, generator)
    matrix = code["_resolved_matrix"]
    field = BinaryExtensionField(m, primitive)
    roots = {
        exponent: polynomial_at_field(generator, field.pow(2, exponent), field)
        for exponent in range(1, 2 * t + 1)
    }
    guards = {
        "primitive_field": field.order == parent_n,
        "required_roots_zero": all(value == 0 for value in roots.values()),
        "generator_degree_matches_r": int(metadata["generator_degree"]) == int(code["redundancy"]),
        "generator_divides_x_n_plus_1": remainder == 0,
        "matrix_matches_construction": constructed["G"] == matrix["G"] and constructed["H"] == matrix["H"],
        "correction_radius_matches": int(metadata["t"]) == t,
        "shortening_map_complete": len(constructed["coordinate_parent_exponents"]) == int(code["n"]),
    }
    return {
        "m": m,
        "primitive_polynomial": primitive,
        "primitive_polynomial_binary": metadata["primitive_polynomial_binary"],
        "primitive_element": "alpha=x mod primitive_polynomial",
        "cyclotomic_cosets": metadata["cyclotomic_cosets"],
        "root_exponents": metadata["root_exponents"],
        "generator_polynomial": generator,
        "generator_polynomial_binary": metadata["generator_polynomial_binary"],
        "generator_degree": metadata["generator_degree"],
        "designed_distance_lower_bound": metadata["designed_distance_lower_bound"],
        "t": t,
        "roots_evaluated": roots,
        "x_parent_n_plus_1_remainder": remainder,
        "coordinate_parent_exponents": constructed["coordinate_parent_exponents"],
        "shortening": constructed["shortening"],
        "guards": guards,
        "gate_status": "PASS" if all(guards.values()) else "FAIL",
    }


def polynomial_remainder(dividend: int, divisor: int) -> int:
    work = dividend
    degree = divisor.bit_length() - 1
    while work and work.bit_length() - 1 >= degree:
        work ^= divisor << (work.bit_length() - 1 - degree)
    return work


def polynomial_at_field(polynomial: int, value: int, field: BinaryExtensionField) -> int:
    result = 0
    power = 1
    for degree in range(polynomial.bit_length()):
        if polynomial & (1 << degree):
            result ^= power
        power = field.mul(power, value)
    return result


def translation_invariance_record(
    adapter: Any,
    h: Sequence[Sequence[int]],
    *,
    implementation_id: str,
    k: int,
    n: int,
) -> dict[str, Any]:
    payloads = [0, (1 << k) - 1, *(1 << bit for bit in range(k))]
    for index in range(16):
        digest = hashlib.sha256(f"gate02:{implementation_id}:{index}".encode()).digest()
        payloads.append(int.from_bytes(digest, "big") & ((1 << k) - 1))
    payloads = list(dict.fromkeys(payloads))
    probe_positions = [(), (0,), (n - 1,), (0, 1) if n > 1 else (0,)]
    if n > 2:
        probe_positions.append((0, 1, 2))
    probe_positions.extend((value % n,) for value in range(16))
    probes = list(masks_for_positions(probe_positions))
    baseline: dict[int, tuple[str, int | None, int | None]] = {}
    for _, mask in probes:
        result = adapter.decode(mask)
        observation = observe_decode(
            result, payload=0, codeword=0, received=mask, error_mask=mask, h=h
        )
        baseline[mask] = (
            observation.outcome,
            observation.decoded_payload,
            observation.reconstructed_codeword,
        )
    failures: list[dict[str, Any]] = []
    transcript = hashlib.sha256()
    for payload in payloads:
        codeword = adapter.encode(payload)
        for _, mask in probes:
            observation = observe_decode(
                adapter.decode(codeword ^ mask),
                payload=payload,
                codeword=codeword,
                received=codeword ^ mask,
                error_mask=mask,
                h=h,
            )
            base = baseline[mask]
            expected_payload = None if base[1] is None else base[1] ^ payload
            expected_codeword = None if base[2] is None else base[2] ^ codeword
            ok = (
                observation.outcome == base[0]
                and observation.decoded_payload == expected_payload
                and observation.reconstructed_codeword == expected_codeword
            )
            transcript.update(f"{payload:x}|{mask:x}|{observation.outcome}|{int(ok)}\n".encode())
            if not ok and len(failures) < 8:
                failures.append({"payload": payload, "mask": mask, "observation": observation.as_dict()})
    structural = type(adapter).__name__ in {
        "LinearSyndromeAdapter",
        "BoundedCyclicAdapter",
        "DeclaredSyndromeTableAdapter",
        "PrimitiveBCHAdapter",
    } or bool(getattr(adapter, "_gate02_structural_translation_invariant", False))
    return {
        "implementation_id": implementation_id,
        "encoder_linearity_basis": "G-row XOR encoder",
        "decoder_policy_basis": "syndrome-only lookup/action followed by XOR correction",
        "structural_policy_recognized": structural,
        "payload_basis": {
            "zero": True,
            "all_one": True,
            "basis_payload_count": k,
            "sha256_derived_payload_count": 16,
            "unique_payloads_checked": len(payloads),
        },
        "probe_mask_count": len(probes),
        "empirical_equivariance_passed": not failures,
        "failures": failures,
        "ordered_transcript_sha256": transcript.hexdigest(),
        "zero_codeword_reduction_proven": structural and not failures,
    }


def canonical_code_spec(code: Mapping[str, Any], implementations: Sequence[str]) -> dict[str, Any]:
    matrix = code["_resolved_matrix"]
    g, h = matrix["G"], matrix["H"]
    n, k, r = int(code["n"]), int(code["k"]), int(code["redundancy"])
    data_positions = list(map(int, code["systematic"]["data_positions"]))
    parity_positions = [position for position in range(n) if position not in set(data_positions)]
    generator = code["matrix_definition"].get("deterministic_generator")
    bch = verify_bch_construction(code)
    native_map: dict[str, Any]
    callable_name = None if generator is None else generator.get("callable")
    if callable_name == "green_ecc_phy.matrices:conventional_extended_hamming":
        from .matrices import conventional_extended_hamming

        native_order = conventional_extended_hamming(k=k)["native_coordinate_order"]
        native_map = {
            "kind": "canonical-to-positional-RTL",
            "canonical_to_native_zero_based": [value - 1 for value in native_order],
            "proof": "deterministic generator native_coordinate_order and systematic matrix identity",
        }
    elif callable_name in {
        "green_ecc_phy.matrices:cyclic_systematic",
        "green_ecc_phy.bch:primitive_bch_systematic",
    }:
        native_map = {
            "kind": "canonical-data-low-to-polynomial-parity-low",
            "canonical_to_native_zero_based": [r + value for value in range(k)] + list(range(r)),
            "proof": "systematic polynomial encoder: native=[parity low | data high]",
        }
    else:
        native_map = {
            "kind": "canonical-direct",
            "canonical_to_native_zero_based": list(range(n)),
            "proof": "registered systematic G/H and generated/archive coordinate labels",
        }
    identity = {
        "rank_g": rank(g),
        "rank_h": rank(h),
        "g_h_transpose_zero": is_zero_matrix(matmul(g, transpose(h))),
        "encoder_basis_codewords_valid": all(
            syndrome_from_columns(encode(1 << bit, g), matrix_columns_as_ints(h)) == 0
            for bit in range(k)
        ),
        "systematic_payload_extraction": all(
            ((encode(1 << bit, g) >> data_positions[bit]) & 1) == 1
            and sum((encode(1 << bit, g) >> p) & 1 for p in data_positions) == 1
            for bit in range(k)
        ),
        "matrix_sha256_matches_manifest": canonical_hash({"G": g, "H": h})
        == code["content_hashes"]["matrix_sha256"],
    }
    construction = {
        "matrix_definition": code["matrix_definition"],
        "source_provenance": code.get("source_provenance", []),
        "proof_references": code.get("proof_references", []),
        "bch": bch,
    }
    if code["code_id"] == "hsiao-secded-72-64-v1":
        columns = matrix_columns_as_ints(h)
        construction["hsiao_style_odd_column_checks"] = {
            "all_columns_odd": all(value.bit_count() % 2 == 1 for value in columns),
            "all_columns_distinct_nonzero": len(set(columns)) == n and all(columns),
            "claim_boundary": "Hsiao-style odd-column construction; no global minimum-total-ones optimality claim",
        }
    return {
        "code_id": code["code_id"],
        "canonical_name": code["name"],
        "family": code["family"],
        "n": n,
        "k": k,
        "r": r,
        "rate": exact_fraction(k, n),
        "linear": True,
        "systematic": bool(code["systematic"]["enabled"]),
        "data_positions": data_positions,
        "parity_positions": parity_positions,
        "storage_ordering": [
            {"storage_coordinate": position, "coordinate_type": "data" if position in data_positions else "parity"}
            for position in range(n)
        ],
        "bit_convention": "integer bit i is canonical storage coordinate i; little-index coordinate convention",
        "G": g,
        "H": h,
        "generator_polynomial": None if bch is None else bch["generator_polynomial"],
        "parent_and_shortening": code.get("shortening"),
        "construction": construction,
        "native_to_canonical_equivalence": native_map,
        "distance_claim": code["distance_evidence"],
        "declared_correction_universe": code.get("guaranteed_correction_set", []),
        "declared_detection_universe": code.get("guaranteed_detection_set", []),
        "decoder_outside_guarantee": code.get("known_miscorrection_domain", []),
        "implementation_ids": sorted(implementations),
        "identity_checks": identity,
        "identity_gate": "PASS" if all(identity.values()) else "FAIL",
    }


def universe_definitions_for(
    code: Mapping[str, Any], implementation: Mapping[str, Any]
) -> list[dict[str, Any]]:
    n, k = int(code["n"]), int(code["k"])
    implementation_id = str(implementation["implementation_id"])
    definitions = [
        {
            "universe_id": f"{implementation_id}:weight-{weight}",
            "kind": "all_combinations",
            "weight": weight,
            "coordinate_space": "canonical storage coordinates",
            "total_masks": comb(n, weight),
            "declared_capability": _weight_capability(code, implementation, weight),
        }
        for weight in range(4)
    ]
    if n <= 12:
        definitions.append(
            {
                "universe_id": f"{implementation_id}:all-masks",
                "kind": "all_masks",
                "weight": None,
                "coordinate_space": "canonical storage coordinates",
                "total_masks": 1 << n,
                "declared_capability": "observation",
            }
        )
    policy = str(implementation["adapter"]["parameters"].get("policy", ""))
    if policy in {"bounded_adjacent_double", "bounded_adjacent_triple"}:
        weight = 2 if policy.endswith("double") else 3
        definitions.extend(
            [
                {
                    "universe_id": f"{implementation_id}:logical-storage-noncircular-adjacent-{weight}",
                    "kind": "adjacent_windows",
                    "weight": weight,
                    "coordinate_space": "logical storage-coordinate adjacency; not physical adjacency",
                    "total_masks": n - weight + 1,
                    "declared_capability": "logical_storage_adjacency_correction_audit",
                    "coordinate_type_coverage": adjacency_type_coverage(k, n, weight),
                },
                {
                    "universe_id": f"{implementation_id}:historical-data-only-noncircular-adjacent-{weight}",
                    "kind": "data_adjacent_windows",
                    "weight": weight,
                    "coordinate_space": "historical adjacent payload indices; reported separately",
                    "total_masks": k - weight + 1,
                    "declared_capability": "correction",
                    "coordinate_type_coverage": {"data-data" if weight == 2 else "data-data-data": k - weight + 1},
                },
            ]
        )
    claims = implementation.get("capability_claims", {}).get("claimed_error_classes", [])
    for claim in claims:
        if claim.get("generator") == "explicit":
            positions = list(claim.get("positions", []))
            definitions.append(
                {
                    "universe_id": f"{implementation_id}:{claim['class_id']}",
                    "kind": "explicit",
                    "positions": positions,
                    "actual_position_weights": dict(sorted(Counter(len(item) for item in positions).items())),
                    "coordinate_space": "canonical storage coordinates from archived table",
                    "total_masks": len({tuple(sorted(item)) for item in positions}),
                    "declared_capability": "correction" if claim.get("kind") == "correction" else "detection",
                }
            )
    unique: dict[str, dict[str, Any]] = {}
    for item in definitions:
        unique[item["universe_id"]] = item
    return list(unique.values())


def _weight_capability(code: Mapping[str, Any], implementation: Mapping[str, Any], weight: int) -> str:
    if weight == 0:
        return "clean"
    correction_weights = {
        int(item["weight"])
        for item in code.get("guaranteed_correction_set", [])
        if item.get("generator") == "all_combinations"
    }
    detection_weights = {
        int(item["weight"])
        for item in code.get("guaranteed_detection_set", [])
        if item.get("generator") == "all_combinations"
    }
    if weight in correction_weights:
        return "correction"
    if weight in detection_weights:
        return "detection"
    return "observation"


def adjacency_type_coverage(k: int, n: int, weight: int) -> dict[str, int]:
    coverage: Counter[str] = Counter()
    for start in range(n - weight + 1):
        types = ["data" if position < k else "parity" for position in range(start, start + weight)]
        coverage["-".join(types)] += 1
    return dict(sorted(coverage.items()))


def masks_for_definition(definition: Mapping[str, Any], n: int, k: int) -> Iterator[tuple[tuple[int, ...], int]]:
    kind = definition["kind"]
    if kind == "all_combinations":
        yield from masks_of_weight(n, int(definition["weight"]))
    elif kind == "all_masks":
        for mask in range(1 << n):
            yield tuple(position for position in range(n) if mask & (1 << position)), mask
    elif kind == "adjacent_windows":
        weight = int(definition["weight"])
        yield from masks_for_positions(tuple(range(start, start + weight)) for start in range(n - weight + 1))
    elif kind == "data_adjacent_windows":
        weight = int(definition["weight"])
        yield from masks_for_positions(tuple(range(start, start + weight)) for start in range(k - weight + 1))
    elif kind == "explicit":
        yield from masks_for_positions(definition["positions"])
    else:
        raise ValueError(f"unsupported universe kind: {kind}")


def validate_aggregate(aggregate: Mapping[str, Any]) -> None:
    total = int(aggregate["total_masks"])
    fields = ("clean", "corrected", "due", "sdc_miscorrection", "sdc_undetected", "invalid_state")
    if sum(int(aggregate[field]) for field in fields) != total:
        raise ValueError("aggregate outcome counts do not sum to total_masks")
    corrected = int(aggregate["corrected"])
    due = int(aggregate["due"])
    sdc = int(aggregate["sdc_miscorrection"]) + int(aggregate["sdc_undetected"])
    expected = {
        "correction_fraction": exact_fraction(corrected, total),
        "due_fraction": exact_fraction(due, total),
        "safe_handling_fraction": exact_fraction(corrected + due, total),
        "detection_fraction": exact_fraction(corrected + due, total),
        "sdc_fraction": exact_fraction(sdc, total),
    }
    for field, value in expected.items():
        if aggregate[field] != value:
            raise ValueError(f"aggregate {field} is inconsistent")
