import json

import pytest
import qcrit_loader
from ser_model import qcrit_lookup


def test_direct_lookup():
    val = qcrit_lookup("sram6t", 14, 0.80, 75, 50)
    assert val == pytest.approx(0.28, rel=1e-6)


def test_out_of_bounds_warns_and_clamps():
    with pytest.warns(RuntimeWarning):
        val = qcrit_lookup("sram6t", 14, 0.90, 75, 50)
    assert val == pytest.approx(0.28, rel=1e-6)


def test_missing_temp_field(monkeypatch, tmp_path):
    element = "bad"
    data_dir = tmp_path / "data"
    schema_dir = tmp_path / "schemas"
    data_dir.mkdir()
    schema_dir.mkdir()

    data = {
        "units": {"qcrit": "fC"},
        "entries": [
            {
                "node_nm": 14,
                "vdd": 0.8,
                "pulse_rise_ps": 50,
                "method": "sim",
                "source": "test",
                "date": "2023-01-01",
                "qcrit": {"mean_fC": 0.28},
            }
        ],
    }
    (data_dir / f"qcrit_{element}.json").write_text(json.dumps(data))

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "units": {"type": "object"},
            "entries": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["units", "entries"],
    }
    (schema_dir / f"qcrit_{element}.schema.json").write_text(json.dumps(schema))

    monkeypatch.setattr(qcrit_loader, "__file__", str(tmp_path / "qcrit_loader.py"))
    qcrit_loader._QCRIT_CACHE.clear()

    with pytest.raises(ValueError, match="tempC"):
        qcrit_loader._load_qcrit_table(element)
