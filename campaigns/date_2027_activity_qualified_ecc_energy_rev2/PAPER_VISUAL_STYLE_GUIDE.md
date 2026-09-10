# Paper Visual Style Guide

## Roles and preservation

Figures are classified as `CURRENT_BASELINE`, `REVISED_FINAL`, `CANDIDATE`, `ANALYSIS_ONLY`, or `SUPERSEDED_BUT_PRESERVED` in `DATE2027_FIGURE_MANIFEST.csv`. Prior visuals remain in their preservation directories even when they are not used in the revised paper.

## Palette and redundant encoding

- Evidence stages use blue `#0072B2`, green `#009E73`, and orange `#D55E00` by experimental role.
- Ordering cells use Hsiao-lower blue `#2C7BB6`, conventional-lower red `#D7191C`, and unavailable light gray.
- Color never carries category alone: cells include signed values, scatter plots include geometry and zero lines, and component bars use labels/hatching.
- Rainbow palettes, decorative gradients, and truncated axes intended to exaggerate small effects are prohibited.

## Typography and geometry

- One-column figures are authored at 3.45 in and two-column figures at 7.08 in.
- Plot text must remain legible in the compiled two-column PDF; captions carry scope and delta definitions.
- Quantitative axes and columns state units. Zero references are explicit.
- Canonical figures are vector PDF/SVG; PNG previews are exported at 450 dpi.

## Statistical and causal restraint

- Show every matched seed where practical and preserve unavailable cells rather than imputing them.
- Short mean bars are descriptive, not confidence intervals.
- Vectorless power and activity-aware energy are never plotted as commensurate magnitudes.
- Component accounting may support “consistent with” language but does not establish a net-level causal mechanism.
