#!/usr/bin/env python3
"""Fail-closed validation for the generated ISCAS paper artifact."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PAPER = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def pdf_page_count(path: Path) -> int:
    # pdfTeX writes page dictionaries as plain objects. The word boundary keeps
    # /Type /Pages out of the count and avoids an optional PDF dependency.
    return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))


def main() -> int:
    failures: list[str] = []
    required = [
        "main.tex", "references.bib", "main.pdf", "EVIDENCE_AUDIT.md",
        "LITERATURE_MAP.md", "CLAIM_LEDGER.md", "RESULT_PROVENANCE.csv",
        "UNIT_AUDIT.md", "DATE_OVERLAP_AUDIT.md", "INTERNAL_REVIEW.md",
        "REPRODUCE.md", "SUBMISSION_READINESS.md",
        "figures/figure1_evidence_pipeline.pdf",
        "figures/figure2_feasibility_energy.pdf",
        "figures/figure3_workload_boundary.pdf",
        "tables/generated_claims.tex", "tables/architecture_population.tex",
        "tables/headline_results.tex", "tables/derived_metrics.json",
    ]
    for rel in required:
        check((PAPER / rel).is_file(), f"missing required artifact: {rel}", failures)

    with (PAPER / "RESULT_PROVENANCE.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    ids = [row["claim_id"] for row in rows]
    check(len(rows) >= 12, "too few provenance rows", failures)
    check(len(ids) == len(set(ids)), "duplicate provenance claim IDs", failures)
    for row in rows:
        sources = row["source_path"].split("|")
        hashes = row["source_sha256"].split("|")
        check(len(sources) == len(hashes), f"source/hash arity mismatch: {row['claim_id']}", failures)
        for source, expected in zip(sources, hashes):
            path = ROOT / source
            check(path.is_file(), f"missing provenance source: {source}", failures)
            if path.is_file():
                check(digest(path) == expected, f"source hash drift: {source}", failures)

    with (PAPER / "tables/derived_metrics.json").open(encoding="utf-8") as stream:
        derived = json.load(stream)
    check(derived["primary_seeds"] == [13, 17, 19, 23], "unexpected primary cohort", failures)
    check(derived["primary_record_count"] == 40, "unexpected primary E5 record count", failures)
    check(derived["matched_operation_comparison_count"] == 20, "unexpected comparison count", failures)
    check(derived["hsiao_lower_count"] == 4, "unexpected lower-energy count", failures)

    tex = (PAPER / "main.tex").read_text(encoding="utf-8")
    check("IEEEtran" in tex and "conference" in tex, "IEEE conference class missing", failures)
    check("\\clearpage\n\\bibliographystyle" in tex, "references-only page boundary missing", failures)
    check("globally greenest" not in tex.lower(), "unsupported global-winner wording", failures)
    check("silicon-measured" not in tex.lower(), "unsupported silicon measurement wording", failures)

    log = (PAPER / "main.log").read_text(encoding="utf-8", errors="replace")
    bad_log_patterns = (
        "undefined references", "Citation `", "Reference `", "multiply defined",
        "Overfull \\hbox", "Fatal error", "Emergency stop",
    )
    for pattern in bad_log_patterns:
        check(pattern not in log, f"LaTeX log contains: {pattern}", failures)

    pages = pdf_page_count(PAPER / "main.pdf")
    check(pages == 5, f"expected 5 PDF pages, found {pages}", failures)

    if failures:
        print("VALIDATION FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VALIDATION PASSED")
    print(f"provenance_rows={len(rows)}")
    print(f"pdf_pages={pages}")
    print("author_placeholder=REMAINS_MUST_DO")
    print("date_activity_overlap=REMAINS_MUST_DO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
