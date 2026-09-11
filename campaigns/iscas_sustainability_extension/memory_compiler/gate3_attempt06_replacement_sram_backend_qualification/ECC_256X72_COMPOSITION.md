# ECC 256×72 composition

`ecc_sram_256x72_sram22` is a two-bank logical memory, not a merged physical bitcell array:

```text
64-bit payload -> Hsiao encoder -> codeword[63:0] -> sram22_256x64m4w8
                              \-> codeword[71:64] -> sram22_256x8m8w1

synchronized {clock, reset, address, enable, write}
two macro outputs -> 72-bit codeword -> Hsiao decoder -> corrected payload/status
```

The implementation reuses the repository-qualified `hsiao-secded-72-64-v1` code identity (`n=72`, `k=64`, exact minimum distance 4):

| Source | Frozen SHA-256 |
|---|---|
| `hsiao_secded_72_64_v1_encoder.sv` | `638b36ff3ab1ee31bb8e29b8d5ea064b5b36d1d7df7a3f2b96c52e305a31e036` |
| `hsiao_secded_72_64_v1_syndrome.sv` | `5b232248546e1945ab5084b7f4850851bb62c6e54dc9c4fa00950e2a457590be` |
| `hsiao_secded_72_64_v2_algorithmic_decoder.sv` | `3c422dbbddab55e8e2ae141b571e60e63f4ecd87ac409d64b59cc184f21aadcf` |

The deterministic testbench passed no-error reads, all 72 possible single-bit corruptions with correction/status checking, and all 2,556 double-bit pairs with uncorrectable detection/status checking. A test-only XOR fault mask is outside the hardened macros and is tied to zero in the physical top; it does not modify stored macro data or physical views.

Result: `HSIAO_SECDED_PASS singles=72 doubles=2556` and `SRAM22_256X72_COMPOSITION_PASS`.

