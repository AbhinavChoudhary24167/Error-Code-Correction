# Rstb interface characterization

**Classification D: INSUFFICIENT_EVIDENCE** for a universal interface limitation or an invalid rstb constraint. The evidence supports a narrower finding: all four strongest x16 buffer/inverter families tested fail the 256x64 interface in zero-wire diagnostics; the strongest tested phase-preserving clkinv pair also fails after local placement. Historical Gate-3 remains FAIL / RESIDUAL_SRAM_INPUT_DRV_FAIL.

The 256x64 rising pin capacitance is 0.448008 pF versus 0.250926 pF for 256x8 (1.785419 times). SPEF declares PIN_CAP NONE: its parasitic capacitance must be added to the Liberty pin load, never substituted for it. The data net parasitics are only 0.00213879 pF (U0) and 0.00111857 pF (E0), under 0.5% of the rising pin load. This is strong evidence that the frozen macro input-capacitance model, rather than long external wiring alone, dominates the load.

## Matched frozen post-route condition

| Design/pin | Rise cap (pF) | Wire cap (pF) | Driver input rise/fall (ns) | Macro worst slew (ns) | Route length (um) |
|---|---:|---:|---|---:|---:|
| E0 u_protected_memory.u_data/rstb | 0.448008 | 0.00111857 | 0.038298469 / 0.028718838 | 0.615635812 | 10.67 |
| E0 u_protected_memory.u_ecc/rstb | 0.250926 | 0.00163490 | 0.043022502 / 0.024114789 | 0.307288498 | 8.95 |
| U0 u_data/rstb | 0.448008 | 0.00213879 | 0.163767353 / 0.103794731 | 0.619147718 | 19.09 |

## Controlled zero-wire results

Eight tiny netlists use frozen TT Liberty, no wire parasitics, one macro load, and the strongest available drive suffix in each unary family. Each runs three defined source slew conditions (0.01, 0.1, 0.3 ns). Inverter pairs preserve rstb phase; no production netlist or constraints are changed.

| Macro | Driver topology | Source slew (ns) | Worst macro slew (ns) | 0.351 ns |
|---|---|---:|---:|---|
| sram22_256x64m4w8 | buf single | 0.01 | 0.622587085 | FAIL |
| sram22_256x64m4w8 | buf single | 0.1 | 0.623028457 | FAIL |
| sram22_256x64m4w8 | buf single | 0.3 | 0.623167217 | FAIL |
| sram22_256x64m4w8 | clkbuf single | 0.01 | 0.604175150 | FAIL |
| sram22_256x64m4w8 | clkbuf single | 0.1 | 0.604766726 | FAIL |
| sram22_256x64m4w8 | clkbuf single | 0.3 | 0.605171859 | FAIL |
| sram22_256x64m4w8 | clkinv pair | 0.01 | 0.391104341 | FAIL |
| sram22_256x64m4w8 | clkinv pair | 0.1 | 0.391078472 | FAIL |
| sram22_256x64m4w8 | clkinv pair | 0.3 | 0.391355038 | FAIL |
| sram22_256x64m4w8 | inv pair | 0.01 | 0.540709436 | FAIL |
| sram22_256x64m4w8 | inv pair | 0.1 | 0.540572882 | FAIL |
| sram22_256x64m4w8 | inv pair | 0.3 | 0.540466607 | FAIL |
| sram22_256x8m8w1 | buf single | 0.01 | 0.360097736 | FAIL |
| sram22_256x8m8w1 | buf single | 0.1 | 0.360672832 | FAIL |
| sram22_256x8m8w1 | buf single | 0.3 | 0.361042917 | FAIL |
| sram22_256x8m8w1 | clkbuf single | 0.01 | 0.350827545 | MET |
| sram22_256x8m8w1 | clkbuf single | 0.1 | 0.351086378 | FAIL |
| sram22_256x8m8w1 | clkbuf single | 0.3 | 0.352352440 | FAIL |
| sram22_256x8m8w1 | clkinv pair | 0.01 | 0.225432172 | MET |
| sram22_256x8m8w1 | clkinv pair | 0.1 | 0.225478470 | MET |
| sram22_256x8m8w1 | clkinv pair | 0.3 | 0.226208657 | MET |
| sram22_256x8m8w1 | inv pair | 0.01 | 0.310572118 | MET |
| sram22_256x8m8w1 | inv pair | 0.1 | 0.310464084 | MET |
| sram22_256x8m8w1 | inv pair | 0.3 | 0.310635298 | MET |

## Local placement

