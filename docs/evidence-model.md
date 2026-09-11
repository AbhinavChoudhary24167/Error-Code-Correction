# Evidence model

Evidence strength and evidence eligibility are different. A high-tier measurement can still be incompatible with a target metric because its workload, boundary, technology, or functional unit differs.

## Tiers

| Tier | Quantity represented | Typical source | Validation/failure condition | Final optimization use |
|---|---|---|---|---|
| E0 | Absent/unknown | No source | Required operand missing | Never |
| E1 | Parametric assumption | User scenario/config | Units/domain declared; fails if implicit or out of domain | Sensitivity/conditional analysis only |
| E2 | Published/model evidence | Cited external source | Native boundary and applicability recorded; fails on unsupported transfer | Conditional/model use only |
| E3 | Analytical, exact logical, or RTL evidence | Enumeration, equation, RTL regression | Reproducible source and declared universe; fails on counterexample or missing identity | Logical/analytical objectives only |
| E4 | Synthesis/PnR/tool estimate | Matched implementation reports | Tool/PDK/corner/constraint/provenance present; timing may still fail | Physical diagnostics within matching boundary |
| E5 | Matched activity-qualified post-route evidence | Routed netlist, parasitics, VCD, operation window | Coverage, operation count, hashes, and boundary pass; incomplete macro power limits scope | Qualified only for measured boundary |
| E6 | Independent cross-validation | Separate method/tool/dataset | Independence and boundary match established | Metric-specific |
| E7 | Silicon/fab measurement | Calibrated hardware/fab evidence | Traceable measured setup and uncertainty | Metric-specific; not present here |

The repository also uses general classes such as `exact_functional`, `analytical_model`, `structural_tool`, `physical_characterization`, `hardware_measurement`, and `unsupported`. These are compatible descriptions, not automatic tier promotions.

## Required fields

An evidence record should identify the quantity and unit; value/null state; architecture/implementation; source and source type; technology/PVT; workload/scenario; measurement/model boundary; seed or deterministic-not-applicable status; uncertainty; evidence tier; qualification status; allowed/forbidden uses; dependencies; and source hashes.

## Qualification rules

A quantity can participate in an analysis only when:

1. its producer passed the relevant functional and integrity gates;
2. its evidence tier and kind meet that analysis's minimum;
3. technology, PVT, workload, payload, service boundary, and units are compatible;
4. every required upstream operand is present;
5. its status permits the intended use;
6. the comparison is fair and all hard constraints pass.

Failure is explicit. The record remains available for diagnostics or historical audit but is excluded from claims that require more.

## Current examples

- The exact logical SBU/DBU response surfaces are E3. They provide `P(outcome | logical mask class, architecture)`, not an event rate.
- Routed area/timing and vectorless power in the matched population are E4 tool estimates. A completed GDS does not imply timing closure or signoff.
- The v3.3 records are E5 for post-route ECC logic under named operations. They do not include complete address/data/state-dependent SRAM macro-internal energy.
- Public semiconductor sustainability sources can be E2 for method/trend context but are not SKY130 manufacturing inventory.
- Silicon/radiation and node-native lifecycle evidence are absent here.

## Central rule

`available data != qualified evidence`

The implication is deliberate: a numeric field, plot, completed process, or higher tier elsewhere does not grant permission to use a quantity. Qualification is local to a defined metric and claim.
