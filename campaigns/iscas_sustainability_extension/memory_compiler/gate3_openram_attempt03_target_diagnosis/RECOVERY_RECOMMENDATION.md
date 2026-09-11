# Recovery classification and one recommended strategy

## Evidence-based classification

- **B. SKY130_TECH_PLUGIN_LIMITATION** — the stock-compatible 16x8 control repeats DRC/LVS failure in SKY130 primitive and replica hierarchies.
- **C. TARGET_CONFIGURATION_LIMITATION** — the 256x72 spare-row plus 2:1 mux geometry triggers an invalid characterization probe row.
- **D. SPARE_REPAIR_CONFIGURATION_ERROR** — spare support expands the external contract, and the scalar `spare_wen0`/indexed `spare_wen0[0]` connection is inconsistent.
- **E. CHARACTERIZER_LIMITATION** — timing-graph construction excludes every bitcell for the invalid probe row; a separate corner code path references unbound `nom_corner`.
- **F. PDK/VERIFICATION_INTEGRATION_PROBLEM** — systematic primitive-rule DRC failures and repeated extracted-net partitions occur with matched device counts, including on the control.
- **G. LOCAL_CONFIGURATION_ERROR** — using `nominal_corner_only` together with `only_use_config_corners` triggers the later control Liberty failure.

The evidence does not establish a general **A. OPENRAM_CORE_LIMITATION** independent of SKY130/these configurations, and **H. UNKNOWN** is unnecessary for the diagnosed failure layers.

## Exactly one next strategy

Create `gate3_openram_attempt04_sky130_control_integration_repair` as a **control-first upstream reproducer and minimal technology-integration repair**. Its sole pass boundary should be that the unchanged shipped-compatible 16x8 logical control passes the unmodified Magic and Netgen qualification criteria after a separately hashed, audited repair to the SKY130 primitive/layout-view integration. Do not run 256x72 and do not patch the characterizer in that attempt; physical-verification health must be established first.

This is preferred over a version-only upgrade or another target retry. As checked on 2026-08-31, the official OpenRAM release page still lists v1.2.48 as latest, the stable setup continues to install the pinned SKY130 inputs through `make sky130-install`, and upstream issue #292 remains an open tiny-SKY130 LVS-mismatch report. There is therefore no established released upgrade that can be claimed to fix the control.

Primary references:

- https://github.com/VLSIDA/OpenRAM/releases
- https://github.com/VLSIDA/OpenRAM/issues/292
- https://github.com/VLSIDA/OpenRAM/blob/stable/docs/source/basic_setup.md
- https://github.com/VLSIDA/OpenRAM/blob/stable/Makefile

Only after that new attempt produces a genuinely DRC/LVS-qualified control should a later namespace address interface and characterization defects and reconsider 256x72. Gate 3 remains finalized `FAIL`, and Gate 4 remains unauthorized.

