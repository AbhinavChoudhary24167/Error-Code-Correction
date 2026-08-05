from __future__ import annotations

from pathlib import Path

from green_ecc_phy.contracts import DecodeResult, DecodeStatus
from green_ecc_phy.gate02 import (
    adjacency_type_coverage,
    aggregate_universe,
    canonical_code_spec,
    guarded_distance_certificate,
    masks_for_definition,
    observe_decode,
    universe_definitions_for,
    validate_aggregate,
)
from green_ecc_phy.hashing import scientific_file_sha256
from green_ecc_phy.registry import EccRegistry


ROOT = Path(__file__).resolve().parents[2]


def _registry() -> EccRegistry:
    return EccRegistry.builtin(ROOT)


def test_detected_miscorrection_is_not_safe_detection() -> None:
    registry = _registry()
    code = registry.code("extended-hamming-secded-72-64-v1")
    result = DecodeResult(
        data=1,
        status=DecodeStatus.CORRECTED,
        syndrome=7,
        corrected_codeword_optional=1,
        error_location_optional=0,
        latency=0,
    )
    observation = observe_decode(
        result,
        payload=0,
        codeword=0,
        received=7,
        error_mask=7,
        h=code["_resolved_matrix"]["H"],
    )
    assert observation.raw_detected
    assert observation.outcome == "SDC_MISCORRECTION"


def test_aggregate_uses_exact_safe_detection_equations() -> None:
    registry = _registry()
    implementation_id = "secded-rtl-combinational-72-64-v1"
    code = registry.code("extended-hamming-secded-72-64-v1")
    definition = {
        "kind": "all_combinations",
        "weight": 2,
        "declared_capability": "detection",
    }
    aggregate, witness = aggregate_universe(
        registry.adapter(implementation_id),
        code["_resolved_matrix"]["H"],
        implementation_id=implementation_id,
        code_id=code["code_id"],
        universe_id="double",
        masks=masks_for_definition(definition, 72, 64),
        declared_capability="detection",
        universe_definition="all weight-2 masks",
    )
    validate_aggregate(aggregate)
    assert witness is None
    assert aggregate["due"] == 2556
    assert aggregate["safe_handling_fraction"] == "1/1"
    assert aggregate["detection_fraction"] == "1/1"


def test_full_storage_adjacency_includes_parity_boundary_and_parity_only() -> None:
    pair = adjacency_type_coverage(64, 72, 2)
    triple = adjacency_type_coverage(64, 72, 3)
    assert pair == {"data-data": 63, "data-parity": 1, "parity-parity": 7}
    assert triple["data-data-parity"] == 1
    assert triple["data-parity-parity"] == 1
    assert triple["parity-parity-parity"] == 6


def test_adjacency_universes_are_complete_and_data_only_is_separate() -> None:
    registry = _registry()
    implementation = registry.implementation("secdaec-rtl-bounded-72-64-v1")
    code = registry.code(str(implementation["code_id"]))
    definitions = universe_definitions_for(code, implementation)
    by_id = {item["universe_id"]: item for item in definitions}
    full = by_id[f"{implementation['implementation_id']}:logical-storage-noncircular-adjacent-2"]
    historical = by_id[f"{implementation['implementation_id']}:historical-data-only-noncircular-adjacent-2"]
    assert full["total_masks"] == 71
    assert historical["total_masks"] == 63
    assert full["coordinate_space"].startswith("logical storage-coordinate")


def test_exact_distance_certificate_has_every_macwilliams_guard() -> None:
    registry = _registry()
    code = registry.code("odd-column-secded-4-8")
    certificate = guarded_distance_certificate(
        code,
        verifier_sha256=scientific_file_sha256(ROOT / "green_ecc_phy" / "gate02.py"),
    )
    assert certificate["distance_evidence"] == "EXACT"
    assert certificate["gate_status"] == "PASS"
    assert all(certificate["macwilliams_guards"].values())
    assert certificate["upper_witness"]["weight"] == 4


def test_t3_shortened_bch_remains_only_a_designed_bound() -> None:
    registry = _registry()
    code = registry.code("shortened-bch-85-64-t3-v1")
    certificate = guarded_distance_certificate(
        code,
        verifier_sha256=scientific_file_sha256(ROOT / "green_ecc_phy" / "gate02.py"),
    )
    assert certificate["distance_evidence"] == "DESIGNED_BOUND"
    assert certificate["exact_minimum_distance"] is None
    assert certificate["designed_distance_lower_bound"] == 7


def test_canonical_spec_records_complete_native_mapping() -> None:
    registry = _registry()
    code = registry.code("extended-hamming-secded-72-64-v1")
    spec = canonical_code_spec(
        code,
        [
            identifier
            for identifier, implementation in registry.implementations.items()
            if implementation["code_id"] == code["code_id"]
        ],
    )
    mapping = spec["native_to_canonical_equivalence"]["canonical_to_native_zero_based"]
    assert sorted(mapping) == list(range(72))
    assert len(spec["G"]) == 64
    assert len(spec["H"]) == 8
    assert spec["identity_gate"] == "PASS"
