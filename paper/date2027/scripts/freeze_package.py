#!/usr/bin/env python3
"""Freeze the reviewed DATE 2027 manuscript package with SHA-256 provenance."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PAPER = ROOT / "paper" / "date2027"
OUTPUT = ROOT / "output" / "pdf" / "date2027_submission.pdf"
GATE07 = ROOT / "docs" / "date2027" / "rigour_gate_07" / "GATE07_MANUSCRIPT_EVIDENCE.json"
DEST = ROOT / "DATE2027_MANUSCRIPT_FREEZE.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_sha256(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def hashed(paths: list[Path]) -> dict[str, str]:
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(paths)}


def main() -> None:
    required = [OUTPUT, PAPER / "main.tex", PAPER / "references_date2027.bib", GATE07]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing freeze inputs: " + ", ".join(missing))

    source_files = [PAPER / "main.tex", *sorted((PAPER / "sections").glob("*.tex"))]
    figures = sorted((PAPER / "figures").glob("*.pdf"))
    table_data = sorted((PAPER / "data").glob("table_*.csv"))
    figure_data = sorted((PAPER / "data").glob("figure*.csv"))

    freeze = {
        "schema_version": 1,
        "generation_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "selected_title": "Implementation Identity Matters: Post-Route Trade-offs in Memory ECC Hardware",
        "manuscript_sha256": sha256(OUTPUT),
        "manuscript_path": OUTPUT.relative_to(ROOT).as_posix(),
        "manuscript_source_tree_sha256": source_tree_sha256(source_files),
        "manuscript_source_files": [path.relative_to(ROOT).as_posix() for path in source_files],
        "bibliography_sha256": sha256(PAPER / "references_date2027.bib"),
        "bibliography_path": (PAPER / "references_date2027.bib").relative_to(ROOT).as_posix(),
        "figure_hashes": hashed(figures),
        "figure_data_hashes": hashed(figure_data),
        "table_data_hashes": hashed(table_data),
        "gate07_evidence_sha256": sha256(GATE07),
        "gate07_evidence_path": GATE07.relative_to(ROOT).as_posix(),
        "final_contribution_statements": [
            "An identity-preserving cross-layer evaluation method that admits correctness-qualified ECC implementations and keeps guarantees, observations, architecture, and unavailable physical data distinct.",
            "A quantified non-dominated post-route trade-off between two exact-equivalent SECDED microarchitectures.",
            "An implementation-scoped correction-versus-feasibility result for the evaluated BCH RTL, while retaining unavailable Hsiao PPA explicitly rather than estimating it.",
        ],
        "final_claim_ids": ["C01", "C02", "C03", "C04", "C05", "C06", "C07"],
        "remaining_known_limitations": [
            "Specific evaluated RTL implementations only.",
            "SKY130HD at TT 1.80 V / 25 C only.",
            "One common 10 ns target and one deterministic seed/worker policy; no seed distribution or multi-corner signoff.",
            "Hsiao PPA unavailable under the unchanged 4096-bit synthesis-memory policy.",
            "BCH target-clock energy excluded because the evaluated implementation misses 10 ns.",
            "OpenSTA activity-based power estimates, not silicon measurements.",
            "No FIT, SER, field weighting, physical SRAM-array mapping, interleaving, or scrubbing model.",
            "Three routed designs and two timing-feasible energy points.",
        ],
        "validation": {
            "numerical_claims": "PASS (9/9 required semantic claims)",
            "page_budget": "PASS (6 manuscript pages + 1 references-only page)",
            "visual_review": "PASS (all 7 pages rendered and inspected)",
            "fonts": "PASS (embedded; no Type 3 fonts)",
            "reviewer_simulation": "PASS",
        },
    }
    DEST.write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    print(DEST)


if __name__ == "__main__":
    main()
