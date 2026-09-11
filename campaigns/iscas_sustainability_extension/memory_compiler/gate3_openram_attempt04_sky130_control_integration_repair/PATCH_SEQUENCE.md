# Patch sequence

| Phase | Audited change | Config hash | DRC tiles | LVS | Top devices E/S | Top nets E/S | Result |
|---|---|---|---:|---|---:|---:|---|
| P0 | None; pinned baseline | `dc22607…82fd6` | 2,140 | FAIL | 1,802 / 1,802 | 658 / 698 | Reproduced prior failure |
| P1 | Eight exact `lvs.spice` parameter normalizations from SRAM commit `8dccd8d…` copied into campaign-local `lvs_lib` | same | 2,140 | FAIL | 1,802 / 1,802 | 658 / 698 | No connectivity or DRC improvement |
| P2 | Complete the same upstream commit with its dummy maglef LI/OBS removal and ordinary bitcell SPICE synchronization | same | 2,140 | FAIL | 1,802 / 1,802 | 658 / 698 | No improvement; final audited state |

No second defect family was patched after P2. No installed source, installed PDK, verification deck, prior evidence, or control configuration was edited. The final result does not satisfy a partial-repair threshold because both verifier outcomes and all reported mismatch counts are unchanged.
