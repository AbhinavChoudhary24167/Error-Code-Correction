# Node-scaling validation

## Qualification outcome

`PARTIAL_NUMERIC_CALIBRATION_TEXTUAL_ANCHORS_ONLY`

The model structure is validated against primary imec trends, but a complete
absolute wafer-carbon curve is not qualified. The current public paper exposes
exact textual anchors at N28 and projected A14; intermediate graph coordinates
were deliberately not digitized. The live public dashboard requires an account,
so it supplied no numeric calibration during this campaign.

## Tests against imec evidence

| Required behavior | Primary evidence | Result | Qualification |
|---|---|---|---|
| Wafer fab electricity rises with advanced process complexity | IEDM 2023 reports nearly 3x from N28 to A14 | Model allows explicit node inventories and does not scale by node name | STRUCTURE_VALIDATED |
| Grid-CI sensitivity rises | 1.64 kWh/cm2 N28 to approximately 4.30 kWh/cm2 A14 | Exact endpoints recorded | SOURCE_CALIBRATED_ENDPOINTS |
| EUV can reduce route energy despite higher scanner power | IEDM 2023 says N7 EUV removes multiple steps | Route sums lithography plus eliminated deposition/etch/clean steps | PROPERTY_TESTED |
| Direct gas burden responds to abatement | IEDM 2023 Figure 8 discussion | Scope 1 decreases monotonically with abatement efficiency | PROPERTY_TESTED |
| Per-die burden grows super-linearly with die area | IEDM 2023 die-size sensitivity | Gross-die geometry plus area-dependent yield reproduces the mechanism | PROPERTY_TESTED |
| Upstream remains distinct from Scope 1+2 | IEDM 2023 and GHG Protocol | Separate upstream field; incomplete upstream never called full Scope 3 | ACCOUNTING_VALIDATED |
| Absolute C_wafer at 28/14/7/5/3/2 | Public exact values not recovered for a common boundary | No production curve emitted | NOT_QUALIFIED |

## Historical trend check

The 2020 PPACE official imec summary reports 28-to-2 nm per-wafer multipliers
of 3.46 for electricity, 2.3 for UPW, and 2.5 for GHG. These validate the
direction that process complexity can overwhelm naive geometric node scaling.
They are not current coefficients.

The 2023 model updates flows, grid mix, gas utilization, abatement, and LCIA
factors. It reports that direct emissions fall from N3 to A14 as EUV removes
deposition/etch layers, opposite the older PPACE direct-emission forecast.
This is retained as model evolution rather than treated as a failed match.

## Rejected baselines

- `C_wafer proportional to 1/node`: rejected; node label has no physical unit
  that maps to wafer carbon.
- `C_pattern = k * masks`: rejected; masks conflate wafer process repetitions
  with photomask-set NRE.
- `advanced imec coefficient = SKY130 coefficient`: rejected; the current
  physical results remain `MEASURED_SKY130_PHYSICAL`, while node-carbon
  scenarios remain `IMEC_CALIBRATED_ADVANCED_NODE`, translated, parametric, or
  bounded.

## Required next evidence

A complete validation curve needs authenticated imec.netzero exports for a
fixed geography, process route, grid, abatement state, maturity, and version,
with Scope 1/2/3 boundaries and absolute units saved alongside every row.
