# Claim-to-evidence map

| Claim | Evidence | Status |
|---|---|---|
| The physical population contains 40 matched routed/GDS runs | Frozen v3.2 `RUN_MANIFEST.json`, hash pinned in this campaign | Supported (inherited E4) |
| U0, SECDED, and Hsiao are setup-feasible at 10 ns | `TIMING_FEASIBILITY.json`, five seeds each | Supported |
| Only U0 is setup-feasible at 5 ns | `TIMING_FEASIBILITY.json`, five seeds each | Supported |
| Workloads are deterministic and semantically matched | `WORKLOAD_MANIFEST.json` | Supported as infrastructure only |
| Activity-aware operation energy is E5 | No qualifying activity/power record | Forbidden |
| Whole-memory E5 energy is qualified | `SRAM_MACRO_POWER_QUALIFICATION.json` | Forbidden |
| Hsiao retains lower operation energy than SECDED | No E5 energy measurements | Unresolved |
| BCH is equal-performance at 10 ns | Negative WNS for 5/5 seeds | Forbidden |
| Physical FIT/Qcrit/interleaver benefit/absolute lifecycle carbon | Required evidence absent | Forbidden |
| A global winner exists | Mandatory dimensions remain blocked | `NO_GLOBAL_WINNER_QUALIFIED` |
