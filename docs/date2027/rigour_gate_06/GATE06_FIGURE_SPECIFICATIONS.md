# Gate 06 paper figure specifications

All figures are generated deterministically from the hash-verified Gate 05 dataset. SVG and PDF are manuscript masters; PNG files are review previews. Hsiao is never placed at zero or infinity, and BCH is never plotted as an achievable-energy point.

## Figure 1 — Cross-layer methodology

- **Files:** `figures/F01_CROSS_LAYER_METHOD.svg`, `.pdf`, `.png`
- **Claim served:** exact identity and missing-data boundaries are preserved from correctness through design-space conclusions.
- **Content:** correctness identity → exact reliability universes → RTL architecture → frozen physical implementation → comparison spaces A/B/C.
- **Mandatory annotation:** Hsiao stops at reliability-only; BCH retains routed physical evidence but no achievable target-clock energy.

## Figure 2 — Area versus achieved Fmax

- **Files:** `figures/F02_AREA_VS_FMAX.svg`, `.pdf`, `.png`
- **Claim served:** common physical policy exposes an architectural SECDED trade-off and BCH target infeasibility.
- **Points:** combinational SECDED, pipelined SECDED, BCH.
- **Reference:** horizontal 100 MHz target line.
- **Exclusion:** Hsiao is annotated `PPA_UNAVAILABLE`, not plotted.

## Figure 3 — Normalized physical effects

- **Files:** `figures/F03_NORMALIZED_PHYSICAL_COST.svg`, `.pdf`, `.png`
- **Claim served:** effect sizes relative to combinational SECDED are multi-dimensional and directionally conflicting.
- **Axes:** each metric is normalized to the conventional combinational SECDED value (100%); arrows identify minimize/maximize direction.
- **Metrics:** area, detailed wirelength, Fmax, no-error power, and no-error achievable steady-stream energy.
- **Missing semantics:** BCH achievable-energy bar is absent and annotated `TARGET_CLOCK_INFEASIBLE`; its diagnostic power is not used as an achievable-power comparison. Hsiao is annotated `PPA_UNAVAILABLE`.

## Figure 4 — Reliability-only outcome composition

- **Files:** `figures/F04_RELIABILITY_OUTCOMES.svg`, `.pdf`, `.png`
- **Claim served:** correction guarantees and beyond-guarantee outcomes are distinct; Hsiao and BCH remain scientifically informative without fabricating physical comparability.
- **Bars:** exhaustive weight-3 SDC miscorrection and DUE fractions for conventional SECDED semantics, Hsiao, and BCH.
- **Guarantee labels:** SECDED-class W1 correction/W2 detection; BCH W1/W2 correction.
- **Caveat:** the bars are canonical-coordinate observations, not operational probabilities or weight-3 correction guarantees.
