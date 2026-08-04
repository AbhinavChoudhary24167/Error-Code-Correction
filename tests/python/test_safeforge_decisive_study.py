import json
from pathlib import Path

from codeforge.decisive_study import run_decisive_study


ROOT = Path(__file__).resolve().parents[2]


def test_decisive_study_preserves_the_negative_gate(tmp_path):
    config = json.loads((ROOT / "configs/safeforge_decisive_72.json").read_text())
    config["fixed_code"] = "reports/code_synthesis/baselines/odd_column_secded_code.json"
    config["nominal_distribution"] = "configs/fault_distributions/small_hotspot_8bit.json"
    config["support_expansions"] = ["configs/fault_distributions/small_shifted_8bit.json"]
    config["heldout_synthetic_distributions"] = ["configs/fault_distributions/small_shifted_8bit.json"]
    config["placement_constraints"] = {
        "allowed_families": ["identity", "interleaved", "adjacent_swap"]
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    result = run_decisive_study(
        repo_root=ROOT,
        config_path=config_path,
        outdir=tmp_path,
    )
    assert result["gate"]["overall_status"] == "failed_negative_result"
    assert (tmp_path / "manifest.json").exists()
