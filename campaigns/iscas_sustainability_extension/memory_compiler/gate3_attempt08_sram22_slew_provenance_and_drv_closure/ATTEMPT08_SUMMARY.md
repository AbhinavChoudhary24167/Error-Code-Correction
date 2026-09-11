# Attempt08 summary

Attempt08 is classified `SLEW_REPAIR_PARTIAL`; recommendation is `KEEP_GATE3_FAILED`. The frozen original inventory is U0 65 = A0/B1/C64/D0/E0/F0 and E0 80 = A3/B4/C72/D0/E1/F0. The population is structurally tied to SRAM interfaces (65/65 U0 and 77/80 E0), with E0's other three report rows representing one repairable standard-cell net.

Three legal E0 driver upgrades remove that standard-cell net and `din[56:57]`, producing canonical U0/E0 slew counts 65/75. No constraint or macro was changed. Setup, hold, integration DRC, capacitance and antenna remain zero in both canonical designs. U0 WNS/TNS is 4.46099/0 ns; E0 is 0.584552/0 ns.

The 0.04 ns macro-output default is explicit but contradicts the delivered output tables, so those Class-C rows have documented upstream provenance limitations. The remaining macro-input and clock rows are different: explicit 0.351 ns pin rules coincide with the maximum characterized input-transition axis and are genuinely exceeded. Consequently the canonical pair cannot use the provenance-limited exception.

All five matched seeds completed. U0/E0 route-clean status is True/True; matched setup/hold-clean pairs are 4/5; matched external timing/DRV-closure pairs are 0/5. E0 seed 17 now has 1 hold violations and worst hold slack -0.000169975 ns. Historical Gate 3 remains failed; reassessment, Attempt09, Gate 4, and carbon work were not started.
