# imec source boundaries

The canonical metadata are in `SOURCE_REGISTRY.json` and `.csv`.

## Public virtual fab and SSTS

The 2023 first-party public-access release describes a generic high-volume
manufacturing virtual fab, with the public tool focused on Scope 1 and Scope 2
and node coverage from N28 onward.  It is a methodological/provenance anchor,
not a numerical SKY130 table.  The public application requires account access;
no authenticated values are used here.

The 2022 SSTS whitepaper supplies normalized sensitivity and structural
evidence for bottom-up electricity/direct-gas accounting.  Normalized scenario
figures do not become absolute wafer coefficients.

## 2020/2022 PPACE-era evidence

PPACE/EDTM studies support historical advanced-node process-complexity and
patterning trends.  Their system boundaries and historical utilization/
abatement assumptions differ from the later cradle-to-gate model.  They are
trend/qualitative evidence only and are not silently updated into current
coefficients.

## 2023 cradle-to-gate study

The registered boundary is generic 300 mm high-volume logic manufacturing from
N28 through projected A14, using imec.netzero v1.5.67.  Registered assumptions
include a 10×10 mm die, 86% Murphy die yield, 90% line yield, 17% facility share,
0.454 kgCO2e/kWh grid, and IPCC-2019 Tier-2c abatement.  Test, dicing, packaging,
tools/infrastructure, fab-waste treatment, and parts of Scope 3 are excluded.

Textual energy/grid-sensitivity anchors of 1.64 kWh/cm2 at N28 and approximately
4.30 kWh/cm2 at projected A14 remain native advanced-node evidence.  Graph-only
absolute values were not digitized.  Projected nodes are not measurements.

## Lithography evidence

The public lithography paper supports route-level accounting: an equipment
power increase can be offset by eliminated deposition/etch/clean steps.  It
does not justify a universal EUV/DUV crossover or a SKY130 coefficient.

## Transfer prohibition

Every imec entry retains original technology, route, publication/version,
units, assumptions, grid, yield, boundary, and modelled/projected status.
Cross-boundary numerical comparison is rejected until boundaries are
reconciled.  In particular:

`ADVANCED-NODE IMEC COEFFICIENTS MUST NEVER BE RELABELLED AS SKY130 MEASUREMENTS.`
