from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.gate03es.scope_compatibility import is_registered_additive_path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_06"
GATE05 = ROOT / "docs/date2027/rigour_gate_05"

COMB = "secded-rtl-combinational-72-64-v1"
PIPE = "secded-rtl-pipelined-72-64-v1"
HSIAO = "hsiao-generated-combinational-72-64-v1"
BCH = "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"


def _json(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate06_required_outputs_and_additive_scope() -> None:
    for name in (
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
    ):
        assert (OUT / name).is_file()
    for path in (
        "docs/date2027/rigour_gate_06/GATE06_ADJUDICATION.md",
        "scripts/gate06/build_gate06.py",
        "tests/python/test_gate06_analysis.py",
    ):
        assert is_registered_additive_path(path)


def test_gate06_uses_hash_verified_gate05_only() -> None:
    policy = _json("GATE06_ANALYSIS_POLICY.json")
    assert policy["authoritative_input_policy"]["gate05_only"] is True
    assert policy["authoritative_input_policy"]["stale_thesis_results_imported"] is False
    assert policy["authoritative_input_policy"]["new_physical_runs"] is False
    for source in policy["authoritative_input_policy"]["gate05_artifacts"]:
        assert _sha(ROOT / source["path"]) == source["sha256"]


def test_gate06_effect_sizes_recomputed_from_raw_gate05() -> None:
    records = {
        row["implementation_id"]: row
        for row in json.loads((GATE05 / "GATE05_INTEGRATED_RESULTS.json").read_text(encoding="utf-8"))["records"]
    }
    effects = {row["comparison"]: row for row in _json("GATE06_EFFECT_SIZES.json")["comparisons"]}
    metrics = effects["pipelined SECDED vs combinational SECDED"]["metrics"]

    def expected(key: str) -> float:
        candidate = records[PIPE]["physical"]["metrics"][key]
        reference = records[COMB]["physical"]["metrics"][key]
        return (candidate - reference) / reference * 100.0

    assert metrics["standard_cell_instance_area_um2"]["percent_change"] == expected("standard_cell_instance_area_um2")
    assert metrics["cell_count"]["percent_change"] == expected("cell_count")
    assert metrics["detailed_route_wirelength_um"]["percent_change"] == expected("detailed_route_wirelength_um")
    assert metrics["achieved_fmax_mhz"]["percent_change"] == expected("achieved_fmax_mhz")
    assert metrics["nominal_operation_latency_cycles"]["absolute_change"] == 2
    bch = effects["BCH vs combinational SECDED"]["metrics"]
    assert bch["timing_deficit_ns"]["candidate_raw"] == 4.78052
    assert bch["no_error_achievable_total_energy_pj_per_operation"]["missing_reason"] == "TARGET_CLOCK_INFEASIBLE"


def test_gate06_three_spaces_and_exact_dominance() -> None:
    policy = _json("GATE06_ANALYSIS_POLICY.json")
    spaces = policy["comparison_spaces"]
    assert spaces["A_FULL_PHYSICALLY_FEASIBLE"]["members"] == [COMB, PIPE]
    assert spaces["B_PHYSICAL_IMPLEMENTATION"]["members"] == [COMB, PIPE, BCH]
    assert spaces["C_RELIABILITY_ONLY"]["members"] == [COMB, PIPE, HSIAO, BCH]
    dominance = _json("GATE06_DOMINANCE_ANALYSIS.json")
    exact = {row["space"]: row for row in dominance["spaces"]}
    assert exact["A_FULL_PHYSICALLY_FEASIBLE"]["dominance_pairs"] == []
    assert exact["A_FULL_PHYSICALLY_FEASIBLE"]["nondominated"] == [COMB, PIPE]
    assert exact["B_PHYSICAL_IMPLEMENTATION"]["dominance_pairs"] == [
        {"dominator": COMB, "dominated": BCH}
    ]
    assert dominance["reliability_stratified"]["cross_tier_dominance_computed"] is False
    assert dominance["nsga_ii_used"] is False


def test_gate06_tables_preserve_missing_and_infeasible_values() -> None:
    with (OUT / "GATE06_PHYSICAL_TABLE.csv").open(encoding="utf-8", newline="") as stream:
        rows = {row["implementation_id"]: row for row in csv.DictReader(stream)}
    assert rows[HSIAO]["area_um2"] == "PPA_UNAVAILABLE"
    assert rows[HSIAO]["no_error_power_w"] == "PPA_UNAVAILABLE"
    assert rows[BCH]["achievable_energy_pj_per_operation"] == "TARGET_CLOCK_INFEASIBLE"
    assert float(rows[BCH]["diagnostic_target_energy_pj_per_operation"]) > 8000
    with (OUT / "GATE06_RELIABILITY_TABLE.csv").open(encoding="utf-8", newline="") as stream:
        reliability = {row["implementation_id"]: row for row in csv.DictReader(stream)}
    assert reliability[COMB]["weight2_behavior"] == "DUE 2556/2556"
    assert reliability[BCH]["weight2_behavior"] == "CORRECTED 3003/3003"
    assert reliability[HSIAO]["weight3_sdc_fraction"] == "2847/4970"


def test_gate06_figures_are_vector_first_and_missing_safe() -> None:
    for stem in (
        "F01_CROSS_LAYER_METHOD",
        "F02_AREA_VS_FMAX",
        "F03_NORMALIZED_PHYSICAL_COST",
        "F04_RELIABILITY_OUTCOMES",
    ):
        for suffix in (".svg", ".pdf", ".png"):
            assert (OUT / "figures" / f"{stem}{suffix}").stat().st_size > 1000
    specs = (OUT / "GATE06_FIGURE_SPECIFICATIONS.md").read_text(encoding="utf-8")
    assert "PPA_UNAVAILABLE" in specs
    assert "TARGET_CLOCK_INFEASIBLE" in specs
    assert "not operational probabilities" in specs


def test_gate06_claim_ranking_limitations_and_readiness() -> None:
    claims = _json("GATE06_CLAIM_RANKING.json")["claims"]
    assert {row["rank"] for row in claims} == {"STRONG", "SUPPORTED", "WEAK", "UNSUPPORTED"}
    assert next(row for row in claims if row["id"] == "A")["rank"] == "STRONG"
    assert next(row for row in claims if row["id"] == "C")["rank"] == "SUPPORTED"
    limitations = _json("GATE06_LIMITATIONS.json")["limitations"]
    assert len(limitations) >= 12
    strength = _json("GATE06_PAPER_STRENGTH.json")
    assert strength["decision"] == "DATE_REGULAR_PAPER_CORE_READY"
    assert len(strength["dimensions"]) == 8
    report = (OUT / "GATE06_ADJUDICATION.md").read_text(encoding="utf-8")
    assert "`GATE_06_PASS`" in report
    assert report.rstrip().endswith("`GATE_07_READY`")


def test_gate06_evidence_hashes_verify() -> None:
    for line in (OUT / "GATE06_EVIDENCE.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        assert _sha(OUT / relative.removeprefix("./")) == expected


def test_gate06_builder_is_byte_deterministic(tmp_path: Path) -> None:
    # The repository's ``python`` and ``python3`` commands intentionally resolve
    # to different supported Matplotlib versions.  Figure serialization is
    # deterministic within either analysis environment, but its exact bytes are
    # not a cross-version compatibility contract.  Generate twice with the
    # active interpreter; the separate evidence-manifest test protects every
    # frozen delivered byte.
    regenerated = [tmp_path / "gate06_a", tmp_path / "gate06_b"]
    child_environment = dict(os.environ)
    child_environment["MPLCONFIGDIR"] = str(tmp_path / "matplotlib_config")
    for output in regenerated:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/gate06/build_gate06.py"), "--out", str(output)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=child_environment,
        )

    generated_hashes = [
        {
            path.relative_to(output).as_posix(): _sha(path)
            for path in output.rglob("*") if path.is_file()
        }
        for output in regenerated
    ]
    assert generated_hashes[0] == generated_hashes[1]
