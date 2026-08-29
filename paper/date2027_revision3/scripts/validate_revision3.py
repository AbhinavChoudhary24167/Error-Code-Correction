#!/usr/bin/env python3
"""Validate Revision-3 provenance, citation, and DATE layout contracts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    tex_path = HERE / "date2027_revision3.tex"
    bib_path = HERE / "date2027_revision3.bib"
    pdf_path = HERE / "date2027_revision3.pdf"
    log_path = HERE / "date2027_revision3.log"
    registry_path = HERE / "data/claim_registry.json"

    for path in (tex_path, bib_path, pdf_path, log_path, registry_path):
        require(path.is_file() and path.stat().st_size > 0, f"missing artifact: {path}")

    tex = tex_path.read_text(encoding="utf-8")
    bib = bib_path.read_text(encoding="utf-8")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    # Evidence sources are immutable inputs; every current hash must match the registry.
    for name, record in registry["sources"].items():
        source = REPO / record["path"]
        require(source.is_file(), f"missing evidence source: {name}: {source}")
        require(sha256(source) == record["sha256"], f"evidence hash drift: {name}")
    require(registry["formal_status"] == "PASS", "formal qualification is not PASS")
    require(registry["logic_depth_assessment"] == "NOT ASSESSABLE", "logic-depth missingness changed")

    # Curated one-page bibliography: exactly 27 entries, all and only cited entries.
    bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib))
    cite_groups = re.findall(r"\\cite\{([^}]+)\}", tex)
    cited_keys = {key.strip() for group in cite_groups for key in group.split(",")}
    require(len(bib_keys) == 27, f"expected 27 bibliography entries, found {len(bib_keys)}")
    require(cited_keys == bib_keys, f"citation mismatch; uncited={sorted(bib_keys-cited_keys)}, missing={sorted(cited_keys-bib_keys)}")

    # Scientific claim boundaries and the intentionally small Hsiao presentation.
    required_phrases = (
        "implementation identity determines what must be measured separately",
        "what must be measured separately}, not that every implementation transformation must produce a large difference",
        "panels intentionally share one y-axis",
        "Mapped logic depth is \\emph{not assessable}",
        "Reduced glitch propagation is plausible",
        "not technology portability",
        "not about the feasibility of BCH as a code family",
    )
    for phrase in required_phrases:
        require(phrase in tex, f"required claim boundary missing: {phrase}")
    forbidden_phrases = (
        "we measured $F_{\\max}$",
        "technology-independent",
        "BCH is infeasible",
        "We demonstrate that pipelining reduces",
        "hierarchical Hsiao is superior",
    )
    for phrase in forbidden_phrases:
        require(phrase not in tex, f"forbidden overclaim present: {phrase}")
    require("set_ylim(-30, 60)" in (HERE / "scripts/build_revision3.py").read_text(encoding="utf-8"), "shared Hsiao/SECDED visual scale changed")

    # DATE contract: six body pages followed by one reference page and no hard layout error.
    require(tex.count("\\clearpage") == 1, "expected one explicit body/reference page break")
    require("Output written on date2027_revision3.pdf (7 pages" in log, "final PDF is not exactly seven pages")
    require(re.search(r"\[6\]\s*\(date2027_revision3\.bbl", log) is not None, "bibliography does not start after six body pages")
    require("Overfull \\hbox" not in log and "Overfull \\vbox" not in log, "overfull LaTeX box detected")
    require("undefined citations" not in log.lower(), "undefined citation detected")
    require("undefined references" not in log.lower(), "undefined reference detected")

    figure_rows = (HERE / "data/figure02_equivalent_effects.csv").read_text(encoding="utf-8").splitlines()
    require(len(figure_rows) == 41, "Figure 2 must retain 2 studies x 4 metrics x 5 seeds")
    require(len(registry["macros"]) >= 70, "generated claim registry is unexpectedly incomplete")

    print("REVISION3_VALIDATION_PASS")
    print("pages=7 body=6 references=1 bibliography_entries=27 citations=27")
    print(f"evidence_sources={len(registry['sources'])} generated_macros={len(registry['macros'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
