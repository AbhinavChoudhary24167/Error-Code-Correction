from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from architecture.schedule_pipeline import run_transition_schedule


REPO = Path(__file__).resolve().parents[2]


def test_schedule_pipeline_emits_schema_valid_deployable_study(tmp_path: Path) -> None:
    payload = json.loads(
        (REPO / "configs" / "transition_schedule.example.json").read_text(encoding="utf-8")
    )
    payload["trace_generators"] = [
        item for item in payload["trace_generators"]
        if item["family"] in {"one_time_sbu_to_mbu", "short_noisy_fluctuations"}
    ]
    payload["uncertainty_samples"] = 3
    payload["sweeps"]["epoch_accesses"] = [1_000_000, 100_000_000]
    payload["sweeps"]["transition_energy_multipliers"] = [0.0, 2.0]
    config = tmp_path / "config.json"
    config.write_text(json.dumps(payload), encoding="utf-8")
    outdir = tmp_path / "schedule"
    summary = run_transition_schedule(config, outdir, repo_root=REPO)
    assert summary["trace_count"] == 2
    result = json.loads((outdir / "data" / "schedule_result.json").read_text(encoding="utf-8"))
    schema = json.loads((REPO / "schemas" / "schedule-result.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(result, schema)
    assert result["deployment_policy"]["transition_sequence"][-2:] == [
        "commit_protected_mode", "resume"
    ]
    manifest = json.loads((outdir / "result_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_tree_sha256"]
    assert manifest["generated_trace_sources"]["one_time_sbu_to_mbu"]["seed"] == 1725
    assert (outdir / "figures" / "policy_timeline.svg").is_file()
    assert (outdir / "deployment" / "transition_policy.json").is_file()
    assert "not synthesized or measured" in (outdir / "findings.md").read_text(encoding="utf-8")