Three in-memory experiments insert a clkinv_16 pair near the target, remove filler cells from the in-memory copy, legalize the placement, and estimate parasitics using the frozen SKY130HD setRC.tcl. They retain the original upstream reset chain. They are placement diagnostics, not rerouted implementations or whole-design closure.

| Target | Condition | Macro worst slew (ns) |
|---|---|---:|
| u_protected_memory.u_data/rstb | IDEALIZED_LOCAL_PLACEMENT | 0.397579938 |
| u_protected_memory.u_data/rstb | LEGALIZED_LOCAL_PLACEMENT | 0.391856194 |
| u_protected_memory.u_ecc/rstb | IDEALIZED_LOCAL_PLACEMENT | 0.223931819 |
| u_protected_memory.u_ecc/rstb | LEGALIZED_LOCAL_PLACEMENT | 0.225908533 |
| u_data/rstb | IDEALIZED_LOCAL_PLACEMENT | 0.397579819 |
| u_data/rstb | LEGALIZED_LOCAL_PLACEMENT | 0.395562857 |

## Decomposition and numerical checks

`slew ≈ threshold_ratio × NLDM(input_slew, Cpin(edge)+Cwire)`, with placement/coupling and distributed RC treated separately. SKY130HD tables describe 20–80% slew; SRAM22 describes 10–90%. The STA linear threshold-span conversion is 80/60 = 4/3. The script uses bilinear interpolation within the characterized table domain, prohibits extrapolation, and verifies the zero-wire values against standalone OpenSTA. The local effective resistance is d(t20–80)/dC / ln(4), in ohms, a first-order RC equivalent derived from the adjacent characterized load points; it is not a transistor measurement. The CSV includes 16 bounded table diagnostics, 24 STA conditions, three extracted observations, and six local-placement conditions, with evidence labels. The JSON contains all actual STA and placement observations, full source hashes, and physical locations.

An idealized zero-wire table is not a universal lower bound on distributed-RC STA: effective capacitance and waveform treatment can change the tool result. The observed post-route buf16 data slew is slightly lower than the simple lumped table estimate; neither result is substituted for the other.

## SPICE and constraint provenance

The frozen transistor-level netlists were inspected recursively along the directly connected rstb net. The JSON lists control, address/control-register and column-periphery branches and all reached primitive terminals. This proves connectivity, not capacitance accuracy. No SPICE transient, extracted internal RC simulation, or Liberty regeneration was performed. Both rstb pins explicitly specify max_transition=0.351 ns and retain the same characterization ceiling. No new evidence invalidates that constraint. It is independent of the SRAM output default_max_transition=0.04 ns inconsistency.

## Claim disposition and remaining work

Proven: heavy data rstb pin load; exact reproduction of the U0/E0 seed-11 failure and ECC closure; zero-wire and locally placed strongest-family diagnostics; no standard-cell-model-only tested repair closes data rstb. Unproven: impossibility for every legal SKY130HD topology, internal macro parasitic accuracy, and invalidity of the 0.351 ns limit. Classifications A/B/C are therefore not asserted. Historical five-seed setup/hold-clean pairs remain 5/5 and external DRV-clean pairs remain 0/5; these bounded new diagnostics are seed-independent tiny netlists or seed-11 ODB experiments, not a new five-seed physical repair.

All rstb experiments use UPSTREAM_ORIGINAL Liberty. Phase-A output-constraint diagnostic copies do not alter rstb pin caps, tables, or max_transition. PPA/energy/reliability/carbon/GREEN ranking changes are NOT_MEASURED for these interface diagnostics; there is no retained production repair. The ISCAS analysis may use qualified physical baselines with residual DRV visible. No new signoff, energy, or interleaving claims are introduced.

Recommended next action: obtain independent rstb capacitance/transition characterization with stimulus and internal extraction provenance. A broader interface impossibility claim requires a defined legal topology space and an established bound, not another blind sweep.

## Reproduction and integrity

`python scripts/rstb_characterize.py --prepare`; run `scripts/rstb_run_diagnostics.sh <repository-root>` and `scripts/rstb_run_local.sh <repository-root>` with the frozen Docker image; then `python scripts/rstb_characterize.py`. Shell runners refuse to overwrite raw logs and mount the entire repository read-only in Docker. All ODB edits are transient in memory. The initial missing-technology invocation and filler-overlap attempt are retained as explicitly failed exploratory logs; completed runs use standalone STA or remove fillers only in memory. The campaign root records protected-baseline verification and repository regressions. Source SHA-256 values in this phase were recomputed from the frozen files.
