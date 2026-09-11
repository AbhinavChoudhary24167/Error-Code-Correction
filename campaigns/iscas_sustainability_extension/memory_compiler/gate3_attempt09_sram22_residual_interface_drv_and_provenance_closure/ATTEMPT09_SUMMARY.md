# Attempt09 summary

Attempt09 is `RESIDUAL_SRAM_INPUT_DRV_FAIL`; recommendation is `KEEP_GATE3_FAILED`. The fixed E0 interface ECO closes the ECC `rstb` and data-SRAM clock violations, retains balanced clock polarity, and a common 25 ps hold-repair policy is used across all E0 seeds. No constraint, macro, or production Liberty changed.

Canonical seed 11 reports U0 65 warnings = 64 Class C + 1 genuine data-`rstb`; E0 73 = 72 Class C + 1 genuine data-`rstb`. Setup/hold/capacitance/integration-DRC/antenna are 0/0/0/0/0 in both. U0 WNS/TNS is 4.460990000/0.000000000 ns; E0 is 0.611109000/0.000000000 ns.

The 136 Class-C warnings are causally classified `UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY` and `PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV`: six frozen macro/corner views inherit 0.04 ns on every output without pin override, while their own output tables exceed 0.04 ns at minimum load/fastest input. The diagnostic exclusion removes Class C while leaving one genuine `rstb` row per design. This classification does not repair or waive those input rows.

Across seeds 11/13/17/19/23, route-clean pairs are 5/5, setup/hold-clean pairs are 5/5, and genuine-external-DRV-clean pairs are 0/5. Seed 17 E0 finishes at 0.004361120 ns with 0 violations. Power is only `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`; energy/access is `NOT_QUALIFIED`. Gate-3 reassessment, Attempt10, carbon work, and Gate 4 were not started.
