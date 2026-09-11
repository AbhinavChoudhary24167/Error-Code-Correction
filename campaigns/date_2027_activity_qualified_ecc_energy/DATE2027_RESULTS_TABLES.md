# DATE 2027 Results Tables

Delta definition throughout: Hsiao SECDED minus conventional SECDED. Negative favors Hsiao.

## Headline operation-energy result

| Operation | Matched pairs | Mean delta (pJ/op) | Sample SD (pJ) | Range (pJ/op) | Hsiao lower |
|---|---:|---:|---:|---:|---:|
| Idle | 4 | +0.019108 | 0.039517 | -0.028663 to +0.068117 | 1/4 |
| Clean write | 4 | +0.120682 | 0.031926 | +0.072963 to +0.139452 | 0/4 |
| Clean read | 5 | -0.030838 | 0.164294 | -0.213063 to +0.170538 | 3/5 |
| Single-bit correction | 5 | +0.309500 | 0.177933 | +0.148294 to +0.521353 | 0/5 |
| Double-bit detection | 5 | +0.193505 | 0.176897 | +0.029814 to +0.405498 | 0/5 |

Overall: Hsiao lower in 4/23 activity-qualified cells. Vectorless diagnostic: Hsiao lower total logic power in 5/5 matched seeds.

## Physical qualification means

| Metric | Mean delta | Interpretation |
|---|---:|---|
| Total instance area | +237.6 um2 | Hsiao larger |
| Standard-cell area | +237.2 um2 | Hsiao larger |
| Wirelength | +2992.8 um | Hsiao longer |
| Via count | +467.8 | Hsiao more vias |
| Setup WNS | +0.2436916 ns | Hsiao more slack on average; better in 4/5 |

All ten routes are timing feasible at 10 ns.

## Mean component power deltas (uW)

| Operation | Internal | Switching | Leakage | Total sign count favoring Hsiao |
|---|---:|---:|---:|---:|
| Idle | -0.006723 | +1.916756 | +0.000033 | 1/4 |
| Write | -0.114320 | +12.177697 | +0.000054 | 0/4 |
| Clean read | +25.890768 | -28.973364 | +0.000083 | 3/5 |
| Correction | +35.456382 | -4.518486 | +0.000057 | 0/5 |
| Detection | +30.415412 | -11.072448 | +0.000050 | 0/5 |

## Activity qualification

- 46 operation records.
- 99.298390–99.356061% functional logic coverage.
- 100% sequential coverage.
- All 72 SRAM-output roots represented.
- 16 warm-up cycles and 256 measured operations per record.
- Final routed zero-delay gate-netlist VCD plus final SPEF.
- ECC-logic boundary; macro-internal/whole-memory energy excluded.

Machine-readable authoritative values are in `data/` and `DATE2027_REPRODUCIBILITY_TABLE.csv`.

