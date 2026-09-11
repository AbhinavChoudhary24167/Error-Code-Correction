# Primitive bisection matrix

`Standalone DRC` is the leaf cell's error-tile count under the same `sky130A` Magic setup. `Rule occurrences` can exceed tiles because multiple rules can annotate a tile. Full source-MAG views were also tested and were substantially worse; the table uses the maglef values actually seen by the OpenRAM verification flow. Raw logs preserve both views.

| Primitive / hierarchy | Instances or replication in control | Source module / view | Expected versus extracted pins | Standalone DRC tiles (rule occurrences) | Schematic / extracted devices | LVS | Notes |
|---|---:|---|---|---:|---:|---|---|
| `sram_sp_cell_opt1` | Repeated through 17×9 array hierarchy | `custom/sky130_bitcell_base_array.py`; `maglef_lib`, `gds_lib`, `lvs_lib` | BL, BR, WL, VPWR, VGND, VNB, VPB; extracted WL split and disconnected proxy | 8 (16) | 8 / 8 | FAIL, 9 schematic / 10 extracted nets | Full MAG: 124 tiles; generated main array: 360 tiles |
| `sram_sp_cell_opt1a` | Alternating array leaf | same hard-macro loaders | same functional pins; extracted WL split | 8 (16) | 8 / 8 | FAIL, 9 / 10 nets | Full MAG: 124 tiles |
| replica bitcells | Repeated in replica arrays/column | `custom/replica_bitcell_array.py`; imported views | same functional pins; extracted WL split | 8 (16) | 8 / 8 | FAIL, 8 / 9 nets | Replica and capped arrays each 380 tiles |
| dummy bitcell | 1×9 dummy row/column hierarchy | imported `openram_sp_cell_opt1a_dummy` views | data/supply pins; extracted proxy/disconnected nodes | 8 (17) | 8 / 8 | FAIL before flattening | Dummy array: 34 tiles; full MAG: 101 tiles |
| `sram_sp_colend` | 10 in capped array report | imported maglef/GDS/LVS view | expected `gate vnb br bl vdd gnd vpb`; extracted adds `m2_0_4#`, `m2_0_236#` and disconnected pins | 7 (14) | 1 / 1 | Leaf devices match; hierarchy FAIL | Full MAG: 37 tiles; proxy partitions propagate upward |
| `sram_sp_colenda` | 10 in capped array report | imported maglef/GDS/LVS view | same mismatch class as `colend` | 7 (14) | 1 / 1 | Leaf devices match; hierarchy FAIL | Full MAG: 36 tiles |
| colend centre / P-centre | Repeated in column caps | imported maglef/GDS | pin audit preserved in extraction | 7–8 (11–15) | not separately compared | Not isolated | Column-cap arrays: 65 tiles each |
| wordline straps | Repeated across bitcell rows | imported maglef/GDS | rail/power labels from vendor abstract | 12–13 (14–17) | not separately compared | Not isolated | Full MAG: 55–58 tiles |
| corners / row ends | Array boundaries | imported maglef/GDS | boundary supply/rail pins | 5–7 (8–10) | not separately compared | Not isolated | Row-cap arrays: 117 tiles each |
| sense amplifier | 9 columns including spare | `sense_amp_array.py`; imported `openram_sense_amp` | archived source pin list | 0 | matched within parent | No leaf failure reported | Not a DRC origin |
| write driver | 9 columns including spare | `write_driver_array.py`; imported `openram_write_driver` | archived source pin list | 0 | matched within parent | No leaf failure reported | Not a DRC origin |
| precharge | 9 columns including spare | `precharge.py`, generated layout | BL/BR, enable, VDD | 3 | included in 227/227 port-data devices | Parent FAIL | Small generated DRC contributor |
| decoder NAND2/NAND3 | 39 / 8 in bank summary | imported `openram_sp_nand2_dec` / `nand3_dec` | A/B[/C], Z, VDD, GND | 0 | imported leaves match | PASS at imported leaf | Generated wrappers later show power partition |
| generated `pnand2_0` | 1 | `pnand2.py` / generated Magic | A, B, Z, VDD, GND; extracted well/bulk node split | 0 at imported NAND leaf | 4 / 4 | FAIL, 7 / 6 nets | Smallest definite generated LVS mismatch |
| generated `pnand3` | 1 | `pnand3.py` / generated Magic | A, B, C, Z, VDD, GND; well/bulk partition | 0 at imported NAND leaf | 6 / 6 | FAIL, 9 / 8 nets | Independent of vendor parameter normalization |
| column mux | 0 | not instantiated (`words_per_row=1`) | N/A | N/A | N/A | N/A | Correctly excluded |
| generated contacts / power ring | many | `base/contact.py`, routers | layer-stack connectivity | folded into parents | N/A | contributes to net partitions | Direct top GDS test confirms layer materialization problem |

The smallest reproducible physical defects are in leaf imported SRAM views (5–13 tiles). The smallest definite LVS netlist mismatch is a four-device generated NAND wrapper, while the earliest imported-view evidence is already present in one-device `colend`/`colenda` pin partitions and eight-device bitcell net splits. This is therefore a view-stack integration failure, not 2,140 independent top-level layout mistakes.
