# Matched final-route comparison

Canonical seed 11 gives clean final detailed routes for U0 and E0 under the same PVT, RC, clock, density target, macro halo, IO rule, PDN, placement/resizer/legalization/CTS strategy and routing algorithms. It is classified `MATCHED_ROUTE_PASS_TIMING_LIMITED`: route, setup, hold, capacitance and antenna checks close, but U0/E0 retain 65/80 legitimate maximum-slew violations. Quantitative values are therefore preserved as a matched, extracted diagnostic comparison and are not promoted to a full timing-clean qualification.

| Metric | U0 | E0 | E0−U0 |
|---|---:|---:|---:|
| SRAM macro area (µm²) | 201,266.5968 | 260,331.5664 | +59,064.9696 (+29.3466%) |
| standard/physical-cell area (µm²) | 5,566.59 | 15,418.5 | +9,851.91 |
| total placed design area (µm²) | 206,833 | 275,750 | +68,917 (+33.3201%) |
| core area (µm²) | 439,734.24 | 615,627.936 | +175,893.696 (+40.0%) |
| die area (µm²) | 470,000 | 650,000 | +180,000 (+38.2979%) |
| whitespace (µm²) | 232,901.24 | 339,877.936 | +106,976.696 |
| achieved utilization | 47.0360% | 44.7917% | −2.2443 points |
| final wirelength (µm) | 22,186 | 79,745 | +57,559 (+259.4384%) |
| final vias | 1,084 | 6,686 | +5,602 (+516.7897%) |
| setup WNS / TNS (ns) | +4.46099 / 0 | +0.591127 / 0 | −3.869863 / 0 |
| worst hold slack (ns) | +0.0249489 | +0.000901557 | −0.024047343 |
| total vectorless power (mW) | 0.804510 | 1.97447 | +1.16996 (+145.4252%) |

The extra ECC macro is exactly 59,064.9696 µm². Attempt06 isolated 4,710.77 µm² of ECC logic at synthesis. The final-route non-macro displacement is 9,851.91 µm² because it additionally includes physical/tap, buffering, clock and route-repair cells; it must not be relabeled as pure Boolean ECC logic.

Final layer wirelength U0/E0 in µm is met1 436/22,384, met2 18,944/43,956, met3 137/6,431, met4 2,668/6,904 and met5 0/68. Global-route aggregate resource usage is 1.29%/3.31%, with zero final congestion for both. Timing-repair buffers are 156/551. U0 has no built clock tree for its single macro sink; E0 has three clock buffers and one inverter. Both reports say no launch/capture paths exist, so clock skew is `NOT_OBSERVABLE_NO_LAUNCH_CAPTURE_PATHS`, not a measured zero. Final path-specific target-clock latencies are 0.0021/0.0101 ns for U0 and 0.2847/0.4942 ns for E0.

The achieved common constrained frequency is 100 MHz. Diagnostic fmax is 180.538 MHz for U0 and 106.283 MHz for E0. Power is `COMPARATIVE_POST_ROUTE_TOOL_ESTIMATE`; energy/access is `NOT_QUALIFIED` because equivalent trustworthy activity annotation was not obtained.

Four of five seed pairs (11, 13, 19, 23) repeat clean route plus setup/hold closure. Seed 17 is route-clean but has two E0 hold violations; every seed retains maximum-slew violations. Thus ≥3 route-clean/setup-hold matched seeds close, while zero seeds satisfy the full timing/DRV gate.

The clean-route criterion concerns integration-generated geometry outside immutable SRAM22 internals. The SRAM22 macro internals retain the Attempt06 classification `DRC_NOT_INDEPENDENTLY_REPRODUCIBLE`; no foundry waiver or leaf-level signoff claim is made.
