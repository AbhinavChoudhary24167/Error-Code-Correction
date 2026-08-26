from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from scripts.gate03es.scope_compatibility import is_registered_additive_path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_05"


def _json(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_gate05_required_outputs_exist_and_hash() -> None:
    for name in (
        "GATE05_IMPLEMENTATION_IDENTITY.json",
        "GATE05_RELIABILITY_SOURCE_MAP.json",
        "GATE05_INTEGRATED_RESULTS.csv",
        "GATE05_INTEGRATED_RESULTS.json",
        "GATE05_DERIVED_METRICS.json",
        "GATE05_MISSING_EVIDENCE.json",
        "GATE05_CLAIM_CANDIDATES.md",
        "GATE05_ADJUDICATION.md",
        "GATE05_EVIDENCE.sha256",
    ):
        assert (OUT / name).is_file()
    for line in (OUT / "GATE05_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        assert hashlib.sha256((OUT / relative.removeprefix("./")).read_bytes()).hexdigest() == expected


def test_gate05_paths_are_registered_as_additive_not_historical() -> None:
    for path in (
        "docs/date2027/rigour_gate_05/GATE05_ADJUDICATION.md",
        "scripts/gate05/build_gate05.py",
        "tests/python/test_gate05_integration.py",
    ):
        assert is_registered_additive_path(path)


def test_gate05_exact_architecture_identity_join() -> None:
    identity = _json("GATE05_IMPLEMENTATION_IDENTITY.json")
    rows = {row["implementation_id"]: row for row in identity["implementations"]}
    assert len(rows) == 4
    comb = rows["secded-rtl-combinational-72-64-v1"]
    pipe = rows["secded-rtl-pipelined-72-64-v1"]
    assert comb["code_id"] == pipe["code_id"] == "extended-hamming-secded-72-64-v1"
    assert comb["architecture"]["pipeline_depth_cycles"] == 0
    assert pipe["architecture"]["pipeline_depth_cycles"] == 2
    assert pipe["mapping_status"].startswith("EXACT_CODE_LEVEL")
    assert rows["hsiao-generated-combinational-72-64-v1"]["full_ppa_point_available"] is False


def test_gate05_reliability_is_universe_specific_and_not_field_weighted() -> None:
    records = _json("GATE05_INTEGRATED_RESULTS.json")["records"]
    by_id = {row["implementation_id"]: row for row in records}
    for row in records:
        universes = row["reliability"]["exact_fault_universes"]
        assert [item["weight"] for item in universes] == [0, 1, 2, 3]
        assert row["reliability"]["modeled_support_fault_coverage"]["fraction"] == "1"
        assert row["reliability"]["field_or_distribution_weighted_sdc_due"]["missing_reason"] == "METRIC_NOT_PROVEN"
    assert by_id["secded-rtl-combinational-72-64-v1"]["reliability"]["exact_fault_universes"][3]["sdc_fraction"] == "809/1065"
    assert by_id["hsiao-generated-combinational-72-64-v1"]["reliability"]["exact_fault_universes"][3]["sdc_fraction"] == "2847/4970"
    assert by_id["shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"]["reliability"]["exact_fault_universes"][3]["sdc_fraction"] == "265/1463"


def test_gate05_missing_values_are_not_zero() -> None:
    records = _json("GATE05_INTEGRATED_RESULTS.json")["records"]
    by_id = {row["implementation_id"]: row for row in records}
    hsiao = by_id["hsiao-generated-combinational-72-64-v1"]
    assert all(value is None for value in hsiao["physical"]["metrics"].values())
    assert hsiao["power_by_trace"] == {"double_error": None, "no_error": None, "single_error": None}
    assert set(value for key, value in hsiao["missing_reasons"].items() if key.startswith("physical.metrics")) == {"PPA_UNAVAILABLE"}
    bch = by_id["shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"]
    assert bch["power_by_trace"]["no_error"]["metrics"]["total_energy_pj_per_operation_estimate"] > 8000
    assert bch["power_by_trace"]["no_error"]["metrics"]["achievable_total_energy_pj_per_operation"] is None


def test_gate05_operation_normalization_and_architecture_trade() -> None:
    derived = _json("GATE05_DERIVED_METRICS.json")
    norm = derived["operation_normalization"]
    assert norm["useful_operations_per_trace"] == 100000
    assert norm["reset_cycles"] == 6
    assert norm["drain_cycles"] == 4
    assert norm["common_initiation_interval_cycles"] == 1
    assert norm["latency_cycles"]["secded-rtl-combinational-72-64-v1"] == 1
    assert norm["latency_cycles"]["secded-rtl-pipelined-72-64-v1"] == 3
    trade = derived["conventional_secded_architecture_trade"]
    assert 36.0 < trade["area_percent_change"] < 37.0
    assert 45.0 < trade["fmax_percent_change"] < 46.0
    assert -25.0 < trade["no_error_achievable_energy_percent_change"] < -23.0
    assert trade["initiation_interval_change_cycles"] == 0


def test_gate05_csv_has_explicit_missing_tokens() -> None:
    with (OUT / "GATE05_INTEGRATED_RESULTS.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 4
    by_id = {row["implementation_id"]: row for row in rows}
    assert by_id["hsiao-generated-combinational-72-64-v1"]["area_um2"] == "PPA_UNAVAILABLE"
    assert by_id["hsiao-generated-combinational-72-64-v1"]["fit_ser_projection"] == "METRIC_NOT_PROVEN"
    assert by_id["shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"]["no_error_achievable_energy_pj_per_operation"] == "TARGET_CLOCK_INFEASIBLE"


def test_gate05_verdict_and_gate06_readiness() -> None:
    report = (OUT / "GATE05_ADJUDICATION.md").read_text(encoding="utf-8")
    assert "`GATE_05_CONDITIONAL_PASS`" in report
    assert report.rstrip().endswith("`GATE_06_READY`")
    claims = (OUT / "GATE05_CLAIM_CANDIDATES.md").read_text(encoding="utf-8")
    assert "## STRONG" in claims
    assert "## SUPPORTED" in claims
    assert "## WEAK" in claims
    assert "## UNSUPPORTED" in claims
    assert "Any final best-ECC selection" in claims
