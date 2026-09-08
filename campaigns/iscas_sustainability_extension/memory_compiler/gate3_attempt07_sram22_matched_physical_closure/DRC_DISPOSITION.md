# DRC disposition

U0 and E0 each have zero OpenROAD final detailed-route violations in seed 11, zero-byte final route-DRC reports, zero macro-boundary integration violations, zero standard-cell/routing violations, and zero final antenna violations. The same is true for all five matched seeds. This is `INTEGRATION_DRC_CLEAN_WITH_UNQUALIFIED_HARD_MACRO_INTERNALS`.

The integration result is deliberately separate from hard-IP internals. Attempt06 observed 34,459 generic-deck markers in `sram22_256x64m4w8` and 5,831 in `sram22_256x8m8w1`, localized fraction 1.0 inside SRAM hierarchy, with neither a public SRAM22 foundry waiver nor an independently reproducible SRAM-special signoff deck. Those observations are frozen as `MACRO_INTERNAL_DRC_NOT_INDEPENDENTLY_SIGNOFF_QUALIFIED` and `DRC_NOT_INDEPENDENTLY_REPRODUCIBLE`. They were not suppressed, waived or converted into a full-chip/foundry DRC pass. Physical LVS remains `NOT_INDEPENDENTLY_REPRODUCED`.
