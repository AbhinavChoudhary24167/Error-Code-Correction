# GREEN-ECC DATE 2027 Gate 03E Report

## Outcome

Gate 03 re-entry is **not currently authorized**. WSL2, Docker CE, the immutable ORFS image, source reconciliation, SKY130HD collateral, two targetless full GCD flows, and all four technology-mapping jobs are complete. The pre-frozen reproducibility policy reports a failure, so readiness cannot be claimed. Because the deadline has not expired, no terminal failure verdict is issued.

The Gate-03R freeze is local commit `db32a47d103495787a17b59388dfad3cc4cb77e8` with annotated local tag `gate03e-pre-reboot-db32a47`. Neither was pushed. Gate-03E files remain uncommitted. Gate-03R remains `REMEDIATION_FAILED` with the three sub-results recorded in the authorization artifact.

## Environment and identity

- Ubuntu 24.04.4 runs as WSL2 with systemd; Docker Engine CE 29.7.2 is active and enabled.
- Successful execution of `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e` is the Docker functional health test.
- Registry tag `26Q3-275-g56496f398` resolves to the required Linux/amd64 manifest `sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e` and image ID `sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`.
- Official source commit `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2` and Git tree `2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a` are frozen with 29 recursive submodules and 28,939 hashed checkout files.
- Narrow execution reconciliation is PASS: 169 byte-identical files, 0 missing, 0 additional, and 0 mismatched. Files outside the execution subset are recorded separately; the OCI digest remains the identity of the complete container.
- The selected Liberty metadata confirms process 1.0, 25 °C, and 1.8 V for `sky130_fd_sc_hd__tt_025C_1v80`.

## Official GCD flows

Both new clean run directories invoked exactly `make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk`. The pinned Makefile declares `.DEFAULT_GOAL := all` and `all: check-yosys check-openroad synth floorplan place cts route finish`. Both runs completed synthesis, floorplanning, placement, CTS, routing, extraction/STA, and final netlist/DEF/GDS generation. The effective `LEC_CHECK=0` retains the pinned flow's documented default after an optional Kepler library was proven incompatible with this AVX2-only host.

The first native optional-LEC attempt is retained under `$GATE03E_EVIDENCE/attempts/gcd-native-lec-avx512-failure-01`: the pinned `libnaja_python.so` executes an unconditional AVX-512VL instruction and exits with SIGILL on the Ryzen 7 7735HS WSL2 host. This is an image/host optional-check compatibility issue, not an ORFS physical-flow failure.

## Reproducibility result

Policy SHA-256: `258694f328084c3fb92dec24e07b3b40d261037d5b1bd8d32b119684211d0b9a`. It was frozen before run 1 and was not changed afterward. Each run inventory contains 106 raw and canonical artifact records. All 15 required semantic GDS/DEF/netlist/SDC/SPEF comparisons pass exactly, and the authoritative JSON cell counts, areas, utilization instance counts, routing/antenna/violation counts match. Nevertheless, the complete comparison is FAIL: 27 raw-hash differences include 16 unexplained or tolerance-breach classifications, and 29 numeric records breach their pre-frozen rule. No post-run exclusion was invented.

Every raw-hash difference is retained below; the complete 551,701-byte comparison with all metric records is indexed at `$GATE03E_EVIDENCE/runs/gcd-run-comparison.json`.

