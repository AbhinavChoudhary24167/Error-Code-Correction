from __future__ import annotations

import json
from pathlib import Path

from green_ecc_phy.hashing import canonical_hash
from green_ecc_phy.registry import EccRegistry
from green_ecc_phy.study import payload_normalization
from green_ecc_phy.verification import verify_implementation


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "green_ecc_physical_simulation" / "multi_ecc_evaluation"


def _registry() -> EccRegistry:
    return EccRegistry.builtin(ROOT)


def test_decoder_policy_can_attach_without_new_code_or_core_family_branch() -> None:
    registry = _registry()
    implementations = {
        identifier for identifier, item in registry.implementations.items()
        if item["code_id"] == "extended-hamming-secded-72-64-v1"
    }
    assert implementations == {
        "secded-rtl-combinational-72-64-v1",
        "secdaec-rtl-bounded-72-64-v1",
        "taec-rtl-bounded-72-64-v1",
    }
    assert len({registry.implementation(item)["decoder_policy_id"] for item in implementations}) == 3


def test_distinct_encoder_codeword_sets_have_distinct_code_specifications() -> None:
    registry = _registry()
    valid = registry.code("primitive-bch-63-51-t2-v1")
    rejected = registry.code("repository-cyclic-63-51-v1")
    assert valid["code_spec_id"] != rejected["code_spec_id"]
    assert valid["encoder_id"] != rejected["encoder_id"]
    assert valid["content_hashes"]["matrix_sha256"] != rejected["content_hashes"]["matrix_sha256"]
    assert valid["distance_evidence"]["exact_minimum_distance"] == 5
    assert rejected["distance_evidence"]["exact_minimum_distance"] == 2


def test_partial_taec_is_not_promoted_to_full_taec() -> None:
    report = verify_implementation(_registry(), "taec-rtl-bounded-72-64-v1")
    assert report["verification_status"] == "passed"
    assert report["capability_verification_status"] == "partially_verified"
    result = next(item for item in report["class_results"] if item["class_id"] == "all-adjacent-triple-data-errors")
    assert result["exact_fraction"] == "0/62"
    assert result["outcome_counts"] == {"MISCORRECTED": 62}


def test_payload_normalization_handles_unequal_k_and_padding() -> None:
    bch = payload_normalization(51, 63)
    secded = payload_normalization(64, 72)
    assert bch["protected_64b_word"]["codewords_required"] == 2
    assert bch["protected_64b_word"]["encoded_bits"] == 126
    assert bch["protected_64b_word"]["padding_information_bits"] == 38
    assert secded["protected_64b_word"]["codewords_required"] == 1
    assert secded["protected_64b_word"]["encoded_bits"] == 72


def test_rejected_candidates_never_enter_scenario_selection() -> None:
    payload = json.loads((OUT / "scenario_selection_results.json").read_text(encoding="utf-8"))
    rejected = {"cyclic-rtl-bounded-search-63-51-v1", "secdaec-rtl-bounded-72-64-v1"}
    for scenario in payload["scenarios"]:
        assert scenario["winner"] not in rejected
        decisions = {item["implementation_id"]: item for item in scenario["candidate_decisions"]}
        assert all(decisions[item]["status"] == "rejected" for item in rejected)


def test_analytical_fields_never_populate_physical_fields() -> None:
    payload = json.loads((OUT / "scenario_selection_results.json").read_text(encoding="utf-8"))
    for candidate in payload["scenarios"][0]["candidate_records"]:
        assert candidate["analytical_metrics"]["modelled_total_energy"]["value"] >= 0
        assert all(value is None for value in candidate["physical_metrics"].values())
        assert candidate["evidence_level"] == "exact_functional_plus_analytical_sensitivity"


def test_summary_counts_and_substantive_hash_contracts() -> None:
    registry = _registry()
    framework = json.loads((OUT / "framework_summary.json").read_text(encoding="utf-8"))
    study = json.loads((OUT / "software_study_summary.json").read_text(encoding="utf-8"))
    assert framework["registered_code_specifications"] == len(registry.codes)
    assert framework["registered_encoder_decoder_implementations"] == len(registry.implementations)
    assert study["registered_code_specifications"] == len(registry.codes)
    assert study["registered_encoder_decoder_implementations"] == len(registry.implementations)
    supplied = study.pop("summary_sha256")
    assert supplied == canonical_hash(study)
    scenarios = json.loads((OUT / "scenario_selection_results.json").read_text(encoding="utf-8"))["scenarios"]
    for scenario in scenarios:
        supplied = scenario.pop("scenario_sha256")
        assert supplied == canonical_hash(scenario)
