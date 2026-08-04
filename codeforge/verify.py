"""Independent matrix, syndrome-decoder, and probability-mass verifier."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import random
from typing import Any, Mapping, Sequence

from .faults import ErrorPattern, FaultDistribution
from .gf2 import (
    bit_string,
    encode,
    encode_from_row_masks,
    generator_row_masks,
    is_zero_matrix,
    matmul,
    positions_to_mask,
    rank,
    syndrome,
    syndrome_from_columns,
    transpose,
    validate_matrix,
)


OUTCOMES = (
    "correct",
    "corrected",
    "detected_uncorrectable",
    "silent_corruption",
    "decoder_failure",
)


class VerificationError(ValueError):
    """Raised when a code document is structurally invalid."""


@dataclass(frozen=True)
class DecodeResult:
    outcome: str
    syndrome: int
    decoded_data: int | None
    correction_mask: int


def _decoder_map(code: Mapping[str, Any], n: int, r: int) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for entry in code.get("decoder", {}).get("correction_entries", []):
        raw_syndrome = entry["syndrome"]
        syndrome_value = int(raw_syndrome, 2) if isinstance(raw_syndrome, str) else int(raw_syndrome)
        if syndrome_value <= 0 or syndrome_value >= (1 << r):
            raise VerificationError(f"invalid correction syndrome {raw_syndrome!r}")
        if syndrome_value in mapping:
            raise VerificationError(f"duplicate correction entry for syndrome {bit_string(syndrome_value, r)}")
        mapping[syndrome_value] = positions_to_mask(entry["positions"], n)
    return mapping


def decode_word(
    received: int,
    *,
    original_data: int,
    h: Sequence[Sequence[int]],
    k: int,
    decoder_map: Mapping[int, int],
    h_columns: Sequence[int] | None = None,
) -> DecodeResult:
    syndrome_value = (
        syndrome_from_columns(received, h_columns)
        if h_columns is not None
        else syndrome(received, h)
    )
    if syndrome_value == 0:
        decoded = received & ((1 << k) - 1)
        return DecodeResult(
            outcome="correct" if decoded == original_data else "silent_corruption",
            syndrome=0,
            decoded_data=decoded,
            correction_mask=0,
        )
    if syndrome_value not in decoder_map:
        return DecodeResult(
            outcome="detected_uncorrectable",
            syndrome=syndrome_value,
            decoded_data=None,
            correction_mask=0,
        )
    correction_mask = int(decoder_map[syndrome_value])
    corrected_word = received ^ correction_mask
    corrected_syndrome = (
        syndrome_from_columns(corrected_word, h_columns)
        if h_columns is not None
        else syndrome(corrected_word, h)
    )
    if corrected_syndrome != 0:
        return DecodeResult(
            outcome="decoder_failure",
            syndrome=syndrome_value,
            decoded_data=None,
            correction_mask=correction_mask,
        )
    decoded = corrected_word & ((1 << k) - 1)
    return DecodeResult(
        outcome="corrected" if decoded == original_data else "silent_corruption",
        syndrome=syndrome_value,
        decoded_data=decoded,
        correction_mask=correction_mask,
    )


def _validate_code_structure(code: Mapping[str, Any]) -> tuple[int, int, int, list[list[int]], list[list[int]]]:
    k = int(code["k"])
    r = int(code["r"])
    n = int(code["n"])
    if n != k + r:
        raise VerificationError(f"n={n} must equal k+r={k+r}")
    h = [[int(value) for value in row] for row in code["H"]]
    g = [[int(value) for value in row] for row in code["G"]]
    h_rows, h_cols = validate_matrix(h, name="H")
    g_rows, g_cols = validate_matrix(g, name="G")
    if (h_rows, h_cols) != (r, n):
        raise VerificationError(f"H has shape {h_rows}x{h_cols}, expected {r}x{n}")
    if (g_rows, g_cols) != (k, n):
        raise VerificationError(f"G has shape {g_rows}x{g_cols}, expected {k}x{n}")
    return k, r, n, h, g


def verify_code_document(
    code: Mapping[str, Any],
    distribution: FaultDistribution,
    *,
    exhaustive_data_limit_bits: int = 12,
    random_data_trials: int = 2048,
    random_seed: int = 0,
) -> dict[str, Any]:
    """Verify a supplied code independently of the synthesis implementation."""

    k, r, n, h, g = _validate_code_structure(code)
    if distribution.bit_width != n:
        raise VerificationError(
            f"fault distribution width {distribution.bit_width} does not match code n={n}"
        )
    h_rank = rank(h)
    orthogonality = matmul(g, transpose(h))
    orthogonal = is_zero_matrix(orthogonality)
    systematic_h = all(
        h[row][k + col] == (1 if row == col else 0)
        for row in range(r)
        for col in range(r)
    )
    systematic_g = all(
        g[row][col] == (1 if row == col else 0)
        for row in range(k)
        for col in range(k)
    )
    decoder_map = _decoder_map(code, n, r)
    h_columns = [
        sum(int(h[row][col]) << row for row in range(r)) for col in range(n)
    ]
    g_row_masks = generator_row_masks(g)
    if any(
        syndrome_from_columns(mask, h_columns) != syndrome_value
        for syndrome_value, mask in decoder_map.items()
    ):
        raise VerificationError("decoder correction entry does not match its declared syndrome")

    if k <= exhaustive_data_limit_bits:
        data_words = list(range(1 << k))
        data_campaign = "exhaustive"
        linearity_reduction = False
    else:
        rng = random.Random(random_seed)
        edge_words = {0, (1 << k) - 1}
        data_words = sorted(edge_words | {rng.getrandbits(k) for _ in range(random_data_trials)})
        data_campaign = "seeded_random_plus_edges"
        linearity_reduction = True

    per_pattern: list[dict[str, Any]] = []
    probability_mass = Counter({outcome: 0.0 for outcome in OUTCOMES})
    total_cases = 0
    outcome_consistent = True
    expected_outcome_by_pattern: dict[str, str] = {}
    for pattern in distribution.patterns:
        mask = pattern.mask(n)
        observed: Counter[str] = Counter()
        syndrome_value = syndrome_from_columns(mask, h_columns)
        verification_words = data_words if not linearity_reduction else [0]
        for data in verification_words:
            codeword = encode_from_row_masks(data, g_row_masks)
            if syndrome_from_columns(codeword, h_columns) != 0:
                raise VerificationError("encoder generated a non-codeword")
            result = decode_word(
                codeword ^ mask,
                original_data=data,
                h=h,
                k=k,
                decoder_map=decoder_map,
                h_columns=h_columns,
            )
            observed[result.outcome] += 1
            total_cases += 1
        if len(observed) != 1:
            outcome_consistent = False
            outcome = "decoder_failure"
        else:
            outcome = next(iter(observed))
        probability_mass[outcome] += pattern.probability
        expected_outcome_by_pattern[pattern.pattern_id] = outcome
        per_pattern.append(
            {
                "pattern_id": pattern.pattern_id,
                "family": pattern.family,
                "positions": list(pattern.positions),
                "probability": pattern.probability,
                "syndrome": bit_string(syndrome_value, r),
                "outcome": outcome,
                "data_outcomes": dict(sorted(observed.items())),
            }
        )

    randomized_modeled_checks = 0
    randomized_beyond_universe_checks = 0
    beyond_universe_outcomes: Counter[str] = Counter()
    if linearity_reduction:
        rng = random.Random(random_seed)
        patterns = list(distribution.patterns)
        for index, data in enumerate(data_words):
            pattern = patterns[index % len(patterns)]
            codeword = encode_from_row_masks(data, g_row_masks)
            result = decode_word(
                codeword ^ pattern.mask(n),
                original_data=data,
                h=h,
                k=k,
                decoder_map=decoder_map,
                h_columns=h_columns,
            )
            if result.outcome != expected_outcome_by_pattern[pattern.pattern_id]:
                outcome_consistent = False
            randomized_modeled_checks += 1
            multiplicity = rng.randint(1, min(4, n))
            random_mask = positions_to_mask(rng.sample(range(n), multiplicity), n)
            random_result = decode_word(
                codeword ^ random_mask,
                original_data=data,
                h=h,
                k=k,
                decoder_map=decoder_map,
                h_columns=h_columns,
            )
            beyond_universe_outcomes[random_result.outcome] += 1
            randomized_beyond_universe_checks += 1
            if random_result.outcome == "decoder_failure":
                outcome_consistent = False
        total_cases += randomized_modeled_checks + randomized_beyond_universe_checks

    no_error_ok = True
    for data in data_words:
        codeword = encode_from_row_masks(data, g_row_masks)
        result = decode_word(
            codeword,
            original_data=data,
            h=h,
            k=k,
            decoder_map=decoder_map,
            h_columns=h_columns,
        )
        no_error_ok = no_error_ok and result.outcome == "correct"

    corrected_probability = probability_mass["corrected"] + probability_mass["correct"]
    due_probability = probability_mass["detected_uncorrectable"]
    sdc_probability = probability_mass["silent_corruption"]
    decoder_failure_probability = probability_mass["decoder_failure"]
    residual_probability = due_probability + sdc_probability + decoder_failure_probability
    raw_fit = distribution.raw_fit
    declared = code.get("constraints", {})
    max_sdc = declared.get("max_sdc_probability")
    max_residual_fit = declared.get("max_residual_fit")
    constraint_results = {
        "max_sdc_probability": {
            "limit": max_sdc,
            "actual": sdc_probability,
            "satisfied": max_sdc is None or sdc_probability <= float(max_sdc) + 1e-15,
        },
        "max_residual_fit": {
            "limit": max_residual_fit,
            "actual": raw_fit * residual_probability if raw_fit is not None else None,
            "satisfied": (
                max_residual_fit is None
                or (
                    raw_fit is not None
                    and raw_fit * residual_probability <= float(max_residual_fit) + 1e-15
                )
            ),
        },
    }
    matrix_checks = {
        "rank_h": h_rank,
        "rank_h_expected": r,
        "full_rank": h_rank == r,
        "g_h_transpose_zero": orthogonal,
        "systematic_h": systematic_h,
        "systematic_g": systematic_g,
    }
    passed = (
        all(matrix_checks.values())
        and no_error_ok
        and outcome_consistent
        and all(item["satisfied"] for item in constraint_results.values())
        and math.isclose(sum(probability_mass.values()), 1.0, rel_tol=0.0, abs_tol=1e-12)
    )
    return {
        "schema_version": 1,
        "verification_status": "passed" if passed else "failed",
        "code_id": str(code.get("code_id", "external-code")),
        "distribution_id": distribution.distribution_id,
        "dimensions": {"k": k, "r": r, "n": n},
        "matrix_checks": matrix_checks,
        "decoder_checks": {
            "correction_entries": len(decoder_map),
            "no_error_identity": no_error_ok,
            "outcome_independent_of_data": outcome_consistent,
        },
        "campaign": {
            "kind": data_campaign,
            "data_words": len(data_words),
            "error_patterns": len(distribution.patterns),
            "decoder_cases": total_cases,
            "random_seed": random_seed if data_campaign != "exhaustive" else None,
            "modeled_error_vectors_exhaustive": True,
            "linearity_reduction_applied": linearity_reduction,
            "randomized_modeled_checks": randomized_modeled_checks,
            "randomized_beyond_universe_checks": randomized_beyond_universe_checks,
            "beyond_universe_outcomes": dict(sorted(beyond_universe_outcomes.items())),
        },
        "probability_mass": {
            "corrected": corrected_probability,
            "due": due_probability,
            "sdc": sdc_probability,
            "decoder_failure": decoder_failure_probability,
            "residual": residual_probability,
            "sum": math.fsum(probability_mass.values()),
        },
        "fit": {
            "raw_fit": raw_fit,
            "residual_fit": raw_fit * residual_probability if raw_fit is not None else None,
            "sdc_fit": raw_fit * sdc_probability if raw_fit is not None else None,
            "model": "raw_fit multiplied by conditional modeled-error outcome mass",
        },
        "constraint_results": constraint_results,
        "per_pattern": per_pattern,
        "limitations": [
            "The probability results are conditional on the supplied finite error universe.",
            "Physical PPA is not inferred from structural verification.",
        ],
    }
