# ASIC SystemVerilog ECC Track

## Directory Overview
- `asic/include/`: common packages (`ecc_pkg.sv`).
- `asic/rtl/common/`: shared RTL utilities and fixed-entry aliases.
- `asic/rtl/secded/`: SEC-DED encoder/decoder.
- `asic/rtl/secdaec/`: SEC-DAEC adjacent-double aware decoder.
- `asic/rtl/taec/`: TAEC-style triple-adjacent-aware decoder.
- `asic/rtl/bch/`: BCH encoder and bounded t<=2 decoder.
- `asic/rtl/polar/`: Polar encoder and bounded hard-decision decoder.
- `asic/rtl/sram/`: SRAM wrappers (`sram_*`).
- `asic/tb/`: self-checking family and wrapper testbenches.
- `asic/scripts/`: compile / run / regression scripts.

## Modeling Notes by ECC Family
- **SEC-DED**: canonical Hamming parity placement + overall parity bit. Decoder emits syndrome, correction mask, overall mismatch, and corrected codeword.
- **SEC-DAEC**: starts from SEC-DED decode, then performs explicit adjacent data-bit pair syndrome matching to recover DAEC patterns.
- **TAEC**: starts from SEC behavior; if unresolved and odd-parity mismatch exists, searches adjacent 3-bit windows in data domain for syndrome match.
- **BCH**: systematic polynomial-division encoder. Decoder computes remainder syndrome and then performs bounded candidate search (0/1/2 bit flips) against valid remainder=0 check.
- **Polar**: Arikan transform encoder with deterministic frozen mask assumption. Decoder uses transform-based estimate with frozen-bit enforcement, then bounded 1/2 info-bit local search to reduce Hamming distance.

## Assumptions / Limitations
- TAEC and Polar decoders are **bounded practical models**, not full optimum decoders.
- BCH decoder is mathematically valid for bounded correction, but area-heavy because it performs exhaustive candidate checks.
- Frozen-bit reliability ordering for Polar is intentionally simplified (lower indices frozen).
- All limitations are explicit in module header comments for future enhancement.

## Build and Simulation Commands
```bash
# compile a single testbench
asic/scripts/compile.sh tb_secded

# run one test
asic/scripts/run.sh tb_secded

# run full ASIC regression
asic/scripts/regress.sh
```

## Debugging Notes (waveform-first signals)
- SEC families: `syndrome_o`, `overall_mismatch_o`, `correction_mask_o`, `error_pos_o`.
- SEC-DAEC/TAEC: `adjacent_double_corrected_o`, `triple_adjacent_corrected_o`.
- BCH: `syndrome_o`, `corrected_codeword_o`, internal candidate search results.
- Polar: `u_dbg_o`, `u_hat_o`, `corrected_codeword_o`, `err_*` flags.

## 19-entry mapping
See `asic/docs/MODULE_MAP.md`.
