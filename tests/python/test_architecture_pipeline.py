from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import jsonschema


REPO = Path(__file__).resolve().parents[2]


def test_architecture_pipeline_emits_valid_deployable_configuration(tmp_path: Path) -> None:
    config_schema = json.loads(
        (REPO / "schemas" / "architecture-dse-config.schema.json").read_text(encoding="utf-8")
    )
    config = json.loads(
        (REPO / "configs" / "architecture_dse.example.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(config, config_schema)
    outdir = tmp_path / "architecture"
    result = subprocess.run(
        [
            sys.executable,
            "eccsim.py",
            "architecture",
            "--config",
            "configs/architecture_dse.example.json",
            "--outdir",
            str(outdir),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)
    assert summary["scenario_count"] == 3
    assert summary["ecc_family_count"] == 5
    assert summary["ecc_configuration_count"] == 5
    assert summary["candidate_scenario_evaluations"] == 15

    deployment = json.loads(
        (outdir / "deployment" / "selected_configuration.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (REPO / "schemas" / "deployable-ecc-configuration.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(deployment, schema)
    assert deployment["metadata_format"]["mode_bits"] == 3
    assert deployment["metadata_format"]["stored_bits"] == 9
    assert deployment["validation_level"] == "conditional_projected"
    assert deployment["architecture_mode"] == "runtime_adaptive"
    assert deployment["hardware_topology"] == "gated_parallel"
    assert deployment["selection_fabric"]["logical_model"]["mux_2to1_count_total"] == 784
    assert deployment["controller_configuration"]["illegal_mode_action"] == "force_safe_fallback"
    assert set(deployment["selected_results"]) == {
        "moderate-low-carbon", "moderate-high-carbon", "heavy-fault-regime"
    }

    reports = json.loads((outdir / "data" / "scenario_reports.json").read_text(encoding="utf-8"))
    detail = reports[0]["candidate_details"]["sec-ded-64"]
    assert detail["layout"]["container_bits"] == 128
    assert detail["fabric"]["mux_2to1_count_total"] == 784
    assert detail["fabric"]["physical_metrics_characterized"] is False
    assert (outdir / "deployment" / "green_ecc_config_pkg.sv").is_file()
    assert (outdir / "result_manifest.json").is_file()
    manifest = json.loads((outdir / "result_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_tree_sha256"]
    assert "architecture/pipeline.py" in manifest["source_files"]
    assert manifest["repository_dirty"] is True
    modes = json.loads(
        (outdir / "data" / "deployment_mode_comparison.json").read_text(encoding="utf-8")
    )
    assert modes[0]["mux_2to1_count"] == 0
    assert modes[0]["reconfiguration_charged"] is False
    assert modes[2]["reconfiguration_charged"] is True
    topologies = json.loads(
        (outdir / "data" / "topology_comparison.json").read_text(encoding="utf-8")
    )
    assert {item["topology"] for item in topologies} == {
        "fixed", "parallel", "gated_parallel", "shared_reconfigurable"
    }
    assert (outdir / "data" / "scalability_benchmark.json").is_file()
    optimizer = json.loads(
        (outdir / "data" / "optimizer_validation.json").read_text(encoding="utf-8")
    )
    assert optimizer["agreement"] is True
    assert optimizer["symmetric_difference_count"] == 0

    counterfactuals = json.loads(
        (outdir / "data" / "baseline_counterfactuals.json").read_text(encoding="utf-8")
    )
    assert counterfactuals
    assert counterfactuals[0]["active_objectives"] == ["FIT"]
    assert "not evidence of a lifecycle-carbon advantage" in counterfactuals[0]["reason"]

    candidates = json.loads((outdir / "data" / "all_candidates.json").read_text(encoding="utf-8"))
    for candidate in candidates:
        assert "metric_provenance" in candidate
        assert candidate["metric_provenance"]["selection_fabric_logical"]["source"] == "analytical"
        for provenance in candidate["metric_provenance"].values():
            required = {
                "source", "technology_node_nm", "standard_cell_library", "device_model",
                "process_corner", "vdd_volts", "temperature_c", "tool", "tool_version",
                "calibration_source", "uncertainty", "repository_commit", "input_config",
                "repository_dirty", "source_tree_sha256", "input_config_sha256", "result_run_id"
            }
            assert required <= set(provenance)
            assert provenance["source"]
            assert provenance["repository_commit"]
