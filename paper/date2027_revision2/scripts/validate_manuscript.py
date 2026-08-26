#!/usr/bin/env python3
"""Independently validate Revision-2 manuscript identity and headline numbers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
REV2 = REPO / "docs/date2027/revision2"
RESULTS = REV2 / "results"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_macros(path: Path) -> dict[str, str]:
    return dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{([^}]*)\}", path.read_text(encoding="utf-8")))


def expect(macros: dict[str, str], name: str, value: float, digits: int) -> None:
    expected = f"{value:.{digits}f}"
    if macros.get(name) != expected:
        raise AssertionError(f"macro {name}: {macros.get(name)!r} != {expected!r}")


def main() -> int:
    evidence = json.loads((RESULTS / "REV2_MANUSCRIPT_EVIDENCE.json").read_text(encoding="utf-8"))
    paired = json.loads((RESULTS / "REV2_SECDED_PAIRED_SEED_EFFECTS.json").read_text(encoding="utf-8"))
    macros = parse_macros(HERE / "data/generated_claims.tex")
    mapping = {
        "area_percent": "SecAreaEffect", "detailed_wirelength_percent": "SecWireEffect",
        "slack_derived_frequency_percent": "SecFreqEffect", "achievable_energy_percent": "SecEnergyEffect",
    }
    for key, prefix in mapping.items():
        summary = paired["effects"][key]["summary"]
        expect(macros, prefix + "Mean", summary["mean"], 1)
        expect(macros, prefix + "Min", summary["minimum"], 1)
        expect(macros, prefix + "Max", summary["maximum"], 1)
        expect(macros, prefix + "Std", summary["sample_standard_deviation"], 2)
    if macros["BchFeasible"] != evidence["bch_10ns_feasibility"]:
        raise AssertionError("BCH feasibility macro mismatch")
    if macros["HsiaoFeasible"] != evidence["hsiao_10ns_feasibility"]:
        raise AssertionError("Hsiao feasibility macro mismatch")

    text = "\n".join(path.read_text(encoding="utf-8") for path in [HERE / "main.tex", *sorted((HERE / "sections").glob("*.tex"))])
    forbidden = ("achieved Fmax", "measured Fmax", "SECDED dominates BCH", "p-value", "first work to")
    for phrase in forbidden:
        if phrase.lower() in text.lower():
            raise AssertionError(f"forbidden manuscript wording: {phrase}")
    required = ("slack-derived frequency estimate", "not a frequency sweep", "implementation identity", "matched")
    for phrase in required:
        if phrase.lower() not in text.lower():
            raise AssertionError(f"required manuscript wording absent: {phrase}")

    freeze = json.loads((REV2 / "REV2_HSIAO_RTL_FREEZE.json").read_text(encoding="utf-8"))
    for record in freeze["source_files"]:
        path = REPO / record["path"]
        if sha256(path) != record["sha256"]:
            raise AssertionError(f"post-freeze Hsiao identity change: {record['path']}")
    preservation = json.loads((REV2 / "REV2_REV1_PRESERVATION_AUDIT.json").read_text(encoding="utf-8"))
    for record in preservation["protected_artifacts"]:
        path = REPO / record["path"]
        if sha256(path) != record["sha256"]:
            raise AssertionError(f"Revision-1 preservation mismatch: {record['path']}")

    expected_outputs = [
        HERE / "tables/generated_table_i.tex", HERE / "tables/generated_table_ii.tex",
        HERE / "figures/figure01_methodology.pdf", HERE / "figures/figure02_seed_area_frequency.pdf",
        HERE / "figures/figure03_paired_effects.pdf", HERE / "data/claim_registry.json",
    ]
    missing = [str(path) for path in expected_outputs if not path.is_file()]
    if missing:
        raise AssertionError(f"missing generated outputs: {missing}")
    print("REV2_MANUSCRIPT_VALIDATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
