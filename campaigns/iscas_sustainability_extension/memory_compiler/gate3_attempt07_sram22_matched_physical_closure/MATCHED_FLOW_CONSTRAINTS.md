# Matched flow constraints

Attempt07 uses one policy for U0 and E0. Both use the pinned OpenROAD-flow-scripts image, `sky130hd`, `sky130_fd_sc_hd`, SRAM22 commit `75cbe961e18ee00d5a6c73fa455505f0bcdf4c05`, the TT/25 °C/1.8 V Liberty views, the platform nominal RC setup and extraction corner `X`, and signal routing on met1 through met5. There are no added timing derates.

Both SDCs create `core_clk` at 10.0 ns (100 MHz), use 0.10 ns uncertainty, 0.50 ns input/output delay, 0.02 pF output load, and a 0.60 ns design maximum transition. Architecture-specific port sets are the only SDC difference. Native Liberty transition and capacitance limits remain active and are not overridden or suppressed.

The common floorplanning rule is 30% placement target density, a 20 µm macro halo/blockage halo, approximately 10 µm outer core margin, the same PDN grid, all external signal pins on the top edge, and macro signal-pin edges facing an internal routing channel. Core size is allowed to scale with contents. U0 uses a 1000×470 µm die and E0 a 1000×650 µm die. The realized site-snapped cores are 439,734.24 and 615,627.936 µm². The data macro has exactly the same placement `(30.36, 31.23) MX` in both. E0 adds the ECC macro at `(30.36, 382.84) R0`, leaving a nominal 59.97 µm face-to-face signal channel.

Synthesis, timing-driven global placement, legalization, CTS, FastRoute, TritonRoute, extraction, fill, reporting and GDS merge are identical algorithms. Attempt06 experiments showed that placement-stage `repair_design` could not satisfy the immutable 256×64 `rstb` Liberty transition limit: the load is 0.448008 pF, the strongest legal external driver still produced 0.467 ns against a 0.351 ns pin limit, and an attempted instance-pin exception was rejected by STA. Attempt07 therefore applies the same symmetric database carry-forward after timing-driven global placement to both designs; post-CTS timing repair is retained. This is a documented policy decision, not an SDC exception.

Seeds 11, 13, 17, 19 and 23 use this configuration without per-seed tuning. The machine-readable record is `MATCHED_FLOW_CONSTRAINTS.json`.
