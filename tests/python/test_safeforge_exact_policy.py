import json
from pathlib import Path

import pytest

from codeforge.ambiguity import build_support
from codeforge.exact_policy import compile_exact_robust_policy, verify_exact_policy_certificate
from codeforge.faults import load_fault_distribution


ROOT = Path(__file__).resolve().parents[2]


def _fixture():
    code = json.loads(
        (ROOT / "reports/code_synthesis/baselines/odd_column_secded_code.json").read_text()
    )
    nominal = load_fault_distribution(
        "configs/fault_distributions/small_hotspot_8bit.json", repo_root=ROOT
    )
    shifted = load_fault_distribution(
        "configs/fault_distributions/small_shifted_8bit.json", repo_root=ROOT
    )
    support = build_support(nominal, [shifted])
    ambiguity = {
        "ambiguity_id": "test-tv",
        "type": "total_variation",
        "radius": 0.02,
    }
    return code, support, ambiguity


def test_exact_policy_certificate_replays_without_optimizer_state():
    code, support, ambiguity = _fixture()
    result = compile_exact_robust_policy(code, support, ambiguity, sdc_limit=0.05)
    verification = verify_exact_policy_certificate(code, support, ambiguity, result)
    assert verification["verification_status"] == "passed", verification["failures"]
    assert result["optimization"]["a_posteriori_absolute_gap"] <= 1e-8
    assert result["metrics"]["worst_case"]["sdc"] <= 0.05 + 1e-10


def test_stringent_tv_limit_forces_support_universal_actions():
    code, support, ambiguity = _fixture()
    result = compile_exact_robust_policy(code, support, ambiguity, sdc_limit=0.001)
    assert result["metrics"]["worst_case"]["sdc"] == pytest.approx(0.0)


def test_zero_sdc_decomposition_honors_policy_storage_budget_exactly():
    code, support, ambiguity = _fixture()
    result = compile_exact_robust_policy(
        code, support, ambiguity, sdc_limit=0.001, max_correction_entries=1
    )
    verification = verify_exact_policy_certificate(code, support, ambiguity, result)
    assert result["selected_correction_count"] == 1
    assert verification["verification_status"] == "passed", verification["failures"]


def test_exact_policy_detects_certificate_tampering():
    code, support, ambiguity = _fixture()
    result = compile_exact_robust_policy(code, support, ambiguity, sdc_limit=0.05)
    result["sdc_limit_modeled_support"] = 0.0
    verification = verify_exact_policy_certificate(code, support, ambiguity, result)
    assert verification["verification_status"] == "failed"
    assert "certificate_sha256 does not match certificate contents" in verification["failures"]


@pytest.mark.parametrize(
    ("ambiguity_file", "sdc_limit"),
    [
        ("structured_small_example.json", 0.4),
        ("wasserstein_small_example.json", 0.2),
    ],
)
def test_exact_constraint_generation_supports_interval_and_transport_ambiguity(
    ambiguity_file, sdc_limit
):
    code, support, _ = _fixture()
    ambiguity = json.loads((ROOT / "configs/ambiguity" / ambiguity_file).read_text())
    result = compile_exact_robust_policy(code, support, ambiguity, sdc_limit=sdc_limit)
    verification = verify_exact_policy_certificate(code, support, ambiguity, result)
    assert verification["verification_status"] == "passed", verification["failures"]
    assert result["metrics"]["worst_case"]["sdc"] <= sdc_limit + 1e-8
