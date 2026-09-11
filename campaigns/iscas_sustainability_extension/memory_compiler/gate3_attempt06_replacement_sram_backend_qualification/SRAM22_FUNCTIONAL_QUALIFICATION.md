# SRAM22 functional qualification

The immutable upstream Verilog models were compiled with the Attempt06 wrapper and deterministic SystemVerilog testbench. Both macros passed reset-inhibit behavior, write/read, read-after-write, multiple and boundary addresses, all-zero, all-one, checkerboard, fixed-seed pseudo-random patterns, and write-mask tests.

| Test target | Result |
|---|---|
| `sram22_256x64m4w8` | `SRAM22_256X64_FUNCTIONAL_PASS` |
| `sram22_256x8m8w1` | `SRAM22_256X8_FUNCTIONAL_PASS` |
| synchronized 64+8 pair | `SRAM22_256X72_COMPOSITION_PASS` |
| overall | `ATTEMPT06_FUNCTIONAL_QUALIFICATION_PASS` |

The 64-bit macro's eight mask bits control byte lanes. The 8-bit macro's eight mask bits control individual ECC bits; the ECC wrapper writes a complete codeword and drives all mask bits active. Neither functional model nor macro internals were changed.

Evidence: `tests/tb_attempt06_sram22.sv`, `rtl/ecc_sram_256x72_sram22.sv`, and `raw/functional/simulation.log`.

