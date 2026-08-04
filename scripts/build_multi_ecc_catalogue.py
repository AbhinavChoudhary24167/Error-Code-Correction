#!/usr/bin/env python3
"""Deterministically materialize the built-in GREEN-ECC-PHY catalogue and hashes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from codeforge.artifacts import render_systemverilog
from codeforge.equivalence import weight_enumerators
from codeforge.gf2 import matrix_columns_as_ints
from green_ecc_phy.bch import primitive_bch_generator, primitive_bch_systematic
from green_ecc_phy.hashing import canonical_hash, file_sha256, manifest_sha256
from green_ecc_phy.matrices import conventional_extended_hamming, cyclic_systematic, hsiao_odd_column


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_sources(root: Path, paths: list[str]) -> dict[str, str]:
    return {path: file_sha256(root / path) for path in paths}


def _finalize_code(root: Path, payload: dict[str, Any], matrix: Mapping[str, Any], sources: list[str]) -> dict[str, Any]:
    payload["content_hashes"] = {
        "algorithm": "sha256",
        "manifest_sha256": "0" * 64,
        "matrix_sha256": canonical_hash({"G": matrix["G"], "H": matrix["H"]}),
        "source_files": _hash_sources(root, sources),
    }
    payload["content_hashes"]["manifest_sha256"] = manifest_sha256(payload)
    return payload


def _finalize_manifest(root: Path, payload: dict[str, Any], sources: list[str]) -> dict[str, Any]:
    payload["source_hashes"] = _hash_sources(root, sources)
    payload["manifest_sha256"] = "0" * 64
    payload["manifest_sha256"] = manifest_sha256(payload)
    return payload


def _error_class(class_id: str, weight: int, statuses: list[str]) -> dict[str, Any]:
    return {
        "class_id": class_id,
        "generator": "all_combinations",
        "weight": weight,
        "acceptable_statuses": statuses,
    }


def _code_base(
    *, code_id: str, equivalence_id: str, family: str, name: str, k: int, n: int,
    generator: str, parameters: Mapping[str, Any], correction: list[dict[str, Any]],
    detection: list[dict[str, Any]], miscorrection: list[dict[str, Any]],
    unsupported: list[str], decoder_policy: Mapping[str, Any], provenance: list[dict[str, str]],
    distance_evidence: Mapping[str, Any] | None = None,
    shortening: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "code_spec_id": code_id,
        "encoder_id": f"{code_id}-systematic-encoder",
        "code_id": code_id,
        "canonical_equivalence_class_id": equivalence_id,
        "family": family,
        "name": name,
        "version": "1.0.0",
        "field": {"kind": "GF(2)", "order": 2},
        "k": k,
        "n": n,
        "redundancy": n - k,
        "symbol_width": 1,
        "systematic": {"enabled": True, "data_positions": list(range(k))},
        "matrix_definition": {"deterministic_generator": {"callable": generator, "parameters": dict(parameters)}},
        "shortening": dict(shortening or {"enabled": False, "parameters": None}),
        "puncturing": {"enabled": False, "parameters": None},
        "guaranteed_correction_set": correction,
        "guaranteed_detection_set": detection,
        "known_miscorrection_domain": miscorrection,
        "unsupported_error_classes": unsupported,
        "distance_evidence": dict(distance_evidence or {"exact_minimum_distance": None, "designed_distance_lower_bound": None, "method": "not established"}),
        "decoder_policy": dict(decoder_policy),
        "proof_references": provenance,
        "source_provenance": provenance,
        "license": "MIT repository code; cited evidence retains its original provenance",
    }


def _implementation(
    *, implementation_id: str, code_id: str, sources: list[str], encoder: str | None,
    decoder: str | None, wrapper: str | None, policy: str, adapter_factory: str,
    adapter_parameters: Mapping[str, Any], compatible: list[str], evidence_path: str,
    evidence_test_id: str, capabilities: Mapping[str, Any], parameters: Mapping[str, Any] | None = None,
    verified_capabilities: list[str] | None = None,
    failed_capabilities: list[str] | None = None,
    unsupported_capabilities: list[str] | None = None,
    architecture_style: str = "combinational",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "code_spec_id": code_id,
        "encoder_id": f"{code_id}-systematic-encoder",
        "implementation_id": implementation_id,
        "code_id": code_id,
        "version": "1.0.0",
        "source_files": sources,
        "encoder_top": encoder,
        "decoder_top": decoder,
        "wrapper_module": wrapper,
        "configuration_modules": [],
        "parameters": dict(parameters or {}),
        "architecture_style": architecture_style,
        "pipeline_stages": 0,
        "initiation_interval": 1,
        "encoder_latency": 0,
        "decoder_latency": 0,
        "clock_reset": {"clock_required": False, "reset_required": False},
        "transaction_protocol": {"kind": "combinational_request_response", "backpressure": False},
        "output_status_semantics": {
            "native_flags_are_adapted": True,
            "harness_derives_miscorrected_from_golden_data": True,
        },
        "decoder_policy_id": policy,
        "metadata_requirements": {"bits_per_codeword": 0},
        "mux_requirements": {"required_in_fixed_mode": False, "architecture_owned": True},
        "controller_requirements": {"required_in_fixed_mode": False, "architecture_owned": True},
        "reencoding_requirements": {"required_for_code_transition": True, "architecture_owned": True},
        "compatible_deployment_architectures": compatible,
        "adapter": {"factory": adapter_factory, "parameters": dict(adapter_parameters)},
        "verification_vectors": {"miscorrection_probes": []},
        "verification_evidence": [
            {
                "kind": "rtl_reference_differential",
                "path": evidence_path,
                "test_id": evidence_test_id,
                "status": "passed",
            }
        ],
        "capability_claims": {
            "data_independence_proof": "linear encoder and translation-invariant syndrome decoder; outcomes depend only on the error mask",
            **dict(capabilities),
        },
        "verified_capabilities": list(verified_capabilities or []),
        "failed_capabilities": list(failed_capabilities or []),
        "unsupported_capabilities": list(unsupported_capabilities or []),
        "backend_id": None,
        "evidence_level": "exact_functional_reference" if architecture_style == "reference_only" else "rtl_and_exact_functional",
        "source_provenance": [{"path": path, "role": "RTL/reference/evidence"} for path in sources],
        "license": "MIT repository code",
    }


def build(root: Path) -> None:
    physical_root = root / "green_ecc_physical_simulation"
    registry_root = physical_root / "registry"
    generated_rtl = physical_root / "rtl" / "hsiao_secded_72_64"

    hsiao = hsiao_odd_column(k=64, redundancy=8)
    columns = matrix_columns_as_ints(hsiao["H"])
    generated_code = {
        "code_id": "hsiao-secded-72-64-v1", "k": 64, "r": 8, "n": 72,
        "H": hsiao["H"], "G": hsiao["G"],
        "decoder": {
            "correction_entries": [
                {"syndrome": f"{column:08b}", "positions": [position]}
                for position, column in enumerate(columns)
            ]
        },
    }
    rtl = render_systemverilog(generated_code)
    for name, contents in rtl.items():
        path = generated_rtl / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")

    evidence = "reports/safeforge_hardware_validation/validation_summary.json"
    hsiao_code_sources = ["codeforge/gf2.py", "codeforge/artifacts.py", "reports/safeforge_decisive_72/code_and_evidence_audit.json"]
    hsiao_code = _code_base(
        code_id="hsiao-secded-72-64-v1",
        equivalence_id="binary-72-64-hsiao-minimum-odd-column-v1",
        family="Hsiao SECDED",
        name="Hsiao minimum-total-ones SECDED (72,64)",
        k=64, n=72,
        generator="green_ecc_phy.matrices:hsiao_odd_column",
        parameters={"k": 64, "redundancy": 8},
        correction=[_error_class("all-single-bit-errors", 1, ["CORRECTED"])],
        detection=[_error_class("all-double-bit-errors", 2, ["CORRECTED", "DETECTED_UNCORRECTABLE"])],
        miscorrection=[{"domain": "weight>=3 outside guaranteed SECDED universe", "expected_behavior": "may miscorrect"}],
        unsupported=["guaranteed correction of weight >=2", "guaranteed detection of weight >=3"],
        decoder_policy={"policy_id": "minimum-weight-single-syndrome-v1", "nonzero_unknown_syndrome": "DETECTED_UNCORRECTABLE"},
        distance_evidence={"exact_minimum_distance": 4, "designed_distance_lower_bound": 4, "method": "exact dual enumeration plus binary MacWilliams transform"},
        provenance=[
            {"path": "codeforge/gf2.py", "role": "deterministic matrix construction"},
            {"path": "reports/safeforge_decisive_72/code_and_evidence_audit.json", "role": "classification and prior verification evidence"},
        ],
    )
    _write(registry_root / "codes" / "hsiao-secded-72-64-v1.json", _finalize_code(root, hsiao_code, hsiao, hsiao_code_sources))

    positional = conventional_extended_hamming(k=64)
    positional_sources = ["asic/include/ecc_pkg.sv", "asic/rtl/secded/secded_codec.sv", "asic/tb/tb_secded.sv"]
    positional_code = _code_base(
        code_id="extended-hamming-secded-72-64-v1",
        equivalence_id="binary-72-64-conventional-extended-hamming-v1",
        family="Extended Hamming SECDED",
        name="Conventional positional extended-Hamming SECDED (72,64)",
        k=64, n=72,
        generator="green_ecc_phy.matrices:conventional_extended_hamming",
        parameters={"k": 64},
        correction=[_error_class("all-single-bit-errors", 1, ["CORRECTED"])],
        detection=[_error_class("all-double-bit-errors", 2, ["CORRECTED", "DETECTED_UNCORRECTABLE"])],
        miscorrection=[{"domain": "odd weight >=3", "expected_behavior": "may alias a single-error syndrome"}],
        unsupported=["guaranteed adjacent-double correction", "guaranteed adjacent-triple correction", "guaranteed correction of weight >=2"],
        decoder_policy={
            "policy_id": "repository-policy-family-v1",
            "variants": ["secded", "bounded-adjacent-double", "bounded-adjacent-triple"],
            "note": "decoder variants do not create distinct mathematical codewords",
        },
        distance_evidence={"exact_minimum_distance": 4, "designed_distance_lower_bound": 4, "method": "exact dual enumeration plus binary MacWilliams transform"},
        provenance=[
            {"path": "asic/rtl/secded/secded_codec.sv", "role": "repository RTL encoder and baseline decoder"},
            {"path": "asic/tb/tb_secded.sv", "role": "RTL functional test"},
        ],
    )
    _write(registry_root / "codes" / "extended-hamming-secded-72-64-v1.json", _finalize_code(root, positional_code, positional, positional_sources))

    bch = cyclic_systematic(n=63, k=51, generator_polynomial=0b1000111101011)
    bch_sources = ["asic/rtl/bch/bch_codec.sv", "asic/tb/tb_bch.sv"]
    bch_code = _code_base(
        code_id="repository-cyclic-63-51-v1",
        equivalence_id="repository-degree12-cyclic-63-51-v1",
        family="BCH candidate / cyclic code",
        name="Repository degree-12 systematic cyclic (63,51) code",
        k=51, n=63,
        generator="green_ecc_phy.matrices:cyclic_systematic",
        parameters={"n": 63, "k": 51, "generator_polynomial": 0b1000111101011},
        correction=[_error_class("all-single-bit-errors", 1, ["CORRECTED"])],
        detection=[],
        miscorrection=[{"domain": "some triple-bit errors", "expected_behavior": "known <=2-search alias"}],
        unsupported=["BCH distance-5 claim", "guaranteed double-error correction", "guaranteed triple-error detection"],
        decoder_policy={"policy_id": "bounded-valid-codeword-search-weight2-v1", "search_weight": 2},
        distance_evidence={"exact_minimum_distance": 2, "designed_distance_lower_bound": None, "method": "exact dual enumeration plus binary MacWilliams transform"},
        provenance=[
            {"path": "asic/rtl/bch/bch_codec.sv", "role": "systematic polynomial encoder and bounded decoder"},
            {"path": "asic/tb/tb_bch.sv", "role": "positive and negative RTL tests"},
        ],
    )
    _write(registry_root / "codes" / "repository-cyclic-63-51-v1.json", _finalize_code(root, bch_code, bch, bch_sources))

    # A separately identified, mathematically valid primitive BCH portfolio.
    # The historical RTL candidate above remains untouched and rejected.
    bch_certificate_path = "green_ecc_physical_simulation/evidence/primitive_bch_construction_certificate.json"
    bch_test_path = "tests/python/test_bch_reference.py"
    reference_bch_specs = [
        {
            "code_id": "primitive-bch-63-51-t2-v1", "m": 6, "t": 2,
            "primitive_polynomial": 0x43, "shortened_k": None,
            "name": "Primitive narrow-sense BCH (63,51,t=2)",
        },
        {
            "code_id": "shortened-bch-71-64-t1-v1", "m": 7, "t": 1,
            "primitive_polynomial": 0x83, "shortened_k": 64,
            "name": "Shortened primitive BCH (71,64,t=1)",
        },
        {
            "code_id": "shortened-bch-78-64-t2-v1", "m": 7, "t": 2,
            "primitive_polynomial": 0x83, "shortened_k": 64,
            "name": "Shortened primitive BCH (78,64,t=2)",
        },
        {
            "code_id": "shortened-bch-85-64-t3-v1", "m": 7, "t": 3,
            "primitive_polynomial": 0x83, "shortened_k": 64,
            "name": "Shortened primitive BCH (85,64,t=3)",
        },
    ]
    bch_matrices: dict[str, dict[str, Any]] = {}
    bch_certificate_entries: list[dict[str, Any]] = []
    for spec in reference_bch_specs:
        matrix = primitive_bch_systematic(
            m=spec["m"], t=spec["t"],
            primitive_polynomial=spec["primitive_polynomial"],
            shortened_k=spec["shortened_k"],
        )
        bch_matrices[spec["code_id"]] = matrix
        construction = primitive_bch_generator(
            m=spec["m"], t=spec["t"], primitive_polynomial=spec["primitive_polynomial"]
        )
        exact_distance = None
        exact_method = None
        if len(matrix["H"]) <= 16:
            exact = weight_enumerators(matrix["H"])
            exact_distance = exact["minimum_distance"]
            exact_method = exact["method"]
        bch_certificate_entries.append(
            {
                "code_spec_id": spec["code_id"],
                "n": len(matrix["G"][0]), "k": len(matrix["G"]), "t": spec["t"],
                "primitive_polynomial": spec["primitive_polynomial"],
                "generator_polynomial": construction["generator_polynomial"],
                "generator_polynomial_binary": construction["generator_polynomial_binary"],
                "cyclotomic_cosets": construction["cyclotomic_cosets"],
                "defining_consecutive_roots": construction["defining_consecutive_roots"],
                "designed_distance_lower_bound": construction["designed_distance_lower_bound"],
                "exact_minimum_distance": exact_distance,
                "exact_distance_method": exact_method,
                "shortening": matrix["shortening"],
                "matrix_sha256": canonical_hash({"G": matrix["G"], "H": matrix["H"]}),
            }
        )
    bch_certificate: dict[str, Any] = {
        "schema_version": 1,
        "certificate_id": "green-ecc-primitive-bch-construction-v1",
        "field_and_bound_method": "explicit primitive-polynomial verification, conjugate-root generator construction, and narrow-sense consecutive-root BCH bound",
        "entries": bch_certificate_entries,
    }
    bch_certificate["certificate_sha256"] = canonical_hash(bch_certificate)
    _write(root / bch_certificate_path, bch_certificate)

    for spec, certificate_entry in zip(reference_bch_specs, bch_certificate_entries):
        matrix = bch_matrices[spec["code_id"]]
        k = len(matrix["G"])
        n = len(matrix["G"][0])
        exact_distance = certificate_entry["exact_minimum_distance"]
        parameters = {
            "m": spec["m"], "t": spec["t"],
            "primitive_polynomial": spec["primitive_polynomial"],
            "shortened_k": spec["shortened_k"],
        }
        provenance = [
            {"path": "green_ecc_phy/bch.py", "role": "deterministic field, generator, systematic matrix, syndrome and decoder reference"},
            {"path": bch_certificate_path, "role": "machine-readable construction and distance certificate"},
            {"path": bch_test_path, "role": "exhaustive correction and malformed-input regression"},
        ]
        sources = ["green_ecc_phy/bch.py", bch_certificate_path, bch_test_path]
        if spec["code_id"] == "primitive-bch-63-51-t2-v1":
            provenance.extend([
                {"path": "src/bch63.cpp", "role": "independent repository BCH implementation using the same GF(2^6) primitive polynomial"},
                {"path": "tests/unit/BCH63_test.cpp", "role": "independent exhaustive single/double C++ tests"},
            ])
            sources.extend(["src/bch63.cpp", "src/bch63.hpp", "tests/unit/BCH63_test.cpp"])
        code = _code_base(
            code_id=spec["code_id"],
            equivalence_id=f"binary-{n}-{k}-primitive-bch-t{spec['t']}-v1",
            family="Primitive binary BCH",
            name=spec["name"],
            k=k, n=n,
            generator="green_ecc_phy.bch:primitive_bch_systematic",
            parameters=parameters,
            correction=[
                _error_class(f"all-weight-{weight}-errors", weight, ["CORRECTED"])
                for weight in range(1, spec["t"] + 1)
            ],
            detection=[],
            miscorrection=[
                {
                    "domain": f"weights greater than bounded correction strength t={spec['t']}",
                    "expected_behavior": "may be detected uncorrectable or silently miscorrected",
                }
            ],
            unsupported=[f"guaranteed correction beyond weight {spec['t']}", "physical PPA claims"],
            decoder_policy={
                "policy_id": f"primitive-bch-bounded-syndrome-t{spec['t']}-v1",
                "syndrome_count": 2 * spec["t"],
                "locator": "deterministic exact syndrome-to-mask table through t",
            },
            provenance=provenance,
            distance_evidence={
                "exact_minimum_distance": exact_distance,
                "designed_distance_lower_bound": certificate_entry["designed_distance_lower_bound"],
                "method": certificate_entry["exact_distance_method"] or "narrow-sense BCH consecutive-root bound",
            },
            shortening={
                "enabled": bool(matrix["shortening"]["enabled"]),
                "parameters": matrix["shortening"] if matrix["shortening"]["enabled"] else None,
            },
        )
        _write(
            registry_root / "codes" / f"{spec['code_id']}.json",
            _finalize_code(root, code, matrix, sources),
        )

    # Complete matrix-plus-decoder artifacts emitted by earlier CodeForge and
    # SafeForge phases.  Every distinct archived matrix is its own code spec;
    # no equivalence is inferred from a family label or common dimensions.
    archived_specs = [
        ("reports/code_synthesis/baselines/odd_column_secded_code.json", "reports/code_synthesis/verification_report.json"),
        ("reports/code_synthesis/code.json", "reports/code_synthesis/verification_report.json"),
        ("reports/code_synthesis_64/baselines/odd_column_secded_code.json", "reports/code_synthesis_64/verification_report.json"),
        ("reports/code_synthesis_64/code.json", "reports/code_synthesis_64/verification_report.json"),
        ("reports/safeforge_64_study/code.json", "reports/safeforge_64_study/result_manifest.json"),
        ("reports/safeforge_study/robust_cosynthesized_code.json", "reports/safeforge_study/result_manifest.json"),
        ("reports/portfolio_cosynthesis/codes/forge-sram-portfolio-72-64-v1-geometry-filtered-joint.json", "reports/portfolio_cosynthesis/result_manifest.json"),
        ("reports/portfolio_cosynthesis/codes/forge-sram-portfolio-72-64-v1-spatial-hotspot-joint.json", "reports/portfolio_cosynthesis/result_manifest.json"),
    ]
    archived_entries: list[dict[str, Any]] = []
    for code_path, evidence_path in archived_specs:
        archived = json.loads((root / code_path).read_text(encoding="utf-8"))
        matrix = {"G": archived["G"], "H": archived["H"]}
        code_id = str(archived["code_id"])
        k = int(archived["k"])
        n = int(archived["n"])
        exact = weight_enumerators(matrix["H"])
        entries = list(archived.get("decoder", {}).get("correction_entries", []))
        single_positions = {
            int(entry["positions"][0]) for entry in entries if len(entry["positions"]) == 1
        }
        all_singles = single_positions == set(range(n))
        singles_only = all(len(entry["positions"]) == 1 for entry in entries)
        correction = [_error_class("all-single-bit-errors", 1, ["CORRECTED"])] if all_singles else []
        detection = (
            [_error_class("all-double-bit-errors", 2, ["DETECTED_UNCORRECTABLE"])]
            if all_singles and singles_only and int(exact["minimum_distance"]) >= 4 else []
        )
        provenance = [
            {"path": code_path, "role": "archived exact G, H, coordinate order, and deployed syndrome table"},
            {"path": evidence_path, "role": "archived generation/verification evidence"},
        ]
        code = _code_base(
            code_id=code_id,
            equivalence_id=f"archived-matrix-{canonical_hash(matrix)[:20]}",
            family="SafeForge/CodeForge synthesized binary linear code",
            name=f"Archived synthesized code {code_id}",
            k=k, n=n,
            generator="green_ecc_phy.matrices:hsiao_odd_column",
            parameters={"k": k, "redundancy": n - k},
            correction=correction,
            detection=detection,
            miscorrection=[{
                "domain": "error masks outside the explicitly verified deployed syndrome table",
                "expected_behavior": "may be detected uncorrectable or silently miscorrected",
            }],
            unsupported=["family-wide correction claims beyond the exact deployed table", "physical PPA claims"],
            decoder_policy={
                "policy_id": f"{code_id}-archived-syndrome-table",
                "correction_entry_count": len(entries),
                "all_single_entries_present": all_singles,
            },
            provenance=provenance,
            distance_evidence={
                "exact_minimum_distance": exact["minimum_distance"],
                "designed_distance_lower_bound": exact["minimum_distance"],
                "method": exact["method"],
            },
        )
        code["matrix_definition"] = {
            "generator_matrix": matrix["G"],
            "parity_check_matrix": matrix["H"],
        }
        _write(
            registry_root / "codes" / f"{code_id}.json",
            _finalize_code(root, code, matrix, [code_path, evidence_path]),
        )
        archived_entries.append({
            "code_id": code_id, "code_path": code_path, "evidence_path": evidence_path,
            "matrix": matrix, "decoder_entries": entries, "all_singles": all_singles,
            "exact_minimum_distance": exact["minimum_distance"],
        })

    hsiao_rtl_sources = [
        str(path.relative_to(root)).replace("\\", "/") for path in sorted(generated_rtl.glob("*.sv"))
    ] + [evidence]
    implementations: list[dict[str, Any]] = []
    implementations.append(_implementation(
        implementation_id="hsiao-generated-combinational-72-64-v1", code_id="hsiao-secded-72-64-v1",
        sources=hsiao_rtl_sources, encoder="hsiao_secded_72_64_v1_encoder", decoder="hsiao_secded_72_64_v1_decoder",
        wrapper=None, policy="minimum-weight-single-syndrome-v1",
        adapter_factory="green_ecc_phy.adapters:create_linear_adapter", adapter_parameters={"policy": "single_error"},
        compatible=["fixed-hsiao-whole-memory-v1"], evidence_path=evidence,
        evidence_test_id="safeforge_72_modeled_campaign",
        capabilities={"mathematical": "SECDED", "rtl": "generated combinational RTL", "physical_characterization": None},
        verified_capabilities=["all-single-bit correction", "all-double-bit detection"],
        unsupported_capabilities=["weight>=2 correction", "weight>=3 detection"],
    ))

    common_positional = ["asic/include/ecc_pkg.sv", "asic/rtl/secded/secded_codec.sv"]
    implementations.append(_implementation(
        implementation_id="secded-rtl-combinational-72-64-v1", code_id="extended-hamming-secded-72-64-v1",
        sources=common_positional + ["asic/tb/tb_secded.sv", evidence], encoder="secded_encoder", decoder="secded_decoder",
        wrapper="sec_ded_64", policy="repository-secded-v1",
        adapter_factory="green_ecc_phy.adapters:create_linear_adapter", adapter_parameters={"policy": "single_error"},
        compatible=["fixed-secded-whole-memory-v1", "configurable-gated-parallel-bank-v1", "adaptive-shared-page-v1"],
        evidence_path=evidence, evidence_test_id="tb_secded",
        capabilities={"mathematical": "SECDED", "rtl": "single correction and double detection tested", "physical_characterization": None},
        verified_capabilities=["all-single-bit correction", "all-double-bit detection"],
        unsupported_capabilities=["weight>=2 correction", "weight>=3 detection"],
        parameters={"DATA_W": 64},
    ))
    implementations.append(_implementation(
        implementation_id="secdaec-rtl-bounded-72-64-v1", code_id="extended-hamming-secded-72-64-v1",
        sources=common_positional + ["asic/rtl/secdaec/secdaec_codec.sv", "asic/tb/tb_secdaec.sv", evidence],
        encoder="secdaec_encoder", decoder="secdaec_decoder", wrapper="sec_daec_64",
        policy="repository-bounded-adjacent-double-v1",
        adapter_factory="green_ecc_phy.adapters:create_linear_adapter", adapter_parameters={"policy": "bounded_adjacent_double"},
        compatible=["configurable-gated-parallel-bank-v1", "adaptive-shared-page-v1"], evidence_path=evidence,
        evidence_test_id="tb_secdaec",
        capabilities={
            "mathematical": "same extended-Hamming codeword set as SECDED",
            "rtl": "bounded adjacent-pair search; not a universal SEC-DAEC proof",
            "physical_characterization": None,
            "adjacency_definition": "consecutive canonical data coordinates 0..63 within one protected word; no word, bank, page, or parity-boundary crossing",
            "claimed_error_classes": [{
                "kind": "correction", "class_id": "all-adjacent-double-data-errors",
                "generator": "adjacent_windows", "weight": 2, "coordinate_count": 64,
                "acceptable_statuses": ["CORRECTED"],
            }],
        }, parameters={"DATA_W": 64},
        verified_capabilities=["all-single-bit correction"],
        failed_capabilities=["all-double-bit detection: 302/2556 silent miscorrections"],
        unsupported_capabilities=["unrestricted adjacent-double correction guarantee"],
    ))
    implementations.append(_implementation(
        implementation_id="taec-rtl-bounded-72-64-v1", code_id="extended-hamming-secded-72-64-v1",
        sources=common_positional + ["asic/rtl/taec/taec_codec.sv", "asic/tb/tb_taec.sv", evidence],
        encoder="taec_encoder", decoder="taec_decoder", wrapper="taec_64",
        policy="repository-bounded-adjacent-triple-v1",
        adapter_factory="green_ecc_phy.adapters:create_linear_adapter", adapter_parameters={"policy": "bounded_adjacent_triple"},
        compatible=["configurable-gated-parallel-bank-v1", "adaptive-shared-page-v1"], evidence_path=evidence,
        evidence_test_id="tb_taec",
        capabilities={
            "mathematical": "same extended-Hamming codeword set as SECDED",
            "rtl": "negative triple/single syndrome collision is archived; TAEC is not guaranteed",
            "physical_characterization": None,
            "adjacency_definition": "consecutive canonical data coordinates 0..63 within one protected word; no word, bank, page, or parity-boundary crossing",
            "claimed_error_classes": [{
                "kind": "correction", "class_id": "all-adjacent-triple-data-errors",
                "generator": "adjacent_windows", "weight": 3, "coordinate_count": 64,
                "acceptable_statuses": ["CORRECTED"],
            }],
        }, parameters={"DATA_W": 64},
        verified_capabilities=["all-single-bit correction", "all-double-bit detection"],
        failed_capabilities=["adjacent-triple correction guarantee"],
        unsupported_capabilities=["full TAEC guarantee"],
    ))
    implementations.append(_implementation(
        implementation_id="cyclic-rtl-bounded-search-63-51-v1", code_id="repository-cyclic-63-51-v1",
        sources=["asic/rtl/bch/bch_codec.sv", "asic/tb/tb_bch.sv", evidence],
        encoder="bch_encoder", decoder="bch_decoder", wrapper="bch_63",
        policy="bounded-valid-codeword-search-weight2-v1",
        adapter_factory="green_ecc_phy.adapters:create_bounded_cyclic_adapter", adapter_parameters={"search_weight": 2},
        compatible=["fixed-cyclic-whole-memory-v1"], evidence_path=evidence, evidence_test_id="tb_bch",
        capabilities={
            "mathematical": "degree-12 cyclic code; distance-5 BCH identity unproved",
            "rtl": "bounded <=2 candidate search with archived triple miscorrection",
            "physical_characterization": None,
        }, parameters={"N": 63, "K": 51, "G_POLY": "13'b1_000111101011"},
        verified_capabilities=[],
        failed_capabilities=["all-single-bit correction: 33/63 failures", "BCH designed-distance-five identity"],
        unsupported_capabilities=["selection eligibility"],
    ))
    for spec in reference_bch_specs:
        matrix = bch_matrices[spec["code_id"]]
        n = len(matrix["G"][0])
        k = len(matrix["G"])
        architecture_id = f"fixed-{spec['code_id']}"
        implementation_id = f"{spec['code_id']}-reference-decoder"
        reference_sources = ["green_ecc_phy/bch.py", bch_certificate_path, bch_test_path]
        if spec["code_id"] == "primitive-bch-63-51-t2-v1":
            reference_sources.extend(["src/bch63.cpp", "src/bch63.hpp", "tests/unit/BCH63_test.cpp"])
        implementations.append(_implementation(
            implementation_id=implementation_id,
            code_id=spec["code_id"],
            sources=reference_sources,
            encoder=None, decoder=None, wrapper=None,
            policy=f"primitive-bch-bounded-syndrome-t{spec['t']}-v1",
            adapter_factory="green_ecc_phy.bch:create_bch_adapter",
            adapter_parameters={
                "m": spec["m"], "t": spec["t"],
                "primitive_polynomial": spec["primitive_polynomial"],
            },
            compatible=[architecture_id],
            evidence_path=bch_certificate_path,
            evidence_test_id=f"exhaustive_masks_through_t{spec['t']}",
            capabilities={
                "mathematical": f"primitive BCH with designed distance >= {2 * spec['t'] + 1}",
                "software_reference": "systematic encoder, GF syndromes, deterministic bounded locator",
                "physical_characterization": None,
            },
            parameters={"N": n, "K": k, "M": spec["m"], "T": spec["t"]},
            verified_capabilities=[
                f"all-weight-{weight} correction" for weight in range(1, spec["t"] + 1)
            ],
            unsupported_capabilities=[f"guaranteed correction beyond t={spec['t']}", "physical PPA"],
            architecture_style="reference_only",
        ))
    for archived in archived_entries:
        code_id = archived["code_id"]
        implementation_id = f"{code_id}-archived-table-decoder"
        architecture_id = f"fixed-{code_id}"
        explicit_positions = [list(map(int, entry["positions"])) for entry in archived["decoder_entries"]]
        implementations.append(_implementation(
            implementation_id=implementation_id,
            code_id=code_id,
            sources=[archived["code_path"], archived["evidence_path"]],
            encoder=None, decoder=None, wrapper=None,
            policy=f"{code_id}-archived-syndrome-table",
            adapter_factory="green_ecc_phy.adapters:create_declared_table_adapter",
            adapter_parameters={"table_path": archived["code_path"]},
            compatible=[architecture_id],
            evidence_path=archived["evidence_path"],
            evidence_test_id=f"{code_id}-archived-verification",
            capabilities={
                "mathematical": f"exact binary linear [{len(archived['matrix']['G'][0])},{len(archived['matrix']['G'])}] code with d={archived['exact_minimum_distance']}",
                "software_reference": "archived deterministic syndrome correction table",
                "physical_characterization": None,
                "claimed_error_classes": [{
                    "kind": "correction",
                    "class_id": "all-archived-correction-table-entries",
                    "generator": "explicit", "weight": 1,
                    "positions": explicit_positions,
                    "acceptable_statuses": ["CORRECTED"],
                }],
            },
            verified_capabilities=[
                f"all {len(explicit_positions)} archived syndrome-table leaders",
                *( ["all-single-bit correction"] if archived["all_singles"] else [] ),
            ],
            unsupported_capabilities=["unlisted error masks", "physical PPA"],
            architecture_style="reference_only",
        ))
    for implementation in implementations:
        sources = list(implementation["source_files"])
        _write(
            registry_root / "implementations" / f"{implementation['implementation_id']}.json",
            _finalize_manifest(root, implementation, sources),
        )

    all_positional = [
        "secded-rtl-combinational-72-64-v1", "secdaec-rtl-bounded-72-64-v1", "taec-rtl-bounded-72-64-v1"
    ]
    architectures = [
        _architecture("fixed-hsiao-whole-memory-v1", "fixed", "whole_memory", ["hsiao-generated-combinational-72-64-v1"], "hsiao-generated-combinational-72-64-v1"),
        _architecture("fixed-secded-whole-memory-v1", "fixed", "whole_memory", ["secded-rtl-combinational-72-64-v1"], "secded-rtl-combinational-72-64-v1"),
        _architecture("fixed-cyclic-whole-memory-v1", "fixed", "whole_memory", ["cyclic-rtl-bounded-search-63-51-v1"], "cyclic-rtl-bounded-search-63-51-v1"),
        _architecture(
            "configurable-gated-parallel-bank-v1", "configurable_gated_parallel", "bank_granularity", all_positional,
            "secded-rtl-combinational-72-64-v1", fallback="secded-rtl-combinational-72-64-v1",
            sources=["asic/rtl/common/green_ecc_select_mux.sv", "asic/rtl/common/green_ecc_mode_controller.sv", evidence],
        ),
        _architecture(
            "adaptive-shared-page-v1", "adaptive_shared_datapath", "page_granularity", all_positional,
            "secded-rtl-combinational-72-64-v1", fallback="secded-rtl-combinational-72-64-v1",
            sources=["asic/rtl/common/green_ecc_transition_controller.sv", "asic/rtl/common/green_ecc_select_mux.sv", evidence],
        ),
    ]
    for spec in reference_bch_specs:
        implementation_id = f"{spec['code_id']}-reference-decoder"
        architectures.append(_architecture(
            f"fixed-{spec['code_id']}", "fixed", "whole_memory",
            [implementation_id], implementation_id,
            sources=["green_ecc_phy/bch.py", bch_certificate_path],
        ))
    for archived in archived_entries:
        implementation_id = f"{archived['code_id']}-archived-table-decoder"
        architectures.append(_architecture(
            f"fixed-{archived['code_id']}", "fixed", "whole_memory",
            [implementation_id], implementation_id,
            sources=[archived["code_path"], archived["evidence_path"]],
        ))
    for architecture in architectures:
        sources = list(architecture.pop("_sources"))
        _write(
            registry_root / "architectures" / f"{architecture['architecture_id']}.json",
            _finalize_manifest(root, architecture, sources),
        )

    backends = [
        _backend(
            "structural-yosys-local-v1", "structural_synthesis_only", True,
            "Yosys generic logic only; no Liberty timing, power, or physical area",
            tool="Yosys 0.30+48", evidence_paths=["reports/safeforge_hardware_validation/nominal_robust_structural_comparison.json"],
        ),
        _backend("cadence-st65-unavailable-v1", "cadence_genus_innovus_tempus", False, "Cadence tools, ST65 PDK, and characterized libraries are not locally discoverable"),
        _backend("openroad-sky130-unavailable-v1", "yosys_opensta_openroad", False, "OpenSTA/OpenROAD/SKY130/OpenRAM and characterized SRAM collateral are unavailable"),
        _backend("not-characterized-v1", "unavailable", False, "Explicit null backend for unsupported physical evidence"),
    ]
    for backend in backends:
        backend["manifest_sha256"] = "0" * 64
        backend["manifest_sha256"] = manifest_sha256(backend)
        _write(registry_root / "backends" / f"{backend['backend_id']}.json", backend)

    workload = {
        "schema_version": 1,
        "workload_id": "functional-uniform-placeholder-v1",
        "description": "Functional comparison identity only; no measured or SAIF activity is available.",
        "activity_source": None,
        "activity_sha256": None,
        "physical_power_eligible": False,
    }
    _write(registry_root / "workloads" / "functional-uniform-placeholder-v1.json", workload)
    scenario = {
        "schema_version": 1,
        "scenario_id": "no-physical-selection-v1",
        "comparison_basis": "equal_data_width",
        "k": 64,
        "workload_id": workload["workload_id"],
        "objective": "encoder_energy",
        "direction": "min",
        "proxy_winner": None,
    }
    _write(registry_root / "scenarios" / "no-physical-selection-v1.json", scenario)
    analytical_study = {
        "schema_version": 1,
        "study_id": "green-ecc-phy-software-simulation-v1",
        "preregistration_status": "parameters materialized by catalogue build before scenario winners are computed",
        "comparison_payloads_bits": [1, 64, 512],
        "adjacency_definition": "linear consecutive coordinates within each encoded codeword; adjacency never crosses a codeword, word, bank, or page boundary",
        "grid": {
            "supply_voltage_v": [0.8, 1.0],
            "temperature_c": [25.0, 85.0],
            "scrub_interval_s": [1.0, 3600.0],
            "carbon_intensity_kgco2_per_kwh": [0.1, 0.7],
            "fault_profile_ids": ["sbu_dominant", "adjacent_mbu", "triple_stress"],
            "workload_ids": ["low_activity", "high_activity"],
            "reliability_requirement_ids": ["service", "stringent"],
        },
        "fault_profiles": {
            "sbu_dominant": {
                "class_probability_per_codeword_access": {
                    "single": 9.8e-8, "adjacent_double": 1.0e-9,
                    "nonadjacent_double": 1.0e-9, "adjacent_triple": 0.0,
                    "nonadjacent_triple": 0.0,
                },
                "provenance": "explicit uncalibrated sensitivity profile; not a measured SER/FIT distribution",
            },
            "adjacent_mbu": {
                "class_probability_per_codeword_access": {
                    "single": 5.0e-8, "adjacent_double": 4.0e-8,
                    "nonadjacent_double": 5.0e-9, "adjacent_triple": 5.0e-9,
                    "nonadjacent_triple": 0.0,
                },
                "provenance": "explicit uncalibrated sensitivity profile; not a measured SER/FIT distribution",
            },
            "triple_stress": {
                "class_probability_per_codeword_access": {
                    "single": 3.0e-8, "adjacent_double": 2.0e-8,
                    "nonadjacent_double": 1.0e-8, "adjacent_triple": 3.0e-8,
                    "nonadjacent_triple": 1.0e-8,
                },
                "provenance": "explicit uncalibrated sensitivity stress profile; not a measured radiation result",
            },
        },
        "workloads": {
            "low_activity": {"payload_accesses": 1000000, "write_fraction": 0.1, "lifetime_s": 3600.0},
            "high_activity": {"payload_accesses": 1000000000, "write_fraction": 0.5, "lifetime_s": 3600.0},
        },
        "reliability_requirements": {
            "service": {"max_sdc_probability_per_64b_access": 1.0e-8, "max_due_probability_per_64b_access": 1.0e-6},
            "stringent": {"max_sdc_probability_per_64b_access": 1.0e-12, "max_due_probability_per_64b_access": 1.0e-7},
        },
        "equal_information_capacity_bits": 8388608,
        "analytical_model": {
            "model_id": "green-ecc-explicit-sensitivity-energy-v1",
            "parameters": {
                "bit_access_energy_j_at_1v": 1.0e-15,
                "xor_activity_energy_j_at_1v": 2.0e-16,
                "leakage_power_w_per_stored_bit_at_25c": 1.0e-15,
                "temperature_leakage_multiplier_at_85c": 2.0,
                "scrub_read_write_energy_multiplier": 2.0,
            },
            "provenance": "explicit sensitivity parameters selected before winners; no measured technology library, SRAM macro, activity trace, or PDK",
            "evidence_level": "analytical_sensitivity",
        },
        "uncertainty_models": {
            "storage_dominated": {"bit_energy_scale": 1.5, "xor_energy_scale": 0.5, "leakage_scale": 1.5},
            "base": {"bit_energy_scale": 1.0, "xor_energy_scale": 1.0, "leakage_scale": 1.0},
            "logic_dominated": {"bit_energy_scale": 0.5, "xor_energy_scale": 2.0, "leakage_scale": 0.5},
        },
        "selector": {
            "selector_id": "verified-feasible-lexicographic-v1",
            "hard_constraints": ["verification_status", "sdc_limit", "due_limit"],
            "objective_order": ["modelled_total_energy_j", "decoder_complexity_proxy", "encoded_bits_per_64b", "implementation_id"],
            "weights": None,
        },
        "physical_metrics": None,
    }
    analytical_study["preregistration_sha256"] = canonical_hash(analytical_study)
    _write(registry_root / "scenarios" / "software-simulation-study-v1.json", analytical_study)

    config = {
        "schema_version": 1,
        "registry_id": "green-ecc-phy-builtin-v1",
        "codes": [f"codes/{name}.json" for name in ["hsiao-secded-72-64-v1", "extended-hamming-secded-72-64-v1", "repository-cyclic-63-51-v1"] + [spec["code_id"] for spec in reference_bch_specs] + [item["code_id"] for item in archived_entries]],
        "implementations": [f"implementations/{item['implementation_id']}.json" for item in implementations],
        "architectures": [f"architectures/{item['architecture_id']}.json" for item in architectures],
        "backends": [f"backends/{item['backend_id']}.json" for item in backends],
        "catalogue_sha256": "0" * 64,
    }
    config["catalogue_sha256"] = canonical_hash({key: value for key, value in config.items() if key != "catalogue_sha256"})
    _write(registry_root / "registry.json", config)
    _build_external_fixture(root)


def _build_external_fixture(root: Path) -> None:
    fixture = root / "tests" / "fixtures" / "multi_ecc_external"
    plugin = "tests/fixtures/multi_ecc_external/plugin.py"
    evidence = "tests/fixtures/multi_ecc_external/evidence.json"
    matrix = {"G": [[1, 1, 1]], "H": [[1, 1, 0], [1, 0, 1]]}
    code = _code_base(
        code_id="test-repetition-3-1-v1",
        equivalence_id="test-only-repetition-3-1-v1",
        family="test-only repetition",
        name="External acceptance-test repetition (3,1)",
        k=1, n=3,
        generator="../plugin.py::repetition_matrix",
        parameters={},
        correction=[_error_class("all-single-bit-errors", 1, ["CORRECTED"])],
        detection=[],
        miscorrection=[{"domain": "all double-bit errors", "expected_behavior": "majority decoder miscorrects"}],
        unsupported=["scientific comparison", "double-bit detection"],
        decoder_policy={"policy_id": "majority-vote-v1"},
        provenance=[{"path": plugin, "role": "external executable test plugin"}],
    )
    _write(fixture / "codes" / "repetition.json", _finalize_code(root, code, matrix, [plugin]))
    implementation = _implementation(
        implementation_id="test-repetition-majority-reference-v1",
        code_id="test-repetition-3-1-v1",
        sources=[plugin, evidence],
        encoder=None,
        decoder=None,
        wrapper=None,
        policy="majority-vote-v1",
        adapter_factory="../plugin.py::create_adapter",
        adapter_parameters={},
        compatible=["test-fixed-repetition-v1"],
        evidence_path=evidence,
        evidence_test_id="external_plugin_exhaustive_acceptance",
        capabilities={"mathematical": "single-error correction", "rtl": None, "physical_characterization": None},
    )
    implementation["architecture_style"] = "reference_only"
    _write(
        fixture / "implementations" / "repetition.json",
        _finalize_manifest(root, implementation, list(implementation["source_files"])),
    )
    architecture = _architecture(
        "test-fixed-repetition-v1", "fixed", "whole_memory",
        ["test-repetition-majority-reference-v1"], "test-repetition-majority-reference-v1",
    )
    sources = list(architecture.pop("_sources"))
    _write(fixture / "architectures" / "fixed.json", _finalize_manifest(root, architecture, sources))
    registry = {
        "schema_version": 1,
        "registry_id": "external-test-ecc-v1",
        "codes": ["codes/repetition.json"],
        "implementations": ["implementations/repetition.json"],
        "architectures": ["architectures/fixed.json"],
        "backends": [],
        "catalogue_sha256": "0" * 64,
    }
    registry["catalogue_sha256"] = canonical_hash({key: value for key, value in registry.items() if key != "catalogue_sha256"})
    _write(fixture / "registry.json", registry)


def _architecture(
    architecture_id: str, architecture_type: str, scope: str, allowed: list[str], active: str,
    *, fallback: str | None = None, sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "architecture_id": architecture_id,
        "architecture_type": architecture_type,
        "deployment_scope": scope,
        "allowed_implementation_ids": allowed,
        "active_implementation": active,
        "configuration_mechanism": {"kind": "static" if architecture_type == "fixed" else "protected_mode_register"},
        "mux_topology": {"kind": "none" if architecture_type == "fixed" else "gated_parallel_or_shared", "physical_cost": None},
        "controller": {"kind": "none" if architecture_type == "fixed" else "repository_transition_controller", "physical_cost": None},
        "metadata": {"bits_per_unit": 0 if architecture_type == "fixed" else 3, "protection": "triplicated mode identity"},
        "transition_sequencing": {"required": architecture_type != "fixed", "verification_required": True},
        "reencoding_requirements": {"required": architecture_type != "fixed", "energy": None, "latency": None},
        "fallback_implementation": fallback,
        "transition_cost_evidence": None,
        "physical_characterization_identity": None,
        "_sources": sources or [],
    }


def _backend(
    backend_id: str, kind: str, available: bool, reason: str, *, tool: str | None = None,
    evidence_paths: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "backend_id": backend_id,
        "kind": kind,
        "available": available,
        "adapter": {"factory": "green_ecc_phy.backends:create_null_safe_backend"},
        "tool": tool,
        "technology": None,
        "pdk": None,
        "library": None,
        "corner": None,
        "voltage": None,
        "temperature": None,
        "timing_constraints": None,
        "evidence_paths": evidence_paths or [],
        "reason": reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    build(args.repo_root.resolve())


if __name__ == "__main__":
    main()
