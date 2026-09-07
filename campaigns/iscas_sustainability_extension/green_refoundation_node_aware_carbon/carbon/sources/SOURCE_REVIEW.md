# Semiconductor-carbon source review

Access date: 2026-09-08. The machine-readable registry is the source of
record. This review explains which evidence may enter the model and why.

## Source hierarchy and admission rule

Tier A contains first-party imec model publications, the first-party foundry
disclosure, IPCC characterization factors, and the GHG Protocol accounting
boundary. Tier B contains peer-reviewed architectural and LCA models used for
independent cross-checks. No blog summary is used where the primary paper,
institutional repository, standards body, or tool repository is available.

A number is admissible to a production calibration only when node/process
route, wafer diameter, system boundary, units, and material assumptions are
recoverable. Otherwise it remains a qualitative constraint, a normalized
validation point, or an explicitly parametric input.

## What the current imec evidence supports

The 2023 IEDM paper is the strongest public numeric anchor recovered. It uses
imec.netzero v1.5.67 for a generic 300 mm high-volume fab, covers nine logic
flows from N28 through projected A14, and stops at the fab gate before wafer
test, dicing, and packaging. It explicitly excludes tool/infrastructure
construction and waste treatment, and its Scope 3 inventory is incomplete.

Text-supported anchors admitted by this campaign are:

- 10x10 mm2 functional die, 86% Murphy die yield, and 90% line yield;
- 0.15 defects/cm2 for the Murphy-yield sensitivity;
- 17% of virtual-fab electricity allocated to facilities;
- industry-average grid CI of 0.454 kgCO2e/kWh;
- grid-CI sensitivities of 1.64 kWh/cm2 at N28 and approximately 4.30
  kWh/cm2 at A14;
- Scope 1 at about 6-8%, Scope 2 at 52-65%, and reported incomplete Scope 3
  at 41% for N28 versus 28% for A14 under the paper's scenario;
- EUV tools may draw much more power per tool while a route using EUV may use
  less total energy by eliminating DUV multipatterning/deposition/etch steps.

Values visible only as graph coordinates are not digitized into calibration.
Projected A-series nodes are model results, not fab measurements.

## imec.netzero public access result

The public landing page and disclaimer were inspected directly. The numeric
dashboard redirects to account sign-in and states that a public account plus
acceptance of terms is required. No account was created and no dashboard
values were extracted. Therefore `SRC_IMEC_NETZERO_APP_2026` is a primary but
access-limited source, and all current numeric anchors come from the public
peer-reviewed 2023 paper rather than an unauditable screenshot or copied web
number. Any future authenticated export must preserve imec's mandatory
acknowledgement and capture the complete scenario metadata.

## Historical imec comparison

The 2020 PPACE result supports historical direction and ratios from 28 nm to
2 nm: per-wafer electricity, water, and GHG burden increased as process
complexity rose. It cannot be subtracted directly from the 2023 result because
process flows, grid carbon intensity, utilization/release factors, abatement,
LCIA characterization, and system boundary changed. The 2023 paper itself
notes that improved abatement reverses the older prediction for direct GHG at
the most advanced modeled nodes. This evolution is a scientific result, not a
reason to tune the new model back to the older curve.

## Patterning model implication

Mask count is not a carbon coefficient. The wafer model represents route-level
lithography, etch, deposition, clean, CMP, and metrology steps with explicit
step energy. Patterning energy is either a diagnostic subset of total fab
energy or an addition to an explicitly non-patterning energy boundary. Physical
photomask-set manufacture is a separate NRE term and remains
`PARAMETRIC_UNCERTAIN` until a credible mask-manufacturing carbon source is
available.

## Architecture/LCA cross-checks

ACT 2022 and ACT3 define logic embodied carbon as area multiplied by a
yield-adjusted sum of fab electricity, gas/chemical, and material intensities.
The campaign implements this equation independently for matched-assumption
comparison; it does not import ACT's coefficients. ACT3 broadens the component
and bill-of-material structure but does not eliminate the need for process and
boundary provenance.

CarbonClarity adds distributions for fab CI, energy per area, gas per area,
and yield. Its non-parametric KDE is appropriate when enough real observations
exist. The present campaign does not have a defensible sample set for every
node, so it will not manufacture a KDE from guessed points. Sparse inputs use
declared scenario intervals; their quantiles are labeled scenario-ensemble
quantiles, not statistical confidence bounds.

Pirson et al. show why per-area values vary sharply across publications when
system boundaries are mismatched. TSMC's first-party per-wafer product-carbon
figures are retained as an external magnitude and maturity/utilization check,
not as an imec coefficient: their foundry-specific ISO 14067 boundary and node
bins differ from the generic-HVM imec boundary.

## Gases and accounting boundary

The model admits AR6 GWP-100 factors for CF4, C2F6, NF3, and SF6. These factors
convert emitted gas mass to CO2e; they never imply gas consumption, effective
release, or destruction/removal efficiency. Those process inputs need their
own sources or explicit ranges. Scope 1, purchased-energy Scope 2, and supported
upstream terms remain separate. A Scope1+2 calculation is never called complete
Scope 3 or full lifecycle carbon.

## Remaining evidence gaps

- authenticated current imec.netzero scenario exports with complete metadata;
- exact public SKY130 wafer inventory;
- credible physical photomask-set manufacturing CO2e;
- source-calibrated release/utilization and abatement distributions by gas and
  process route;
- qualified macro energy and full SRAM activity for operational carbon;
- package and replacement allocations matched to this SRAM architecture.

These gaps bound qualification; they do not invalidate the equation and
property-test layers.
