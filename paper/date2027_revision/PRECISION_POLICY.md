# Numerical precision policy

This policy governs every number displayed in `main.tex`, its generated tables,
and its generated figures. Calculations retain the full precision stored in the
qualified source artifacts; rounding occurs only at the presentation boundary.

## Display rules

| Quantity | Normal display | Reason |
|---|---:|---|
| Large paired effects (temporal SECDED) | 1 decimal percentage point | The seed envelope is wider than the last displayed digit. |
| Small paired effects (structural Hsiao) | 3 decimal percentage points | Sub-percent area and low-single-digit effects require enough digits to preserve sign and relative scale. |
| Power-component and cell-group effects | 2 decimals | Supports numerical reconciliation without implying instrument-grade accuracy. |
| Absolute power differences in Fig. 3(a) | 4 decimals mW; leakage identified in nW in prose | Additive units are required when comparing component contributions. |
| Area and detailed wirelength means | nearest integer | Source precision exceeds what is useful in manuscript prose. |
| Signed-slack-derived frequency estimate | 1 decimal MHz | It is a deterministic transform of signed slack, not measured or achieved clock frequency. |
| Energy/op | 2 decimals pJ/op | Keeps the physical scale visible without exposing irrelevant source digits. |
| Power components | 4 decimals mW; leakage 4 decimals nW | Needed to show that leakage is negligible relative to milliwatt dynamic components. |
| Latency, initiation interval, violations, feasibility and sign counts | integer | These are exact counts under the declared contract. |

Min--max envelopes use the same precision as their corresponding means. A plus
sign is shown when direction matters. Figures may use coarser tick labels, but
their underlying CSV data retain full source precision.

## Semantic rules

- `f_slack = 1000 / (T - s_setup)` is always called a signed-slack-derived
  frequency estimate or timing metric. It is never called measured, achieved,
  characterized, or sign-off `Fmax`.
- Percentage effects are paired by seed before aggregation. They are not ratios
  of separately averaged endpoints.
- The five deterministic seeds are reported with descriptive sample spread,
  min--max envelope, and sign count. No confidence interval, p-value, or
  population claim is made.
- A target-infeasible or join-ineligible quantity is unavailable and displayed
  as an em dash. It is never imputed as zero.
- Positive area, cell, wire, via, and energy effects are costs. Positive timing
  effect is a benefit. Captions state this convention where the sign could be
  ambiguous.
- Power-component arithmetic is accounting evidence. It does not establish a
  unique causal mechanism such as glitch suppression.

The generated macros and `RESULT_PROVENANCE.csv` are the source of displayed
numbers. Hand-entered replacements are prohibited.

Tables use the document's normal 10-point font. Generated figure labels are
sized for at least 10-point rendering at their manuscript placement; the build
must not recover space by reducing either.
