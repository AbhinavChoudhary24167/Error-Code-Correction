# ISCAS methodology summary: GREEN Matrix v3.2

Schema version: `3.2.0`

Campaign commit: `29f20b196e04c713f88fd1a93440a2ff47986f06`

Parent campaign commit: `1f6bcd009e7a05ebcde35a3272161a9a81ec7bf7`

Generation date: `2026-09-08`

## Problem and gap

Semiconductor reliability/sustainability optimization commonly combines
quantities with radically different evidence quality. Open-PDK research flows
may lack the physical event occurrence, bitcell mapping, activity-complete
energy, and manufacturing inventory required for absolute decisions; replacing
them with logical injection frequency or transferred literature values creates
unsupported precision.

## Methodology and contribution

GREEN Matrix v3.2 represents each architecture/scenario as the vector
`[reliability consequence, operational resource consequence, physical
implementation cost, lifecycle consequence, evidence quality]`. Every operand
is carried by `M_E`; `M_P` contains implementation consequences; and `M_S`
returns `QUALIFIED`, `CONDITIONAL`, `DIAGNOSTIC`, or `BLOCKED` plus a blocking
set. Qualification checks tier and technology, process, PVT, measurement
boundary, workload/activity, architecture, spatial mapping, and lifecycle
compatibility. A high tier cannot override a boundary mismatch.

Contributions:

- executable guards separating event occurrence from conditional response;
- exact U0/E0 conditional response surfaces for four declared logical mask classes;
- exact diagnostic, conditional-scenario, and qualified-or-blocked Pareto objects;
- `SCENARIO_SPACE_NONDOMINANCE_FRACTION`, explicitly not a physical probability;
- an auditable all-of criterion for E5 activity completeness;
- dependency-traceable evidence records and fail-closed decision admissibility.

## Demonstration and result

The demonstration reuses the frozen v3.1 U0/E0 five-seed matched physical
population. It establishes conditional logical-response tradeoffs and E4
diagnostic implementation summaries. It does not establish E5 energy, a routed
I1/I2 interleaver, physical event rates, absolute SDC/DUE/FIT, Qcrit, SKY130
manufacturing/lifecycle carbon, CSCI/MRCC, a qualified sustainability front, or
a global winner. Final classification: `GREEN_MATRIX_V3_2_EVIDENCE_AWARE_DECISION_MODEL_CONDITIONAL_FRONT_VALIDATED_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED`.

## Claim-to-evidence map

| Claim | Required evidence | Current status |
|---|---|---|
| Conditional ECC response | Exact logical patterns and decoder outcome | E3 `CONDITIONAL` |
| Implementation tradeoff | Matched routed U0/E0 population | E4 `DIAGNOSTIC` |
| Operation energy | Complete matched activity and isolated service window | `BLOCKED`, E4 only |
| Physical SDC/DUE/FIT | Matched event rate/PMF and verified spatial map | `BLOCKED` |
| Interleaver physical benefit | Routed I1/I2 plus verified topology map | `BLOCKED` |
| SKY130 manufacturing carbon | Matched manufacturing inventory/boundary | `BLOCKED` |
| CSCI/MRCC | Qualified reliability, energy, lifecycle, and lifetime operands | `BLOCKED` |
| Qualified sustainability front/global winner | Every declared mandatory dimension qualified | `BLOCKED` |

## Limitations and threats to validity

The logical mask classes are not measured physical topology distributions.
Vectorless power and partial-annotation energy are tool diagnostics with
residual v3.1 limitations. The finite scenario set is researcher-declared and
its uniform counting measure is not epistemic confidence. Macro dimensions and
SPICE instance counts do not establish bitcell XY or adjacency. Literature
records are technology/process/geometry mismatches. Manufacturing and lifetime
boundaries are incomplete. These limitations are encoded as guards rather than
hidden through imputation.

## Figure specification

```text
Physical Event Source [BLOCKED]
        |  M_E gate
        v
Topology / Physical Mapping [BLOCKED]
        |  M_E gate
        v
Logical Corruption [ANALYTICAL]
        |  M_E gate
        v
ECC + Interleaving Response [CONDITIONAL]
        |  M_E gate
        v
Service Outcome [CONDITIONAL]
        |  M_E gate
        v
Operational Cost [DIAGNOSTIC]
        |  M_E gate
        v
Lifecycle Scenario [BLOCKED]
```

Use solid green for measured, blue dashed for conditional, amber dotted for
diagnostic, and a red stop marker for blocked transitions. The sidecar
`data/FIGURE_SPECIFICATION.json` is the machine-readable source.

## Scientific principle

Unknown physical quantities remain unknown; exact conditional analysis is
reported only within its declared boundary. The method is informed by public
imec SSTS/imec.netzero bottom-up concepts, but no certification, compliance,
validation, standardization, endorsement, or SKY130 manufacturing datum from
imec is claimed.
