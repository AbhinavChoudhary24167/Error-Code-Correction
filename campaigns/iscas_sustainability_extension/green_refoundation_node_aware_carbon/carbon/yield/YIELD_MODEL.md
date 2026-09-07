# Yield and good-die allocation model

The wafer-to-die boundary is:

`N_good = N_gross(D, A) * Y(D0, A, model) * Y_line`

where the continuous gross-die approximation is:

`N_gross ~= pi(D/2)^2/A - pi*D/sqrt(2A)`.

The approximation accounts for circular-edge loss but not scribe lanes,
edge-exclusion rings, reticle fields, or rectangular aspect ratio. Results are
expected counts, not integer floorplan promises.

Three yield models are implemented:

- Poisson: `Y = exp(-D0*A)`;
- negative binomial: `Y = (1 + D0*A/alpha)^(-alpha)`;
- Murphy: `Y = ((1-exp(-D0*A))/(D0*A))^2`, with the zero-defect limit set to 1.

`D0` is defects/cm2 and die area is converted from mm2 to cm2 before every
yield calculation. Negative-binomial `alpha` is mandatory and has no hidden
default. The 2023 imec paper uses a Murphy model with `D0=0.15 defects/cm2`
and reports 86% die yield for its 10x10 mm2 functional die, plus 90% line
yield. Those values may reproduce that paper's study assumption; they are not
universal node yields.

The per-good-die process carbon is `C_wafer/N_good`. Increasing die area both
reduces geometric die count and generally reduces yield, producing the
super-linear die-carbon behavior reported by imec. The host-die context is
therefore part of every incremental ECC result.
