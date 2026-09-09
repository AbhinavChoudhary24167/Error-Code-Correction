# Paper tables

## Primary table — matched 10 ns physical and operation-aware comparison

All values are arithmetic means across matched placement seeds. Energy excludes SRAM macro-internal energy. The E4 and E5 labels are evidence classes, not technology generations.

| Metric | SECDED mean | Hsiao mean | Hsiao − SECDED | Paired ordering | Qualification |
|---|---:|---:|---:|---|---|
| Total instance area (µm²) | 273979.8 | 274217.4 | 237.6 | Hsiao higher 5/5 | post-route E4 geometry |
| Standard-cell area (µm²) | 13648.3 | 13885.5 | 237.2 | Hsiao higher 5/5 | post-route E4 geometry |
| Wirelength (µm) | 73141.2 | 76134.0 | 2992.8 | Hsiao higher 5/5 | post-route E4 geometry |
| Via count | 5595.2 | 6063.0 | 467.8 | Hsiao higher 5/5 | post-route E4 geometry |
| Setup WNS (ns) | 0.4338 | 0.6774 | 0.2437 | Hsiao better 4/5 | both 5/5 feasible at 10 ns |
| Vectorless total power (mW) | 2.2882 | 1.9735 | -0.3147 | Hsiao lower 5/5 | E4 diagnostic |
| Clean read energy (pJ/op) | 12.5593 | 12.5285 | -0.0308 | Hsiao lower 3/5 | E5 ECC-logic only |
| Clean write energy (pJ/op) | 11.2622 | 11.3828 | 0.1207 | Hsiao lower 0/4 | E5 ECC-logic only |
| Correction energy (pJ/op) | 13.4383 | 13.7478 | 0.3095 | Hsiao lower 0/5 | E5 ECC-logic only |
| Detection energy (pJ/op) | 13.4359 | 13.6294 | 0.1935 | Hsiao lower 0/5 | E5 ECC-logic only |

Table note: total instance area equals standard-cell plus macro instance area. Both architectures use the same 260,332 µm² macro area. The primary table does not include U0 or BCH in energy columns because they lack E5 evidence; BCH also fails the 10 ns timing constraint in all five inherited seeds.

## Supplementary per-seed values

Per-seed physical and energy deltas are retained in `GREEN_PAIRED_STATISTICS.json` and the sealed source `E5_MATCHED_SEED_DELTAS.csv`; they should remain in the repository supplement rather than consume manuscript table space.
