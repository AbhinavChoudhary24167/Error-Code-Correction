# SRAM22 output-transition provenance

Classification: `UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY`. Canonical disposition: `PROVENANCE_LIMITED_NOT_EXTERNAL_INTEGRATION_DRV`. This is neither a foundry waiver nor signoff certification; every original warning remains in production reports.

Both production TT views contain `default_max_transition : 0.04`. All 72 selected macro output pins (64 + 8) inherit it: none has a pin-level `max_transition` override, while every output has `max_capacitance : 0.52`. Thresholds are 10–90% slew and 50% input/output switching thresholds.

| Frozen view | Outputs | Output overrides | Transition tables | Minimum grid value (ns) | Min-load/fast-input range (ns) |
|---|---:|---:|---:|---:|---:|
| `sram22_256x64m4w8_ff_n40C_1v95.lib` | 64 | 0 | 4 | 0.057383 | 0.057428–0.106188 |
| `sram22_256x64m4w8_ss_100C_1v60.lib` | 64 | 0 | 4 | 0.148440 | 0.148440–0.208403 |
| `sram22_256x64m4w8_tt_025C_1v80.lib` | 64 | 0 | 4 | 0.080573 | 0.080607–0.137135 |
| `sram22_256x8m8w1_ff_n40C_1v95.lib` | 8 | 0 | 4 | 0.058250 | 0.058263–0.103977 |
| `sram22_256x8m8w1_ss_100C_1v60.lib` | 8 | 0 | 4 | 0.151059 | 0.151080–0.204111 |
| `sram22_256x8m8w1_tt_025C_1v80.lib` | 8 | 0 | 4 | 0.081685 | 0.081707–0.134220 |

The audit covers both locally frozen macros at FF/−40 C/1.95 V, TT/25 C/1.8 V, and SS/100 C/1.6 V: 6/6 published views and all four bus-scope output transition tables (`rise_transition`, `fall_transition`, `retain_rise_slew`, `retain_fall_slew`). In every table the value at the fastest input and minimum 0.007 pF characterized load is already greater than 0.04 ns. The causal contradiction therefore exists before routed external RC is added.

- U0: 64 structural output rows; reported-transition/0.04 ratio min/median/max = 3.552339/3.765393/3.975067. Extracted parasitic load min/median/max = 0.00605414/0.007657895/0.00923835 pF; below/within/above the 0.007–0.52 pF characterized domain = 22/42/0.
- E0: 72 structural output rows; reported-transition/0.04 ratio min/median/max = 3.853236/5.410324/10.722083. Extracted parasitic load min/median/max = 0.00608528/0.01653835/0.0522396 pF; below/within/above the 0.007–0.52 pF characterized domain = 4/68/0.

The SPEF declares `PIN_CAP NONE`, so the load comparison deliberately reports extracted D_NET parasitic capacitance as a reproducible lower bound and does not invent receiver Liberty capacitance. Full per-output measurements are preserved in `raw/class_c_output_measurements.json`; full per-view table evidence is in `raw/sram22_output_provenance_audit.json`. Counts remain tied exactly to macro width across normal rerouting, while the same Liberty contradiction exists at minimum characterized load, so excessive external RC alone cannot explain Class C.
