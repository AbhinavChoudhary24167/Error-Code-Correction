"""Model bundle persistence helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib


MODEL_FILENAME = "model.joblib"


def save_model_bundle(bundle: dict[str, Any], model_dir: Path) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / MODEL_FILENAME
    joblib.dump(bundle, model_path)
    return model_path


def load_model_bundle(model_dir: Path) -> dict[str, Any]:
    model_path = model_dir / MODEL_FILENAME
    if not model_path.is_file():
        raise FileNotFoundError(f"Missing model bundle: {model_path}")
    return joblib.load(model_path)
