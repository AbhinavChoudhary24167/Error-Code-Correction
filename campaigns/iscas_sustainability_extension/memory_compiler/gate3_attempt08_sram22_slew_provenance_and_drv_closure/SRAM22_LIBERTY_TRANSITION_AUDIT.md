# SRAM22 Liberty transition audit

The exact TT/25 C/1.8 V files used by OpenROAD are preserved under `raw/liberty`. Both libraries set input and output thresholds to 50%, slew lower thresholds to 10%, slew upper thresholds to 90%, and `default_max_transition : 0.04`. Every input pin has explicit `max_transition : 0.351`. The delay template input-transition axis is `[0.002, 0.008, 0.03, 0.073, 0.138, 0.231, 0.351]` ns and its output-capacitance axis is `[0.007, 0.013, 0.033, 0.065, 0.13, 0.26, 0.52]` pF. Output timing is related to rising `clk`; output pins have `max_capacitance : 0.52` but no pin-level max-transition override.

Thus macro-input rows have two distinct, aligned facts: `EXPLICIT_MAX_TRANSITION_DESIGN_RULE` at 0.351 ns and `LIBRARY_CHARACTERIZATION_RANGE_LIMIT` at 0.351 ns. They are not dismissed as mere extrapolation warnings.

Macro-output rows expose a different defect. The inherited 0.04 ns value is explicit, but each output's own characterized table already predicts a transition above it at the minimum 0.007 pF load and fastest 0.002 ns input. For `sram22_256x64m4w8`, representative `dout[0]` values are 0.137135 ns rise and 0.083310 ns fall. For `sram22_256x8m8w1`, they are 0.134220 ns rise and 0.081710 ns fall. Therefore 0.04 ns is self-incompatible with the delivered macro characterization. This is recorded as `EXPLICIT_MAX_TRANSITION_DESIGN_RULE_WITH_SELF_INCONSISTENT_OUTPUT_TABLE`, not silently removed and not confused with physical invalidity.

The characterization was not independently regenerated. The upstream library's physical validity beyond its documented axes remains unsupported.
