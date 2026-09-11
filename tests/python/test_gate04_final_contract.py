from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from green_ecc_phy.hashing import scientific_file_sha256


ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate04_final_set_matches_frozen_four_run_contract() -> None:
    contract = json.loads((ROOT / "scripts/gate04_final/contract_v1.json").read_text(encoding="utf-8"))
    final_set = json.loads(
        (ROOT / "docs/date2027/rigour_gate_04_final/GATE04_FINAL_ECC_SET.json").read_text(encoding="utf-8")
    )
    included = [row for row in final_set["records"] if row["classification"] == "INCLUDED"]
    excluded = [row for row in final_set["records"] if row["classification"] == "EXCLUDED"]
    assert len(included) == 4
    assert len(excluded) == 15
    assert [row["implementation_id"] for row in included] == contract["included_implementation_ids"]
    assert [row["implementation_id"] for row in contract["runs"]] == contract["included_implementation_ids"]
    assert len({row["run_id"] for row in contract["runs"]}) == 4
    assert contract["gate04_evidence_root"].endswith("gate04-final-confirmatory-02")
    assert set(contract["infrastructure_replacements"]) == {
        "secded-comb-final-01",
        "secded-pipe-final-01",
    }
    assert all(row["formal_exhaustive_correctness_status"].startswith("PASS") for row in included)


def test_gate04_final_policy_is_the_qualified_ten_ns_policy() -> None:
    contract = json.loads((ROOT / "scripts/gate04_final/contract_v1.json").read_text(encoding="utf-8"))
    assert contract["environment_identity"] == "DATE_FINAL_PHYSICAL_ENVIRONMENT_FROZEN"
    assert contract["flow"]["clock_period_ns"] == 10.0
    assert contract["flow"]["physical_seed"] == 11
    assert contract["flow"]["num_cores"] == 1
    assert contract["flow"]["core_utilization_percent"] == 35
    assert contract["flow"]["place_density"] == 0.55
    assert contract["execution_policy"]["optional_clock_sweep_authorized"] is False
    assert "CLEAN_REPLACEMENT_NAMESPACE_JUSTIFIED" in (
        ROOT / "docs/date2027/rigour_gate_04_final/GATE04_INFRASTRUCTURE_INCIDENT.md"
    ).read_text(encoding="utf-8")
    assert (ROOT / "scripts/gate04_final/configs/ecc.sdc").read_bytes() == (
        ROOT / "scripts/gate03f/configs/ecc.sdc"
    ).read_bytes()


def test_gate04_final_frozen_source_hashes_match_without_rtl_changes() -> None:
    contract = json.loads((ROOT / "scripts/gate04_final/contract_v1.json").read_text(encoding="utf-8"))
    migrations = json.loads(
        (
            ROOT
            / "green_ecc_physical_simulation/registry/scientific_hash_migrations.json"
        ).read_text(encoding="utf-8")
    )["bindings"]
    for relative, expected in contract["source_hashes"].items():
        source = ROOT / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() == expected:
            continue
        migration = migrations.get(relative)
        assert migration is not None
        assert migration["legacy_sha256"] == expected
        assert scientific_file_sha256(source) == migration["canonical_sha256"]


def test_gate04_full_precision_power_parser_uses_text_total_row() -> None:
    analyzer = _load_module("gate04_final_analyzer", "scripts/gate04_final/analyze_results.py")
    fixture = ROOT / "tests/fixtures/gate04_full_precision_power.rpt"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    try:
        fixture.write_text(
            "Group Internal Switching Leakage Total\n"
            "Total 6.786616984755e-03 7.788169197738e-03 7.300083204598e-09 1.457479409873e-02 100.0%\n",
            encoding="utf-8",
            newline="\n",
        )
        assert analyzer.parse_full_precision_power(fixture) == {
            "internal_power_w": 6.786616984755e-03,
            "switching_power_w": 7.788169197738e-03,
            "leakage_power_w": 7.300083204598e-09,
            "total_power_w": 1.457479409873e-02,
        }
    finally:
        fixture.unlink(missing_ok=True)


def test_gate04_power_precision_adjudication_is_prospective_and_resolved() -> None:
    text = (ROOT / "docs/date2027/rigour_gate_04_final/GATE04_POWER_PRECISION_ADJUDICATION.md").read_text(
        encoding="utf-8"
    )
    assert "ERROR_CLASS_POWER_DIFFERENCE_RESOLVED_BELOW_PRIOR_SERIALIZATION_PRECISION" in text
    assert "report_power -digits 12" in text
    assert "never average" in text
    activity = json.loads(
        (ROOT / "docs/date2027/rigour_gate_04_final/GATE04_POWER_ACTIVITY_AUDIT.json").read_text(encoding="utf-8")
    )
    assert len(activity["rows"]) == 9
    for family in ("conventional_secded", "hsiao", "bch78"):
        counts = {row["non_clock_bit_transitions"] for row in activity["rows"] if row["family"] == family}
        assert len(counts) > 1
