# E0 final closure

Canonical seed 11 completed the same stage sequence and algorithms as U0: synthesis, floorplan, exact macro placement, PDN, timing-driven global placement, symmetric placement database carry-forward, detailed placement, CTS, global route, detailed route, filler, extraction, SPEF, DEF, ODB and merged GDS. KLayout found matching GDS/OAS cells for every LEF cell and no orphan cells. VDD and VSS power-grid shapes are connected.

The final result is `INTEGRATION_DRC_CLEAN_WITH_UNQUALIFIED_HARD_MACRO_INTERNALS`: detailed-route DRC 0, macro-boundary violations 0, final antenna violations 0, setup violations 0, hold violations 0, maximum-capacitance violations 0 and unconstrained endpoints 0. Six antenna diodes were inserted during detailed-route repair and the reroute returned to zero DRC and zero antenna violations. Worst setup slack is +0.591127 ns, TNS is 0 ns and worst hold slack is +0.000901557 ns at 10 ns. The critical setup path is data-SRAM output through Hsiao decoder/flag combinational logic to `detected_uncorrectable`.

There are 80 maximum-slew violations: 72 immutable SRAM output pins, five SRAM input pins and three ordinary standard-cell logic pins, detailed in `E0_TIMING_DRV_ROOT_CAUSE.md`. They are neither hidden nor waived. Seed 11 therefore closes route/setup/hold but not the full timing/DRV gate.

Area and route metrics are: 260,331.5664 µm² macro area, 15,418.5 µm² reported standard-cell/physical-cell area, 275,750 µm² total placed design area, 615,627.936 µm² core, 650,000 µm² die, 44.7917% achieved total utilization, 79,745 µm wirelength and 6,686 vias. Final layer wirelength is li1/met1/met2/met3/met4/met5 = 0/22,384/43,956/6,431/6,904/68 µm. Global routing ended at 3.31% aggregate resource usage and zero max/total congestion.

CTS contains three clock buffers and one clock inverter. There are no register-to-register launch/capture paths, so clock skew is not observable; path-specific target-clock latencies in the final report are 0.2847 and 0.4942 ns. Vectorless post-route power is 1.39174 mW internal, 0.582002 mW switching, 0.000734367 mW leakage and 1.97447 mW total, classified `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`.

Canonical artifacts are under `raw/openroad/work/results/sky130hd/attempt07_e0/seed11`; reports and logs are preserved in the parallel directories.
