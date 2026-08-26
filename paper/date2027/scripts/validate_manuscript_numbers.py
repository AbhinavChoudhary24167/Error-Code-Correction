#!/usr/bin/env python3
"""Semantically validate important manuscript claims against Gate 07 evidence."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PAPER = ROOT / "paper" / "date2027"
G7 = ROOT / "docs" / "date2027" / "rigour_gate_07"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct(candidate: float, baseline: float) -> float:
    return (candidate - baseline) / baseline * 100.0


def main() -> None:
    ledger = load(G7 / "GATE07_CLAIM_LEDGER.json")
    figures = load(G7 / "GATE07_FIGURE_DATA.json")
    registry = load(PAPER / "data" / "claim_registry.json")
    by_claim = {claim["claim_id"]: claim for claim in ledger["claims"]}
    by_semantic = {entry["semantic_id"]: entry for entry in registry["claims"]}

    assert by_claim["C01"]["final_status"] == "CLAIM_FROZEN"
    assert by_claim["C02"]["final_status"] == "CLAIM_FROZEN"
    assert by_claim["C04"]["final_status"] == "CLAIM_FROZEN"

    c02 = by_claim["C02"]["raw_numbers"]
    expected = {
        "SEC_AREA_PCT": pct(c02["area_um2"][1], c02["area_um2"][0]),
        "SEC_WIRE_PCT": pct(c02["wirelength_um"][1], c02["wirelength_um"][0]),
        "SEC_FMAX_PCT": pct(c02["fmax_mhz"][1], c02["fmax_mhz"][0]),
        "SEC_ENERGY_PCT": pct(c02["energy_pj_per_operation"][1], c02["energy_pj_per_operation"][0]),
    }
    c04 = by_claim["C04"]["raw_numbers"]
    expected.update({"BCH_WNS": c04["wns_ns"], "BCH_DEFICIT": c04["timing_deficit_ns"], "BCH_FMAX": c04["fmax_mhz"]})
    bch_id = "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"
    routed = figures["F03_NORMALIZED_PHYSICAL_COST"]["routed_metrics"][bch_id]
    expected.update(
        {
            "BCH_AREA_PCT": routed["standard_cell_instance_area_um2"],
            "BCH_WIRE_PCT": routed["detailed_route_wirelength_um"],
            "BCH_FMAX_PCT": routed["achieved_fmax_mhz"],
        }
    )

    required_rounded = {
        "SEC_AREA_PCT": "36.702",
        "SEC_WIRE_PCT": "12.067",
        "SEC_FMAX_PCT": "45.911",
        "SEC_ENERGY_PCT": "-24.016",
        "BCH_AREA_PCT": "207.356",
        "BCH_WIRE_PCT": "310.975",
        "BCH_FMAX_PCT": "-72.258",
        "BCH_WNS": "-4.78052",
        "BCH_FMAX": "67.6566",
    }
    for semantic_id, expected_value in expected.items():
        assert semantic_id in by_semantic, semantic_id
        registered = by_semantic[semantic_id]
        assert math.isclose(float(registered["value"]), float(expected_value), rel_tol=0.0, abs_tol=1e-12), semantic_id
        if semantic_id in required_rounded:
            assert format(float(registered["value"]), registered["format"]) == required_rounded[semantic_id], semantic_id

    macro_text = (PAPER / "data" / "generated_claims.tex").read_text(encoding="utf-8")
    manuscript_text = "\n".join(path.read_text(encoding="utf-8") for path in [PAPER / "main.tex", *sorted((PAPER / "sections").glob("*.tex"))])
    for entry in registry["claims"]:
        macro = entry.get("display_macro") or entry.get("macro")
        if macro and entry["semantic_id"] in required_rounded:
            assert re.search(rf"\\newcommand\{{\\{re.escape(macro)}\}}", macro_text), macro
            assert f"\\{macro}" in manuscript_text, f"important macro not used: {macro}"

    forbidden_literal = "8488.495"
    assert forbidden_literal not in manuscript_text
    assert "GATE_03" not in manuscript_text and "Gate 03" not in manuscript_text
    print("NUMERICAL_VALIDATION_PASS: 9 required quantitative claims match frozen Gate 07 evidence.")


if __name__ == "__main__":
    main()
