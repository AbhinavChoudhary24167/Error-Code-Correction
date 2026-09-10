# Figure Design Review

## Final manuscript figures

### Figure 1 — evidence pipeline

- Decision: include, one column.
- Strength: makes the physical-identity control and measurement boundary visible before results.
- Risk addressed: readers otherwise conflate routed timing, activity, and macro energy.
- Source: semantic JSON; generated in all three formats.

### Figure 2 — estimator/operation ordering matrix

- Decision: include as the two-column principal figure.
- Strength: all five seeds and both estimator regimes are visible; mixed units are separated by headings; missing cells are explicit.
- Accessibility: sign, signed number, and color all encode the winner.
- Risk addressed: a mean-only chart could conceal seed reversals and unavailable pairs.

### Figure 3 — operation energy deltas

- Decision: include, one column.
- Strength: shows every matched activity value, zero line, operation means, and denominators.
- Risk addressed: Table II alone would hide dispersion.

### Figure 4 — component decomposition

- Decision: include, one column.
- Strength: supports the mechanistic interpretation that internal and switching terms oppose each other.
- Limitation: uses means and is diagnostic; caption explicitly subordinates it to per-seed total energy.

## Preserved candidates and analysis

- `figures/candidates/figure04_component_decomposition_alternative.*`: heatmap alternative rejected because the stacked signed bar exposes component competition more naturally.
- `figures/analysis/figure05_activity_coverage.*`: retained as audit evidence; omitted because coverage is stated compactly in text and the page budget is better spent on the ordering result.
- The first bar-chart candidate for component decomposition remains preserved in the directory history/output set; no scientific source data were deleted.

## Final review

PASS. Figures are publication-specific, self-contained with captions, vector-preserved, traceable to source rows, and do not use decorative imagery or borrowed graphics.

