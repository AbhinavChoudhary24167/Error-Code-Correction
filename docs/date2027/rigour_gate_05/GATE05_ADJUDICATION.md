# DATE 2027 Gate 05 reliability x physical-cost integration

`GATE_05_CONDITIONAL_PASS`

| ECC / architecture | Reliability evidence / SDC | Weight-3 DUE | Area um2 | WNS ns | Fmax MHz | 10 ns | No-error power W | Achievable energy/op pJ | Wirelength um | DRC |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| Conventional SECDED (72,64), combinational | w1/w2 safe=1/1; w3 SDC=809/1065 | 256/1065 | 18644.100 | 0.000000 | 243.881000 | MEETS_10NS | 0.0145747940987 | 145.762515781 | 44609 | 0 |
| Conventional SECDED (72,64), pipelined | w1/w2 safe=1/1; w3 SDC=809/1065 | 256/1065 | 25486.900 | 0.000000 | 355.849000 | MEETS_10NS | 0.011074507609 | 110.756150598 | 49992 | 0 |
| Hsiao SECDED (72,64), combinational | w1/w2 safe=1/1; w3 SDC=2847/4970 | 2123/4970 | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | NOT_AVAILABLE_PHYSICAL_FAILURE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE |
| Shortened BCH (78,64,t=2), combinational syndrome/Chien | w1/w2 safe=1/1; w3 SDC=265/1463 | 1198/1463 | 57303.700 | -4.780520 | 67.656600 | FAILS_10NS | 0.848764657974 | TARGET_CLOCK_INFEASIBLE | 183332 | 0 |

The SDC and DUE entries are exhaustive **weight-3 observation-only** fractions. In every declared/proven weight-1/weight-2 support universe, modeled safe handling is 1/1 and SDC is zero. The table never treats weight-3 behavior as a correction guarantee or field-weighted rate.

## Identity adjudication

- Conventional combinational SECDED maps directly to the Gate 02 aggregate and Gate 03R exact RTL proof.
- Pipelined SECDED has the same proven code behavior as combinational SECDED through universal encoder/decoder equivalence, but retains an independent architecture and physical row.
- Hsiao maps directly to its Gate 02 aggregate plus two Gate 03 compiled functional campaigns; its Gate 04 PPA is unavailable.
- BCH maps from the Gate 02 reference to the exact Gate 03R RTL identity through the independent matrix reconstruction and all 3,082 symbolic weight-0/1/2 proof jobs.

## Operation normalization

`VALID_FOR_EQUIVALENT_STEADY_STREAM_USEFUL_OPERATION_COMPARISON`

Every power trace contains 100,000 asserted-valid comparison transactions at initiation interval one, preceded by six reset clocks and followed by four drain clocks. The four-cycle drain exceeds the pipelined SECDED boundary latency of three cycles. Both SECDED architectures therefore perform the same accepted steady-stream work over the same 1,000,100,000 ps trace. The energy comparison is valid for steady-stream throughput; it does not erase the pipelined architecture's nominal latency increase from one to three cycles.

## Supported cross-layer trade-offs

- Pipelined versus combinational SECDED: area +36.702%, Fmax +45.911%, detailed wirelength +12.067%, no-error power -24.016%, and achievable steady-stream energy/op -24.016%. Pipeline depth and nominal latency increase by two cycles; initiation interval stays at one.
- Evaluated BCH versus combinational SECDED: area +207.356%, detailed wirelength +310.975%, and Fmax -72.258%. BCH corrects the larger proven fault universe but fails the common 10 ns target.
- Hsiao's exhaustive weight-3 SDC fraction is lower than conventional SECDED's in the respective canonical-coordinate universes, but the missing PPA prevents a complete reliability-cost point.

## Missing and excluded evidence

- Hsiao physical dimensions are `PPA_UNAVAILABLE`; no values are fabricated and it is excluded from future full-dimensional PPA analysis.
- BCH diagnostic target-constraint power and energy estimates are preserved, but achievable 100 MHz energy is `TARGET_CLOCK_INFEASIBLE`.
- FIT, SER, operationally weighted SDC/DUE, and physical placement/interleaving effects are `METRIC_NOT_PROVEN`.
- Reliability-per-cost scalar ratios are not computed without a common physically weighted fault distribution. Formal Pareto analysis is deferred to Gate 06.

## Gate 05 verdict

`GATE_05_CONDITIONAL_PASS`

The exact identity join is defensible for all four implementations. Three architectures have complete physical rows, including BCH's scientifically meaningful timing failure, and Hsiao contributes only validated reliability evidence. The bounded Hsiao PPA absence prevents an unconditional pass but does not invalidate the principal cross-layer comparison.

## Gate 06 readiness

Gate 06 may use only the three complete PPA points for full-dimensional analysis and must retain Hsiao as reliability-only unless a separately authorized physical result exists. No Gate 06 analysis has been started.

`GATE_06_READY`
