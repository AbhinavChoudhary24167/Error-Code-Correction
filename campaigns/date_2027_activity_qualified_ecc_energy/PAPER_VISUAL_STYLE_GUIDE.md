# Paper Visual Style Guide

## Purpose

Figures must make the architecture-ordering test legible in print, grayscale, and color without implying more precision or scope than the data support.

## Palette and encodings

- Hsiao-lower / negative delta: blue `#2C7BB6`.
- Conventional-lower / positive delta: red `#D7191C`.
- Mean marker / secondary emphasis: orange `#D6604D`.
- Missing/unavailable: light gray with an em dash.
- Text and axes: near-black; grid lines light gray.
- Never rely on hue alone: cells contain signed numbers and captions define the sign.

## Typography and geometry

- Sans-serif plot labels at a size readable when embedded in one IEEE column.
- No chart title repeats the manuscript caption unless it adds the delta definition.
- Units appear on every quantitative axis or column heading.
- Zero reference lines are black and explicit.
- One-column figures are designed at 3.45 in; two-column figures at 7.08 in.
- PNG exports are 450 dpi; PDF and SVG are the canonical vector forms.

## Statistical honesty

- Show all seeds for paired energy deltas.
- Show missing cells rather than interpolating.
- Use short mean bars only; do not imply confidence intervals where none were calculated.
- Captions name the denominator and measurement boundary.
- Do not combine vectorless power magnitudes with activity energy magnitudes on one numeric axis.

## Accessibility checks

- Blue/red choices have large lightness and saturation contrast.
- Signed cell text and a zero line preserve meaning under color-vision deficiency or grayscale printing.
- Decorative gradients, 3-D effects, and low-contrast labels are prohibited.

