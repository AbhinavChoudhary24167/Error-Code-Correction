# DATE 2027 Revision-3 manuscript audit

## Scope and source state

- Starting repository commit: `b51291442bbd04346dac939dea6ba7d532b9c5c4`.
- Revision branch: `codex/date-2027-paper-revision-3`.
- Source branch at audit start: `codex/date-2027-breadth-remediation`.
- Pre-existing user work preserved and excluded from this manuscript-only revision:
  - modified `scripts/gate03e/validate_artifacts.py`;
  - modified `tests/python/test_gate03_artifacts.py`;
  - untracked qualified `campaigns/date_2027_breadth_remediation/` campaign.
- No physical experiment is authorized or required. The paper consumes only already-qualified evidence.

## Current manuscript

- Primary Revision-2 source: `paper/date2027_revision2/main.tex` plus seven files under `sections/`.
- Primary Revision-2 PDF: `paper/date2027_revision2/date2027_submission_v2.pdf`.
- PDF audit: 7 US-letter pages, comprising six body pages and one references page.
- Revision-2 bibliography: `paper/date2027_revision2/references_date2027_v2.bib`, 14 entries, all displayed on page 7.
- Revision-2 figure generator: `paper/date2027_revision2/scripts/build_artifacts.py`.
- Revision-2 validator: `paper/date2027_revision2/scripts/validate_manuscript.py`.
- Visual audit: readable IEEE two-column layout with three figures and three tables. The related-work section is too narrow for the expanded implementation-identity story, the historical Hsiao recovery and BCH discussion consume disproportionate space, and the paper lacks the qualified structural Hsiao pair, component-level power decomposition, and 5 ns replication.

## Qualified evidence located

### Revision 2

- Registry: `docs/date2027/revision2/results/REV2_MANUSCRIPT_EVIDENCE.json`.
- Per-seed paired SECDED effects: `docs/date2027/revision2/results/REV2_SECDED_PAIRED_SEED_EFFECTS.json`.
- Per-architecture summaries: `docs/date2027/revision2/results/REV2_ARCHITECTURE_SUMMARY.json`.
- Frozen environment: `docs/date2027/revision2/REV2_MULTI_SEED_ENVIRONMENT.json`.
- Run-level evidence: `docs/date2027/revision2/results/REV2_RUN_RESULTS.csv` and `.json`.

### Breadth remediation

- Frozen physical contract: `campaigns/date_2027_breadth_remediation/physical/contract_v1.json`.
- Structural pair: `analysis/A_structural_pair_summary.json` and `A_structural_pair_per_seed.csv`.
- Power decomposition: `analysis/B_power_components_summary.json` and `B_power_components_per_seed.csv`.
- 5 ns condition: `analysis/C_5ns_summary.json` and `C_5ns_per_seed.csv`.
- Formal qualification: `formal/results/A_formal_qualification.json`.
- Mapped structural comparison: `synthesis/A_synthesis_structural_comparison.json`.
- Historical-integrity status: `FINAL_baseline_integrity_check.json` and `FINAL_campaign_status.md`.

## Revision decision

The manuscript is reconstructed around the experimentally tested separation

`ECC semantics != hardware architecture identity != physical identity`.

The large exact-equivalent temporal SECDED displacement and the modest, mixed exact-equivalent Hsiao structural displacement receive equal methodological status but deliberately unequal visual magnitude. The Hsiao effect will not be magnified through a separate narrow axis. The 5 ns campaign is described as constraint-condition robustness within one technology, not technology portability. BCH is retained only as a stronger-guarantee feasibility boundary.

## Title candidates

1. **From ECC Semantics to Physical Outcomes: Identity-Preserving Evaluation of Memory ECC Hardware** (selected)
2. **Implementation Identity Matters: Formal-to-Physical Evidence for Memory ECC Hardware**
3. **Correctness Before PPA: Implementation-Qualified Evidence for Memory ECC Hardware**

Candidate 1 most directly names the semantic-to-physical transition while avoiding a claim of universal numerical portability.

## Output plan

- New source root: `paper/date2027_revision3/`.
- Final source/PDF/bibliography: `date2027_revision3.tex`, `.pdf`, and `.bib`.
- Programmatic outputs: three vector PDF figures, two generated LaTeX tables, a generated macro file, and a machine-readable claim registry.
- Page target: six body pages plus one references page.
- Bibliography target: 22--30 cited and verified entries; 27 entries were admitted after the literature audit.
