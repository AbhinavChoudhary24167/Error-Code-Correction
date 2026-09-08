# SRAM22 physical-view qualification

## Hardened-view consumption

| Evidence | 256×64 | 256×8 |
|---|---:|---:|
| GDS readability / expected top | PASS | PASS |
| Resolved GDS cells | 8,889 | 5,233 |
| Direct top instances | 2,480 | 1,766 |
| GDS / LEF boundary | 690.12 × 291.64 µm, exact | 261.72 × 225.68 µm, exact |
| LEF pins / geometry / obstructions | QUALIFIED | QUALIFIED |
| OpenROAD macro import | QUALIFIED | QUALIFIED |

The GDS files were losslessly decompressed from the frozen upstream `.gds.gz` files. KLayout parsed the complete hierarchy, top boundaries match LEF exactly, expected external labels were found, the views use SKY130 layers accepted by the pinned `sky130hd` OpenROAD platform, and both macros were imported as unmodified hardened blocks. No internal macro geometry, pin, topology, or mask mapping was edited.

## DRC and the dense-bitcell hypothesis

The available ORFS public KLayout runset is incomplete for leaf signoff (`FEOL=false`, `BEOL=true`, `OFFGRID=true`). It reports 34,459 markers for 256×64 and 5,831 for 256×8. Parsing every `.lyrdb` item shows exactly five reported rule families (`li.1`, `li.3`, `li.5`, `m1.4`, and `m2.4`) and **100% of markers in both runs are attached to SRAM-internal array, bitcell, replica, row-end, strap, or `sram22_inner` hierarchy**. No marker is attributed to a top-level integration cell or ordinary surrounding logic.

This supports the proposed explanation that the generic public deck is flagging dense SRAM-specific geometry. It is consistent with normal hard-macro integration practice, upstream reported silicon operation, and flows that black-box hardened SRAM internals. It is enough to classify integration use as `MACRO_INTEGRATION_BLACKBOX_ACCEPTABLE_WITH_DOCUMENTED_RISK`.

It is not a foundry waiver. The public runset contains special `li.1a`/`li.3a` exceptions for a different named SRAM family, not these SRAM22 cell names; no SRAM22-specific foundry deck, specialized-mask mapping, waiver letter, or signoff report is published. Consequently leaf DRC remains `DRC_NOT_INDEPENDENTLY_REPRODUCIBLE`, and `PHYSICAL_DRC_QUALIFIED` must not be claimed.

## LVS boundary

A representative public-deck comparison of the 256×8 GDS against the immutable upstream SPICE completed extraction but reported `Netlists don't match`. No topology, net, pin, or black-box manipulation was used, and the 256×64 run was not repeated after the same stack was shown not to reproduce equivalence. Status is `NOT_INDEPENDENTLY_REPRODUCED`, distinct from normal `MACRO_INTEGRATION_BLACKBOX` handling in OpenROAD.

Raw evidence is under `raw/qualification/` and `raw/physical/`.

