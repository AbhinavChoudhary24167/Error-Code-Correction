import csv
import json
import math
import uuid
from pathlib import Path

import pytest

from ml.dataset import build_dataset
from ml.features import OPTIONAL_NUMERIC_FEATURES


REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "tests" / "fixtures" / "runtime_ml_feature_pack"


def _new_base(tag: str) -> Path:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    base = RUNTIME / f"{tag}_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=False)
    return base


def _csv_columns(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or [])


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_feature_pack_core_has_no_optional_columns():
    base = _new_base("core_pack")
    dataset_dir = base / "dataset"

    build_dataset(REPO / "reports" / "examples", dataset_dir, feature_pack="core")

    cols = _csv_columns(dataset_dir / "dataset.csv")
    schema = json.loads((dataset_dir / "dataset_schema.json").read_text(encoding="utf-8"))
    assert all(name not in cols for name in OPTIONAL_NUMERIC_FEATURES)
    assert schema["feature_pack"] == "core"
    assert schema["enabled_features"] == []
    assert schema["disabled_features"] == []


def test_feature_pack_tier_mapping_columns():
    base = _new_base("tier_mapping")
    telemetry_dir = base / "telemetry"
    workload_dir = base / "workload"

    build_dataset(REPO / "reports" / "examples", telemetry_dir, feature_pack="core+telemetry")
    build_dataset(REPO / "reports" / "examples", workload_dir, feature_pack="core+telemetry+workload")

    cols_telemetry = _csv_columns(telemetry_dir / "dataset.csv")
    schema_telemetry = json.loads((telemetry_dir / "dataset_schema.json").read_text(encoding="utf-8"))
    assert "telemetry_retry_rate" in cols_telemetry
    assert all(name == "telemetry_retry_rate" or name not in cols_telemetry for name in OPTIONAL_NUMERIC_FEATURES)
    assert schema_telemetry["enabled_features"] == ["telemetry_retry_rate"]

    cols_workload = _csv_columns(workload_dir / "dataset.csv")
    schema_workload = json.loads((workload_dir / "dataset_schema.json").read_text(encoding="utf-8"))
    assert all(name in cols_workload for name in OPTIONAL_NUMERIC_FEATURES)
    assert schema_workload["enabled_features"] == OPTIONAL_NUMERIC_FEATURES


def test_enable_disable_precedence_disable_wins():
    base = _new_base("enable_disable")
    dataset_dir = base / "dataset"

    build_dataset(
        REPO / "reports" / "examples",
        dataset_dir,
        feature_pack="core",
        enable_features=["mbu_class_idx", "ser_slope_vdd"],
        disable_features=["ser_slope_vdd"],
    )

    cols = _csv_columns(dataset_dir / "dataset.csv")
    schema = json.loads((dataset_dir / "dataset_schema.json").read_text(encoding="utf-8"))
    assert "mbu_class_idx" in cols
    assert "ser_slope_vdd" not in cols
    assert schema["enabled_features"] == ["mbu_class_idx"]
    assert schema["disabled_features"] == ["ser_slope_vdd"]


def test_unknown_optional_feature_rejected():
    base = _new_base("unknown_feature")
    dataset_dir = base / "dataset"

    with pytest.raises(ValueError, match="Unknown optional feature"):
        build_dataset(
            REPO / "reports" / "examples",
            dataset_dir,
            feature_pack="core",
            enable_features=["not_a_feature"],
        )


def test_optional_feature_fallback_values_are_deterministic():
    base = _new_base("fallbacks")
    dataset_dir = base / "dataset"

    build_dataset(
        REPO / "reports" / "examples",
        dataset_dir,
        seed=3,
        feature_pack="core+telemetry+workload",
    )

    rows = _csv_rows(dataset_dir / "dataset.csv")
    assert rows
    for row in rows:
        scrub_s = float(row["scrub_s"])
        scrub_log10_s = float(row["scrub_log10_s"])
        fit_true = float(row["fit_true"])
        energy_true = max(float(row["energy_true"]), 1e-12)
        fit_per_watt_proxy = float(row["fit_per_watt_proxy"])

        assert float(row["telemetry_retry_rate"]) == 0.0
        assert float(row["ser_slope_vdd"]) == 0.0
        assert float(row["mbu_class_idx"]) == 1.0
        assert math.isclose(scrub_log10_s, math.log10(max(scrub_s, 1e-12)), rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(fit_per_watt_proxy, fit_true / energy_true, rel_tol=1e-12, abs_tol=1e-12)
