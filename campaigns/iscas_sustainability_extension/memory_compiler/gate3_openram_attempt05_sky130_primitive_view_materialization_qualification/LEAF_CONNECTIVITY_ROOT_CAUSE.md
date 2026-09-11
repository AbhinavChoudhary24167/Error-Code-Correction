# Leaf connectivity root cause

## Test method

Each original vendor GDS was imported by pinned Magic 8.3.311 using the normal `sky130A` technology, checked with unwaived DRC, extracted with `blackbox off`, and compared by pinned Netgen 1.5.221 to the byte-pinned OpenRAM LVS schematic. Full vendor MAG and MAGLEF were separate diagnostic controls.

## `sram_sp_colend`

Direct GDS import reports unknown 92/44, 22/21, and 33/43 records and produces 39 DRC tiles (141 rule occurrences). It extracts one `sky130_fd_pr__special_nfet_pass`, matching the one schematic device and three counted connected nets, but the extracted subcircuit ports are `bl br gnd vdd vpb vnb`; the transistor gate is an internal node named `gate` and is absent at the boundary. Netgen therefore reports `(no matching pin) | gate` and LVS FAIL. The MAGLEF view has seven DRC tiles and extracts no device; it is an abstract port/obstruction view and cannot substitute for electrical qualification. The full vendor MAG has 37 DRC tiles and also fails LVS.

Cause: the provided open views do not jointly preserve a usable electrical boundary pin and clean physical geometry under the pinned normal Magic flow. Missing add-mask materialization is correlated with the GDS warnings, but no specific polygon composition can be named causally without the unavailable semantics.

## `sram_sp_colenda`

Direct GDS has 38 DRC tiles (126 rule occurrences). Its one device, three connected nets, and seven top-level pins match uniquely in standalone Netgen. `bl`, `vdd`, `gnd`, and `vpb` are disconnected feed-through ports in both compared one-device netlists. This limited standalone PASS does not qualify the cell because DRC is nonzero and does not disprove the parent-level proxy partition observed in Attempt04. Full vendor MAG still fails its separate comparison, confirming that substituting the MAG is not a general repair.

Cause classification: standalone logical core equivalence with an unqualified physical view; parent proxy behavior remains a hierarchy/interface incompatibility, not evidence for forced bridging.

## Ordinary and replica bitcells

Both ordinary variants extract the expected eight devices but ten nets versus nine schematic nets and have 126 DRC tiles. Netgen shows schematic `WL` with no matching extracted net. Each replica extracts eight devices but nine nets versus eight, with 125 DRC tiles; `WL` drives only half the expected pass-device gates while the other half is on an anonymous net (`a_0_24#` or `a_0_262#`). The dummy extracts eight devices and fourteen nets versus thirteen, has 100 DRC tiles, and likewise has no net matching schematic `WL`.

The same extra-net counts recur after extracting the full vendor MAG, so the split is not just a MAGLEF obstruction or a transient direct-GDS parser artifact. It is an unjoined wordline partition in the electrical geometry available to normal Magic. Unknown CP1M/CFOM/CLI1 augmentation is a plausible origin, but the evidence cannot distinguish missing poly, contact, or LI composition; selecting one would be a guessed topology change.

## Remaining leaves

All three corners have 35 direct-GDS DRC tiles and no standalone schematic. Row ends, replica row ends, column-center helpers, and wordline straps retain nonzero direct-GDS DRC except the two `_ce` helpers, which lack a standalone schematic comparison. Sense amplifier, write driver, and DFF are DRC-clean but fail standalone LVS. Only the unchanged `openram_sp_nand2_dec` and `openram_sp_nand3_dec` views are both DRC-clean and LVS-equivalent.

The detailed per-cell counts, models, ports, rule histograms, disconnected nodes, and report paths are in `LEAF_PREQUALIFICATION_MATRIX.json`; all raw evidence is under `raw/leaf_prequalification/`.
