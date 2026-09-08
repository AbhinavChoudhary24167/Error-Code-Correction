from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from campaigns.iscas_sustainability_extension.green_refoundation_node_aware_carbon.integrity.build_final_hashes import (
    BASE,
    artifact_paths,
)


def test_final_status_withholds_a_winner_and_preserves_gate3() -> None:
    status = json.loads((BASE / "CAMPAIGN_STATUS.json").read_text(encoding="utf-8"))
    assert status["current_classification"] == "GREEN_METRIC_REFOUNDED_PARTIAL_QUALIFICATION"
    assert status["historical_gate3_status"] == "FAIL"
    assert status["selection"]["qualified_winner"] is None
    assert status["selection"]["eligible_matrix_rows"] == 0


def test_final_hash_manifest_covers_every_nonself_artifact() -> None:
    manifest_path = BASE / "integrity" / "FINAL_ARTIFACT_HASHES.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded = {item["path"]: item for item in manifest["artifacts"]}
    expected = {path.relative_to(BASE).as_posix(): path for path in artifact_paths(BASE)}
    assert set(recorded) == set(expected)
    assert manifest["artifact_count"] == len(expected)
    for relative, path in expected.items():
        assert recorded[relative]["bytes"] == path.stat().st_size
        assert recorded[relative]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_all_requested_figure_statuses_are_explicit() -> None:
    with (BASE / "figures" / "FIGURE_DATA_STATUS.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 15
    assert [row["figure_id"] for row in rows] == [
        f"F{index:02d}" for index in range(1, 16)
    ]
