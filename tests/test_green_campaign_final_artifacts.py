from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from campaigns.iscas_sustainability_extension.green_refoundation_node_aware_carbon.integrity.build_final_hashes import (
    BASE,
    artifact_paths,
)


LEGACY_EOL_BINDINGS = {
    "cleanup/POST_TEST_CLEANUP_MANIFEST.json": {
        "bytes": 20325,
        "sha256": "2d321a54cc49c3243907ee90d3f6e66320c9dc8c74f2e2351f1ef557212c5696",
        "canonical_sha256": "8af17a74b8d69ca9e2c04ac4d0a6417bba4029914cdd2b8a898e929a31edd0e3",
    }
}


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
        raw = path.read_bytes()
        lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        variants = {raw, lf, lf.replace(b"\n", b"\r\n")}
        matched_representation = any(
            recorded[relative]["bytes"] == len(payload)
            and recorded[relative]["sha256"] == hashlib.sha256(payload).hexdigest()
            for payload in variants
        )
        if matched_representation:
            continue
        binding = LEGACY_EOL_BINDINGS.get(relative)
        assert binding is not None
        assert recorded[relative]["bytes"] == binding["bytes"]
        assert recorded[relative]["sha256"] == binding["sha256"]
        assert hashlib.sha256(lf).hexdigest() == binding["canonical_sha256"]


def test_all_requested_figure_statuses_are_explicit() -> None:
    with (BASE / "figures" / "FIGURE_DATA_STATUS.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 15
    assert [row["figure_id"] for row in rows] == [
        f"F{index:02d}" for index in range(1, 16)
    ]
