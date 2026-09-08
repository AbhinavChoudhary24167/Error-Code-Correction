# Attempt06 replacement SRAM backend qualification

Attempt06 selected SRAM22's pre-generated SKY130 macros and reached `SRAM22_PARTIALLY_QUALIFIED`. The exact required pair exists and has complete published GDS/LEF/SPICE/Liberty/Verilog collateral plus upstream-reported 1.8 V, 25 MHz silicon operation. Interfaces, GDS/LEF geometry, executable behavior, Hsiao SECDED composition, and E0 hard-macro physical integration qualified.

The important boundary is explicit. Public-deck DRC markers are entirely SRAM-internal in both macros, supporting integration as immutable black boxes with documented risk. There is no published SRAM22 foundry waiver/signoff deck, so leaf DRC remains `DRC_NOT_INDEPENDENTLY_REPRODUCIBLE`. Public LVS did not reproduce the 256×8 upstream SPICE equivalence. Liberty is usable upstream characterization, not independently regenerated signoff evidence.

E0 completed final routing/GDS with zero route DRC errors, but U0 detailed route did not converge. This prevents the required overall backend qualification and makes U0/E0 metric deltas diagnostic rather than final experimental results. Recommendation is `KEEP_GATE3_FAILED`. Gate 4 remains unauthorized, and no Attempt07 work was started.

