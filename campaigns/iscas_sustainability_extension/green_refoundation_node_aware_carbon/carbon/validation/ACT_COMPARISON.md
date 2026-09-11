# ACT / ACT3 cross-validation

The campaign implements ACT's logic equation independently of the hierarchical
wafer model:

`C_logic = Area * (CI_fab * EPA + GPA + MPA) / Yield`.

Under exactly matched areal inputs and boundary, the independent ACT path and
the GREEN disjoint Scope-2/gas-proxy/material-proxy path agree to floating-point
precision. This validates algebra and units, not the numerical coefficients.

The N28 and A14 rows use imec's printed 1.64 and approximately 4.30 kWh/cm2
grid-sensitivity anchors, 0.454 kgCO2e/kWh, one cm2 die area, and the paper's
0.86 die-yield assumption. GPA and MPA are set to zero to form an explicitly
Scope-2-only boundary; the resulting 0.8658 and 2.27 kgCO2e values are **not**
full die-carbon estimates. The third row is a synthetic full-equation unit
fixture. No ACT defaults are imported or tuned.

ACT 2022 is a coefficient-level architecture model. The current ACT3 repository
uses a broader component/BOM system covering logic, memory, packaging, storage,
materials, and operational carbon. This campaign records that evolution but
does not adopt ACT3 defaults because the exact component boundary is not matched
to the imec generic-HVM calibration or SKY130 physical evidence. A full magnitude
comparison remains unavailable until all EPA/GPA/MPA/yield inputs share a common
node, fab, maturity, and system boundary.

Classification: **ALGEBRA_AND_UNITS_CROSS_VALIDATED; ABSOLUTE_MAGNITUDE_PARTIAL**.
