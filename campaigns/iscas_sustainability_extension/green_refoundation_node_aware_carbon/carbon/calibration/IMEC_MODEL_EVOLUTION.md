# Evolution of imec semiconductor-carbon models

The historical and current models agree on the broad mechanism: advanced
logic flows add process steps and make fab electricity increasingly important.
They must not be compared as if only the publication date changed.

The 2020 PPACE study spans 28 nm to 2 nm and reports normalized per-wafer
growth. The 2023 IEDM study uses imec.netzero v1.5.67, extends the boundary to a
documented (but still incomplete) cradle-to-fab-gate inventory, revises process
flows and pitches, uses updated fab/equipment data, IPCC AR6 characterization,
IPCC 2019 Tier 2c abatement, and a weighted industry grid.

Three conclusions follow:

1. The current grid-CI sensitivity endpoints (1.64 kWh/cm2 at N28 and about
   4.30 kWh/cm2 at A14) validate rising electrical exposure, but cannot be
   divided by the old 28-to-2 nm 3.46x value as a model error.
2. Both generations support route-level analysis: high-power EUV can reduce
   total energy when it removes several DUV multipatterning cycles.
3. Direct GHG is the strongest evolution. The current paper reports a decrease
   from N3 to A14 because of EUV-driven layer removal and improved gas
   utilization/DRE, explicitly contrasting the prior upward forecast.

Therefore the comparison result is `MODEL_EVOLUTION_OBSERVED_BOUNDARIES_NOT_NUMERICALLY_MATCHED`.
No coefficient was tuned to force agreement.
