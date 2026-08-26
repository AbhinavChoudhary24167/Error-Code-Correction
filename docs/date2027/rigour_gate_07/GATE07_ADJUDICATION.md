# DATE 2027 Gate 07 adversarial claim adjudication

## A. Verdict

`GATE_07_PASS`

## B. DATE manuscript readiness

`DATE_MANUSCRIPT_READY`

No unresolved critical reviewer issue remains. Readiness means the evidence is safe to turn into a scoped six-page manuscript; it does not mean external novelty is proven or that submission is guaranteed acceptance.

## C. Three frozen contributions

1. Identity-preserving, fail-closed cross-layer evaluation of correctness-qualified implementations.
2. Quantified non-dominated microarchitectural trade-off between exact-equivalent SECDED implementations.
3. Implementation-scoped correction-versus-physical-feasibility contrast for the evaluated BCH design, with Hsiao missingness retained explicitly.

## D. Frozen claims

Claims C01, C02, and C04 are frozen. They cover the same-semantics SECDED trade-off, its recomputed effect sizes, and the evaluated BCH timing failure.

## E. Removed or narrowed claims

Claims C03, C05, and C06 are narrowed to the evaluated implementations and pinned environment. Hsiao W3 behavior is discussion-only. Practical-significance, FIT/SER, family-wide BCH frequency, Hsiao PPA dominance, achievable BCH target energy, and unique-best-ECC claims are removed.

## F. Energy-comparison verdict

`ENERGY_COMPARISON_VALID`

The 24.016% reduction is valid for equal 100,000-operation steady streams at 10 ns and II=1; it is not a latency improvement.

## G. Main reviewer risks

- External novelty positioning remains high risk because only repository-local notes were authorized.
- Hsiao PPA is unavailable under the unrelaxed frozen synthesis-memory policy.
- Physical breadth is limited to one technology/corner/target and three routed points.
- Reliability observations lack field weighting, FIT/SER, and physical SRAM mapping.

## H. Final figures

Freeze F01 and F02; revise F03 to separate all-routed physical metrics from timing-feasible SECDED-only power/energy; drop F04 under the six-page budget.

## I. Final tables

Freeze two major tables: evaluated implementations and compact physical/reliability results. Keep W3 counts in the reliability semantics artifact/discussion, not a major table.

## J. Final limitations

All mandatory technology, corner, implementation, target, Hsiao, BCH energy, OpenSTA, FIT/SER, field-weighting, W3-semantics, physical-memory, and sample-size limits are assigned to Setup, Results, or Discussion.

## K. Numerical audit result

`NUMERICAL_CLAIM_AUDIT_PASS` with zero mismatches. Every manuscript-visible effect size was regenerated from Gate 05 machine-readable raw values and cross-checked against Gate 06.

## L. Evidence completeness

All final claims, figure data, table rows, limitations, reviewer resolutions, and source identities are machine-readable and SHA-256 inventoried. No new measurement, physical run, RTL change, model change, excluded thesis subsystem, or optimizer was introduced.

## M. Gate 08 readiness

`GATE_08_READY`
