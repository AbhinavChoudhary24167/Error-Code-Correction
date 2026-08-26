from pathlib import Path

from scripts.gate03es.adjudicate_lf_scope import candidate_relpaths


def test_candidate_scope_excludes_build_and_runtime_products(tmp_path: Path) -> None:
    included = (
        "scripts/gate03e/validate_artifacts.py",
        "tests/python/test_gate03_artifacts.py",
        "scripts/gate03er/reproducibility.py",
        "scripts/gate03es/validate_scope.py",
        "tests/python/test_gate03es_lf_scope.py",
    )
    excluded = (
        "PracticalSRAMSimulator.exe",
        "drift.json",
        "tests/fixtures/runtime_ml_feature_pack/generated/dataset.csv",
        "scripts/gate03es/__pycache__/ignored.pyc",
    )
    for relative in (*included, *excluded):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n")

    result = candidate_relpaths(tmp_path)

    assert set(included) <= set(result)
    assert not set(excluded) & set(result)
