#!/usr/bin/env python3
"""Validate provenance, scientific claim boundaries, and DATE layout."""

from __future__ import annotations

import csv
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


def validate_sources(registry: dict[str, object]) -> None:
    sources = registry["sources"]
    require(isinstance(sources, dict) and len(sources) == 14,
            "expected the fourteen frozen evidence sources")
    for name, untyped_record in sources.items():
        require(isinstance(untyped_record, dict), f"invalid source record: {name}")
        record = untyped_record
        source = REPO / str(record["path"])
        require(source.is_file(), f"missing evidence source: {name}: {source}")
        require(sha256(source) == record["sha256"], f"evidence hash drift: {name}")


def validate_provenance(path: Path) -> tuple[int, int]:
    expected_fields = [
        "claim_id", "paper_section", "experiment", "baseline_identity",
        "changed_identity", "condition", "seed", "metric", "raw_value",
        "display_value", "unit", "source_artifact", "source_hash",
        "qualification_status",
    ]
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == expected_fields, "provenance schema drift")
        rows = list(reader)
    require(len(rows) == 307, f"expected 307 provenance rows, found {len(rows)}")
    require(all(all(value != "" for value in row.values()) for row in rows),
            "blank provenance field detected")

    allowed_status = {
        "PROSPECTIVELY_FROZEN", "PROVEN", "PROVEN_TRANSACTION_RELATION",
        "QUALIFIED_HASH_JOINED_POWER", "QUALIFIED_MATCHED_PHYSICAL",
        "QUALIFIED_PHYSICAL_TARGET_INFEASIBLE",
        "QUALIFIED_STRUCTURAL_DISTINCTNESS", "QUALIFIED_TRACE",
    }
    require({row["qualification_status"] for row in rows} <= allowed_status,
            "unknown qualification status")

    hash_cache: dict[Path, str] = {}
    for row in rows:
        source = REPO / row["source_artifact"]
        require(source.is_file(), f"provenance source missing: {source}")
        actual = hash_cache.setdefault(source, sha256(source))
        require(actual == row["source_hash"],
                f"provenance source hash drift: {row['claim_id']}: {source}")

    claim_ids = {row["claim_id"] for row in rows}
    required_claims = {
        "SEC10_AREA", "SEC10_TIMING", "SEC10_ENERGY", "SECDED_LATENCY",
        "SECDED_FORMAL", "SECDED_ENCODER_PROOF", "SECDED_DECODER_PROOF",
        "SECDED_ALIGNMENT",
        "HSIAO_FORMAL", "HS_AREA", "HS_TIMING", "HS_ENERGY",
        "POWER_EFFECT_INTERNAL", "POWER_EFFECT_SWITCHING",
        "POWER_EFFECT_TOTAL", "POWER_DELTA_INTERNAL", "POWER_DELTA_SWITCHING",
        "POWER_DELTA_TOTAL", "TRACE_RESET_CYCLES", "TRACE_DRAIN_CYCLES",
        "SEC5_AREA", "SEC5_TIMING", "SEC5_ENERGY",
        "BCH_FEASIBILITY", "BCH_SLACK", "BCH_VIOLATIONS",
    }
    require(required_claims <= claim_ids,
            f"required claims absent: {sorted(required_claims - claim_ids)}")

    bch_energy = [row for row in rows if row["claim_id"].startswith("BCH_")
                  and "energy" in row["metric"].lower()]
    require(not bch_energy, "target-infeasible BCH must not acquire energy")
    return len(rows), len(claim_ids)


def validate_citations(tex: str, bib: str) -> int:
    bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib))
    cite_groups = re.findall(r"\\cite\{([^}]+)\}", tex)
    cited_keys = {key.strip() for group in cite_groups for key in group.split(",")}
    require(len(bib_keys) == 27, f"expected 27 entries, found {len(bib_keys)}")
    require(cited_keys == bib_keys,
            f"citation mismatch; uncited={sorted(bib_keys-cited_keys)}, "
            f"missing={sorted(cited_keys-bib_keys)}")
    return len(bib_keys)