| Path | Predefined classification | Result | Explanation |
|---|---|---:|---|
| `container.log` | `unexplained_or_tolerance_breach` | FAIL | line 38 has a nonnumeric canonical difference |
| `logs/sky130hd/gcd/base/1_1_yosys_canonicalize.log` | `unexplained_or_tolerance_breach` | FAIL | line 35 has a nonnumeric canonical difference |
| `logs/sky130hd/gcd/base/1_2_yosys.log` | `unexplained_or_tolerance_breach` | FAIL | line 258 has a nonnumeric canonical difference |
| `logs/sky130hd/gcd/base/1_synth.log` | `predeclared_metadata_or_ordering` | PASS | absolute_run_root, cpu_time_field, elapsed_time_field, peak_memory_field, trailing_horizontal_whitespace |
| `logs/sky130hd/gcd/base/2_1_floorplan.log` | `unexplained_or_tolerance_breach` | FAIL | line 160 has a tolerance breach |
| `logs/sky130hd/gcd/base/2_2_floorplan_macro.log` | `predeclared_metadata_or_ordering` | PASS | absolute_run_root, cpu_time_field, elapsed_time_field, peak_memory_field, trailing_horizontal_whitespace |
| `logs/sky130hd/gcd/base/2_3_floorplan_tapcell.log` | `unexplained_or_tolerance_breach` | FAIL | line 16 has a tolerance breach |
| `logs/sky130hd/gcd/base/2_4_floorplan_pdn.log` | `predeclared_metadata_or_ordering` | PASS | absolute_run_root, cpu_time_field, elapsed_time_field, peak_memory_field, trailing_horizontal_whitespace |
| `logs/sky130hd/gcd/base/3_1_place_gp_skip_io.log` | `unexplained_or_tolerance_breach` | FAIL | line 103 has a tolerance breach |
| `logs/sky130hd/gcd/base/3_2_place_iop.log` | `unexplained_or_tolerance_breach` | FAIL | line 25 has a tolerance breach |
| `logs/sky130hd/gcd/base/3_3_place_gp.log` | `unexplained_or_tolerance_breach` | FAIL | line 399 has a tolerance breach |
| `logs/sky130hd/gcd/base/3_4_place_resized.log` | `unexplained_or_tolerance_breach` | FAIL | line 97 has a tolerance breach |
| `logs/sky130hd/gcd/base/3_5_place_dp.log` | `predeclared_metadata_or_ordering` | PASS | absolute_run_root, cpu_time_field, elapsed_time_field, peak_memory_field, trailing_horizontal_whitespace |
| `logs/sky130hd/gcd/base/4_1_cts.log` | `unexplained_or_tolerance_breach` | FAIL | line 56 has a tolerance breach |
| `logs/sky130hd/gcd/base/5_1_grt.json` | `unexplained_or_tolerance_breach` | FAIL | logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__congestion_rsmt_s: delta 4.478999999999985e-05 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__finalization_s: delta 9.360000000000097e-05 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__initial_rsmt_s: delta 0.00014670000000000004 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__monotonic_s: delta 0.0010737200000000002 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__new_route_l_s: delta 2.5332000000000008e-05 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__overflow_iterations_s: delta 2.2507999999999968e-05 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__route_l_s: delta 3.4780000000000097e-06 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__route_z_s: delta 1.0420000000000012e-06 exceeds 0.0; logs/sky130hd/gcd/base/5_1_grt.json.globalroute__global_route__fastroute__spiral_s: delta 1.7173000000000047e-05 exceeds 0.0 |
| `logs/sky130hd/gcd/base/5_1_grt.log` | `unexplained_or_tolerance_breach` | FAIL | line 98 has a tolerance breach |
| `logs/sky130hd/gcd/base/5_2_route.log` | `unexplained_or_tolerance_breach` | FAIL | line 158 has a tolerance breach |
| `logs/sky130hd/gcd/base/5_3_fillcell.log` | `unexplained_or_tolerance_breach` | FAIL | line 18 has a tolerance breach |
| `logs/sky130hd/gcd/base/6_1_fill.log` | `predeclared_metadata_or_ordering` | PASS | absolute_run_root, cpu_time_field, elapsed_time_field, peak_memory_field, trailing_horizontal_whitespace |
| `logs/sky130hd/gcd/base/6_1_merge.log` | `predeclared_metadata_or_ordering` | PASS | cpu_time_field, elapsed_time_field, peak_memory_field |
| `logs/sky130hd/gcd/base/6_report.log` | `unexplained_or_tolerance_breach` | FAIL | line 71 has a tolerance breach |
| `objects/sky130hd/gcd/base/klayout.lyt` | `unexplained_binary_difference` | FAIL | no predeclared canonical or tolerance rule explains this binary difference |
| `results/sky130hd/gcd/base/6_1_merged.gds` | `predeclared_metadata_or_ordering` | PASS | gds_bgnlib_bgnstr_dates_and_order |
| `results/sky130hd/gcd/base/6_final.gds` | `predeclared_metadata_or_ordering` | PASS | gds_bgnlib_bgnstr_dates_and_order |
| `results/sky130hd/gcd/base/6_final.spef` | `predeclared_metadata_or_ordering` | PASS | spef_date_field, trailing_horizontal_whitespace |
| `run-command.txt` | `predeclared_metadata_or_ordering` | PASS | absolute_run_root |
| `run-metadata.json` | `predeclared_metadata_or_ordering` | PASS | absolute_run_root, json_metadata_key:end_time, json_metadata_key:start_time, json_object_key_order_and_encoding |

## GREEN-ECC mapping readiness

All four bounded 1,200-second `make synth` jobs pass against the frozen SKY130HD Liberty. Every flattened cell instance is a SKY130HD master, no mapped latches or black boxes remain, no fault-injection input enters a boundary, and equivalence remains assessable. The independent combinational SECDED boundary maps to 594 cells with zero sequential cells; the pipelined boundary maps to 924 cells including 302 sequential cells. Their normalized hashes and master histograms differ. BCH encoder/decoder mapping also passes. These are structural readiness results only; no comparative PPA was calculated or published.

The direct production SECDED package elaboration attempt failed before mapping because the pinned Yosys Verilog-2005 frontend rejects the production package construct. It was reported and preserved before any RTL change. Production RTL remains untouched; the combinational job uses the already accepted Gate-03R package-free implementation whose exact identity is referenced by `SECDED_PROOF_SUMMARY.json`.

## Scope and evidence

No production RTL, registry, selector, results, paper material, or previous-gate evidence was changed. Large physical outputs remain under `/var/lib/green-ecc-gate03e` and are identified by stable root-relative paths, sizes, raw hashes, and canonical hashes. The 108 retained raw logs are copied byte-for-byte under `raw_logs/` and indexed by `RAW_LOG_INDEX.csv`.
