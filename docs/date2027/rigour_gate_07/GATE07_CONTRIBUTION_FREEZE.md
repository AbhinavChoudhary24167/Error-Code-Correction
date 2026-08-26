# Gate 07 contribution freeze

Repository-local literature notes establish that Hsiao coding, adaptive/reconfigurable ECC, hardware-aware code/checker optimization, and generic reproducibility practices cannot be claimed as new. Those notes focus largely on excluded adaptive, co-synthesis, and SafeForge subsystems; they do not establish a priority claim for this narrowed post-route study. The manuscript must therefore avoid “first,” “unique,” and universal novelty wording.

## Novelty-role classification

| Proposition | Classification | Frozen treatment |
|---|---|---|
| Correctness-qualified implementation identities rather than nominal labels | METHODOLOGICAL_SUPPORT | Essential validity control, not claimed as an ECC theorem |
| Explicit separation of code semantics from RTL microarchitecture | PRIMARY_CONTRIBUTION | Controlled SECDED comparison plus identity transfer |
| Common post-route characterization | SECONDARY_CONTRIBUTION | Required empirical basis, not novel by itself |
| Reproducibility-qualified physical methodology | METHODOLOGICAL_SUPPORT | Bounded to the pinned flow and repetitions |
| Reliability × physical-cost interpretation without a composite score | PRIMARY_CONTRIBUTION | Categorical tiers and explicit missingness |
| Quantified same-semantics SECDED trade-off and stronger-correction BCH feasibility contrast | PRIMARY_CONTRIBUTION | Main empirical finding; implementation-scoped |

## Three frozen manuscript contributions

1. An identity-preserving cross-layer evaluation method that admits only correctness-qualified ECC implementations and keeps guarantees, observed outcomes, architecture, and missing physical data distinct.
2. A controlled post-route measurement showing that two exact-equivalent SECDED microarchitectures are non-dominated: pipelining trades area and two cycles of latency for higher achieved frequency and lower steady-stream energy per operation.
3. An implementation-scoped correction-versus-feasibility result: the evaluated W2-correcting BCH design incurs substantially greater routed cost and misses the shared 10 ns target, while Hsiao remains explicitly reliability-only under the frozen synthesis policy.

## Central message

**One sentence:** For the evaluated correctness-qualified 64-bit-payload ECCs, correction guarantees do not determine implementation choice: SECDED microarchitecture changes the area/latency–Fmax/energy trade-off, while the stronger-correcting BCH RTL incurs much larger routed cost and misses the common 10 ns target.

**Three sentences:** Correctness qualification establishes what each implementation protects, but it does not predict physical cost. Under one pinned SKY130HD flow, combinational and pipelined implementations of the same SECDED semantics occupy different non-dominated points, while the evaluated W2-correcting BCH implementation is larger, more routing-intensive, and timing-infeasible at 10 ns. A reviewer-safe ECC comparison must therefore preserve implementation identity, categorical reliability semantics, timing feasibility, and explicit missing data rather than collapse them into one score.

Local sources consulted: `docs/RESEARCH_NOVELTY.md`, `docs/PORTFOLIO_COSYNTHESIS_NOVELTY_GATE.md`, and `docs/SAFEFORGE_LITERATURE.md`. This is not a systematic external novelty review.
