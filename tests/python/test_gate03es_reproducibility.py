from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.gate03es.odb_semantic_export import REQUIRED_CATEGORIES, SCHEMA_ID
from scripts.gate03es.reproducibility import compare_run_metadata, read_json_no_duplicates, validate_policy
from scripts.gate03es.scope_compatibility import is_registered_additive_path


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "scripts/gate03es/reproducibility_policy_v3.json"
CATALOG = ROOT / "scripts/gate03es/producer_catalog_v3.json"
SCHEMA = ROOT / "scripts/gate03es/qor_metric_schema_v3.json"


def metadata(label: str, number: int) -> dict[str, object]:
    return {
        "schema_version": 3,
        "run_label": label,
        "container_root": f"/gate03es-run-0{number}",
        "host_root": f"/var/lib/green-ecc-gate03es/runs/{label}",
        "policy_frozen_at": "2026-08-14T00:00:00Z",
        "start_time": f"2026-08-14T0{number}:00:00Z",
        "end_time": f"2026-08-14T0{number}:01:00Z",
        "exit_status": 0,
        "container_id": f"container-{number}",
        "process_id": number,
    }


def test_policy_v3_is_closed_and_prospective() -> None:
    assert validate_policy(POLICY, CATALOG, SCHEMA) == []
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["prospective_only"] is True
    assert policy["preserves_gate03er_verdict"] == "ENVIRONMENT_ENABLEMENT_FAILED"
    assert policy["anti_posthoc_rules"]["path_specific_exclusion_list"] == []


def test_v3_reuses_every_v2_qor_identity_and_tolerance() -> None:
    v2 = json.loads((ROOT / "docs/date2027/rigour_gate_03er/QOR_METRIC_SCHEMA_V2.json").read_text(encoding="utf-8"))
    v3 = json.loads(SCHEMA.read_text(encoding="utf-8-sig"))
    stable_fields = ("artifact", "path", "gating", "absolute_tolerance", "unit", "family")
    assert len(v2["metrics"]) == len(v3["metrics"]) == 456
    assert [tuple(row[field] for field in stable_fields) for row in v2["metrics"]] == [
        tuple(row[field] for field in stable_fields) for row in v3["metrics"]
    ]
    assert {row["classification"] for row in v3["metrics"]} == {
        "SCIENTIFIC_EXACT", "SCIENTIFIC_TOLERANCED", "RUNTIME_RESOURCE_OBSERVATION"
    }


def test_run_labels_are_mandatory_distinct_provenance_not_equality_gated(tmp_path: Path) -> None:
    first, second = tmp_path / "run5.json", tmp_path / "run6.json"
    first.write_text(json.dumps(metadata("gcd-run-05", 5)), encoding="utf-8")
    second.write_text(json.dumps(metadata("gcd-run-06", 6)), encoding="utf-8")
    result = compare_run_metadata(
        first,
        second,
        json.loads(POLICY.read_text(encoding="utf-8")),
        json.loads(CATALOG.read_text(encoding="utf-8")),
    )
    assert result["pass"] is True
    labels = [row for row in result["fields"] if row["field"] == "run_label"]
    assert len(labels) == 2
    assert all(row["class"] == "PROVENANCE_IDENTITY" for row in labels)
    assert all(row["cross_run_equality_gated"] is False for row in labels)


def test_missing_malformed_duplicate_unexpected_or_equal_label_fails(tmp_path: Path) -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    good = metadata("gcd-run-06", 6)
    second = tmp_path / "second.json"
    second.write_text(json.dumps(good), encoding="utf-8")
    cases = [
        {key: value for key, value in metadata("gcd-run-05", 5).items() if key != "run_label"},
        {**metadata("bad-label", 5)},
        {**metadata("gcd-run-06", 5)},
        {**metadata("gcd-run-05", 5), "unexpected": 1},
    ]
    for index, value in enumerate(cases):
        first = tmp_path / f"first-{index}.json"
        first.write_text(json.dumps(value), encoding="utf-8")
        assert compare_run_metadata(first, second, policy, catalog)["pass"] is False
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"run_label":"gcd-run-05","run_label":"gcd-run-06"}', encoding="utf-8")
    try:
        read_json_no_duplicates(duplicate)
    except ValueError as exc:
        assert "duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate metadata key was accepted")


def test_scope_adapter_is_additive_and_fail_closed() -> None:
    assert is_registered_additive_path("docs/date2027/rigour_gate_03es/REPORT.md")
    assert is_registered_additive_path("scripts/gate03es/reproducibility.py")
    assert is_registered_additive_path("tests/python/test_gate03es_reproducibility.py")
    assert not is_registered_additive_path("docs/date2027/rigour_gate_03e/modified.json")
    assert not is_registered_additive_path("docs/date2027/rigour_gate_03/modified.json")
    assert not is_registered_additive_path("docs/date2027/rigour_gate_03es_evil/file")
    assert not is_registered_additive_path("unrelated/unauthorized.txt")
    assert not is_registered_additive_path("../docs/date2027/rigour_gate_03es/file")


def test_odb_semantic_export_declares_every_required_category() -> None:
    assert SCHEMA_ID == "gate03es-complete-odb-semantic-export-v1"
    assert set(REQUIRED_CATEGORIES) == {
        "technology", "units", "die_core_geometry", "rows", "tracks", "masters",
        "instances", "orientations", "placement_status", "nets", "pins",
        "connectivity", "routing_shapes", "vias",
    }


def test_gate03er_failure_and_scientific_pass_are_not_reinterpreted() -> None:
    report = (ROOT / "docs/date2027/rigour_gate_03er/GATE_03ER_REPORT.md").read_text(encoding="utf-8")
    comparison = json.loads((ROOT / "docs/date2027/rigour_gate_03er/FRESH_RUN_COMPARISON.json").read_text(encoding="utf-8"))
    assert (ROOT / "docs/date2027/rigour_gate_03er/GATE_03ER_VERDICT.txt").read_text().strip() == "ENVIRONMENT_ENABLEMENT_FAILED"
    assert "Semantic physical outputs, technology XML, stage ODBs, mapped masters, and all frozen QoR rules passed" in report
    assert comparison["failures"] == ["run-metadata.json: canonical scientific/technology difference"]
    assert all(row["pass"] for key in ("semantic_artifact_comparisons", "technology_xml_comparisons", "mapped_master_histograms", "metric_comparisons") for row in comparison[key])
    assert hashlib.sha256((ROOT / "scripts/gate03er/reproducibility_policy_v2.json").read_bytes()).hexdigest() == "d605d48ecb040e43d77fd278756e31e663ed30d329388e2217d13bc348a41493"
