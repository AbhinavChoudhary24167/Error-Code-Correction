# ASIC Integrated ECC SRAM Wrappers

This directory adds **synthesizable, top-level integrated SRAM wrappers** for fixed ECC entries:

- `sec-ded-64`  -> `sram_secded_top`
- `sec-daec-64` -> `sram_secdaec_top`
- `taec-64`     -> `sram_taec_top`
- `bch-63`      -> `sram_bch_top`
- `polar-64-32` -> `sram_polar_64_32_top`
- `polar-64-48` -> `sram_polar_64_48_top`
- `polar-128-96`-> `sram_polar_128_96_top`

## Module hierarchy pattern

All top modules follow the same architecture:

1. `*_encoder` maps `wdata` to ECC codeword.
2. `sram_core` stores full codeword (`CODE_W`) at `addr`.
3. `*_decoder` decodes/corrects read codeword.
4. Outputs are gated with `valid` from the SRAM read pipeline.

```
write: wdata -> encoder -> sram_core.mem[addr]
read : sram_core.mem[addr] -> decoder -> rdata + error flags
```

## Common interface

Each top module exports:

- `clk`, `rst_n`, `cs`, `we`, `addr`, `wdata`, `rdata`, `valid`
- `err_detected`, `err_corrected`, `err_uncorrectable`
- `double_error`, `adjacent_error`, `triple_adjacent_error`

`valid` is asserted one cycle after `cs && !we`.

## Files

- `common/`
  - `sram_core.sv`: shared synthesizable storage core.
  - `ecc_types_pkg.sv`: optional shared enum/sizing helper package.
- `secded/`
  - `secded_encoder.sv`, `secded_decoder.sv`, `sram_secded_top.sv`
- `secdaec/`
  - `secdaec_encoder.sv`, `secdaec_decoder.sv`, `sram_secdaec_top.sv`
- `taec/`
  - `taec_encoder.sv`, `taec_decoder.sv`, `sram_taec_top.sv`
- `bch/`
  - `bch_encoder.sv`, `bch_decoder.sv`, `sram_bch_top.sv`
- `polar/`
  - `polar_encoder_64_32.sv`, `polar_decoder_64_32.sv`, `sram_polar_64_32_top.sv`
  - `polar_encoder_64_48.sv`, `polar_decoder_64_48.sv`, `sram_polar_64_48_top.sv`
  - `polar_encoder_128_96.sv`, `polar_decoder_128_96.sv`, `sram_polar_128_96_top.sv`

## Synthesis/test usage notes

- Include existing base codec files from `asic/rtl/*` together with new wrapper files.
- The wrappers are pure RTL and avoid TB-only constructs.
- `DEPTH` defaults to `2**ADDR_W`, override as needed for experiments.

Example compile list concept:

1. Base codec/package files (`asic/include/ecc_pkg.sv`, `asic/rtl/**`).
2. New common files (`asic/common/**`).
3. One selected ECC family wrapper set.

## Assumptions and approximations

- **SEC-DED**: standard single-error correction and double-error detection behavior.
- **SEC-DAEC**: adjacent double-error correction follows the existing bounded adjacent search model.
- **TAEC**: triple-adjacent correction follows the existing syndrome-pattern model.
- **BCH(63,51)**: decoder uses existing bounded <=2-bit correction search (area-heavy but synthesizable).
- **Polar** wrappers use existing bounded local-search decoder (not full SC/SCL decoder).

These approximations are inherited from existing codec implementations and are preserved for interface and synthesis compatibility.
