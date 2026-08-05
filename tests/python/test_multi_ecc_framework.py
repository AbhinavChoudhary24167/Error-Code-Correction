from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from green_ecc_phy.backends import CharacterizationStore, characterize_implementation
from green_ecc_phy.comparison import build_comparison_views, select_physical
from green_ecc_phy.hashing import manifest_sha256
from green_ecc_phy.registry import EccRegistry
from green_ecc_phy.verification import verify_implementation


ROOT = Path(__file__).resolve().parents[2]


def _registry() -> EccRegistry:
    return EccRegistry.builtin(ROOT)


def test_builtin_registry_separates_codes_implementations_and_architectures() -> None:
    registry = _registry()
    assert len(registry.codes) == 15
    assert len(registry.implementations) == 17
    assert len(registry.architectures) == 17
    implementation_counts = {
        code_id: sum(item["code_id"] == code_id for item in registry.implementations.values())
        for code_id in registry.codes
    }
    assert implementation_counts["extended-hamming-secded-72-64-v1"] == 3
    technology_terms = {"cell_area", "critical_path", "encoder_energy", "leakage_power"}
    for code in registry.codes.values():
        assert not (technology_terms & set(code))
        assert code["n"] == code["k"] + code["redundancy"]


def test_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    source = ROOT / "green_ecc_physical_simulation" / "registry"
    payload = json.loads((source / "registry.json").read_text(encoding="utf-8"))
    payload["codes"] = [str((source / payload["codes"][0]).resolve())] * 2
    payload["implementations"] = []
    payload["architectures"] = []
    payload["backends"] = []
    payload["scientific_hash_migration"] = str(
        (source / payload["scientific_hash_migration"]).resolve()
    )
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate code_id"):
        EccRegistry.load(path, repo_root=ROOT)


def test_registry_rejects_broken_hash_and_unknown_code_reference(tmp_path: Path) -> None:
    source = ROOT / "green_ecc_physical_simulation" / "registry"
    code_path = source / "codes" / "hsiao-secded-72-64-v1.json"
    broken = json.loads(code_path.read_text(encoding="utf-8"))
    broken["content_hashes"]["manifest_sha256"] = "0" * 64
    broken_path = tmp_path / "broken-code.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")
    builtin_config = json.loads((source / "registry.json").read_text(encoding="utf-8"))
    config = {
        "schema_version": 1, "codes": [str(broken_path)],
        "implementations": [], "architectures": [], "backends": [],
        "scientific_source_hash_scheme": builtin_config["scientific_source_hash_scheme"],
        "scientific_hash_migration": str(
            (source / builtin_config["scientific_hash_migration"]).resolve()
        ),
        "scientific_hash_migration_sha256": builtin_config[
            "scientific_hash_migration_sha256"
        ],
    }
    config_path = tmp_path / "broken-registry.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="broken manifest_sha256"):
        EccRegistry.load(config_path, repo_root=ROOT)

    implementation_path = source / "implementations" / "hsiao-generated-combinational-72-64-v1.json"
    implementation = json.loads(implementation_path.read_text(encoding="utf-8"))
    implementation["code_id"] = "unknown-code"
    implementation["manifest_sha256"] = manifest_sha256(implementation)
    copied_implementation = tmp_path / "unknown-code-implementation.json"
    copied_implementation.write_text(json.dumps(implementation), encoding="utf-8")
    config.update(
        {
            "codes": [str(code_path)],
            "implementations": [str(copied_implementation)],
        }
    )
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown code_id"):
        EccRegistry.load(config_path, repo_root=ROOT)


