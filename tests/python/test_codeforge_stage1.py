from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import jsonschema
import pytest

from codeforge.gf2 import is_zero_matrix, matmul, rank, transpose
from codeforge.pipeline import run_code_synthesis, verify_external_code


REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def forged(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("codeforge")
    summary = run_code_synthesis(
        REPO / "configs" / "code_synthesis.example.json",
        output,
        repo_root=REPO,
    )
    assert summary["status"] == "optimal"
    assert summary["optimality_proven"] is True
    assert summary["verification_status"] == "passed"
    return output


def test_exact_synthesis_emits_full_rank_orthogonal_systematic_code(forged: Path) -> None:
    code = json.loads((forged / "code.json").read_text(encoding="utf-8"))
    assert rank(code["H"]) == code["r"]
    assert is_zero_matrix(matmul(code["G"], transpose(code["H"])))
    schema = json.loads((REPO / "schemas" / "linear-code.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(code, schema)


def test_exhaustive_certificate_controls_sdc_and_beats_equal_redundancy_baseline(
    forged: Path,
) -> None:
    report = json.loads((forged / "verification_report.json").read_text(encoding="utf-8"))
    baseline = json.loads(
        (forged / "baselines" / "odd_column_secded_verification.json").read_text(encoding="utf-8")
    )
    assert report["campaign"]["kind"] == "exhaustive"
    assert report["campaign"]["data_words"] == 16
    assert report["campaign"]["error_patterns"] == 18
    assert report["campaign"]["decoder_cases"] == 288
    assert report["campaign"]["linearity_reduction_applied"] is False
    assert report["probability_mass"]["sdc"] == pytest.approx(0.0)
    assert report["probability_mass"]["corrected"] == pytest.approx(0.91)
    assert baseline["probability_mass"]["corrected"] == pytest.approx(0.48)
    assert report["fit"]["residual_fit"] == pytest.approx(90.0)
    assert report["verification_status"] == "passed"


def test_external_matrix_uses_same_independent_verifier(forged: Path) -> None:
    report = verify_external_code(
        forged / "code.json",
        REPO / "configs" / "fault_distributions" / "small_hotspot_8bit.json",
        repo_root=REPO,
    )
    assert report["verification_status"] == "passed"
    assert all(item["outcome"] != "silent_corruption" for item in report["per_pattern"])


def test_generated_python_and_cpp_references_agree(forged: Path, tmp_path: Path) -> None:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is unavailable")
    python_model = forged / "reference" / "reference_model.py"
    cpp_model = forged / "reference" / "reference_model.cpp"
    executable = tmp_path / "reference_model.exe"
    subprocess.run([compiler, "-std=c++17", str(cpp_model), "-o", str(executable)], check=True)
    for data, error in [(0, 0), (5, 1), (10, 3), (15, 0x24)]:
        py = subprocess.check_output(
            [sys.executable, str(python_model), str(data), str(error)], text=True
        ).strip()
        cpp = subprocess.check_output([str(executable), str(data), str(error)], text=True).strip()
        assert cpp == py


def test_generated_rtl_contains_encoder_syndrome_decoder_and_self_check(forged: Path) -> None:
    rtl = forged / "rtl"
    names = {path.name for path in rtl.iterdir()}
    assert any(name.endswith("_encoder.sv") for name in names)
    assert any(name.endswith("_syndrome.sv") for name in names)
    assert any(name.endswith("_decoder.sv") for name in names)
    testbench = next(path for path in rtl.iterdir() if path.name.startswith("tb_"))
    assert "$fatal" in testbench.read_text(encoding="utf-8")


def test_forge_code_cli_and_verify_code_cli(forged: Path) -> None:
    verify = subprocess.run(
        [
            sys.executable,
            str(REPO / "eccsim.py"),
            "verify-code",
            "--code",
            str(forged / "code.json"),
            "--fault-model",
            str(REPO / "configs" / "fault_distributions" / "small_hotspot_8bit.json"),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(verify.stdout)["verification_status"] == "passed"
