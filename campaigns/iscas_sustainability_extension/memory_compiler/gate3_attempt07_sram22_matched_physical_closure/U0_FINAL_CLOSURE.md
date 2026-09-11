# U0 final closure

Canonical seed 11 completed synthesis, floorplan, exact macro placement, PDN, timing-driven global placement, symmetric placement database carry-forward, detailed placement, CTS handling, global route, detailed route, filler, extraction, SPEF, DEF, ODB and merged GDS. KLayout reported that all LEF cells had matching GDS/OAS cells and that the final layout had no orphan cells. Power-grid analysis reported all VDD and VSS shapes connected.

The final result is `INTEGRATION_DRC_CLEAN_WITH_UNQUALIFIED_HARD_MACRO_INTERNALS`: detailed-route DRC 0, macro-boundary violations 0, antenna violations 0, setup violations 0, hold violations 0, maximum-capacitance violations 0 and unconstrained endpoints 0. Worst setup slack is +4.46099 ns, TNS is 0 ns and worst hold slack is +0.0249489 ns at the common 10 ns clock. The critical setup path is wrapper input/reset buffering into the data macro. With only one macro clock sink, CTS builds no clock tree and `report_clock_skew` correctly reports no launch/capture path.

There are 65 maximum-slew violations: all 64 immutable macro `dout` pins at their 0.04 ns Liberty limit plus the macro `rstb` pin. They are retained in the report, not waived, and prevent full timing/DRV closure.

Area and route metrics are: 201,266.5968 µm² macro area, 5,566.59 µm² reported standard-cell/physical-cell area, 206,833 µm² total placed design area, 439,734.24 µm² core, 470,000 µm² die, 47.0360% achieved total utilization, 22,186 µm wirelength and 1,084 vias. Final layer wirelength is li1/met1/met2/met3/met4/met5 = 0/436/18,944/137/2,668/0 µm. Global routing ended at 1.29% aggregate resource usage and zero max/total congestion.

Vectorless post-route power is 0.772797 mW internal, 0.0310699 mW switching, 0.000642569 mW leakage and 0.804510 mW total, classified `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`.

Canonical artifacts are under `raw/openroad/work/results/sky130hd/attempt07_u0/seed11`; timing, route DRC, congestion and visualization reports are under the corresponding `reports` directory, and complete logs are under `logs`.
