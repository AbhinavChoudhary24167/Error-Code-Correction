# Reviewer-style novelty and validity audit

## Evidence freeze

| Category | Status in this phase |
|---|---|
| Established coding theory | Conventional Hsiao odd-column SEC-DED, syndrome decoding, coordinate equivalence |
| Earlier SafeForge | Finite ambiguity solvers, risk certificates, abstaining RTL generation, scheduler gating, earlier heuristic 72-bit mapping |
| Genuinely new here | Unit-explicit system-FIT/tail conversion; exact finite syndrome-action robust compiler with constraint generation and TV decomposition; independent optimality replay; finite constrained placement library and strong sequential baseline |
| Synthetic evidence | All 427 optimization vectors and all three held-out evaluations |
| Literature-derived evidence | Five primary-source aggregate records; three existing structured ambiguity configurations |
| Raw experimental evidence | None ingested |
| Synthesis estimate | Prior generic Yosys/ABC structural counts only |
| Characterized/P&R/measured hardware | None for the decisive policy |

The main matrix is conventional Hsiao/SECDED. The prior “robust” 72-bit artifact and this phase’s placements preserve the column multiset, so they are not counted as new codes. Policy-only, placement-only, sequential, and joint effects are reported separately. The 427-vector universe is hashed; mass outside it is explicit. Every exact policy certificate binds the matrix, policy, placement, support, ambiguity, and source distribution identities, and says that the tail is not covered. The system budget separately binds the tail statement.

## Baseline adequacy

Seven requested roles are present, with one caveat:

1. conventional fixed placement plus conventional decoder;
2. conventional placement plus exact abstaining policy;
3. even/odd interleaving plus conventional decoder;
4. fault-aware placement plus conventional decoder;
5. placement-only collision isolation followed by exact policy compilation;
6. exact joint selection over the same placement library;
7. test-distribution-specialized oracle, explicitly nondeployable.

The conventional decoder is invariant across several column assignments on the nominal SBU/DBU mix, so baseline 4 ties at the conventional placement. Baseline 5 is the stronger comparison. It selects the same placement and result as joint design. This eliminates the proposed joint advantage rather than hiding it behind a weak sequential baseline.

## Certificate validity

All four emitted selected-policy files independently pass. For the primary point, the verifier uses the TV condition `epsilon < delta`, rebuilds every syndrome action from the fixed matrix and 427 vectors, confirms zero SDC loss, verifies primal/dual TV witnesses, and reproduces a zero gap. The proof is exact over 87 placements and the finite action representatives only. It is not global over `64!`, movable parity bits, arbitrary circuits, unbounded support, or a statistically unknown tail.

## External validity

The external evidence table now records raw-data availability, spatial resolution, required 72-bit transformation, lost information, sample-independence status, and licensing. No reusable bit-exact archive was found. Literature aggregate results cannot support held-out word-vector validation. Synthetic holdouts violate the SDC target, which strengthens the negative result but does not substitute for experiment.

## Hardware validity

The previous real tool runs demonstrate RTL executability on their own mappings. They do not establish mapped cell area, delay/slack, power, leakage, routing displacement, or controller overhead for the decisive interleaved policy. Generic cell counts are correctly retained as structural evidence. The requested characterized open flow remains unexecuted.

## Novelty assessment

The exact compiler and certificate structure are a meaningful methodological addition: the result is not merely a renamed Hsiao code or an undocumented lookup-table change. The intended positive empirical contribution is unsupported, however. A paper should be framed as a limit/negative study unless new evidence changes the gate.

## Decision

Reject the positive “substantial certified availability recovery” hypothesis for the evaluated domain. Preserve the exact compiler as infrastructure, freeze further decoder mechanisms, and prioritize the specified measurement campaign. Do not claim first, universal, globally optimal, production-ready, or top-tier.
