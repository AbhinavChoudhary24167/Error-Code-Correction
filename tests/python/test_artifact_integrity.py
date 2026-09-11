import json
import subprocess
import sys

from scripts.check_artifact import ROOT, duplicate_values, missing_fields


def test_integrity_helpers_detect_missing_and_duplicate_fields():
    records = [{"experiment_id": "a"}, {"experiment_id": "a"}, {"other": "b"}]
    assert duplicate_values(records, "experiment_id") == ["a"]
    assert missing_fields(records[2], ("experiment_id", "other")) == ["experiment_id"]


def test_current_status_preserves_scientific_claim_guards():
    path = ROOT / (
        "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/"
        "CAMPAIGN_STATUS.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["global_winner"] == "NO_GLOBAL_WINNER_QUALIFIED"
    assert payload["whole_memory_e5_qualified"] is False
    assert payload["runtime_budget"]["scope"] == "ENTIRE_CAMPAIGN"
    assert payload["runtime_budget"]["seconds"] == 54000


def test_artifact_checker_cli_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/check_artifact.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
