# SRAM22 timing-view qualification

Result: `QUALIFIED_WITH_PROVENANCE_LIMITATION`.

Each macro supplies three Liberty views: FF at −40 °C / 1.95 V, TT at 25 °C / 1.80 V, and SS at 100 °C / 1.60 V. All six files parse with the correct cell name and 256-word dimensions. Units are 1 ns, 1 V, 1 mA, 1 nW, 1 kΩ, and 1 pF. The views contain clock declaration, setup, hold, minimum pulse-width, minimum-period, clock-to-Q/read arcs, write constraints, internal-power lookup tables, and TT leakage-power groups. TT cell areas match LEF after the publisher's integer rounding.

The library comments identify Cadence Liberate MX 23.1.3.126.isr3 characterization from November 2024. The public SRAM22 setup cannot independently rerun proprietary extraction and characterization, so the evidence level is `UPSTREAM_CADENCE_LIBERATE_MX_CHARACTERIZATION_NOT_INDEPENDENTLY_REPRODUCED`. The views are usable for pinned-corner integration STA and diagnostic vectorless power, but not for a claim of independently reproduced timing or signoff-grade energy.

Raw parse: `raw/qualification/timing_view_qualification.json`.
