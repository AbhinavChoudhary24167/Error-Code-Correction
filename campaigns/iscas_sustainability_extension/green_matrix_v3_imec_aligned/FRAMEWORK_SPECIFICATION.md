# Framework specification

## Scientific contract

GREEN Matrix 3.0 separates model structure, parameter value, and evidence
status.  A validated equation does not validate its inputs.  A missing included
term remains unavailable; an excluded term, an explicit zero, a bound, a
parameter, and a measurement are distinct states.

Reliability is a hard feasibility gate, not a weighted score.  With thresholds
provided by the workload/SLA owner, the feasible set is

`F = {a | SDC_a <= theta_SDC, DUE_a <= theta_DUE, latency_a <= theta_L, throughput_a >= theta_T}`.

No universal threshold is embedded.  Within `F`, the framework compares
physical quantities, CSCI/CSCI_bit where qualified, fixed-baseline MRCC, and
exact Pareto fronts.  No arbitrary composite weight is primary.

## Linked matrices

`M_P` is keyed by observation record and design.  It contains architecture,
ECC metadata, node/route/compiler/implementation, interleaving, workload,
policy, fault-control identity, PVT, area, activity diagnostics, latency,
throughput, and conditional logical outcomes.  It contains no lifecycle carbon
and no GREEN score.

`M_E` is keyed by quantity ID and points to an `M_P` entity.  It records value,
unit, source, source type, implementation/experiment hashes, technology, PVT,
workload, measurement/model boundary, tier, evidence kind, uncertainty,
citation/version, qualification, and blocking reason.

`M_S` is keyed by translation ID and design.  It maps a design into independent
fab, manufacturing-grid, use-grid, lifetime, allocation, and system-boundary
scenarios.  It preserves Scope 1, Scope 2, declared upstream components, mask
NRE, packaging, operation, lifecycle carbon, service count, and CSCI as separate
fields.  A new grid or manufacturing inventory rebuilds `M_S` without rerunning
RTL/PnR; new physical observations rebuild `M_P` without changing carbon
equations.

`GREEN_MATRIX_V3_VIEW` is a publication convenience produced by joining the
three matrices.  It is never edited directly.

## Design-space axes

The sparse relational implementation represents `G[A,N,F,I,W,P,G,L,M]`:

- `A`: architecture/ECC;
- `N`: technology and process route;
- `F`: physical fault environment/topology;
- `I`: logical-to-physical interleaving;
- `W`: workload/activity;
- `P`: scrub/retry/service policy;
- `G`: fab, manufacturing-grid, and use-grid scenarios;
- `L`: lifetime and use intensity;
- `M`: observed or derived metric.

## Extension contracts

A new ECC is a registry record plus its observations and evidence.  The schema
supports payload/codeword/parity bits, correction/detection capability, decoder,
pipeline, initiation interval, latency, encoder, and decoder cost.

A new technology points to a process route, wafer geometry, metal/patterning
metadata, inventories, yield model, fab scenario, and sources.  Node names never
generate coefficients or yield implicitly.

A new interleaver must separately provide the physical coordinate-to-logical
bit-to-codeword/bank/word/symbol mapping and its controller area, routing,
wirelength, energy, latency, codeword-bit spacing, and event redistribution.
A bijection alone is not a physical implementation.

A new SRAM compiler is identified on each `M_P` observation; its geometry,
PVT, implementation hash, and evidence are independent of other compilers.

A new environmental category is a metric-registry entry and translation table;
water, materials, waste, and resource depletion do not enter carbon-specific
CSCI.

## Output and compatibility

All v3 behavior is additive under this directory.  ESII, NESII, legacy GREEN
Score, GSE, and GCI retain their historical implementations and are classified
`LEGACY_OR_COMPARISON_METRIC`.  No existing JSON/CSV field or default CLI output
is changed.
