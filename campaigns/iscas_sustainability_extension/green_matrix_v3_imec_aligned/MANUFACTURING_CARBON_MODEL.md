# Bottom-up manufacturing-carbon model

## Route and scopes

A technology selects a process route.  A route contains uniquely identified
steps grouped into lithography, deposition, dry etch, wet clean, implantation,
anneal, CMP, metrology, and other declared modules.  Each step may carry
equipment electricity and gas inventory.  Duplicate step IDs are rejected.

For a declared wafer boundary:

`Scope2 = sum_step(E_step,kWh) × CI_manufacturing_grid`

`Scope1 = sum_gas(mass_consumed × effective_release_fraction × (1-abatement) × GWP100)`

`C_wafer = Scope1 + Scope2 + declared upstream terms`.

Gas identity, process module, consumption, utilization/release semantics,
abatement/destruction efficiency, GWP basis/version, and sources remain
recoverable.  GWP alone is not a gas inventory.  Upstream missing terms block a
boundary that includes them; they are never silently zero.

Patterning is explicit.  Its Scope-2 contribution is a subset diagnostic, not
an extra addend.  EUV/DUV/High-NA comparisons require complete route changes,
including eliminated or added exposures, deposition, etch, and clean.  Scanner
power alone cannot establish a total-footprint crossover.

## Yield and good die

The framework supports Poisson, negative-binomial, Murphy, and externally
measured yield.  Every use declares defect density and units, die area,
clustering factor where relevant, line yield, model, and source.  A node name or
“maturity” label never generates yield.

`N_good = N_gross(wafer geometry, die geometry) × Y_die × Y_line`

`C_process_per_good_die = C_wafer / N_good`.

Packaging, other declared terms, and mask NRE are then added only when inside
the boundary.  Mask burden is amortized as

`C_mask_per_good_die = C_maskset / (N_product_wafers × N_good_per_wafer)`

and is never multiplied into every wafer's patterning burden.

## ECC allocation

The preferred architecture comparison, once inputs qualify, is the marginal
change in gross dies and yield caused by matched baseline-versus-candidate die
area.  Incremental ECC area is not assigned the whole die's carbon.  Simple
area-proportional allocation is at most a declared diagnostic; system allocation
is allowed under a separate boundary.  With today's missing SKY130 inventory,
the active method is `NO_ALLOCATION_INSUFFICIENT_EVIDENCE`.

## Current boundary

Public imec advanced-node models validate structure, trends, and scenario
sensitivity inside their native boundaries.  They do not supply a matched
SKY130 manufacturing inventory.  Current status remains
`SKY130_MANUFACTURING_CARBON_NOT_QUALIFIED`.
