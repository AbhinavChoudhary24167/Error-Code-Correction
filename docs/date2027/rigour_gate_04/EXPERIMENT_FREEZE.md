# GREEN-ECC Gate 04 experiment freeze

Status: **RESULT-BLIND FREEZE PREPARED**

Authorization basis: `SCIENTIFIC_ENVIRONMENT_READY_FORMAL_GATE_FAILED`. Gate 03E-R and Gate 03E-S remain formal failures; this freeze neither edits nor reinterprets them.

## Mandatory physical matrix

- Candidates: `secded-rtl-combinational-72-64-v1`, `secded-rtl-pipelined-72-64-v1`, `hsiao-generated-combinational-72-64-v1`, `shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1`
- Periods: 10.0 ns and 5.0 ns.
- Paired physical seeds: 11, 29, 47, 71, 101.
- Candidate flows: 40; width-matched boundary references: 20; total planned full flows: 60.
- Physical seed control: `GPL_RANDOM_SEED`, `GRT_SEED`, and `OR_SEED` are all assigned the matrix seed. The pinned-source proof is captured by the external freeze.
- Full official flow: synthesis, floorplan, placement, CTS, routing, extraction, post-route STA, final ODB/GDS/DEF/netlist/SDC/SPEF.

## Activity and power

Each no-error, single-error, and double-error trace uses the same frozen SplitMix64 sequence of exactly 100,000 useful 64-bit operations. Fault positions use the frozen width-normalized mapping in `contract_v1.json`. Post-route OpenSTA reads primary-input VCD activity, propagates it through the extracted design, reports direct annotation coverage and unannotated pins, and reports tool-estimated power. No field-rate average, silicon measurement, SRAM-macro energy, or total-system-energy claim is permitted.

## Statistics and hypotheses

All seed values, median, IQR, extrema, paired differences, effect sizes, and paired percentile-bootstrap 95% intervals are required. Bootstrap seed is 474104 with 20,000 resamples. The 5% materiality threshold and H1-H4 tests are frozen verbatim in `contract_v1.json` before any candidate flow.

## Result-blindness

The candidate matrix, flow matrix, wrapper/latency/fairness rules, scenario factors, evidence vocabulary, calculation rules, seed controls, hypotheses, and source-byte hashes are frozen before flow execution. A flow is never silently retried; another attempt requires a new directory and visible row. A missing mandatory candidate, seed mechanism, full stage, activity result, equivalence check, or provenance link fails closed.
