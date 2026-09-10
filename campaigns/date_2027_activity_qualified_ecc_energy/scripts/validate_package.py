#!/usr/bin/env python3
"""Validate the evidence-to-figure-to-PDF chain for the DATE package."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "DATE2027_MANUSCRIPT_BLIND.pdf"
TEX = ROOT / "DATE2027_MANUSCRIPT.tex"
LOG = ROOT / "build/DATE2027_MANUSCRIPT.log"


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def font_subtypes(reader: PdfReader) -> set[str]:
    found: set[str] = set()
    seen: set[int] = set()

    def scan_resources(resources) -> None:
        if resources is None:
            return
        resources = resources.get_object()
        fonts = resources.get("/Font", {})
        fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
        for ref in fonts.values():
            obj = ref.get_object()
            found.add(str(obj.get("/Subtype", "UNKNOWN")))
        xobjects = resources.get("/XObject", {})
        xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
        for ref in xobjects.values():
            obj = ref.get_object()
            marker = id(obj)
            if marker in seen:
                continue
            seen.add(marker)
            if "/Resources" in obj:
                scan_resources(obj["/Resources"])

    for page in reader.pages:
        scan_resources(page.get("/Resources"))
    return found


def main() -> None:
    failures: list[str] = []
    checks: dict[str, object] = {}
    required = [
        "DATE2027_MANUSCRIPT.tex", "DATE2027_MANUSCRIPT.md", "DATE2027_MANUSCRIPT_BLIND.pdf",
        "references.bib", "DATE2027_FIGURE_MANIFEST.csv", "DATE2027_TABLE_MANIFEST.md",
        "FIGURE_DATA_PROVENANCE.md", "DATE2027_REPRODUCIBILITY_TABLE.csv",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    checks["required_files_missing"] = missing
    if missing:
        failures.append(f"Missing required files: {missing}")

    energy = csv_rows(ROOT / "data/operation_energy_deltas.csv")
    repro = csv_rows(ROOT / "DATE2027_REPRODUCIBILITY_TABLE.csv")
    vectorless = csv_rows(ROOT / "data/vectorless_ordering.csv")
    checks["matched_activity_cells"] = len(energy)
    checks["activity_records"] = len(repro)
    checks["vectorless_rows"] = len(vectorless)
    if len(energy) != 23 or len(repro) != 46 or len(vectorless) != 5:
        failures.append("Evidence row counts differ from 23/46/5")
    hsiao_activity = sum(float(r["energy_delta_pJ_per_operation"]) < 0 for r in energy)
    hsiao_vectorless = sum(float(r["total_power_delta_uW"]) < 0 for r in vectorless)
    checks["activity_hsiao_lower"] = hsiao_activity
    checks["vectorless_hsiao_lower"] = hsiao_vectorless
    if (hsiao_activity, hsiao_vectorless) != (4, 5):
        failures.append("Headline sign counts differ from 4/23 and 5/5")

    tex = TEX.read_text(encoding="utf-8")
    bib = (ROOT / "references.bib").read_text(encoding="utf-8")
    cited = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", tex):
        cited.update(k.strip() for k in group.split(","))
    bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
    missing_bib = sorted(cited - bibkeys)
    checks["cited_keys"] = sorted(cited)
    checks["missing_bibliography_keys"] = missing_bib
    if missing_bib:
        failures.append(f"Missing bibliography keys: {missing_bib}")

    final_pdf_stems = {p.stem for p in (ROOT / "figures/final").glob("*.pdf")}
    incomplete_figures = []
    for stem in sorted(final_pdf_stems):
        for ext in ("pdf", "svg", "png"):
            if not (ROOT / f"figures/final/{stem}.{ext}").is_file():
                incomplete_figures.append(f"{stem}.{ext}")
    checks["final_figure_stems"] = sorted(final_pdf_stems)
    checks["incomplete_figure_formats"] = incomplete_figures
    if incomplete_figures or len(final_pdf_stems) != 4:
        failures.append("Final figure-format set is incomplete or not four figures")

    reader = PdfReader(str(PDF))
    page_text = [(p.extract_text() or "") for p in reader.pages]
    checks["pdf_pages"] = len(reader.pages)
    if len(reader.pages) != 7:
        failures.append(f"PDF has {len(reader.pages)} pages, expected 7")
    if "REFERENCES" not in page_text[6].upper():
        failures.append("Page 7 does not contain the References heading")
    forbidden_page7 = ["CONCLUSION", "THREATS TO VALIDITY", "REPLICATION AND FALSIFICATION"]
    bad_page7 = [term for term in forbidden_page7 if term in page_text[6].upper()]
    checks["page7_forbidden_sections"] = bad_page7
    if bad_page7:
        failures.append(f"Page 7 contains technical sections: {bad_page7}")
    if any("REFERENCES" in text.upper() for text in page_text[:6]):
        failures.append("References heading appears before page 7")

    metadata = reader.metadata or {}
    author = str(metadata.get("/Author", "") or "")
    checks["pdf_author_metadata"] = author
    if author.strip():
        failures.append("PDF Author metadata is not empty")
    blind_scan = "\n".join(page_text[:6]) + "\n" + json.dumps(dict(metadata))
    forbidden = ["Abhinav", "OneDrive", "C:\\Users", "github.com/", "green_v3", "E4_", "E5_"]
    blind_hits = [x for x in forbidden if x.lower() in blind_scan.lower()]
    checks["double_blind_forbidden_hits"] = blind_hits
    if blind_hits:
        failures.append(f"Potential blind-review leak: {blind_hits}")

    subtypes = sorted(font_subtypes(reader))
    checks["pdf_font_subtypes"] = subtypes
    if "/Type3" in subtypes:
        failures.append("Type-3 font found")

    log = LOG.read_text(encoding="utf-8", errors="replace")
    log_fail_patterns = ["undefined references", "Citation `", "Reference `", "Overfull \\hbox"]
    log_hits = [x for x in log_fail_patterns if x in log]
    checks["latex_log_failure_hits"] = log_hits
    if log_hits:
        failures.append(f"LaTeX log issues: {log_hits}")

    report = {"status": "PASS" if not failures else "FAIL", "checks": checks, "failures": failures}
    out = ROOT / "build/validation_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
