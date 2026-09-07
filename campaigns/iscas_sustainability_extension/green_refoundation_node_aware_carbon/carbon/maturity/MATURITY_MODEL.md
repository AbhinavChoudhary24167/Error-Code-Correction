# Manufacturing-maturity model

An `EARLY_NODE` or `MATURE_NODE` label has no numeric effect by itself. A
maturity scenario must explicitly declare:

- defect density and line yield;
- fab-electricity factor;
- process-gas-use factor;
- upstream-material factor;
- patterning-step energy factor;
- optional per-gas abatement overrides;
- evidence label, source IDs, and a note.

The implementation applies only those declared factors and returns the defect
density and line yield alongside the transformed wafer inventory. This makes
it impossible for a name such as `MATURE_NODE` to silently improve yield.

CarbonClarity supports the direction that defect density and energy-per-area
vary as a node matures, and identifies energy-per-area and yield as leading
uncertainty sources. The 2023 imec study, in contrast, holds utilization,
idle/downtime, efficiency, and throughput constant across nodes. The included
intervals are therefore parametric research envelopes, not imec measurements.
Concrete draws must retain the `PARAMETRIC_UNCERTAIN` label unless separately
calibrated.
