#!/usr/bin/env python3
"""Fail-closed validation for the Gate 05 evidence join."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_05"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main() -> int:
    required = (
        "GATE05_IMPLEMENTATION_IDENTITY.json",
        "GATE05_RELIABILITY_SOURCE_MAP.json",
        "GATE05_INTEGRATED_RESULTS.csv",
        "GATE05_INTEGRATED_RESULTS.json",
        "GATE05_DERIVED_METRICS.json",
        "GATE05_MISSING_EVIDENCE.json",
        "GATE05_CLAIM_CANDIDATES.md",
        "GATE05_ADJUDICATION.md",
        "GATE05_EVIDENCE.sha256",
    )
    assert all((OUT / name).is_file() for name in required)

    identity = load("GATE05_IMPLEMENTATION_IDENTITY.json")
    integrated = load("GATE05_INTEGRATED_RESULTS.json")
    missing = load("GATE05_MISSING_EVIDENCE.json")
    derived = load("GATE05_DERIVED_METRICS.json")
    assert identity["implementation_count"] == 4
    assert len(integrated["records"]) == 4
    assert identity["operation_normalization"]["status"].startswith("VALID_FOR_EQUIVALENT")
    assert identity["operation_normalization"]["useful_operations_per_trace"] == 100000

    by_id = {row["implementation_id"]: row for row in integrated["records"]}
    comb = by_id["secded-rtl-combinational-72-64-v1"]
    pipe = by_id["secded-rtl-pipelined-72-64-v1"]
    hsiao = by_id["hsiao-generated-combinational-72-64-v1"]
    bch = by_id["shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"]
    assert comb["code_id"] == pipe["code_id"] == "extended-hamming-secded-72-64-v1"
    assert comb["implementation_id"] != pipe["implementation_id"]
    assert pipe["reliability"]["application_to_architecture"].startswith("EXACT_CODE_LEVEL")
    assert hsiao["physical"]["metrics"]["standard_cell_instance_area_um2"] is None
    assert hsiao["missing_reasons"]["physical.metrics.standard_cell_instance_area_um2"] == "PPA_UNAVAILABLE"
    assert bch["physical"]["timing_feasibility"] == "FAILS_10NS"
    for trace in ("no_error", "single_error", "double_error"):
        assert bch["power_by_trace"][trace]["metrics"]["achievable_total_energy_pj_per_operation"] is None
        assert bch["missing_reasons"][f"power_by_trace.{trace}.metrics.achievable_total_energy_pj_per_operation"] == "TARGET_CLOCK_INFEASIBLE"

    for record in integrated["records"]:
        universes = record["reliability"]["exact_fault_universes"]
        assert [row["weight"] for row in universes] == [0, 1, 2, 3]
        assert record["reliability"]["modeled_support_fault_coverage"]["fraction"] == "1"
        assert record["reliability"]["fit_ser_projection"]["value"] is None
        assert record["reliability"]["placement_interleaving"]["value"] is None

    assert derived["conventional_secded_architecture_trade"]["same_reliability_semantics"] is True
    assert derived["conventional_secded_architecture_trade"]["nominal_latency_change_cycles"] == 2
    assert derived["cross_layer_observations"]["reliability_improvement_per_area_overhead"]["value"] is None
    assert missing["zero_substitution_forbidden"] is True

    with (OUT / "GATE05_INTEGRATED_RESULTS.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 4
    csv_by_id = {row["implementation_id"]: row for row in rows}
    assert csv_by_id[hsiao["implementation_id"]]["area_um2"] == "PPA_UNAVAILABLE"
    assert csv_by_id[bch["implementation_id"]]["no_error_achievable_energy_pj_per_operation"] == "TARGET_CLOCK_INFEASIBLE"
    assert csv_by_id[pipe["implementation_id"]]["full_ppa_pareto_point_eligible"] == "true"

    for line in (OUT / "GATE05_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = OUT / relative.removeprefix("./")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    adjudication = (OUT / "GATE05_ADJUDICATION.md").read_text(encoding="utf-8")
    assert adjudication.rstrip().endswith("`GATE_06_READY`")
    assert "GATE_05_CONDITIONAL_PASS" in adjudication
    print("GATE05_VALIDATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
