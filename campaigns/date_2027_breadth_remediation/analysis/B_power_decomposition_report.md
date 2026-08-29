# Workstream B power decomposition

## Evidence join and reproduction

All 10 combinational/pipelined matched-seed records were hash-joined to their immutable run metadata, seed environment, final ODB and netlist, SDC, SPEF, primary-input VCD, power command, and full-precision OpenSTA report. Published total power and energy/op were reproduced exactly to the extraction tolerances. OpenSTA's independently accumulated displayed component/group rows close within the declared 1e-8 W bound; the exact residual is preserved per seed rather than treated as zero.

## Measured decomposition

Across the five paired seeds, pipelining changes internal power by 6.772352% on average (0/5 lower), switching power by -49.481332% (5/5 lower), leakage by 34.426794% (0/5 lower), total power by -23.419005% (5/5 lower), and reconstructed energy/op by -23.419005% (5/5 lower).

| Top-level component | Combinational mean (W) | Pipelined mean (W) | Mean paired effect | Pipelined lower |
|---|---:|---:|---:|---:|
| Internal | 0.0067533182 | 0.0072103837 | +6.772352% | 0/5 |
| Switching | 0.0078221049 | 0.0039514098 | -49.481332% | 5/5 |
| Leakage | 7.3002573e-9 | 9.8134363e-9 | +34.426794% | 0/5 |
| Total | 0.0145754306 | 0.0111618035 | -23.419005% | 5/5 |
| Energy/op (pJ) | 145.768881 | 111.629196 | -23.419005% | 5/5 |

The mean absolute switching change is -0.0038706951 W, while internal rises by 0.0004570655 W and leakage rises by 2.5131790e-9 W. Switching is therefore the largest absolute mean top-level contribution and numerically accounts for the total-power reduction.

OpenSTA cell groups reinforce, but do not causally explain, the decomposition: combinational-group total power falls by 55.496921% (5/5), whereas sequential-group total rises by 70.861003% (0/5 lower) and clock-group total rises by 74.337936% (0/5 lower). Exact per-seed and descriptive values are in the CSV and JSON outputs.

## Interpretation discipline

MEASURED: the component directions and magnitudes above come directly from the routed full-precision power reports.

SUPPORTED INTERPRETATION: the decomposition identifies which OpenSTA power component and cell group numerically account for the total difference.

HYPOTHESIS: glitch suppression or logic-depth effects may explain reduced switching, but the immutable primary-input-only VCD/report bundle does not preserve per-net activity evidence. Therefore no causal glitch-suppression claim is made.

`CLOCK_POWER = SEPARATELY_AVAILABLE_AS_OPENSTA_CLOCK_GROUP`

Register and clock-buffer/inverter subtypes are not separately reported beyond OpenSTA's Sequential and Clock groups; no unsupported subdivision is estimated.

All ten reconstructed totals and energy/op values match the qualified Revision-2 results. The maximum displayed top-level component residual is 9.2097309e-10 W and the maximum displayed cell-group residual is 5.7043510e-9 W, both within the declared 1e-8 W report-precision tolerance.
