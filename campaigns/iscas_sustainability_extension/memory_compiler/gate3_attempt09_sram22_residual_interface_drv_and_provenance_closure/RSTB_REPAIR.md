# RSTB repair

The 0.351 ns SRAM-input requirement was never relaxed. All candidates were legal external SKY130HD cells inserted close to the target on the frozen Attempt08 canonical ODB; two-stage candidates preserve reset polarity. Every nonpersistent experiment is listed below and its complete log remains under `raw/repair_experiments`.

| Target | Candidate | Form | Before → after (ns) | Closes? | Log |
|---|---|---|---:|:---:|---|
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__and4_4` | phase-preserving two-stage | 0.615880728 → 1.694496393 | no | `raw/repair_experiments/e0_data_rstb_and4_4.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__bufinv_16` | phase-preserving two-stage | 0.615880728 → 0.613212705 | no | `raw/repair_experiments/e0_data_rstb_bufinv_16_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__clkinv_16` | phase-preserving two-stage | 0.615880728 → 0.391097069 | no | `raw/repair_experiments/e0_data_rstb_clkinv16_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__clkinv_8` | phase-preserving two-stage | 0.615880728 → 0.649706304 | no | `raw/repair_experiments/e0_data_rstb_clkinv8_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__inv_12` | phase-preserving two-stage | 0.615880728 → 0.635677874 | no | `raw/repair_experiments/e0_data_rstb_inv12_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__inv_16` | phase-preserving two-stage | 0.615880728 → 0.540553927 | no | `raw/repair_experiments/e0_data_rstb_inv16_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__inv_8` | phase-preserving two-stage | 0.615880728 → 0.867528260 | no | `raw/repair_experiments/e0_data_rstb_inv8_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__lpflow_clkbufkapwr_16` | single stage | 0.615880728 → 0.533652604 | no | `raw/repair_experiments/e0_data_rstb_lpflow_clkbufkapwr16.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__lpflow_clkinvkapwr_16` | phase-preserving two-stage | 0.615880728 → 0.377817959 | no | `raw/repair_experiments/e0_data_rstb_lpflow_clkinvkapwr_16_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__mux2_8` | phase-preserving two-stage | 0.615880728 → 0.976370990 | no | `raw/repair_experiments/e0_data_rstb_mux2_8.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__nand2_8` | phase-preserving two-stage | 0.615880728 → 0.967853606 | no | `raw/repair_experiments/e0_data_rstb_nand2_8_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__nand3_4` | phase-preserving two-stage | 0.615880728 → 1.825229526 | no | `raw/repair_experiments/e0_data_rstb_nand3_4_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__nand4_4` | phase-preserving two-stage | 0.615880728 → 2.377002239 | no | `raw/repair_experiments/e0_data_rstb_nand4_4_pair.log` |
| `u_protected_memory.u_data/rstb` | `sky130_fd_sc_hd__or4_4` | phase-preserving two-stage | 0.615880728 → 1.682065010 | no | `raw/repair_experiments/e0_data_rstb_or4_4.log` |
| `u_protected_memory.u_ecc/rstb` | `sky130_fd_sc_hd__clkinv_16` | phase-preserving two-stage | 0.358981788 → 0.225446865 | yes | `raw/repair_experiments/e0_ecc_rstb_clkinv16_pair.log` |
| `u_protected_memory.u_ecc/rstb` | `sky130_fd_sc_hd__clkinv_8` | phase-preserving two-stage | 0.358981788 → 0.369439155 | no | `raw/repair_experiments/e0_ecc_rstb_clkinv8_pair.log` |
| `u_protected_memory.u_ecc/rstb` | `sky130_fd_sc_hd__inv_12` | phase-preserving two-stage | 0.358981788 → 0.363413185 | no | `raw/repair_experiments/e0_ecc_rstb_inv12_pair.log` |
| `u_protected_memory.u_ecc/rstb` | `sky130_fd_sc_hd__inv_16` | phase-preserving two-stage | 0.358981788 → 0.310419142 | yes | `raw/repair_experiments/e0_ecc_rstb_inv16_pair.log` |
| `u_protected_memory.u_ecc/rstb` | `sky130_fd_sc_hd__inv_8` | phase-preserving two-stage | 0.358981788 → 0.492765188 | no | `raw/repair_experiments/e0_ecc_rstb_inv8_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__and4_4` | phase-preserving two-stage | 0.619147718 → 1.694241285 | no | `raw/repair_experiments/u0_data_rstb_and4_4.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__bufinv_16` | phase-preserving two-stage | 0.619147718 → 0.613212705 | no | `raw/repair_experiments/u0_data_rstb_bufinv_16_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__clkinv_16` | phase-preserving two-stage | 0.619147718 → 0.391096354 | no | `raw/repair_experiments/u0_data_rstb_clkinv16_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__clkinv_8` | phase-preserving two-stage | 0.619147718 → 0.649705768 | no | `raw/repair_experiments/u0_data_rstb_clkinv8_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__inv_12` | phase-preserving two-stage | 0.619147718 → 0.635651410 | no | `raw/repair_experiments/u0_data_rstb_inv12_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__inv_16` | phase-preserving two-stage | 0.619147718 → 0.540554583 | no | `raw/repair_experiments/u0_data_rstb_inv16_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__inv_8` | phase-preserving two-stage | 0.619147718 → 0.867556274 | no | `raw/repair_experiments/u0_data_rstb_inv8_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__lpflow_clkbufkapwr_16` | single stage | 0.619147718 → 0.533653975 | no | `raw/repair_experiments/u0_data_rstb_lpflow_clkbufkapwr16.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__lpflow_clkinvkapwr_16` | phase-preserving two-stage | 0.619147718 → 0.377817541 | no | `raw/repair_experiments/u0_data_rstb_lpflow_clkinvkapwr_16_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__mux2_8` | phase-preserving two-stage | 0.619147718 → 0.976426959 | no | `raw/repair_experiments/u0_data_rstb_mux2_8.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__nand2_8` | phase-preserving two-stage | 0.619147718 → 0.967850626 | no | `raw/repair_experiments/u0_data_rstb_nand2_8_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__nand3_4` | phase-preserving two-stage | 0.619147718 → 1.825229406 | no | `raw/repair_experiments/u0_data_rstb_nand3_4_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__nand4_4` | phase-preserving two-stage | 0.619147718 → 2.377002478 | no | `raw/repair_experiments/u0_data_rstb_nand4_4_pair.log` |
| `u_data/rstb` | `sky130_fd_sc_hd__or4_4` | phase-preserving two-stage | 0.619147718 → 1.682313442 | no | `raw/repair_experiments/u0_data_rstb_or4_4.log` |

ECC `rstb` accepted the smallest ordinary phase-preserving repair that closed: two `sky130_fd_sc_hd__inv_16` stages. Its canonical final slew is 0.307288498/0.351 ns. We rejected the larger clock-inverter solution even though it also closed.

The 256×64 data-macro load is infeasible with every legal single-output candidate tested: best U0 is 0.377817541 ns; best E0 is 0.377817959 ns, but its opposite edge is the limiting failure. Parallel drivers were not used because they would create an electrically invalid multi-driver net. Canonical U0/E0 data `rstb` remain 0.619147718/0.615635812 ns against 0.351 ns.

Timing-path impact is measured at whole-design final STA: U0 setup WNS/hold slack moved 4.460990000/0.024948900 → 4.460990000/0.024948900 ns; E0 moved 0.584552000/0.001221250 → 0.611109000/0.009414080 ns. Setup/hold violation counts remain zero canonically.
