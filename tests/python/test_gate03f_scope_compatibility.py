from scripts.gate03es.scope_compatibility import (
    is_registered_additive_path,
    is_scope_path_allowed,
)


def test_gate03f_and_preserved_gate04_paths_are_prospectively_registered() -> None:
    for path in (
        "docs/date2027/rigour_gate_03f/DATE_FINAL_PHYSICAL_ENVIRONMENT.md",
        "scripts/gate03f/run_qualification.sh",
        "tests/python/test_gate03f_scope_compatibility.py",
        "docs/date2027/rigour_gate_04/EXPERIMENT_FREEZE.md",
        "scripts/gate04/run_flow.sh",
        "docs/date2027/rigour_gate_04_final/GATE04_FINAL_ECC_SET.json",
        "scripts/gate04_final/run_matrix.py",
        "tests/python/test_gate04_contract.py",
    ):
        assert is_registered_additive_path(path)


def test_adapter_does_not_register_historical_evidence_or_path_traversal() -> None:
    for path in (
        "docs/date2027/rigour_gate_03e/GATE_03E_REPORT.md",
        "scripts/gate03e/validate_artifacts.py",
        "../docs/date2027/rigour_gate_03f/forged.json",
        "/docs/date2027/rigour_gate_03f/forged.json",
    ):
        assert not is_registered_additive_path(path)

    assert is_scope_path_allowed(
        "docs/date2027/rigour_gate_03e/GATE_03E_REPORT.md",
        ("docs/date2027/rigour_gate_03e/",),
    )