def test_functional_gate_reports_passes_and_rejections() -> None:
    registry = _registry()
    passed = verify_implementation(registry, "secded-rtl-combinational-72-64-v1")
    assert passed["verification_status"] == "passed"
    assert passed["checks"]["deterministic_encoding"] is True
    assert passed["matrix_hash"] == registry.codes[passed["code_id"]]["content_hashes"]["matrix_sha256"]

    secdaec = verify_implementation(registry, "secdaec-rtl-bounded-72-64-v1")
    assert secdaec["verification_status"] == "failed"
    assert any("all-double-bit-errors" in failure for failure in secdaec["failures"])

    cyclic = verify_implementation(registry, "cyclic-rtl-bounded-search-63-51-v1")
    assert cyclic["verification_status"] == "failed"
    assert any("all-single-bit-errors" in failure for failure in cyclic["failures"])


def test_external_ecc_uses_only_public_plugin_interface() -> None:
    registry = EccRegistry.load(
        ROOT / "tests" / "fixtures" / "multi_ecc_external" / "registry.json",
        repo_root=ROOT,
    )
    report = verify_implementation(registry, "test-repetition-majority-reference-v1")
    assert report["verification_status"] == "passed"
    assert report["exhaustive_small_code"] == {"performed": True, "cases": 16, "deterministic": True}
    core_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "green_ecc_phy").glob("*.py"))
    )
    assert "test-repetition" not in core_text
    assert "repetition_matrix" not in core_text


def test_structural_backend_keeps_physical_values_null_and_selection_empty(tmp_path: Path) -> None:
    registry = _registry()
    result = characterize_implementation(
        registry,
        "hsiao-generated-combinational-72-64-v1",
        ROOT / "green_ecc_physical_simulation" / "registry" / "backends" / "structural-yosys-local-v1.json",
        ROOT / "green_ecc_physical_simulation" / "registry" / "workloads" / "functional-uniform-placeholder-v1.json",
        architecture_id="fixed-hsiao-whole-memory-v1",
        output_path=tmp_path / "characterization.json",
    )
    assert result["evidence_level"] == "structural_only"
    assert result["cell_area"] is None
    assert result["encoder_energy"] is None
    assert "cell_area" in result["unsupported_fields"]
    store = CharacterizationStore(registry)
    store.add(result)
    views = build_comparison_views(store)
    assert set(views) == {
        "equal_data_width", "equal_codeword_width", "equal_redundancy",
        "equal_guaranteed_reliability", "equal_timing_target", "equal_area_budget",
        "equal_workload", "same_code_different_implementations",
        "same_implementation_across_corners", "same_code_across_deployment_architectures",
    }
    selection = select_physical(
        store,
        {"comparison_basis": "equal_data_width", "k": 64, "objective": "encoder_energy", "direction": "min"},
    )
    assert selection["winner"] is None
    assert selection["proxy_to_physical_winner_changed"] is None


def test_characterization_store_rejects_unknown_implementation(tmp_path: Path) -> None:
    registry = _registry()
    result = characterize_implementation(
        registry,
        "hsiao-generated-combinational-72-64-v1",
        ROOT / "green_ecc_physical_simulation" / "registry" / "backends" / "not-characterized-v1.json",
        ROOT / "green_ecc_physical_simulation" / "registry" / "workloads" / "functional-uniform-placeholder-v1.json",
    )
    result["implementation_id"] = "unknown"
    basis = dict(result)
    basis.pop("result_sha256")
    from green_ecc_phy.hashing import canonical_hash

    result["result_sha256"] = canonical_hash(basis)
    with pytest.raises(ValueError, match="unknown implementation_id"):
        CharacterizationStore(registry).add(result)


def test_additive_cli_list_and_inspect() -> None:
    listed = subprocess.run(
        [sys.executable, "eccsim.py", "ecc", "list"], cwd=ROOT,
        check=True, capture_output=True, text=True,
    )
    payload = json.loads(listed.stdout)
    assert payload["code_count"] == 15
    inspected = subprocess.run(
        [sys.executable, "eccsim.py", "ecc", "inspect", "--code", "hsiao-secded-72-64-v1"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    detail = json.loads(inspected.stdout)
    assert detail["matrix_checks"]["g_h_transpose_zero"] is True
    assert detail["implementation_ids"] == ["hsiao-generated-combinational-72-64-v1"]
