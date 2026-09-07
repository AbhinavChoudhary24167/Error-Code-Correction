from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
    / "carbon"
    / "model"
)
sys.path.insert(0, str(MODEL))

from semiconductor_carbon import (  # noqa: E402
    IPCC_AR6_GWP100,
    JOULES_PER_KWH,
    grams_to_kg,
    joules_to_kwh,
    kwh_to_joules,
    mm2_to_cm2,
)


def test_joule_kwh_conversion_is_exact_by_definition() -> None:
    assert JOULES_PER_KWH == 3_600_000.0
    assert joules_to_kwh(3_600_000.0) == 1.0
    assert kwh_to_joules(1.0) == 3_600_000.0
    assert kwh_to_joules(joules_to_kwh(123_456.0)) == pytest.approx(123_456.0)


def test_area_and_mass_conversions_are_dimensionally_correct() -> None:
    assert mm2_to_cm2(100.0) == 1.0
    assert grams_to_kg(1_000.0) == 1.0


def test_ipcc_ar6_gwp100_factors_are_not_process_consumption_constants() -> None:
    assert IPCC_AR6_GWP100 == {
        "CF4": 7_380.0,
        "C2F6": 12_400.0,
        "NF3": 17_400.0,
        "SF6": 25_200.0,
    }


def test_source_registry_json_and_csv_have_identical_source_ids() -> None:
    source_dir = (
        ROOT
        / "campaigns"
        / "iscas_sustainability_extension"
        / "green_refoundation_node_aware_carbon"
        / "carbon"
        / "sources"
    )
    registry = json.loads((source_dir / "SOURCE_REGISTRY.json").read_text("utf-8"))
    with (source_dir / "SOURCE_REGISTRY.csv").open(
        "r", encoding="utf-8", newline=""
    ) as stream:
        csv_rows = list(csv.DictReader(stream))
    json_ids = [source["source_id"] for source in registry["sources"]]
    csv_ids = [source["source_id"] for source in csv_rows]
    assert json_ids == csv_ids
    assert len(json_ids) == len(set(json_ids))


def test_every_source_has_required_audit_fields() -> None:
    registry_path = (
        ROOT
        / "campaigns"
        / "iscas_sustainability_extension"
        / "green_refoundation_node_aware_carbon"
        / "carbon"
        / "sources"
        / "SOURCE_REGISTRY.json"
    )
    registry = json.loads(registry_path.read_text("utf-8"))
    required = {
        "source_id",
        "authors",
        "title",
        "year",
        "publisher",
        "doi",
        "source_type",
        "access_date",
        "node_coverage",
        "system_boundary",
        "units",
        "assumptions",
        "usable_fields",
        "limitations",
        "confidence_tier",
    }
    for source in registry["sources"]:
        assert required <= source.keys()
        assert source["access_date"] == "2026-09-08"


@pytest.mark.parametrize(
    "function,value",
    [(joules_to_kwh, -1.0), (kwh_to_joules, -1.0), (mm2_to_cm2, -1.0)],
)
def test_unit_helpers_reject_negative_inputs(function, value: float) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        function(value)
