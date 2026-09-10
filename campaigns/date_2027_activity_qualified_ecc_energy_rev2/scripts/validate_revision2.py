#!/usr/bin/env python3
"""Validate Rev. 2 evidence, PDF layout, bibliography, figures, and blind state."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "DATE2027_MANUSCRIPT_REV2_BLIND.pdf"
TEX = ROOT / "DATE2027_MANUSCRIPT_REV2.tex"
LOG = ROOT / "build/DATE2027_MANUSCRIPT_REV2.log"


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def font_subtypes(reader: PdfReader) -> set[str]:
    found: set[str] = set()
    seen: set[int] = set()

    def scan(resources) -> None:
        if resources is None:
            return
        resources = resources.get_object()
        fonts = resources.get("/Font", {})
        fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
        for ref in fonts.values():
            found.add(str(ref.get_object().get("/Subtype", "UNKNOWN")))
        xobjects = resources.get("/XObject", {})
        xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
        for ref in xobjects.values():
            obj = ref.get_object()
            marker = id(obj)
            if marker in seen:
                continue
            seen.add(marker)
            if "/Resources" in obj:
                scan(obj["/Resources"])

    for page in reader.pages:
        scan(page.get("/Resources"))
    return found


def main() -> int:
    failures: list[str] = []
    required = [
        "PREVIOUS_MANUSCRIPT_AUDIT_UPDATED.md", "CURRENT_MANUSCRIPT_AUDIT.md",
        "CONTROLLED_IMPLEMENTATION_EVIDENCE.md", "FORMAL_QUALIFICATION_MATRIX.csv",
        "DATE2027_TERMINOLOGY_MAP.md", "DATE2027_REFERENCE_AUDIT.csv",
        "DATE2027_LITERATURE_GAP_MATRIX.csv", "DATE2027_CLOSEST_PRIOR_WORK.md",
        "DATE2027_NOVELTY_REDTEAM.md", "DATE2027_CLAIM_LEDGER.md",
        "DATE2027_REPRODUCIBILITY_TABLE.csv", "DATE2027_FIGURE_MANIFEST.csv",
        "DATE2027_TABLE_MANIFEST.md", "PAPER_VISUAL_STYLE_GUIDE.md",
        "PAPER_FIGURE_DESIGN_REVIEW.md", "DATE2027_MANUSCRIPT_REV2.md",
        "DATE2027_MANUSCRIPT_REV2.tex", "references.bib",
        "DATE2027_MANUSCRIPT_REV2_BLIND.pdf", "DATE2027_PAGE_COMPLIANCE.md",
        "DATE2027_DOUBLE_BLIND_AUDIT.md", "DATE2027_CITATION_INTEGRITY.md",
        "DATE2027_REVIEWER_ATTACKS.md", "FATAL_EVIDENCE_GAPS.md",
        "FINAL_REPORT.md", "PROVENANCE_MANIFEST.json",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        failures.append(f"missing required artifacts: {missing}")

    energy = csv_rows(ROOT / "data/operation_energy_deltas.csv")
    repro = csv_rows(ROOT / "DATE2027_REPRODUCIBILITY_TABLE.csv")
    vectorless = csv_rows(ROOT / "data/vectorless_ordering.csv")
    if (len(energy), len(repro), len(vectorless)) != (23, 46, 5):
        failures.append("evidence row counts differ from 23/46/5")
    if sum(float(row["energy_delta_pJ_per_operation"]) < 0 for row in energy) != 4:
        failures.append("activity Hsiao-lower count is not 4/23")
    if sum(float(row["total_power_delta_uW"]) < 0 for row in vectorless) != 5:
        failures.append("vectorless Hsiao-lower count is not 5/5")

    formal = csv_rows(ROOT / "FORMAL_QUALIFICATION_MATRIX.csv")
    if len(formal) != 4 or formal[0]["proof status"] != "PASS" or formal[1]["proof status"] != "PASS":
        failures.append("formal qualification matrix is incomplete")

    tex = TEX.read_text(encoding="utf-8")
    bib = (ROOT / "references.bib").read_text(encoding="utf-8")
    cited = {key.strip() for group in re.findall(r"\\cite\{([^}]+)\}", tex) for key in group.split(",")}
    bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
    if cited - bibkeys:
        failures.append(f"missing bibliography keys: {sorted(cited-bibkeys)}")
    required_phrases = [
        "only to the temporal SECDED pair",
        "did not meet the common 10-ns target in the five matched implementation attempts",
        "does not predict the magnitude or sign",
        "does not establish a causal mechanism",
        "not Monte Carlo process samples",
    ]
    for phrase in required_phrases:
        if phrase not in tex:
            failures.append(f"required scope phrase missing: {phrase}")
    forbidden = [
        "vectorless analysis is inaccurate", "Hsiao is inefficient", "BCH is infeasible",
        "superior architecture", "optimal ECC", "comprehensive framework", "novel framework",
        "GREEN v3", "Gate-3", "Level B", "E4_", "E5_",
    ]
    for phrase in forbidden:
        if phrase.lower() in tex.lower():
            failures.append(f"forbidden wording present: {phrase}")

    final_stems = {p.stem for p in (ROOT / "figures/revised_final").glob("*.pdf")}
    if final_stems != {
        "figure01_evidence_pipeline", "figure02_activity_ordering",
        "figure03_operation_energy_deltas", "figure04_component_decomposition",
    }:
        failures.append(f"unexpected revised-final figure set: {sorted(final_stems)}")
    for stem in final_stems:
        for ext in ("pdf", "svg", "png"):
            if not (ROOT / f"figures/revised_final/{stem}.{ext}").is_file():
                failures.append(f"missing figure format: {stem}.{ext}")

    reader = PdfReader(str(PDF))
    page_text = [page.extract_text() or "" for page in reader.pages]
    if len(page_text) != 7:
        failures.append(f"PDF has {len(page_text)} pages, expected 7")
    if len(page_text) >= 7:
        if "REFERENCES" not in page_text[6].upper():
            failures.append("page 7 is not a references page")
        technical = ["CONCLUSION", "THREATS", "RESULTS", "DISCUSSION"]
        leaks = [term for term in technical if term in page_text[6].upper()]
        if leaks:
            failures.append(f"technical content on page 7: {leaks}")
        if any("REFERENCES" in text.upper() for text in page_text[:6]):
            failures.append("references begin before page 7")
    author = str((reader.metadata or {}).get("/Author", "") or "")
    if author.strip():
        failures.append("PDF author metadata is not empty")
    blind_text = "\n".join(page_text) + json.dumps(dict(reader.metadata or {}))
    for token in ("Abhinav", "OneDrive", "C:\\Users", "github.com/"):
        if token.lower() in blind_text.lower():
            failures.append(f"potential blind-review leak: {token}")
    if "/Type3" in font_subtypes(reader):
        failures.append("Type-3 font found")

    log = LOG.read_text(encoding="utf-8", errors="replace")
    for marker in ("undefined references", "undefined citations", "Overfull \\hbox", "Overfull \\vbox"):
        if marker.lower() in log.lower():
            failures.append(f"LaTeX log issue: {marker}")

    report = {
        "status": "PASS" if not failures else "FAIL",
        "checks": {
            "pdf_pages": len(page_text),
            "technical_pages": 6 if len(page_text) == 7 else None,
            "references_only_page": 7 if len(page_text) == 7 else None,
            "activity_records": len(repro),
            "matched_activity_cells": len(energy),
            "revised_final_figures": sorted(final_stems),
            "font_subtypes": sorted(font_subtypes(reader)),
            "pdf_author_metadata": author,
        },
        "failures": failures,
    }
    (ROOT / "build/validation_report_rev2.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
