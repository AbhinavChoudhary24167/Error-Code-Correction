#!/usr/bin/env python3
"""Fail-closed validation for the ISCAS 2027 paper-finalization package."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5"
EVIDENCE_SEAL = "8cf245ac6ac8cb9b010c073d439f04eb204d48a1"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_close(actual: float, expected: float, tolerance: float = 5e-7) -> None:
    assert abs(actual - expected) <= tolerance, (actual, expected)


def main() -> None:
    required = [
        "GREEN_CLAIM_LEDGER.md",
        "GREEN_EVIDENCE_MATRIX.csv",
        "GREEN_WORKLOAD_ANALYSIS.json",
        "GREEN_PAIRED_STATISTICS.json",
        "GREEN_PARETO_RESULTS.json",
        "GREEN_REPRODUCIBILITY_TABLE.csv",
        "PAPER_TABLES.md",
        "PAPER_OUTLINE.md",
        "MANUSCRIPT_DRAFT.md",
        "MANUSCRIPT_CLAIM_AUDIT.md",
        "FINAL_REPORT.md",
        "SOURCE_PROVENANCE.json",
        "RELATED_WORK_AUDIT.md",
        "NEW_ARTIFACTS.sha256",
    ]
    for name in required:
        assert (OUT / name).is_file(), name
    for index in range(1, 5):
        matches = list((OUT / "PAPER_FIGURES").glob(f"figure0{index}_*.svg"))
        assert len(matches) == 1, (index, matches)
        assert matches[0].with_suffix(".png").is_file()

    diff = subprocess.run(
        ["git", "diff", "--exit-code", EVIDENCE_SEAL, "--", CAMPAIGN.relative_to(ROOT).as_posix()],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert diff.returncode == 0, diff.stdout + diff.stderr

    statistics = load("GREEN_PAIRED_STATISTICS.json")
    ordering = statistics["ordering_summary"]
    assert (ordering["e4_hsiao_lower"], ordering["e4_comparison_count"]) == (5, 5)
    assert (ordering["e5_hsiao_lower"], ordering["e5_comparison_count"]) == (4, 23)
    metrics = statistics["metrics"]
    assert_close(metrics["energy_read_clean"]["mean"], -0.03083788724205234)
    assert_close(metrics["energy_write_clean"]["mean"], 0.1206819181343623)
    assert_close(metrics["energy_read_single_bit_error_correct"]["mean"], 0.30949969114138695)
    assert_close(metrics["energy_read_double_bit_error_detect"]["mean"], 0.19350520360313625)
    decomposition = statistics["component_decomposition_audit"]
    assert decomposition["switching_delta_lower_for_hsiao_count"] == 5
    assert decomposition["internal_delta_higher_for_hsiao_count"] == 5
    assert decomposition["net_energy_lower_for_hsiao_count"] == 3

    workload = load("GREEN_WORKLOAD_ANALYSIS.json")
    assert workload["primary_complete_case_model"]["seeds"] == [13, 17, 19, 23]
    assert workload["scenario_mode"]["declared_deployment_scenarios"] == []
    assert workload["operational_carbon_extension"]["carbon_intensity"] is None

    pareto = load("GREEN_PARETO_RESULTS.json")
    assert pareto["admitted_architectures"] == ["SECDED", "HSIAO_SECDED"]
    assert pareto["global_winner"] == "NO_GLOBAL_WINNER_QUALIFIED"
    assert pareto["clean_read_area_timing_energy"]["front"] == ["HSIAO_SECDED", "SECDED"]

    with (OUT / "GREEN_REPRODUCIBILITY_TABLE.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 46
    assert {row["operation_count"] for row in rows} == {"256"}
    assert {row["warm_up_cycles"] for row in rows} == {"16"}
    coverage = [float(row["functional_logic_activity_coverage"]) for row in rows]
    assert min(coverage) >= 0.99298390
    assert max(coverage) <= 0.99356062
    assert {row["required_sram_output_roots_annotated"] for row in rows} == {"72"}

    manuscript = (OUT / "MANUSCRIPT_DRAFT.md").read_text(encoding="utf-8")
    abstract_match = re.search(r"## Abstract\s+(.*?)\s+## I\.", manuscript, flags=re.S)
    assert abstract_match
    abstract_words = re.findall(r"\b[\w–-]+\b", abstract_match.group(1))
    assert 150 <= len(abstract_words) <= 180, len(abstract_words)
    banned = [
        "in today's rapidly evolving",
        "in recent years",
        "has garnered significant attention",
        "plays a pivotal role",
        "plays a crucial role",
        "it is important to note",
        "it is worth noting",
        "this highlights",
        "this underscores",
        "demonstrates the potential",
        "promising solution",
        "provides valuable insights",
        "paves the way",
        "opens new avenues",
        "groundbreaking",
        "transformative",
        "state-of-the-art",
    ]
    lowered = manuscript.lower()
    for phrase in banned:
        assert phrase not in lowered, phrase
    assert "statistically significant" not in lowered
    assert "not constitute silicon measurements" in lowered
    assert "they are not silicon measurements" in lowered
    assert not re.search(r"whole-memory energy is (qualified|measured|included)", lowered)

    recorded = {}
    manifest = OUT / "NEW_ARTIFACTS.sha256"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        value, relative = line.split("  ", 1)
        recorded[relative] = value
    expected = {
        path.relative_to(OUT).as_posix(): digest(path)
        for path in OUT.rglob("*")
        if path.is_file() and path != manifest and "__pycache__" not in path.parts
    }
    assert recorded == expected
    print("ISCAS 2027 GREEN paper-finalization validation: PASS")


if __name__ == "__main__":
    main()
