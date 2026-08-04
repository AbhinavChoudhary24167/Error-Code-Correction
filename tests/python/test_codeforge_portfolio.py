from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from codeforge.benchmarks import BENCHMARK_FAMILIES, build_benchmark
from codeforge.faults import FaultDistribution, load_fault_distribution
from codeforge.gf2 import bit_string, matrix_columns_as_ints, systematic_matrices
from codeforge.portfolio_pipeline import run_portfolio_cosynthesis
from codeforge.scalable import synthesize_scalable
from codeforge.shared_graph import portfolio_shared_graph


REPO = Path(__file__).resolve().parents[2]


def test_all_fault_benchmarks_are_seeded_normalized_and_labeled_synthetic() -> None:
    for offset, family in enumerate(BENCHMARK_FAMILIES):
        left = build_benchmark(family, bit_width=16, seed=9000 + offset)
        right = build_benchmark(family, bit_width=16, seed=9000 + offset)
        assert left == right
        assert left["provenance"]["kind"] == "synthetic"
        assert left["provenance"]["seed"] == 9000 + offset
        assert left["normalization"]["valid"] is True
        assert sum(item["probability"] for item in left["patterns"]) == pytest.approx(1.0)


def test_scalable_search_is_deterministic_and_requires_independent_verification() -> None:
    distribution = load_fault_distribution(
        REPO / "configs" / "fault_distributions" / "small_hotspot_8bit.json",
        repo_root=REPO,
    )
    config = json.loads((REPO / "configs" / "code_synthesis.example.json").read_text(encoding="utf-8"))
    config["method"] = "deterministic_beam"
    config["search"].update(
        {"seed": 123, "beam_width": 3, "iterations": 4, "mutations_per_candidate": 5}
    )
    first = synthesize_scalable(config, distribution)
    second = synthesize_scalable(config, distribution)
    assert first.code is not None and second.code is not None
    assert first.code["H"] == second.code["H"]
    assert first.code["decoder"] == second.code["decoder"]
    assert first.search["optimality_proven"] is False
    assert first.search["certification"].startswith("candidate must pass")


def test_shared_graph_reconstructs_all_forms_and_shares_duplicate_modes() -> None:
    h, g = systematic_matrices([3, 5, 6, 7], 4)
    columns = matrix_columns_as_ints(h)
    code = {
        "code_id": "graph-test",
        "k": 4,
        "r": 4,
        "n": 8,
        "H": h,
        "G": g,
        "decoder": {
            "correction_entries": [
                {"syndrome": bit_string(syn, 4), "positions": [position]}
                for position, syn in enumerate(columns)
            ]
        },
    }
    graph = portfolio_shared_graph([code, {**code, "code_id": code["code_id"] + "-copy"}])
    assert graph["equivalence_verified"] is True
    assert graph["total_xor_gates"] < graph["naive_total_xor_gates"]


def test_small_portfolio_pipeline_emits_certificates_graph_rtl_and_safety(tmp_path: Path) -> None:
    config = json.loads(
        (REPO / "configs" / "portfolio_cosynthesis.example.json").read_text(encoding="utf-8")
    )
    small_distribution = "configs/fault_distributions/small_hotspot_8bit.json"
    config["portfolio_id"] = "test-small-portfolio"
    config["k"] = 4
    config["r"] = 4
    config["regimes"] = [
        {"regime_id": "left", "probability": 0.5, "fault_distribution": small_distribution},
        {"regime_id": "right", "probability": 0.5, "fault_distribution": small_distribution},
    ]
    config["validation_distributions"] = [small_distribution]
    config["shifted_distributions"] = [small_distribution]
    config["code_template"]["matrix_constraints"] = {
        "min_row_weight": 2,
        "max_row_weight": 6,
        "min_data_column_weight": 2,
        "max_data_column_weight": 4,
    }
    config["code_template"]["constraints"] = {
        "max_sdc_probability": 0.0,
        "max_residual_fit": 1000.0,
        "max_matrix_xor_gates": 24,
    }
    config["code_template"]["search"].update(
        {"beam_width": 2, "iterations": 2, "mutations_per_candidate": 3, "timeout_seconds": 10}
    )
    config["cosynthesis"].update(
        {"iterations": 2, "candidates_per_mode": 2, "timeout_seconds": 10}
    )
    source = tmp_path / "portfolio.json"
    source.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "out"
    summary = run_portfolio_cosynthesis(source, output, repo_root=REPO)
    assert summary["mode_count"] == 2
    portfolio = json.loads((output / "portfolio.json").read_text(encoding="utf-8"))
    schema = json.loads((REPO / "schemas" / "ecc-portfolio.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(portfolio, schema)
    assert portfolio["shared_graph"]["equivalence_verified"] is True
    assert all(report["verification_status"] == "passed" for report in portfolio["certificates"].values())
    assert (output / "rtl").is_dir()
    assert (output / "figures" / "cosynthesis_pareto_trajectory.svg").is_file()
    assert portfolio["hardware_claim_status"].startswith("unsupported")
    assert portfolio["scheduler_integration_status"].startswith("blocked")
