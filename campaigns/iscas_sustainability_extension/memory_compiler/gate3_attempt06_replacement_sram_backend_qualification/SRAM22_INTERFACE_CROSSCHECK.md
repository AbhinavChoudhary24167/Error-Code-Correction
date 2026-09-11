# SRAM22 interface cross-check

Result: **PASS** for both published macros.

| Property | `sram22_256x64m4w8` | `sram22_256x8m8w1` |
|---|---:|---:|
| Address | `addr[7:0]` | `addr[7:0]` |
| Data input/output | 64 / 64 bits | 8 / 8 bits |
| Write mask | 8 bits (byte lanes) | 8 bits (one bit per data bit) |
| Controls | `clk`, `ce`, `we`, active-low `rstb` | same |
| Supplies | `vdd`, `vss` | same |

Macro names, pin sets, directions, data/address/write-mask widths, power pins, and explicit bit indices agree across LEF, SPICE, Verilog, and all Liberty corners. LEF signal pins have geometry on `met1`, supply pins use `met2`, every pin rectangle is inside the declared macro boundary, and obstruction geometry is present. Verilog uses `[MSB:LSB]`, LEF uses individual `bus[index]` pins, SPICE enumerates ascending indices, and Liberty declares `downto` buses with explicit bits; the indices are consistent despite presentation-order differences.

Raw parse: `raw/qualification/interface_crosscheck.json`.

