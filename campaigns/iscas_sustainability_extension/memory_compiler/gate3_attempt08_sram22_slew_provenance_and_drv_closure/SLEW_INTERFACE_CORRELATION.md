# Slew/interface correlation

The counts are structural, not a random cloud of routed nets. In canonical U0, all 65/65 rows are SRAM interface pins: 64 data-macro outputs plus `rstb`. In canonical E0, 77/80 rows are SRAM interface pins: all 72 macro outputs, data-macro `rstb`, `clk`, `din[56]`, `din[57]`, and ECC-macro `rstb`. The other three report rows are three pins on one ordinary standard-cell electrical net.

| Design / macro | Input pins | Output pins | Pins with an applicable max-transition rule | Violating report rows |
|---|---:|---:|---:|---:|
| U0 `sram22_256x64m4w8` | 84 | 64 | 148 | 65 |
| E0 `sram22_256x64m4w8` | 84 | 64 | 148 | 68 |
| E0 `sram22_256x8m8w1` | 28 | 8 | 36 | 9 |

All inputs carry explicit pin-level 0.351 ns rules. All outputs inherit the explicit library-level 0.04 ns default. The E0 accepted repair eliminates `din[56]` and `din[57]`; it does not change either macro or hide any remaining row.
