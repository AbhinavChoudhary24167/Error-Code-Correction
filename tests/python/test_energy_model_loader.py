import json
from pathlib import Path

import pytest
import energy_model


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "calib.json"
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize("missing", ["source", "date", "tempC", "gates"])
def test_missing_metadata(tmp_path, missing):
    entry = {
        "source": "ref",
        "date": "2024-01-01",
        "tempC": 25,
        "gates": {"xor": 1e-12, "and": 2e-12},
    }
    entry.pop(missing)
    data = {"28": {"0.8": entry}}
    path = _write(tmp_path, data)
    with pytest.raises(ValueError):
        energy_model._load_calib(path)


def test_missing_gate_energy(tmp_path):
    entry = {
        "source": "ref",
        "date": "2024-01-01",
        "tempC": 25,
        "gates": {"xor": 1e-12},
    }
    data = {"28": {"0.8": entry}}
    path = _write(tmp_path, data)
    with pytest.raises(ValueError):
        energy_model._load_calib(path)
