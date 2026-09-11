# Figure Design Review

## Revised final manuscript figures

### Figure 1 — evidence pipeline

- Two-row flow prevents crowding across the nine gates.
- Hardware/temporal control, implementation condition/physical state, and activity/measurement are separately colored and explicitly labeled.
- The routed-ECC-logic measurement boundary and SRAM-macro exclusion are visible.
- No repository version name appears.

### Figure 2 — estimator/operation ordering matrix

- This is the principal result figure: all five seeds, vectorless signs, operation-specific signs, and two missing cells are visible.
- Signed numbers and labels preserve meaning in grayscale.
- Different units remain in separate columns rather than sharing a numeric axis.

### Figure 3 — matched operation-energy deltas

- All 23 values, the zero line, operation means, and per-operation denominators are visible.
- The scale is not truncated to imply certainty or significance.

### Figure 4 — component decomposition

- Internal, net-switching, dynamic, and leakage-source data are preserved; the paper plots the visible-scale components and states that dynamic is internal plus switching.
- The caption treats the decomposition as accounting, not causal proof.

## Preserved material

Current-baseline figures remain in `figures/current_baseline/`; former identity-paper figures remain in `figures/superseded_but_preserved/`; alternatives and audit plots remain in `figures/candidates/` and `figures/analysis/`. Source JSON/CSV and the deterministic plotting script are preserved.

## Review result

PASS after page-by-page inspection of the final PDF: no clipping, title overlap, unreadable caption, color-only encoding, accidental blank page, or reference spill was observed.
