# DATE 2027 Gate 04 final ECC physical characterization

`GATE_04_CONDITIONAL_PASS`

`GATE_05_READY`

| ECC implementation | Area um2 | Delta area | WNS ns | Fmax MHz | 10 ns? | No-error power W | Energy/op pJ | Detailed wire um | DRC | Status |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| secded-rtl-combinational-72-64-v1 | 18644.100 | +0.000% | 0.000000 | 243.881000 | MEETS_10NS | 0.0145747940987 | 145.762515781 | 44609 | 0 | PHYSICAL_CHARACTERIZATION_PASS_TIMING_MET |
| secded-rtl-pipelined-72-64-v1 | 25486.900 | +36.702% | 0.000000 | 355.849000 | MEETS_10NS | 0.011074507609 | 110.756150598 | 49992 | 0 | PHYSICAL_CHARACTERIZATION_PASS_TIMING_MET |
| hsiao-generated-combinational-72-64-v1 | N/A | N/A | N/A | N/A | NOT_AVAILABLE_PHYSICAL_FAILURE | N/A | N/A | N/A | N/A | PHYSICAL_CHARACTERIZATION_PARTIAL |
| shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1 | 57303.700 | +207.356% | -4.780520 | 67.656600 | FAILS_10NS | 0.848764657974 | 8488.495344400 (target estimate; timing infeasible) | 183332 | 0 | PHYSICAL_CHARACTERIZATION_PASS_TIMING_MISSED |

## A. Final ECC set

Four correctness-qualified implementations are included and 15 candidates are explicitly excluded. The included set is: secded-rtl-combinational-72-64-v1, secded-rtl-pipelined-72-64-v1, hsiao-generated-combinational-72-64-v1, shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1.

## B. Physical feasibility

Timing met: secded-rtl-combinational-72-64-v1, secded-rtl-pipelined-72-64-v1. Timing missed: shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1. Physical characterization unavailable after a preserved flow failure: hsiao-generated-combinational-72-64-v1. A timing miss remains valid physical data when the complete routed result is clean.

## C. Area hierarchy

Smallest to largest: secded-rtl-combinational-72-64-v1 < secded-rtl-pipelined-72-64-v1 < shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1.

## D. Timing hierarchy

Highest to lowest achieved Fmax: secded-rtl-pipelined-72-64-v1 > secded-rtl-combinational-72-64-v1 > shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1. Negative slack is retained without relaxation.

## E. Routing hierarchy

Lowest to highest detailed-route wirelength: secded-rtl-combinational-72-64-v1 < secded-rtl-pipelined-72-64-v1 < shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1. All reported DRC counts are preserved.

## F. Power hierarchy

For the no-error trace, lowest to highest total power: secded-rtl-pipelined-72-64-v1 < secded-rtl-combinational-72-64-v1 < shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1. Single- and double-error rows remain separate in the machine-readable outputs.

## G. Energy hierarchy

Energy uses the same per-class ordering as power because every trace has the same duration and useful-operation count. Values for a design that fails 10 ns are target-constraint diagnostics, not achievable 100 MHz energy.

## H. Effect sizes relative to SECDED

All raw values are retained. `GATE04_NORMALIZED_RESULTS.json` reports percent deltas relative to conventional combinational SECDED for area, cells, routing, achieved Fmax, and each separate power/activity class. Slack ratios are not computed.

## I. Results excluded from quantitative interpretation

Reference-only and correctness-rejected candidates are excluded from PPA. Any included implementation with `PHYSICAL_CHARACTERIZATION_PARTIAL` has no invented PPA values and is excluded from quantitative hierarchies. Energy for any `FAILS_10NS` design is not interpreted as achievable at 100 MHz. Native rounded OpenSTA JSON is not used for comparative extraction.

## J. Unexpected findings

Gate 03F error-class power equality was a serialization artifact: 12-digit text reports and direct VCD toggle counts resolve small differences. The Hsiao decoder also infers a 256x73 table that exceeds the unchanged ORFS `SYNTH_MEMORY_MAX_BITS=4096` policy, so no route or PPA is available for that implementation. No practical-significance claim is inferred from numerical resolution alone.

## Optional timing-normalized experiment

A separate common-relaxed-clock experiment would be scientifically useful only for claims requiring achievable energy for every timing-missed design. It is proposed but not executed; its period, identity, manifests, and run namespace must be frozen separately before use.

## K. Gate 04 verdict

`GATE_04_CONDITIONAL_PASS`

The four-run primary 10 ns matrix is complete under one common physical policy. Quantitative comparison uses only implementations with valid routed data; preserved partial results are explicitly bounded. The verdict applies only to these RTL implementations, SKY130HD, TT 1.80 V/25 C, and the frozen flow.

## L. Gate 05 readiness

`GATE_05_READY`
