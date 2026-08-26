#!/usr/bin/env python3
"""Fail-closed validator for the DATE 2027 Gate 07 evidence freeze."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_07"
GATE06 = ROOT / "docs/date2027/rigour_gate_06"

COMB = "secded-rtl-combinational-72-64-v1"
PIPE = "secded-rtl-pipelined-72-64-v1"
BCH = "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percent(candidate: float, reference: float) -> float:
    return (candidate - reference) / reference * 100.0


def main() -> int:
    required = (
        "GATE07_SCOPE_STATEMENT.md",
        "GATE07_REVIEWER_ATTACKS.md",
        "GATE07_CLAIM_LEDGER.json",
        "GATE07_NUMERICAL_CLAIM_AUDIT.json",
        "GATE07_ENERGY_AUDIT.md",
        "GATE07_RELIABILITY_SEMANTICS.md",
        "GATE07_PHYSICAL_COMPARABILITY.md",
        "GATE07_CONTRIBUTION_FREEZE.md",
        "GATE07_FIGURE_FREEZE.json",
        "GATE07_TABLE_FREEZE.json",
        "GATE07_LIMITATIONS.md",
        "GATE07_MANUSCRIPT_EVIDENCE.json",
        "GATE07_ADJUDICATION.md",
        "GATE07_FIGURE_DATA.json",
        "GATE07_TABLE_I_IMPLEMENTATIONS.csv",
        "GATE07_TABLE_II_RESULTS.csv",
        "GATE07_EVIDENCE.sha256",
    )
    assert all((OUT / name).is_file() for name in required)

    for line in (OUT / "GATE07_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        assert digest(OUT / relative.removeprefix("./")) == expected

    manuscript = load("GATE07_MANUSCRIPT_EVIDENCE.json")
    assert manuscript["input_policy"]["gate06_frozen"] is True
    assert manuscript["input_policy"]["new_measurements"] is False
    assert manuscript["input_policy"]["excluded_thesis_subsystems_imported"] is False
    for source in manuscript["authoritative_inputs"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["bytes"]
        assert digest(path) == source["sha256"]

    numerical = load("GATE07_NUMERICAL_CLAIM_AUDIT.json")
    assert numerical["source"] == "docs/date2027/rigour_gate_06/GATE06_DESIGN_SPACE.csv"
    assert numerical["result"] == "NUMERICAL_CLAIM_AUDIT_PASS"
    assert numerical["mismatch_count"] == 0
    with (GATE06 / "GATE06_DESIGN_SPACE.csv").open(encoding="utf-8", newline="") as stream:
        design = {row["implementation_id"]: row for row in csv.DictReader(stream)}
    by_comparison = {
        row["comparison"]: {metric["metric"]: metric for metric in row["metrics"]}
        for row in numerical["comparisons"]
    }
    secded = by_comparison["pipelined SECDED vs combinational SECDED"]
    assert math.isclose(
        secded["standard_cell_instance_area_um2"]["recomputed_percent_change"],
        percent(float(design[PIPE]["area_um2"]), float(design[COMB]["area_um2"])),
    )
    assert math.isclose(
        secded["no_error_total_power_w"]["recomputed_percent_change"],
        percent(float(design[PIPE]["no_error_power_w"]), float(design[COMB]["no_error_power_w"])),
    )
    bch = by_comparison["BCH vs combinational SECDED"]
    assert bch["timing_deficit_ns"]["candidate_raw"] == float(design[BCH]["timing_deficit_ns"]) == 4.78052
    assert bch["no_error_achievable_total_energy_pj_per_operation"]["missing_reason"] == "TARGET_CLOCK_INFEASIBLE"

    energy = (OUT / "GATE07_ENERGY_AUDIT.md").read_text(encoding="utf-8")
    for token in (
        "`ENERGY_COMPARISON_VALID`",
        "100,000 accepted",
        "1,000,100,000 ps",
        "6 / 100,000 / 4 cycles",
        "Initiation interval",
        "pipeline bubbles",
        "does not assert lower single-request latency",
    ):
        assert token in energy

    claims = load("GATE07_CLAIM_LEDGER.json")["claims"]
    assert len(claims) == 13
    statuses = {row["final_status"] for row in claims}
    assert statuses == {"CLAIM_FROZEN", "CLAIM_NARROWED", "CLAIM_DISCUSSION_ONLY", "CLAIM_REMOVED"}
    by_id = {row["claim_id"]: row for row in claims}
    assert by_id["C02"]["final_status"] == "CLAIM_FROZEN"
    assert "36.702%" in by_id["C02"]["exact_proposed_wording"]
    assert "45.911%" in by_id["C02"]["exact_proposed_wording"]
    assert "24.016%" in by_id["C02"]["exact_proposed_wording"]
    assert by_id["C03"]["final_status"] == "CLAIM_NARROWED"
    assert by_id["C07"]["final_status"] == "CLAIM_DISCUSSION_ONLY"
    assert all(by_id[claim]["final_status"] == "CLAIM_REMOVED" for claim in ("C09", "C10", "C11", "C12", "C13"))

    reliability = (OUT / "GATE07_RELIABILITY_SEMANTICS.md").read_text(encoding="utf-8")
    assert "do **not** have different W3 universe sizes" in reliability
    assert f"{math.comb(72, 3):,}" in reliability
    assert f"{math.comb(78, 3):,}" in reliability
    for forbidden in ("They are not FIT", "or a W3 correction guarantee"):
        assert forbidden in reliability

    physical = (OUT / "GATE07_PHYSICAL_COMPARABILITY.md").read_text(encoding="utf-8")
    for token in ("SKY130HD", "TT 1.80 V, 25 C", "0.05 pF", "Seed / workers", "72-bit", "78 bits", "SYNTH_MEMORY_MAX_BITS=4096", "reviewer risk: `MEDIUM`"):
        assert token in physical

    reviewers = (OUT / "GATE07_REVIEWER_ATTACKS.md").read_text(encoding="utf-8")
    for heading in ("Reviewer A", "Reviewer B", "Reviewer C"):
        assert heading in reviewers
    assert reviewers.count("CRITICAL") >= 3
    assert "No unresolved `CRITICAL` issue" in reviewers

    contributions = (OUT / "GATE07_CONTRIBUTION_FREEZE.md").read_text(encoding="utf-8")
    assert contributions.count("PRIMARY_CONTRIBUTION") == 3
    assert "Three frozen manuscript contributions" in contributions
    assert "One sentence" in contributions and "Three sentences" in contributions
    assert "not a systematic external novelty review" in contributions.lower()

    figures = {row["id"]: row for row in load("GATE07_FIGURE_FREEZE.json")["figures"]}
    assert figures["F01_CROSS_LAYER_METHOD"]["status"] == "FIGURE_FROZEN"
    assert figures["F02_AREA_VS_FMAX"]["status"] == "FIGURE_FROZEN"
    assert figures["F03_NORMALIZED_PHYSICAL_COST"]["status"] == "FIGURE_REVISE"
    assert figures["F04_RELIABILITY_OUTCOMES"]["status"] == "FIGURE_DROP"
    tables = load("GATE07_TABLE_FREEZE.json")
    assert tables["major_table_count"] == 2
    assert len(tables["tables"]) == 2
    assert "OMIT_FROM_MAJOR_TABLES" in tables["weight3_main_table_decision"]
    with (OUT / "GATE07_TABLE_II_RESULTS.csv").open(encoding="utf-8", newline="") as stream:
        result_rows = list(csv.DictReader(stream))
    assert len(result_rows) == 4
    assert any(row["area_um2"] == "PPA_UNAVAILABLE" for row in result_rows)
    assert any(row["achievable_energy_pj_per_operation"] == "TARGET_CLOCK_INFEASIBLE" for row in result_rows)

    assert manuscript["energy_verdict"] == "ENERGY_COMPARISON_VALID"
    assert manuscript["date_manuscript_readiness"] == "DATE_MANUSCRIPT_READY"
    assert manuscript["gate_verdict"] == "GATE_07_PASS"
    assert manuscript["unresolved_critical_reviewer_issues"] == []
    assert len(manuscript["readiness_scores_1_to_10"]) == 9
    assert all(1 <= score <= 10 for score in manuscript["readiness_scores_1_to_10"].values())

    adjudication = (OUT / "GATE07_ADJUDICATION.md").read_text(encoding="utf-8")
    assert "`GATE_07_PASS`" in adjudication
    assert "`DATE_MANUSCRIPT_READY`" in adjudication
    assert adjudication.rstrip().endswith("`GATE_08_READY`")
    print("GATE07_VALIDATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
