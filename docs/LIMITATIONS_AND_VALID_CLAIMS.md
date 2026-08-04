# Limitations and valid claims

The documentation places limitations next to affected results because evidence class is part of the result.

## Evidence ceiling

The current multi-ECC study supports exact functional verification, explicit analytical sensitivity calculations, and limited generic structural evidence. It contains no physical characterization and no hardware measurement.

| Claim type | Current status | Reason |
|---|---|---|
| Registry and extension contract | Supported | Schemas, hash enforcement and external fixture pass |
| Declared decoder behavior | Supported per verified class | Exact mask enumeration and golden-data harness |
| Scenario-aware analytical recommendation | Conditionally supported | Changes across a preregistered grid using explicit model parameters |
| Structural complexity comparison | Supported as structural-only | Derived matrix/table counts and optional generic synthesis |
| Physical area/timing/power/energy | Not computable | Fields and technology context are null |
| Physical winner or proxy reversal | Not computable | Physical selector has zero eligible candidates |
| Actual adaptive break-even | Not computable | MUX/controller/transition/re-encoding costs are null |
| Hardware/silicon/radiation behavior | Unsupported | No measurement campaign enters evidence |

## Functional scope limitations

- Guarantees apply only to declared, tested universes and coordinate definitions.
- Correction and detection are different: detection/abstention avoids silent output but does not restore data.
- A native `CORRECTED` flag is not trusted without golden-data equality.
- Linear data-independence arguments apply only to the bound deterministic policy.
- Partially verified TAEC is a SECDED-capable implementation with a disproved adjacent-triple claim, not a verified TAEC code.
- The SEC-DAEC and cyclic-labelled candidates remain rejected even if a legacy family model assumes stronger coverage.

## Analytical scope limitations

- Fault profiles are uncalibrated sensitivity distributions, not measured SER or radiation spectra.
- Workloads are access-count/write-fraction abstractions, not traces.
- Energy per bit/XOR, leakage and scrub parameters are explicit analytical inputs.
- Operational carbon uses scenario grid intensity; implementation-specific embodied carbon is absent.
- Recommendation stability uses three deterministic scale tuples, not statistical sampling.
- Sensitivity scores are descriptive association within the grid, not causality.
- Winner identity is conditional on the hard limits, grid and lexicographic energy rule.

## Structural and physical limitations

Generic cells, XOR counts, table literals and depth proxies are not physical cell area, timing, power, routing or energy. Technology independence applies only to exact algebraic/structural counts, not to physical conclusions. A defensible physical comparison would need the same PDK/library/corner, timing constraints, activity/workload, memory macro context and complete MUX/controller/transition accounting.

![Physical evidence gap](figures/physical_evidence_gap.svg)

*Grey means unavailable/null, not zero. Data: [`figure_data/physical_evidence_gap.json`](figure_data/physical_evidence_gap.json).*

## Claims to avoid

Do not state that GREEN-ECC-PHY currently demonstrates a measured percentage energy/carbon saving, a physical PPA winner, an adaptive hardware break-even, technology-independent implementation superiority, silicon reliability, or radiation qualification. Do not cite historical 27% energy or 19% carbon reductions unless a future current pipeline reproduces them with traceable inputs.

Use the exact wording in the [Claim Ledger](CLAIM_LEDGER.md) when preparing a paper or thesis.
