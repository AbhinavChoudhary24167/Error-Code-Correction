from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "eccsim.py"


def test_analyze_surface_missing_candidates_has_actionable_error(tmp_path: Path) -> None:
    missing = tmp_path / "candidates.csv"
    out_csv = tmp_path / "surface.csv"

    cmd = [
        sys.executable,
        str(SCRIPT),
        "analyze",
        "surface",
        "--from-candidates",
        str(missing),
        "--out-csv",
        str(out_csv),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode != 0
    assert "Generate candidates first via `select --emit-candidates <path>`" in res.stderr


def test_ml_split_dataset_missing_dataset_has_actionable_error(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "ml_dataset"

    cmd = [
        sys.executable,
        str(SCRIPT),
        "ml",
        "split-dataset",
        "--dataset",
        str(dataset_dir),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode != 0
    assert "Run `ml build-dataset --from <artifacts_dir> --out" in res.stderr
