# Immutable source-view inventory

All source views were read from pinned commit `dd64256961317205343a3fd446908b42bafba388`; none was modified in place. OpenRAM wrapper views are from commit `b6a6f12642df6b84facc24a77f9a6f67a0d62dab`. Paths in the JSON are logical provenance paths; hashes bind the exact bytes.

| Cell | Category | Pins | GDS hierarchy | Add layers (shape records) | Vendor/OpenRAM view relation |
|---|---|---|---:|---|---|
| `sky130_fd_bd_sram__sram_sp_colend` | column_end | bl, br, vdd, gnd, vpb, vnb, gate | 1 | 22/21=1, 33/43=1, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_colenda` | column_end | bl, br, vdd, gnd, vpb, vnb, gate | 1 | 22/21=1, 33/43=1, 92/44=2 | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_corner` | corner | VPWR, VPB, VNB | 4 | 33/43=1, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_cornera` | corner | VPWR, VPB, VNB | 4 | 33/43=1, 92/44=2 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_cornerb` | corner | VPWR, VPB, VNB | 4 | 33/43=1, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_cell_opt1` | bitcell | BL, BR, VGND, VPWR, VPB, VNB, WL | 14 | 115/43=2, 22/21=7, 33/43=7, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_cell_opt1a` | bitcell | BL, BR, VGND, VPWR, VPB, VNB, WL | 14 | 115/43=2, 22/21=7, 33/43=7, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__openram_sp_cell_opt1_replica` | replica_bitcell | BL, BR, VGND, VPWR, VPB, VNB, WL | 1 | 115/43=2, 22/21=7, 33/43=10, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__openram_sp_cell_opt1a_replica` | replica_bitcell | BL, BR, VGND, VPWR, VPB, VNB, WL | 1 | 115/43=2, 22/21=7, 33/43=10, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__openram_sp_cell_opt1a_dummy` | dummy_bitcell | BL, BR, VGND, VPWR, VPB, VNB, WL | 1 | 115/43=2, 22/21=7, 33/43=10, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_colend_cent` | column_end | VPWR, VPB, VNB | 1 | 33/43=1, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_colend_p_cent` | column_end | VGND, VPB, VNB | 1 | 33/43=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_colenda_cent` | column_end | VPWR, VPB, VNB | 1 | 33/43=1, 92/44=2 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_colenda_p_cent` | column_end | VGND, VPB, VNB | 1 | 33/43=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_rowend` | row_end | VPWR, WL | 4 | 115/43=1, 22/21=1, 33/43=3, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_rowenda` | row_end | VPWR, WL | 4 | 115/43=1, 22/21=1, 33/43=2, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__openram_sp_rowend_replica` | row_end_replica | VPWR, WL | 4 | 115/43=1, 22/21=1, 33/43=3, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__openram_sp_rowenda_replica` | row_end_replica | VPWR, WL | 4 | 115/43=1, 22/21=1, 33/43=2, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_wlstrap` | wordline_strap | VPWR | 4 | 115/43=2, 22/21=2, 33/43=4, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_wlstrapa` | wordline_strap | VPWR | 4 | 115/43=2, 22/21=2, 33/43=3, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_wlstrap_p` | wordline_strap | VGND | 5 | 115/43=2, 22/21=2, 33/43=4 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_wlstrapa_p` | wordline_strap | VGND | 5 | 115/43=2, 22/21=2, 33/43=3 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_wlstrap_ce` | wordline_strap_helper | none | 1 | 115/43=2, 22/21=2, 92/44=1 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__sram_sp_wlstrap_p_ce` | wordline_strap_helper | none | 2 | 115/43=2, 22/21=2 | gds:BYTE_IDENTICAL, lvs_spice:VIEW_NOT_AVAILABLE_ON_BOTH_SIDES, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:BYTE_IDENTICAL |
| `sky130_fd_bd_sram__openram_sense_amp` | support_leaf | BL, BR, DOUT, EN, VDD, GND | 1 | none | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:DIFFERENT |
| `sky130_fd_bd_sram__openram_write_driver` | support_leaf | DIN, BL, BR, EN, VDD, GND | 1 | none | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:DIFFERENT |
| `sky130_fd_bd_sram__openram_dff` | support_leaf | D, Q, CLK, VDD, GND | 1 | none | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:DIFFERENT |
| `sky130_fd_bd_sram__openram_sp_nand2_dec` | support_leaf | A, B, Z, VDD, GND | 1 | none | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:DIFFERENT |
| `sky130_fd_bd_sram__openram_sp_nand3_dec` | support_leaf | A, B, C, Z, VDD, GND | 1 | none | gds:BYTE_IDENTICAL, lvs_spice:BYTE_IDENTICAL, mag:BYTE_IDENTICAL, maglef:BYTE_IDENTICAL, spice:DIFFERENT |

Full per-structure hierarchy, layer/datatype counts, every view path, size, and SHA-256 are in `SOURCE_VIEW_INVENTORY.json` and `raw/gds_analysis/`.
