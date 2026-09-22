# Activity-qualified ECC energy evidence — revision 2

This evidence package preserves the 5/5 vectorless versus 4/23 operation-specific ordering result and adds temporal SECDED, structural Hsiao, 10/5-ns condition sensitivity, and BCH timing-admission controls.

Canonical files:

- `data/` — normalized numerical results and derived statistics;
- `figures/` and `tables/` — reproducible evidence summaries;
- `CONTROLLED_IMPLEMENTATION_EVIDENCE.md` and `FINAL_REPORT.md` — scope and interpretation;
- `scripts/build_artifacts.py` — deterministic evidence regeneration;
- `PROVENANCE_MANIFEST.json` plus its digest — content seal.

The build verifies sealed upstream hashes before regenerating figures and tables. Publication sources, submission PDFs, and review-only material are intentionally excluded from this repository.
