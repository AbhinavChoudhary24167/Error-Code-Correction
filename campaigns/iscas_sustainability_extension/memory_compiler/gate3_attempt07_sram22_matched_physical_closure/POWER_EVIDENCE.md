# Power evidence

OpenROAD final extracted reports provide vectorless estimates at the common TT/25 °C/1.8 V corner. Canonical seed 11 reports U0 internal/switching/leakage/total power of 0.772797/0.0310699/0.000642569/0.804510 mW and E0 of 1.39174/0.582002/0.000734367/1.97447 mW. E0−U0 total displacement is +1.16996 mW (+145.425%). Per-seed values are recorded in `MULTISEED_STATUS.json`.

The evidence level is exactly `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`. It is not measured silicon power, our timing or power characterization of SRAM22, or signoff power. Macro power comes from the frozen upstream Liberty views; switching activity is vectorless/default rather than a workload-derived annotation.

An activity-annotated comparison was considered but not promoted. The SRAM behavioral models and immutable hard-macro Liberty boundary do not provide a trustworthy mapping from a logical VCD through both extracted post-route netlists into equivalent internal macro activity. Generating a VCD would therefore create apparent precision without equivalent macro treatment. No VCD/SAIF result is claimed.

`ENERGY_PER_ACCESS = NOT_QUALIFIED`: activity is not trustworthy enough, so the energy/access claim gate is not satisfied even though the common period is known.
