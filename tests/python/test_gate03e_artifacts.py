from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.gate03e.validate_artifacts import validate


ROOT = Path(__file__).parents[2]
DOC = ROOT / "docs" / "date2027" / "rigour_gate_03e"


def load(name: str):
    return json.loads((DOC / name).read_text(encoding="utf-8"))


def test_gate03e_artifact_validator() -> None:
    assert validate() == []


def test_pinned_image_and_source_are_unchanged() -> None:
    image = load("ORFS_IMAGE_RECONCILIATION.json")
    source = load("ORFS_SOURCE_FREEZE.json")
    assert image["linux_amd64_manifest_digest"] == "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
    assert source["commit"] == "56496f3980fb6e9e58f10c8aea4a98949c0fe5f2"
    assert source["git_tree"] == "2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a"


def test_narrow_reconciliation_has_three_separate_lists() -> None:
    result = load("ORFS_IMAGE_RECONCILIATION.json")["execution_subset"]
    assert result["byte_identity_pass"] is True
    assert len(result["byte_identical_reconciled_files"]) == 169
    assert result["files_missing_from_container"] == []
    assert result["additional_container_files"] == []
    assert result["mismatched_execution_relevant_files"] == []


def test_two_targetless_smoke_runs_and_frozen_failure_are_retained() -> None:
    with (DOC / "GCD_SMOKE_RUNS.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert all(row["invocation"] == "make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk" for row in rows)
    assert all(row["status"] == "PASS" for row in rows)
    assert all(row["reproducibility_status"] == "FAIL" for row in rows)
    command = load("COMMAND_MANIFEST.json")
    assert command["frozen_reproducibility"]["policy_sha256"] == "258694f328084c3fb92dec24e07b3b40d261037d5b1bd8d32b119684211d0b9a"
    assert command["frozen_reproducibility"]["semantic_artifact_failure_count"] == 0
    assert command["frozen_reproducibility"]["reproducibility_pass"] is False


def test_mapping_is_structural_readiness_only() -> None:
    with (DOC / "GREEN_ECC_MAPPING_READINESS.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 4
    assert all(row["status"] == "PASS" for row in rows)
    assert all(row["generic_or_unmapped_cell_type_count"] == "0" for row in rows)
    assert all(row["comparative_ppa_generated"] == "False" for row in rows)
    pipeline = next(row for row in rows if row["job"] == "secded-pipelined")
    combinational = next(row for row in rows if row["job"] == "secded-combinational")
    assert int(pipeline["sequential_cell_count"]) > 0
    assert combinational["sequential_cell_count"] == "0"
    assert pipeline["normalized_mapped_netlist_sha256"] != combinational["normalized_mapped_netlist_sha256"]


def test_predeadline_incomplete_state_does_not_emit_terminal_failure() -> None:
    authorization = (DOC / "GATE_03_REENTRY_AUTHORIZATION.md").read_text(encoding="utf-8")
    assert "Authorization: **NOT AUTHORIZED**" in authorization
    assert "Current status: `INCOMPLETE_PENDING_DEADLINE`" in authorization
    assert "Terminal verdict: `NOT_ISSUED_BEFORE_DEADLINE`" in authorization