def validate_claim_language(tex: str) -> None:
    required_phrases = (
        "ECC semantics do not uniquely determine hardware architecture or physical energy",
        "not measured or achieved $F_{\\max}$",
        "These are not confidence intervals or population statistics",
        "timing is higher in 4/5 and reverses once",
        "do not by themselves prove a glitch mechanism",
        "not DVFS",
        "neither provides eligible target-clock energy nor implies that BCH is inherently slow or impractical",
        "the system was not used as an author or evidence source",
    )
    for phrase in required_phrases:
        require(phrase in tex, f"required claim boundary missing: {phrase}")

    forbidden_phrases = (
        "we measured $F_{\\max}$", "measured Fmax", "achieved Fmax",
        "technology-independent", "BCH is infeasible",
        "pipelining always reduces", "hierarchical Hsiao is superior",
        "statistically significant",
    )
    lowered = tex.lower()
    for phrase in forbidden_phrases:
        require(phrase.lower() not in lowered, f"forbidden overclaim present: {phrase}")

    require("\\title{From ECC Semantics to Physical Outcomes:" in tex,
            "selected title changed")
    require("\\author{\\IEEEauthorblockN{Anonymous submission}}" in tex,
            "double-blind author block changed")
    require(tex.count("\\section*{Acknowledgment}") == 1,
            "AI disclosure acknowledgment missing or duplicated")


def validate_layout(tex: str, log: str) -> None:
    require(tex.count("\\clearpage") == 1,
            "expected one explicit body/reference page break")
    require("Output written on main.pdf (7 pages" in log,
            "final PDF is not exactly seven pages")
    require(re.search(r"\[6.*?\]\s*\(main\.bbl", log, re.DOTALL) is not None,
            "bibliography does not start after six technical pages")
    require("Overfull \\hbox" not in log and "Overfull \\vbox" not in log,
            "overfull LaTeX box detected")
    require("undefined citations" not in log.lower(), "undefined citation detected")
    require("undefined references" not in log.lower(), "undefined reference detected")
    require("Label(s) may have changed" not in log,
            "cross-references require another LaTeX pass")


def main() -> int:
    paths = {
        "tex": HERE / "main.tex",
        "bib": HERE / "references.bib",
        "pdf": HERE / "main.pdf",
        "log": HERE / "main.log",
        "registry": HERE / "data/claim_registry.json",
        "provenance": HERE / "RESULT_PROVENANCE.csv",
    }
    generated = [
        HERE / "figures/figure01_identity_framework.pdf",
        HERE / "figures/figure02_equivalent_effects.pdf",
        HERE / "figures/figure03_power_condition.pdf",
        HERE / "tables/identity_matrix.tex",
        HERE / "tables/headline_results.tex",
        HERE / "data/generated_claims.tex",
    ]
    for path in [*paths.values(), *generated]:
        require(path.is_file() and path.stat().st_size > 0, f"missing artifact: {path}")

    tex = paths["tex"].read_text(encoding="utf-8")
    bib = paths["bib"].read_text(encoding="utf-8")
    log = paths["log"].read_text(encoding="utf-8", errors="replace")
    registry = json.loads(paths["registry"].read_text(encoding="utf-8"))

    validate_sources(registry)
    require(registry["formal_status"] == "PASS", "formal status is not PASS")
    require(registry["logic_depth_assessment"] == "NOT ASSESSABLE",
            "logic-depth missingness changed")
    require(len(registry["macros"]) == 94, "generated macro registry drift")

    rows, claims = validate_provenance(paths["provenance"])
    refs = validate_citations(tex, bib)
    validate_claim_language(tex)
    validate_layout(tex, log)

    figure_rows = (HERE / "data/figure02_equivalent_effects.csv").read_text(
        encoding="utf-8").splitlines()
    require(len(figure_rows) == 41,
            "Figure 2 must retain 2 studies x 4 metrics x 5 seeds")
    upstream = (REPO / "paper/date2027_revision3/scripts/build_revision3.py").read_text(
        encoding="utf-8")
    require("set_ylim(-30, 60)" in upstream,
            "shared Hsiao/SECDED visual scale changed")
    figure3_header = (HERE / "data/figure03_power_condition.csv").read_text(
        encoding="utf-8").splitlines()[0]
    require(figure3_header == "panel,metric,mean_percent,mean_mw",
            "Figure 3 data must retain percentages and additive mW differences")

    print("DATE2027_REVISION_VALIDATION_PASS")
    print(f"pages=7 technical=6 references=1 bibliography_entries={refs}")
    print(f"evidence_sources=14 provenance_rows={rows} claim_ids={claims} macros=94")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
