#!/usr/bin/env python3
"""Fail-closed validation for the DATE 2027 Gate 06 analysis."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_06"
GATE05 = ROOT / "docs/date2027/rigour_gate_05"

COMB = "secded-rtl-combinational-72-64-v1"
PIPE = "secded-rtl-pipelined-72-64-v1"
HSIAO = "hsiao-generated-combinational-72-64-v1"
BCH = "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    required = (
        "GATE06_ANALYSIS_POLICY.json",
        "GATE06_EFFECT_SIZES.json",
        "GATE06_DOMINANCE_ANALYSIS.json",
        "GATE06_DESIGN_SPACE.csv",
        "GATE06_RELIABILITY_TABLE.csv",
        "GATE06_PHYSICAL_TABLE.csv",
        "GATE06_CLAIM_RANKING.json",
        "GATE06_LIMITATIONS.json",
        "GATE06_FIGURE_SPECIFICATIONS.md",
        "GATE06_PAPER_TABLES.md",
        "GATE06_ADJUDICATION.md",
        "GATE06_FIGURE_DATA.json",
        "GATE06_PAPER_STRENGTH.json",
        "GATE06_EVIDENCE.sha256",
    )
    assert all((OUT / name).is_file() for name in required)

    policy = load("GATE06_ANALYSIS_POLICY.json")
    assert policy["authoritative_input_policy"]["gate05_only"] is True
    assert policy["authoritative_input_policy"]["new_physical_runs"] is False
    assert policy["reliability_semantics"]["generic_reliability_score_forbidden"] is True
    assert policy["nsga_ii_adjudication"]["decision"] == "NOT_USED_NO_SCIENTIFIC_VALUE"
    for source in policy["authoritative_input_policy"]["gate05_artifacts"]:
        path = ROOT / source["path"]
        assert digest(path) == source["sha256"]

    effects = load("GATE06_EFFECT_SIZES.json")
    by_name = {row["comparison"]: row for row in effects["comparisons"]}
    pipeline = by_name["pipelined SECDED vs combinational SECDED"]["metrics"]
    assert 36.70 < pipeline["standard_cell_instance_area_um2"]["percent_change"] < 36.71
    assert 45.91 < pipeline["achieved_fmax_mhz"]["percent_change"] < 45.92
    assert 12.06 < pipeline["detailed_route_wirelength_um"]["percent_change"] < 12.08
    assert -24.02 < pipeline["no_error_total_power_w"]["percent_change"] < -24.01
    assert pipeline["nominal_operation_latency_cycles"]["absolute_change"] == 2
    for name in ("BCH vs combinational SECDED", "BCH vs pipelined SECDED"):
        metrics = by_name[name]["metrics"]
        assert metrics["no_error_achievable_total_energy_pj_per_operation"]["missing_reason"] == "TARGET_CLOCK_INFEASIBLE"
        assert metrics["timing_deficit_ns"]["candidate_raw"] == 4.78052

    dominance = load("GATE06_DOMINANCE_ANALYSIS.json")
    spaces = {row["space"]: row for row in dominance["spaces"]}
    space_a = spaces["A_FULL_PHYSICALLY_FEASIBLE"]
    assert set(space_a["nondominated"]) == {COMB, PIPE}
    assert space_a["dominance_pairs"] == []
    space_b = spaces["B_PHYSICAL_IMPLEMENTATION"]
    assert {tuple(row.values()) for row in space_b["dominance_pairs"]} == {(BCH, COMB)}
    assert dominance["reliability_stratified"]["cross_tier_dominance_computed"] is False
    assert dominance["nsga_ii_used"] is False

    with (OUT / "GATE06_DESIGN_SPACE.csv").open(encoding="utf-8", newline="") as stream:
        design = list(csv.DictReader(stream))
    assert len(design) == 4
    design_by_id = {row["implementation_id"]: row for row in design}
    assert design_by_id[HSIAO]["area_um2"] == "PPA_UNAVAILABLE"
    assert design_by_id[BCH]["achievable_energy_pj_per_operation"] == "TARGET_CLOCK_INFEASIBLE"
    assert design_by_id[BCH]["space_b_member"] == "true"
    assert design_by_id[BCH]["space_a_member"] == "false"

    with (OUT / "GATE06_RELIABILITY_TABLE.csv").open(encoding="utf-8", newline="") as stream:
        reliability = list(csv.DictReader(stream))
    rel_by_id = {row["implementation_id"]: row for row in reliability}
    assert rel_by_id[COMB]["weight3_sdc_fraction"] == rel_by_id[PIPE]["weight3_sdc_fraction"] == "809/1065"
    assert rel_by_id[HSIAO]["weight3_sdc_fraction"] == "2847/4970"
    assert rel_by_id[BCH]["weight2_behavior"] == "CORRECTED 3003/3003"

    claims = load("GATE06_CLAIM_RANKING.json")["claims"]
    ranks = {row["rank"] for row in claims}
    assert ranks == {"STRONG", "SUPPORTED", "WEAK", "UNSUPPORTED"}
    assert {row["id"] for row in claims} == set("ABCDEFGHIJKL")
    assert len(load("GATE06_LIMITATIONS.json")["limitations"]) >= 12

    strength = load("GATE06_PAPER_STRENGTH.json")
    assert strength["decision"] == "DATE_REGULAR_PAPER_CORE_READY"
    assert len(strength["dimensions"]) == 8
    assert "aggregate score is computed" in strength["scale"]

    for stem in (
        "F01_CROSS_LAYER_METHOD",
        "F02_AREA_VS_FMAX",
        "F03_NORMALIZED_PHYSICAL_COST",
        "F04_RELIABILITY_OUTCOMES",
    ):
        for suffix in (".svg", ".pdf", ".png"):
            path = OUT / "figures" / f"{stem}{suffix}"
            assert path.is_file() and path.stat().st_size > 1000
        assert b"<svg" in (OUT / "figures" / f"{stem}.svg").read_bytes()[:1000]
        assert (OUT / "figures" / f"{stem}.pdf").read_bytes().startswith(b"%PDF")
        assert (OUT / "figures" / f"{stem}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    for line in (OUT / "GATE06_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        assert digest(OUT / relative.removeprefix("./")) == expected
    report = (OUT / "GATE06_ADJUDICATION.md").read_text(encoding="utf-8")
    assert "`GATE_06_PASS`" in report
    assert "`DATE_REGULAR_PAPER_CORE_READY`" in report
    assert report.rstrip().endswith("`GATE_07_READY`")
    assert digest(GATE05 / "GATE05_EVIDENCE.sha256") == policy["authoritative_input_policy"]["gate05_evidence_manifest_sha256"]
    print("GATE06_VALIDATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
