# E0 timing and DRV root cause

Attempt06 E0 had two hold violations and 77 maximum-slew violations after clean detailed route. Under the matched Attempt07 clock/floorplan policy, ordinary post-CTS hold repair removes both hold violations; seed 11 has +0.000901557 ns worst hold slack, +0.591127 ns setup WNS, zero setup/hold violations, and zero maximum-capacitance violations.

Seed 11 retains 80 maximum-slew violations. The final violator report classifies them as:

- 72 SRAM macro outputs: all 64 data-macro `dout` pins and all eight ECC-macro `dout` pins use an immutable 0.04 ns output-transition limit. External buffering cannot repair the transition measured at the macro driver pin.
- five SRAM macro inputs: data `rstb`, data `clk`, data `din[56]`, data `din[57]`, and ECC `rstb`. These are pin-specific macro Liberty constraints/load effects; the common external resizer policy already uses legal buffers and no macro internals may be changed.
- three standard-cell logic pins: `_540_/A`, `_518_/A`, and `_513_/Y`, each near 0.65 ns against the common 0.60 ns design limit. They are ordinary routed combinational transition violations, not clock-tree, hold, capacitance, or unconstrained-path failures.

The critical setup path begins at a data-SRAM output and passes through decoder/flag logic to `detected_uncorrectable`; it closes by +0.591127 ns at 10 ns. The clock tree has three clock buffers and one clock inverter; no setup or hold clock skew violation is reported. Maximum capacitance, antenna, detailed-route DRC and unconstrained endpoint counts are all zero.

The flow tried ordinary external techniques—timing-driven placement, post-CTS repair, buffering, legal gate sizing, antenna-diode insertion and detailed-route optimization—without modifying SRAM views or semantics. Attempt06 also established that the data-macro `rstb` load cannot meet its immutable Liberty max-transition value even with the strongest available legal external driver. No constraint was suppressed. Because legitimate slew violations remain, the result is `MATCHED_ROUTE_PASS_TIMING_LIMITED`, not full timing closure.
