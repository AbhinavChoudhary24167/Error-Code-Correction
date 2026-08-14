from __future__ import annotations

import csv
import json
from pathlib import Path

from green_ecc_phy.registry import EccRegistry
from scripts.gate03r.validate_artifacts import validate
from scripts.gate03r.verify_bch_identity import EXPECTED_MATRIX_SHA256, bounded_decode, encode, reconstruct


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
REGISTRY = ROOT / "green_ecc_physical_simulation" / "registry"


def load(name: str):
    return json.loads((DOC / name).read_text(encoding="utf-8"))


def test_gate03r_artifact_validator() -> None:
    assert validate() == []


def test_gate03r_verdict_is_exactly_failed_and_does_not_authorize_reentry() -> None:
    assert (DOC / "GATE_03R_VERDICT.txt").read_text(encoding="ascii").strip() == "REMEDIATION_FAILED"
    manifest = load("GATE_03_REENTRY_MANIFEST.json")
    assert manifest["gate03r_verdict"] == "REMEDIATION_FAILED"
    assert manifest["authorization"]["complete_gate03_reentry_authorized"] is False


def test_gate03r_preserves_all_previous_gate_hashes() -> None:
    checks = load("FROZEN_GATE_HASH_CHECK.json")["gates"]
    assert set(checks) == {
        "docs/date2027/rigour_gate_01",
        "docs/date2027/rigour_gate_02",
        "docs/date2027/rigour_gate_03",
    }
    assert all(result["status"] == "PASS" for result in checks.values())


def test_bch_independent_identity_is_exact() -> None:
    result = reconstruct()
    assert result["matrix_sha256"] == EXPECTED_MATRIX_SHA256
    assert result["generator_polynomial_binary"] == "101010001111101"
    assert result["bounded_locator_entries"] == 3081
    assert not result["bounded_locator_collisions"]


def test_bch_exact_proof_index_has_required_mask_universe() -> None:
    rows = list(csv.DictReader((DOC / "FORMAL_PROOF_INDEX.csv").open(encoding="utf-8", newline="")))
    bch = [row for row in rows if row["family"] == "BCH_78_64_T2"]
    assert len(bch) == 3082
    assert sum(row["mask_weight"] == "0" for row in bch) == 1
    assert sum(row["mask_weight"] == "1" for row in bch) == 78
    assert sum(row["mask_weight"] == "2" for row in bch) == 3003
    assert all(row["symbolic_payload_bits"] == "64" and row["status"] == "PASS" for row in bch)


def test_bch_decoder_contract_for_correctable_masks() -> None:
    payload = 0x123456789ABCDEF0
    clean = encode(payload)
    for mask in (0, 1, 1 << 77, (1 << 3) | (1 << 72)):
        result = bounded_decode(clean ^ mask)
        assert result["data"] == payload
        assert result["corrected_codeword"] == clean
        assert result["correction_mask"] == mask
        assert result["uncorrectable"] is False


def test_weight3_is_characterization_only() -> None:
    result = load("BCH_WEIGHT3_CHARACTERIZATION.json")
    assert result["zero_payload_weight3_masks_examined"] == 76076
    assert result["deterministic_payload_mask_samples"] == 1024
    assert result["claim_scope"] == "characterization_only_no_weight3_correction_claim"
    assert result["status"] == "PASS"


def test_secded_exact_equivalence_and_universe_replay() -> None:
    result = load("SECDED_PROOF_SUMMARY.json")
    assert result["encoder_universal_affine_equivalence"] is True
    assert result["decoder_universal_compositional_equivalence"] is True
    assert result["gate02_weight2_masks_replayed"] == 2556
    assert result["gate02_weight3_masks_replayed"] == 59640
    assert result["status"] == "PASS"


def test_registry_overlay_is_explicit_and_additive() -> None:
    default = EccRegistry.load(REGISTRY / "registry.json", repo_root=ROOT)
    overlay = EccRegistry.load(REGISTRY / "registry_gate03r.json", repo_root=ROOT)
    assert len(default.implementations) == 17
    assert len(overlay.implementations) == 19
    assert set(overlay.implementations) - set(default.implementations) == {
        "secded-rtl-pipelined-72-64-v1",
        "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
    }


def test_generic_synthesis_is_not_mislabeled_as_physical_ppa() -> None:
    result = load("SYNTHESIS_AND_STRUCTURE_RESULTS.json")
    assert result["classification"] == "GENERIC_SYNTHESIS_ONLY_NOT_PPA"
    assert all(job["status"] == "PASS" for job in result["jobs"].values())
    assert result["h2_generic_status"] == "PASS"
    assert result["sky130hd_mapping"]["claims_generated"] is False


def test_compiled_rtl_smoke_passes_and_failed_attempt_is_retained() -> None:
    result = load("RTL_SIMULATION_RESULTS.json")
    assert result["status"] == "PASS"
    assert result["passing_simulator"] == "Verilator"
    assert result["bch"]["status"] == "PASS_VERILATOR_COMPILED_SMOKE"
    assert result["secded"]["status"] == "PASS_VERILATOR_COMPILED_SMOKE"
    assert result["icarus_attempt_status"]["preserved_logs"] is True


def test_pinned_environment_blocker_is_not_relaxed() -> None:
    toolchain = load("TOOLCHAIN_FREEZE.json")
    assert toolchain["orfs"]["required_image"].endswith(
        "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
    )
    assert toolchain["orfs"]["substitution_performed"] is False
    assert toolchain["orfs"]["resolved_full_official_commit"] is None
    assert toolchain["environment_provisioning"]["host_changed"] is False


def test_production_boundaries_have_no_injection_inputs() -> None:
    for relative in (
        "asic/rtl/bch/bch_78_64_t2_v1.sv",
        "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "error_mask_i" not in text
        assert "inject_i" not in text
        assert "fault_i" not in text
