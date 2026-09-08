# ACT / ACT3 cross-validation

GREEN Matrix 3.0 uses adapters and matched assumptions; it does not copy ACT or
ACT3 defaults into the process-step model.

For a matched logic boundary, the ACT-style equation is

`C_logic = Area × (CI_fab × EPA + GPA + MPA) / Yield`.

The independent synthetic vector in
`validation/ACT_ACT3_CROSS_VALIDATION.json` uses area 0.5 cm2, CI 0.4
kgCO2e/kWh, EPA 2 kWh/cm2, GPA 0.3 kgCO2e/cm2, MPA 0.2 kgCO2e/cm2, and yield
0.8.  Both paths produce 0.8125 kgCO2e, classified `EXACT_REPRODUCTION` under
`SB_ACT_MATCHED_SYNTHETIC_VALIDATION`.

Real comparisons require matched area, grid CI, energy/gas/materials per area,
yield, package, BOM, and lifecycle boundary.  ACT is a coarser coefficient-based
architecture model; GREEN Matrix 3.0 can aggregate bottom-up steps into its
algebra.  ACT3 expands configurable BOM and system coverage, but its current
defaults remain external and boundary-specific.  With unmatched defaults or
missing SKY130 inventory the classification is `NOT_COMPARABLE`, not agreement.
